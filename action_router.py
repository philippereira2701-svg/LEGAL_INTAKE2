import os
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ActionRouter:
    """
    Orchestrates automated responses to clients based on AI triage.
    """
    def __init__(self):
        # Twilio Configuration
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from = os.getenv("TWILIO_FROM_NUMBER")
        
        # Email Configuration
        self.gmail_user = os.getenv("GMAIL_ADDRESS")
        self.gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
        
        # Calendly link
        self.calendly_link = os.getenv("CALENDLY_LINK", "https://calendly.com/lawyer/consultation")

    def send_client_sms(self, phone: str, message: str):
        """Sends an SMS to the client via Twilio."""
        if not all([self.twilio_sid, self.twilio_token, self.twilio_from]):
            print("Warning: Twilio configuration missing. SMS not sent.")
            return

        client = Client(self.twilio_sid, self.twilio_token)
        try:
            client.messages.create(body=message, from_=self.twilio_from, to=phone)
            print(f"Sent SMS to client: {phone}")
        except Exception as e:
            print(f"Failed to send SMS to client: {e}")

    def send_client_email(self, email: str, subject: str, body: str):
        """Sends an email to the client via Gmail SMTP."""
        if not all([self.gmail_user, self.gmail_pass]):
            print("Warning: Gmail configuration missing. Email not sent.")
            return

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.gmail_user
        msg['To'] = email

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.gmail_user, self.gmail_pass)
                server.send_message(msg)
            print(f"Sent email to client: {email}")
        except Exception as e:
            print(f"Failed to send email to client: {e}")

    def route_action(self, lead: dict):
        """
        Executes the appropriate client communication based on AI recommendation.
        """
        action = lead.get('recommended_action')
        client_name = lead.get('client_name')
        client_phone = lead.get('client_phone')
        client_email = lead.get('client_email')

        if action == "AUTO_BOOK":
            # Immediate high-value outreach
            sms_body = (
                f"Hello {client_name}, we've reviewed your case details and believe we can help. "
                f"Please use this link to book a priority consultation with our team: "
                f"{self.calendly_link}"
            )
            if client_phone:
                self.send_client_sms(client_phone, sms_body)
            
            email_subject = "Action Required: Priority Consultation for Your Legal Claim"
            email_body = (
                f"Dear {client_name},\n\n"
                f"Thank you for contacting our firm. We have prioritized your case for immediate review. "
                f"One of our attorneys would like to speak with you as soon as possible.\n\n"
                f"Please schedule your free consultation using this link: {self.calendly_link}\n\n"
                f"We look forward to speaking with you."
            )
            if client_email:
                self.send_client_email(client_email, email_subject, email_body)

        elif action == "SOFT_REJECT":
            # Polite automated decline
            email_subject = "Update regarding your legal inquiry"
            email_body = (
                f"Dear {client_name},\n\n"
                f"Thank you for reaching out to us. After carefully reviewing the details of your "
                f"incident, we are unable to take on your case at this time. Our decision is based on "
                f"our current caseload and specific case criteria.\n\n"
                f"We recommend you consult with another attorney as soon as possible, as legal "
                f"deadlines may apply to your claim.\n\n"
                f"Sincerely,\nThe Legal Intake Team"
            )
            if client_email:
                self.send_client_email(client_email, email_subject, email_body)

        else: # MANUAL_REVIEW
            # Standard "we've received it" messaging
            email_subject = "We have received your legal intake"
            email_body = (
                f"Dear {client_name},\n\n"
                f"Thank you for submitting your case details. A member of our legal team is "
                f"currently reviewing your information. We will contact you within 24-48 hours "
                f"with next steps.\n\n"
                f"Sincerely,\nThe Legal Intake Team"
            )
            if client_email:
                self.send_client_email(client_email, email_subject, email_body)

if __name__ == "__main__":
    # Test routing logic
    router = ActionRouter()
    test_lead = {
        "client_name": "Test User",
        "client_phone": "555-0199",
        "client_email": "test@user.com",
        "recommended_action": "AUTO_BOOK"
    }
    # router.route_action(test_lead)
