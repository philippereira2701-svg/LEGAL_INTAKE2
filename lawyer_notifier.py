import os
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LawyerNotifier:
    """
    Automated notification system to alert the lawyer of high-value leads.
    """
    def __init__(self):
        # Twilio Configuration
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from = os.getenv("TWILIO_FROM_NUMBER")
        self.lawyer_phone = os.getenv("LAWYER_PHONE")

        # Email Configuration
        self.gmail_user = os.getenv("GMAIL_ADDRESS")
        self.gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
        self.lawyer_email = os.getenv("LAWYER_EMAIL")
        
        # Dashboard URL
        self.dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:5000")

    def send_sms(self, lead: dict):
        """Sends an urgent SMS notification via Twilio."""
        if not all([self.twilio_sid, self.twilio_token, self.twilio_from, self.lawyer_phone]):
            raise ValueError("Twilio credentials missing.")

        client = Client(self.twilio_sid, self.twilio_token)
        
        red_flags = lead.get('red_flags', '[]')
        if isinstance(red_flags, str):
            red_flags = json.loads(red_flags)
        red_flags_str = ", ".join(red_flags) if red_flags else "None"

        body = (
            f"URGENT HIGH-VALUE LEAD — {lead['client_name']} scored {lead['ai_score']}/10.\n"
            f"Incident: {lead['ai_summary'][:50]}...\n"
            f"L: {lead['liability_score']} | D: {lead['damages_score']} | SOL: {lead['sol_score']}.\n"
            f"Red flags: {red_flags_str}.\n"
            f"Client sent Calendly. Call ASAP.\n"
            f"View: {self.dashboard_url}/lead/{lead.get('id', '')}"
        )

        message = client.messages.create(
            body=body,
            from_=self.twilio_from,
            to=self.lawyer_phone
        )
        return message.sid

    def send_email(self, lead: dict):
        """Sends a professional review email via Gmail SMTP."""
        if not all([self.gmail_user, self.gmail_pass, self.lawyer_email]):
            raise ValueError("Gmail credentials missing.")

        red_flags = lead.get('red_flags', '[]')
        if isinstance(red_flags, str):
            red_flags = json.loads(red_flags)
        red_flags_str = ", ".join(red_flags) if red_flags else "None"

        subject = f"Review Required — New Lead Scored {lead['ai_score']}/10"
        body = (
            f"A new lead requires your review.\n\n"
            f"Client: {lead['client_name']}\n"
            f"Summary: {lead['ai_summary']}\n\n"
            f"Pillar breakdown:\n"
            f"- Liability: {lead['liability_score']}/10\n"
            f"- Damages: {lead['damages_score']}/10\n"
            f"- Statute of Limitations: {lead['sol_score']}/10\n\n"
            f"Red flags identified: {red_flags_str}\n"
            f"Recommended action: {lead['recommended_action']}\n\n"
            f"Please log in to your dashboard to make a decision:\n"
            f"{self.dashboard_url}"
        )

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.gmail_user
        msg['To'] = self.lawyer_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(self.gmail_user, self.gmail_pass)
            server.send_message(msg)

    def notify_lawyer(self, lead_data: dict):
        """
        Determines the appropriate notification channel based on lead score.
        """
        score = lead_data.get('ai_score', 0)
        
        try:
            if score >= 8:
                print(f"Sending urgent SMS for lead score {score}...")
                self.send_sms(lead_data)
                return True
            elif score >= 5:
                print(f"Sending review email for lead score {score}...")
                self.send_email(lead_data)
                return True
            else:
                print(f"Lead score {score} too low for automated lawyer notification.")
                return False
        except Exception as e:
            # Log failure but do not crash the main program
            log_msg = f"{datetime.utcnow()} - ERROR notifying lawyer for lead {lead_data.get('id')}: {str(e)}\n"
            with open("intake_log.txt", "a") as f:
                f.write(log_msg)
            print(f"Notification error: {e}")
            return False

if __name__ == "__main__":
    # Test notification logic
    notifier = LawyerNotifier()
    test_lead = {
        "client_name": "Test Client",
        "ai_score": 9,
        "ai_summary": "Test summary of the incident.",
        "liability_score": 10,
        "damages_score": 10,
        "sol_score": 10,
        "red_flags": "[]",
        "recommended_action": "AUTO_BOOK"
    }
    notifier.notify_lawyer(test_lead)
