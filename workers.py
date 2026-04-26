import os
from datetime import datetime, timezone
from typing import Dict

from celery import Celery

from database import CommunicationAttempt, DatabaseManager, Lead, SessionLocal, Tenant
from services.communications import CommunicationsService
from services.mercury_mode import MercuryModeService
from intake_scorer import IntakeScorer

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery = Celery("lexbridge_tasks", broker=REDIS_URL, backend=REDIS_URL)

try:
    import redis

    redis.from_url(REDIS_URL).ping()
except Exception:
    celery.conf.update(task_always_eager=True, task_eager_propagates=True)

@celery.task(bind=True, max_retries=3)
def process_lead_followups_task(self, tenant_id: str, lead_id: int) -> None:
    session = SessionLocal()
    db = DatabaseManager(session)
    try:
        lead = session.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not lead or not tenant:
            return

        scorer = IntakeScorer()
        ai_input = (
            f"{lead.client_name}\n"
            f"{lead.incident_description or ''}\n"
            f"{lead.injuries_sustained or ''}\n"
            f"{lead.incident_location or ''}"
        )
        score_result = scorer.score_lead(ai_input)
        lead.ai_score = score_result.lead_score
        lead.ai_tier = score_result.tier
        lead.ai_summary = score_result.summary
        lead.estimated_case_value = score_result.estimated_case_value
        lead.liability_score = score_result.liability.score
        lead.damages_score = score_result.damages.score
        lead.sol_score = score_result.statute_of_limitations.score
        lead.red_flags = score_result.red_flags
        lead.recommended_action = score_result.recommended_action
        session.commit()

        db.create_lead_event(
            tenant_id,
            lead.id,
            event_type="lead.scoring.completed",
            event_payload={
                "ai_score": lead.ai_score,
                "recommended_action": lead.recommended_action,
            },
        )
        db.update_lead_action(tenant_id, lead.id, "ASYNC_SCORING_RECORDED")

        mercury = MercuryModeService(db)
        mercury.maybe_trigger(tenant_id, lead, tenant.lawyer_phone)
    except Exception as exc:
        db.log_error(
            context="workers.process_lead_followups_task",
            error=exc,
            payload={"tenant_id": tenant_id, "lead_id": lead_id},
            tenant_id=tenant_id,
        )
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    finally:
        session.close()


@celery.task(bind=True, max_retries=3)
def dispatch_pending_communications_task(self) -> Dict[str, int]:
    session = SessionLocal()
    db = DatabaseManager(session)
    sent = 0
    failed = 0
    try:
        attempts = db.get_pending_communication_attempts(limit=100)
        comms = CommunicationsService(db)
        for attempt in attempts:
            tenant = session.query(Tenant).filter(Tenant.id == attempt.tenant_id).first()
            if not tenant:
                failed += 1
                db.update_communication_attempt(
                    attempt.id,
                    status="dead_letter",
                    failure_reason="tenant_missing",
                    retry_count=attempt.retry_count + 1,
                )
                continue
            comms.deliver_attempt(
                attempt,
                {
                    "twilio_sid": tenant.twilio_sid,
                    "twilio_token": tenant.twilio_token,
                    "twilio_phone": tenant.twilio_phone,
                },
            )
            refreshed = session.query(CommunicationAttempt).filter(CommunicationAttempt.id == attempt.id).first()
            if refreshed and refreshed.status == "sent":
                sent += 1
            else:
                failed += 1
        return {"sent": sent, "failed": failed}
    except Exception as exc:
        db.log_error("workers.dispatch_pending_communications_task", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    finally:
        session.close()


@celery.task(bind=True, max_retries=3)
def process_pending_mercury_escalations_task(self) -> Dict[str, int]:
    session = SessionLocal()
    db = DatabaseManager(session)
    processed = 0
    advanced = 0
    try:
        pending = db.get_pending_mercury_escalations(limit=100)
        for escalation in pending:
            processed += 1
            policy = db.get_mercury_policy(escalation.tenant_id)
            tenant = session.query(Tenant).filter(Tenant.id == escalation.tenant_id).first()
            if not tenant:
                continue
            elapsed_seconds = (datetime.now(timezone.utc) - escalation.triggered_at).total_seconds()
            if elapsed_seconds < policy.timeout_seconds:
                db.create_lead_event(
                    escalation.tenant_id,
                    escalation.lead_id,
                    "mercury.pending",
                    {"escalation_id": escalation.id, "level": escalation.level},
                )
                continue

            contacts = [c for c in policy.contacts if c]
            if tenant.lawyer_phone and tenant.lawyer_phone not in contacts:
                contacts.insert(0, tenant.lawyer_phone)

            db.expire_mercury_escalation(escalation.id)
            if escalation.level >= policy.max_levels or escalation.level >= len(contacts):
                db.create_lead_event(
                    escalation.tenant_id,
                    escalation.lead_id,
                    "mercury.exhausted",
                    {"escalation_id": escalation.id, "level": escalation.level},
                )
                continue

            next_level = escalation.level + 1
            owner_phone = contacts[next_level - 1]
            next_escalation = db.create_mercury_escalation(
                tenant_id=escalation.tenant_id,
                lead_id=escalation.lead_id,
                level=next_level,
                owner_phone=owner_phone,
                escalation_key=f"mercury:{escalation.tenant_id}:{escalation.lead_id}:{next_level}",
            )
            attempt = db.create_communication_attempt(
                tenant_id=escalation.tenant_id,
                lead_id=escalation.lead_id,
                channel="sms",
                provider="twilio",
                payload_snapshot={
                    "to_phone": owner_phone,
                    "message": (
                        f"MERCURY MODE ESCALATION L{next_level}: Lead #{escalation.lead_id} "
                        "still unclaimed. Reply ACCEPT to claim now."
                    ),
                },
                idempotency_key=f"mercury-alert:{next_escalation.id}",
                status="pending",
            )
            db.create_lead_event(
                escalation.tenant_id,
                escalation.lead_id,
                "mercury.escalated",
                {
                    "from_escalation_id": escalation.id,
                    "to_escalation_id": next_escalation.id,
                    "attempt_id": attempt.id,
                    "level": next_level,
                },
            )
            advanced += 1
        return {"processed": processed, "advanced": advanced}
    except Exception as exc:
        db.log_error("workers.process_pending_mercury_escalations_task", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    finally:
        session.close()
