import os
from twilio.rest import Client
from dotenv import load_dotenv
from logger import logger

# Load environment variables
load_dotenv()

class ActionRouter:
    """
    Orchestrates automated workflows for LEGAL_PRJ based on lead quality.
    """
    def __init__(self):
        # Twilio Config for automated follow-up
        self.twilio_sid = os.getenv("TWILIO_SID")
        self.twilio_token = os.getenv("TWILIO_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE")

    def route_action(self, lead_data):
        """
        Executes the specialized workflow for the lead.
        """
        action = lead_data.get('recommended_action', 'MANUAL_REVIEW')
        logger.info(f"ROUTING | Lead:{lead_data['client_name']} | Action:{action}")

        if action == "AUTO_BOOK":
            self._trigger_immediate_followup(lead_data)
        elif action == "MANUAL_REVIEW":
            self._notify_paralegal_queue(lead_data)
        elif action == "SEND_REJECTION":
            self._send_soft_rejection(lead_data)

    def _trigger_immediate_followup(self, lead_data):
        """Sends an immediate 'Golden Minute' confirmation text to the client."""
        if not all([self.twilio_sid, self.twilio_token, self.twilio_phone]):
            logger.warning("Twilio suppressed for Follow-up.")
            return

        try:
            client = Client(self.twilio_sid, self.twilio_token)
            message = client.messages.create(
                body=f"Hello {lead_data['client_name']}, an attorney from LEGAL_PRJ has been matched to your case. We will call you shortly.",
                from_=self.twilio_phone,
                to=lead_data['client_phone']
            )
            logger.info(f"AUTO-FOLLOWUP SENT | Client:{lead_data['client_name']}")
        except Exception as e:
            logger.error(f"AUTO-FOLLOWUP ERROR | {str(e)}")

    def _notify_paralegal_queue(self, lead_data):
        # Simulated webhook to CRM
        logger.info(f"CRM | Lead {lead_data['client_name']} pushed to MANUAL_QUEUE.")

    def _send_soft_rejection(self, lead_data):
        # Soft rejection logic
        logger.info(f"AUTO-DECLINE | Lead {lead_data['client_name']} soft rejected via email.")
