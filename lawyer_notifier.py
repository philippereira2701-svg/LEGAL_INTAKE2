import os
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from twilio.rest import Client
from dotenv import load_dotenv
from logger import logger

# Load environment variables
load_dotenv()

class LawyerNotifier:
    """
    Handles multi-channel notifications for high-priority leads.
    """
    def __init__(self):
        # Email Config
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.email_user = os.getenv("SMTP_USER")
        self.email_pass = os.getenv("SMTP_PASS")
        self.lawyer_email = os.getenv("LAWYER_EMAIL", "lawyer@legalprj.com")

        # Twilio Config
        self.twilio_sid = os.getenv("TWILIO_SID")
        self.twilio_token = os.getenv("TWILIO_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE")
        self.lawyer_phone = os.getenv("LAWYER_PHONE")

    def notify_lawyer(self, lead_data):
        """Dispatches email and SMS for high-tier leads."""
        if lead_data.get('ai_score', 0) >= 8:
            logger.info(f"NOTIFICATION | High Priority Lead detected for LEGAL_PRJ: {lead_data['client_name']}")
            self._send_email(lead_data)
            self._send_sms(lead_data)
        else:
            logger.info(f"NOTIFICATION | Regular Lead: {lead_data['client_name']} queued.")

    def _send_email(self, lead_data):
        if not all([self.smtp_server, self.email_user, self.email_pass]):
            logger.warning("SMTP Config missing. Email suppressed.")
            return

        msg_body = f"""
        LEGAL_PRJ | URGENT HIGH-PRIORITY LEAD
        ------------------------------------
        Client: {lead_data['client_name']}
        Phone: {lead_data['client_phone']}
        Email: {lead_data['client_email']}
        
        AI Score: {lead_data['ai_score']}/10
        AI Summary: {lead_data['ai_summary']}
        
        Recommended Action: {lead_data['recommended_action']}
        """
        
        msg = MIMEText(msg_body)
        msg['Subject'] = f"LEGAL_PRJ | High Priority: {lead_data['client_name']}"
        msg['From'] = self.email_user
        msg['To'] = self.lawyer_email

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_pass)
                server.send_message(msg)
            logger.info(f"EMAIL SENT | To:{self.lawyer_email}")
        except Exception as e:
            logger.error(f"EMAIL ERROR | {str(e)}")

    def _send_sms(self, lead_data):
        if not all([self.twilio_sid, self.twilio_token, self.twilio_phone, self.lawyer_phone]):
            logger.warning("Twilio Config missing. SMS suppressed.")
            return

        try:
            client = Client(self.twilio_sid, self.twilio_token)
            message = client.messages.create(
                body=f"LEGAL_PRJ URGENT: {lead_data['client_name']} (Score: {lead_data['ai_score']}/10) needs counsel immediately.",
                from_=self.twilio_phone,
                to=self.lawyer_phone
            )
            logger.info(f"SMS SENT | SID:{message.sid}")
        except Exception as e:
            logger.error(f"SMS ERROR | {str(e)}")
