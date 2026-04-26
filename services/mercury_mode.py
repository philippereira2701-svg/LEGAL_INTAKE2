from database import DatabaseManager, Lead


class MercuryModeService:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def _resolve_contacts(self, tenant_id: str, owner_phone: str | None) -> list[str]:
        policy = self.db.get_mercury_policy(tenant_id)
        contacts = [c for c in policy.contacts if c]
        if owner_phone and owner_phone not in contacts:
            contacts.insert(0, owner_phone)
        return contacts

    def maybe_trigger(self, tenant_id: str, lead: Lead, owner_phone: str | None) -> bool:
        if (lead.ai_score or 0) < 8:
            return False
        contacts = self._resolve_contacts(tenant_id, owner_phone)
        if not contacts:
            return False
        if self.db.get_open_mercury_escalation_for_lead(tenant_id, lead.id):
            return True
        escalation_key = f"mercury:{tenant_id}:{lead.id}:1"
        escalation = self.db.create_mercury_escalation(
            tenant_id=tenant_id,
            lead_id=lead.id,
            level=1,
            owner_phone=contacts[0],
            escalation_key=escalation_key,
        )
        attempt = self.db.create_communication_attempt(
            tenant_id=tenant_id,
            lead_id=lead.id,
            channel="sms",
            provider="twilio",
            payload_snapshot={
                "to_phone": contacts[0],
                "message": (
                    f"MERCURY MODE: High-value lead #{lead.id} requires ownership now. "
                    "Reply ACCEPT to claim."
                ),
            },
            idempotency_key=f"mercury-alert:{escalation.id}",
            status="pending",
        )
        self.db.create_lead_event(
            tenant_id,
            lead.id,
            "mercury.triggered",
            {"escalation_id": escalation.id, "attempt_id": attempt.id, "level": 1},
        )
        return True
