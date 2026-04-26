import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from twilio.base.exceptions import TwilioException
from twilio.rest import Client

from database import CommunicationAttempt, DatabaseManager


class CommunicationsService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def enqueue_acknowledgment(
        self,
        tenant_id: str,
        lead_id: int,
        *,
        client_name: str,
        client_phone: Optional[str],
        firm_name: str,
        calendly_link: Optional[str],
    ) -> CommunicationAttempt:
        payload = {
            "client_name": client_name,
            "client_phone": client_phone,
            "firm_name": firm_name,
            "calendly_link": calendly_link,
            "message": (
                f"Hi {client_name}, we received your intake for {firm_name}. "
                f"Reply here anytime. "
                f"{'Book quickly: ' + calendly_link if calendly_link else 'A team member will contact you shortly.'}"
            ),
        }
        key = f"ack:{tenant_id}:{lead_id}:sms"
        return self.db.create_communication_attempt(
            tenant_id=tenant_id,
            lead_id=lead_id,
            channel="sms",
            provider="twilio",
            payload_snapshot=payload,
            idempotency_key=key,
            status="pending",
        )

    def deliver_attempt(self, attempt: CommunicationAttempt, tenant_data: Dict[str, Any]) -> None:
        try:
            response_id = self._send_sms(attempt.payload_snapshot, tenant_data)
            self.db.update_communication_attempt(
                attempt.id,
                status="sent",
                provider_response_id=response_id,
                failure_reason=None,
            )
            self.db.create_lead_event(
                attempt.tenant_id,
                attempt.lead_id,
                event_type="communication.sent",
                event_payload={
                    "attempt_id": attempt.id,
                    "channel": attempt.channel,
                    "provider_response_id": response_id,
                },
            )
        except Exception as exc:
            next_retry_count = attempt.retry_count + 1
            self.db.schedule_retry(
                attempt.id,
                failure_reason=str(exc),
                retry_count=next_retry_count,
            )
            self.db.create_lead_event(
                attempt.tenant_id,
                attempt.lead_id,
                event_type="communication.failed",
                event_payload={
                    "attempt_id": attempt.id,
                    "error": str(exc),
                    "retry_count": next_retry_count,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    def _send_sms(self, payload: Dict[str, Any], tenant_data: Dict[str, Any]) -> str:
        sid = tenant_data.get("twilio_sid") or os.getenv("TWILIO_ACCOUNT_SID")
        token = tenant_data.get("twilio_token") or os.getenv("TWILIO_AUTH_TOKEN")
        from_phone = tenant_data.get("twilio_phone") or os.getenv("TWILIO_FROM_NUMBER")
        to_phone = payload.get("to_phone") or payload.get("client_phone")
        if not all([sid, token, from_phone, to_phone]):
            raise RuntimeError("Missing SMS provider settings or recipient phone")
        try:
            client = Client(sid, token)
            message = client.messages.create(
                body=payload["message"],
                from_=from_phone,
                to=to_phone,
            )
            return message.sid
        except TwilioException as exc:
            raise RuntimeError(f"Twilio send failed: {exc.msg}") from exc
