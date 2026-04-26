import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict

from twilio.rest import Client


class LawyerNotifier:
    """Sends lawyer notifications and urgent Twilio voice bridge calls."""

    def notify_lawyer(self, lead_data: Dict[str, Any], tenant_data: Dict[str, Any]) -> None:
        if lead_data.get("ai_score", 0) < 8:
            return
        self._send_email(lead_data, tenant_data)
        self._send_sms(lead_data, tenant_data)
        self._trigger_voice_bridge(lead_data, tenant_data)

    def _send_email(self, lead_data: Dict[str, Any], tenant_data: Dict[str, Any]) -> None:
        email_user = tenant_data.get("gmail_address")
        email_pass = tenant_data.get("gmail_app_password")
        lawyer_email = tenant_data.get("lawyer_email")
        if not all([email_user, email_pass, lawyer_email]):
            return

        msg_body = (
            "LEXBRIDGE | HIGH-PRIORITY PI LEAD\n"
            "---------------------------------\n"
            f"Client: {lead_data.get('client_name')}\n"
            f"Phone: {lead_data.get('client_phone')}\n"
            f"Email: {lead_data.get('client_email')}\n"
            f"AI Score: {lead_data.get('ai_score')}/10\n"
            f"Estimated Case Value: ${lead_data.get('estimated_case_value')}\n"
            f"Summary: {lead_data.get('ai_summary')}\n"
        )
        msg = MIMEText(msg_body)
        msg["Subject"] = f"LexBridge Urgent Lead: {lead_data.get('client_name')}"
        msg["From"] = email_user
        msg["To"] = lawyer_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)

    def _send_sms(self, lead_data: Dict[str, Any], tenant_data: Dict[str, Any]) -> None:
        sid = tenant_data.get("twilio_sid")
        token = tenant_data.get("twilio_token")
        from_phone = tenant_data.get("twilio_phone")
        to_phone = tenant_data.get("lawyer_phone")
        if not all([sid, token, from_phone, to_phone]):
            return

        client = Client(sid, token)
        client.messages.create(
            body=(
                f"URGENT PI lead {lead_data.get('ai_score')}/10 | {lead_data.get('client_name')} "
                f"| value ${lead_data.get('estimated_case_value')}"
            ),
            from_=from_phone,
            to=to_phone,
        )

    def _trigger_voice_bridge(self, lead_data: Dict[str, Any], tenant_data: Dict[str, Any]) -> None:
        sid = tenant_data.get("twilio_sid")
        token = tenant_data.get("twilio_token")
        from_phone = tenant_data.get("twilio_phone")
        lawyer_phone = tenant_data.get("lawyer_phone")
        client_phone = lead_data.get("client_phone")
        if not all([sid, token, from_phone, lawyer_phone, client_phone]):
            return

        # First call reaches lawyer. If accepted, TwiML dials the client to bridge both sides.
        twiml = f"<Response><Say>High priority lead from LexBridge. Connecting you now.</Say><Dial>{client_phone}</Dial></Response>"
        client = Client(sid, token)
        client.calls.create(
            twiml=twiml,
            from_=from_phone,
            to=lawyer_phone,
            timeout=20,
        )
