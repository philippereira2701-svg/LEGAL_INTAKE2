import os
import json
import uuid
import logging
from typing import Dict, Any
from celery import Celery, chain
import google.generativeai as genai
from twilio.rest import Client as TwilioClient
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import SessionLocal, DatabaseManager, Lead, Tenant
from rule_engine import RuleEngine

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)

# --- AUTO-FALLBACK FOR REDIS ---
try:
    # Test connection
    import redis
    r = redis.from_url(REDIS_URL)
    r.ping()
except Exception:
    logger.warning("Redis not found. Enabling Celery Eager Mode (tasks will run synchronously).")
    celery.conf.update(
        task_always_eager=True,
        task_eager_propagates=True
    )

# External API Configuration
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM_NUMBER")
GMAIL_USER = os.getenv("GMAIL_ADDRESS")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5000")

@celery.task(bind=True, max_retries=3)
def process_intake_task(self, tenant_id: str, form_data: Dict[str, Any]):
    """Master task to process a new lead intake"""
    session = SessionLocal()
    db = DatabaseManager(session)
    re = RuleEngine()
    tenant_uuid = uuid.UUID(tenant_id)

    try:
        # 1. Rule Engine Pre-processing
        result = re.process(form_data)
        
        if not result['is_disqualified']:
            # 2. Gemini AI Analysis
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            Analyze this legal intake for a personal injury law firm.
            
            Description: {form_data['incident_description']}
            
            Return ONLY a JSON object with these keys:
            - ai_score: integer 1-10
            - ai_tier: "LOW", "MEDIUM", "HIGH"
            - ai_summary: one sentence summary
            - liability_score: 1-10
            - damages_score: 1-10
            - sol_score: 1-10
            - red_flags: list of strings
            - recommended_action: "BOOK_NOW", "STAFF_REVIEW", "REJECT"
            """
            
            response = model.generate_content(prompt)
            # Basic parsing (improve with regex if needed)
            ai_data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
            
            # 3. Apply Modifiers
            final_score = re.apply_modifiers(ai_data['ai_score'], form_data)
            
            # Merge results
            result.update(ai_data)
            result['final_score'] = final_score
            result['rule_engine_score'] = ai_data['ai_score'] # Or some other logic
        
        # 4. Persistence
        lead = db.insert_lead(tenant_uuid, form_data, result)
        db.log_event(lead.id, tenant_uuid, 'scored', result)
        
        # 5. Chain notifications
        chain(
            notify_client_task.s(str(lead.id), tenant_id),
            notify_lawyer_task.s(str(lead.id), tenant_id)
        ).apply_async()

        return str(lead.id)

    except Exception as e:
        logger.error(f"Error processing intake: {str(e)}")
        session.rollback()
        raise self.retry(exc=e, countdown=60)
    finally:
        session.close()

@celery.task(bind=True, max_retries=3)
def notify_client_task(self, lead_id: str, tenant_id: str):
    """Send automated response to the client based on score"""
    session = SessionLocal()
    db = DatabaseManager(session)
    lead_uuid = uuid.UUID(lead_id)
    tenant_uuid = uuid.UUID(tenant_id)
    
    lead = db.get_lead_by_id(lead_uuid, tenant_uuid)
    tenant = session.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    
    if not lead or not tenant:
        return

    try:
        score = lead.final_score
        message = ""
        channel = "email"
        
        if score >= 8:
            channel = "sms"
            message = f"Hello {lead.client_name}, we have reviewed your inquiry regarding your injury. Based on the details, we'd like to speak with you immediately. Please book a time here: {tenant.calendly_link}"
            if lead.client_phone:
                client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
                msg = client.messages.create(body=message, from_=TWILIO_FROM, to=lead.client_phone)
                db.log_communication(lead_uuid, tenant_uuid, 'sms', lead.client_phone, 'client', message)
                db.update_communication_status(None, 'sent', msg.sid) # Need to handle comm_id better
        
        elif score >= 5:
            message = f"Dear {lead.client_name}, thank you for contacting {tenant.firm_name}. An attorney is currently reviewing your case details and will follow up with you within 24 hours."
            send_email(lead.client_email, f"Inquiry Received - {tenant.firm_name}", message)
            db.log_communication(lead_uuid, tenant_uuid, 'email', lead.client_email, 'client', message, f"Inquiry Received - {tenant.firm_name}")
            
        else:
            message = f"Dear {lead.client_name}, thank you for reaching out to us. After a preliminary review, we are unable to take your case at this time. We recommend contacting your local bar association for a referral."
            send_email(lead.client_email, f"Case Status Update - {tenant.firm_name}", message)
            db.log_communication(lead_uuid, tenant_uuid, 'email', lead.client_email, 'client', message, f"Case Status Update - {tenant.firm_name}")

        db.log_event(lead_uuid, tenant_uuid, f'{channel}_sent', {"score": score})

    except Exception as e:
        logger.error(f"Error notifying client: {str(e)}")
        if self.request.retries == self.max_retries:
            db.log_event(lead_uuid, tenant_uuid, 'notification_failed', {"error": str(e)}, success=False)
        raise self.retry(exc=e, countdown=120)
    finally:
        session.close()

@celery.task(bind=True)
def notify_lawyer_task(self, lead_id: str, tenant_id: str):
    """Notify the lawyer about a new lead or notification failure"""
    session = SessionLocal()
    db = DatabaseManager(session)
    lead_uuid = uuid.UUID(lead_id)
    tenant_uuid = uuid.UUID(tenant_id)
    
    lead = db.get_lead_by_id(lead_uuid, tenant_uuid)
    tenant = session.query(Tenant).filter(Tenant.id == tenant_uuid).first()
    
    if not lead or not tenant:
        return

    try:
        score = lead.final_score
        detail_url = f"{DASHBOARD_URL}/leads/{lead.id}"
        
        if score >= 8:
            # Urgent SMS
            message = f"URGENT {score}/10 - {lead.client_name}. {lead.ai_summary[:50]}. Lib:{lead.liability_score} Dam:{lead.damages_score}. Client SMS sent. Dashboard: {detail_url}"
            if tenant.lawyer_phone:
                client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
                client.messages.create(body=message, from_=TWILIO_FROM, to=tenant.lawyer_phone)
                db.log_communication(lead_uuid, tenant_uuid, 'sms', tenant.lawyer_phone, 'lawyer', message)
        
        # Always send email summary for score >= 5
        if score >= 5:
            subject = f"New High-Value Lead: {lead.client_name} ({score}/10)"
            body = f"A new lead has been scored {score}/10.\n\nSummary: {lead.ai_summary}\nRed Flags: {', '.join(lead.red_flags)}\n\nView details: {detail_url}"
            send_email(tenant.lawyer_email, subject, body)
            db.log_communication(lead_uuid, tenant_uuid, 'email', tenant.lawyer_email, 'lawyer', body, subject)

        db.log_event(lead_uuid, tenant_uuid, 'lawyer_notified', {"score": score})

    except Exception as e:
        logger.error(f"Error notifying lawyer: {str(e)}")
    finally:
        session.close()

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Retry failed communications every 15 minutes
    sender.add_periodic_task(900.0, retry_failed_communications_task.s(), name='retry-failed-comms')

@celery.task
def retry_failed_communications_task():
    """Scan and retry failed communications"""
    session = SessionLocal()
    # This would need a way to iterate through tenants or a global query
    # For MVP, let's assume we query all failed comms with attempt_count < 3
    failed_comms = session.query(DatabaseManager.Communication).filter(
        DatabaseManager.Communication.status == 'failed',
        DatabaseManager.Communication.attempt_count < 3
    ).all()
    
    for comm in failed_comms:
        # Re-dispatch based on channel
        logger.info(f"Retrying communication {comm.id}")
        # Implementation details omitted for brevity but should call send_email/twilio again
    session.close()

def send_email(to_email: str, subject: str, body: str):
    """Helper to send email via SMTP"""
    if not GMAIL_USER or not GMAIL_PASS:
        logger.warning("Email credentials missing, skipping send")
        return

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
