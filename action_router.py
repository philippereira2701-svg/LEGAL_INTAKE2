from typing import Any, Dict

from twilio.rest import Client


class ActionRouter:
    """Applies automation branch from AI recommendation."""

    def route_action(self, lead_data: Dict[str, Any], tenant_data: Dict[str, Any]) -> None:
        action = lead_data.get("recommended_action", "MANUAL_REVIEW")
        if action == "AUTO_BOOK":
            self._trigger_immediate_followup(lead_data, tenant_data)
        elif action == "MANUAL_REVIEW":
            self._notify_paralegal_queue(lead_data)
        elif action == "SEND_REJECTION":
            self._send_soft_rejection(lead_data)

    def _trigger_immediate_followup(self, lead_data: Dict[str, Any], tenant_data: Dict[str, Any]) -> None:
        sid = tenant_data.get("twilio_sid")
        token = tenant_data.get("twilio_token")
        from_phone = tenant_data.get("twilio_phone")
        if not all([sid, token, from_phone, lead_data.get("client_phone")]):
            return

        client = Client(sid, token)
        client.messages.create(
            body=(
                f"Hi {lead_data.get('client_name')}, this is LexBridge for {tenant_data.get('firm_name')}. "
                f"Please book now: {tenant_data.get('calendly_link') or 'A team member will call you shortly.'}"
            ),
            from_=from_phone,
            to=lead_data.get("client_phone"),
        )

    def _notify_paralegal_queue(self, lead_data: Dict[str, Any]) -> None:
        return

    def _send_soft_rejection(self, lead_data: Dict[str, Any]) -> None:
        return
