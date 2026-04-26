import logging
from datetime import datetime, timezone
from typing import Optional

from flask import Blueprint, g, jsonify, request
from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlalchemy import text

from auth import create_access_token, require_auth, verify_password
from database import DatabaseManager, SessionLocal, Tenant, User
from services.communications import CommunicationsService
from workers import process_lead_followups_task

logger = logging.getLogger("api")
api_bp = Blueprint("api", __name__)


class IntakeFormSchema(BaseModel):
    client_name: str = Field(min_length=2, max_length=100)
    client_phone: Optional[str] = None
    client_email: Optional[EmailStr] = None
    incident_description: str = Field(min_length=20, max_length=2000)
    incident_location: Optional[str] = Field(default=None, max_length=200)
    incident_date_raw: Optional[str] = Field(default=None, max_length=100)
    injuries: Optional[str] = Field(default=None, max_length=2000)
    police_report_filed: bool = False
    medical_treatment_received: bool = False


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class MercuryPolicySchema(BaseModel):
    contacts: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=120, ge=30, le=900)
    max_levels: int = Field(default=3, ge=1, le=10)
    parallel: bool = False


def get_db_manager():
    session = SessionLocal()
    tenant_id = getattr(g, "tenant_id", None)
    return DatabaseManager(session, tenant_id), session


@api_bp.route("/public/intake/<firm_slug>", methods=["POST"])
def submit_intake(firm_slug: str):
    db, session = get_db_manager()
    try:
        tenant = session.query(Tenant).filter(Tenant.firm_slug == firm_slug, Tenant.is_active.is_(True)).first()
        if not tenant:
            return jsonify({"msg": "Firm not found"}), 404
        try:
            form = IntakeFormSchema.model_validate(request.json or {})
        except ValidationError as exc:
            return jsonify({"msg": "Invalid submission", "errors": exc.errors()}), 422
        if not form.client_phone and not form.client_email:
            return jsonify({"msg": "Contact phone or email is required"}), 400

        # Golden Minute behavior: persist lead immediately and acknowledge before deep async work.
        lead = db.insert_lead(
            str(tenant.id),
            {
                "client_name": form.client_name,
                "client_phone": form.client_phone,
                "client_email": str(form.client_email) if form.client_email else None,
                "incident_description": form.incident_description,
                "incident_location": form.incident_location,
                "incident_date": form.incident_date_raw,
                "injuries_sustained": form.injuries,
                "police_report_filed": form.police_report_filed,
                "medical_treatment_received": form.medical_treatment_received,
                "status": "received",
                "action_taken": "ACK_PENDING",
            },
        )
        db.create_lead_event(
            str(tenant.id),
            lead.id,
            event_type="lead.received",
            event_payload={"channel": "web_form", "firm_slug": firm_slug},
        )

        comms = CommunicationsService(db)
        attempt = comms.enqueue_acknowledgment(
            str(tenant.id),
            lead.id,
            client_name=form.client_name,
            client_phone=form.client_phone,
            firm_name=tenant.firm_name,
            calendly_link=tenant.calendly_link,
        )
        comms.deliver_attempt(
            attempt,
            {
                "twilio_sid": tenant.twilio_sid,
                "twilio_token": tenant.twilio_token,
                "twilio_phone": tenant.twilio_phone,
            },
        )
        db.create_lead_event(str(tenant.id), lead.id, "lead.ack_attempted", {"attempt_id": attempt.id})

        # Deep scoring and Mercury escalation continue asynchronously.
        process_lead_followups_task.delay(str(tenant.id), lead.id)

        return jsonify({"status": "received", "lead_id": lead.id}), 200
    except Exception as exc:
        logger.exception("intake_error")
        db.log_error("api.submit_intake", exc, payload={"firm_slug": firm_slug})
        return jsonify({"msg": "Unable to process submission"}), 500
    finally:
        session.close()


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = LoginSchema.model_validate(request.json or {})
    db, session = get_db_manager()
    try:
        user = session.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            return jsonify({"msg": "Unauthorized"}), 401
        token = create_access_token(
            {
                "tenant_id": str(user.tenant_id),
                "user_id": str(user.id),
                "role": user.role,
                "email": user.email,
            }
        )
        resp = jsonify({"msg": "ok", "role": user.role})
        resp.set_cookie("access_token", token, httponly=True, secure=True, samesite="Lax")
        return resp, 200
    finally:
        session.close()


@api_bp.route("/dashboard/stats", methods=["GET"])
@require_auth
def get_stats():
    db, session = get_db_manager()
    try:
        return jsonify(db.get_dashboard_stats(g.tenant_id))
    finally:
        session.close()


@api_bp.route("/stats", methods=["GET"])
@require_auth
def get_stats_legacy():
    return get_stats()


@api_bp.route("/dashboard/business-metrics", methods=["GET"])
@require_auth
def get_business_metrics():
    db, session = get_db_manager()
    try:
        return jsonify(db.get_business_kpis(g.tenant_id))
    finally:
        session.close()


@api_bp.route("/settings/mercury-policy", methods=["GET"])
@require_auth
def get_mercury_policy():
    db, session = get_db_manager()
    try:
        policy = db.get_mercury_policy(g.tenant_id)
        return jsonify(
            {
                "contacts": policy.contacts,
                "timeout_seconds": policy.timeout_seconds,
                "max_levels": policy.max_levels,
                "parallel": policy.parallel,
            }
        )
    finally:
        session.close()


@api_bp.route("/settings/mercury-policy", methods=["PUT"])
@require_auth
def update_mercury_policy():
    body = MercuryPolicySchema.model_validate(request.json or {})
    db, session = get_db_manager()
    try:
        policy = db.upsert_mercury_policy(
            g.tenant_id,
            contacts=body.contacts,
            timeout_seconds=body.timeout_seconds,
            max_levels=body.max_levels,
            parallel=body.parallel,
        )
        return jsonify(
            {
                "contacts": policy.contacts,
                "timeout_seconds": policy.timeout_seconds,
                "max_levels": policy.max_levels,
                "parallel": policy.parallel,
            }
        )
    finally:
        session.close()


@api_bp.route("/leads", methods=["GET"])
@require_auth
def get_leads():
    page = request.args.get("page", 1, type=int)
    db, session = get_db_manager()
    try:
        leads = db.get_all_leads(g.tenant_id, page=page, page_size=25)
        return jsonify(
            [
                {
                    "id": l.id,
                    "created_at": l.created_at.isoformat(),
                    "client_name": l.client_name,
                    "ai_score": l.ai_score,
                    "status": l.status,
                    "ai_summary": l.ai_summary,
                    "action_taken": l.action_taken,
                    "ai_tier": l.ai_tier,
                }
                for l in leads
            ]
        )
    finally:
        session.close()


@api_bp.route("/leads/<int:lead_id>", methods=["GET"])
@require_auth
def get_lead_detail(lead_id: int):
    db, session = get_db_manager()
    try:
        lead = db.get_lead_by_id(g.tenant_id, lead_id)
        if not lead:
            return jsonify({"msg": "Lead not found"}), 404
        timeline = db.get_lead_timeline(g.tenant_id, lead_id)
        return jsonify(
            {
                "id": lead.id,
                "client_name": lead.client_name,
                "client_phone": lead.client_phone,
                "client_email": lead.client_email,
                "incident_description": lead.incident_description,
                "final_score": lead.ai_score,
                "ai_tier": lead.ai_tier,
                "ai_summary": lead.ai_summary,
                "red_flags": lead.red_flags or [],
                "status": lead.status,
                "timeline": [
                    {
                        "time": e.created_at.isoformat(),
                        "type": e.event_type,
                        "payload": e.event_payload,
                    }
                    for e in timeline
                ],
            }
        )
    finally:
        session.close()


@api_bp.route("/leads/<int:lead_id>/override", methods=["POST"])
@require_auth
def override_lead_status(lead_id: int):
    data = request.json or {}
    next_status = str(data.get("status", "")).strip()
    if next_status not in {"pending", "contacted", "booked", "rejected", "received", "processing"}:
        return jsonify({"msg": "Invalid status"}), 422
    db, session = get_db_manager()
    try:
        lead = db.get_lead_by_id(g.tenant_id, lead_id)
        if not lead:
            return jsonify({"msg": "Lead not found"}), 404
        db.set_lead_status(g.tenant_id, lead_id, next_status)
        db.create_lead_event(
            g.tenant_id,
            lead_id,
            "lead.status_overridden",
            {"status": next_status, "user_id": g.user_id},
        )
        return jsonify({"status": "ok"}), 200
    finally:
        session.close()


@api_bp.route("/leads/<int:lead_id>/human-contact", methods=["POST"])
@require_auth
def mark_human_contact(lead_id: int):
    db, session = get_db_manager()
    try:
        db.update_lead_sla(
            g.tenant_id,
            lead_id,
            first_human_contact_at=datetime.now(timezone.utc),
        )
        db.create_lead_event(
            g.tenant_id,
            lead_id,
            "lead.first_human_contact",
            {"source": "manual"},
        )
        return jsonify({"status": "ok"}), 200
    finally:
        session.close()


@api_bp.route("/leads/<int:lead_id>/mercury/accept", methods=["POST"])
@require_auth
def accept_mercury_escalation(lead_id: int):
    db, session = get_db_manager()
    try:
        pending = db.get_pending_mercury_escalation_for_lead(g.tenant_id, lead_id)
        if not pending:
            return jsonify({"status": "not_found"}), 404
        db.complete_mercury_escalation(pending.id)
        db.create_lead_event(g.tenant_id, lead_id, "mercury.accepted", {"escalation_id": pending.id})
        return jsonify({"status": "accepted"}), 200
    finally:
        session.close()


@api_bp.route("/health/live", methods=["GET"])
def health():
    return jsonify({"status": "live"})


@api_bp.route("/health/ready", methods=["GET"])
def readiness():
    db, session = get_db_manager()
    try:
        session.execute(text("SELECT 1"))
        return jsonify({"status": "ready"})
    except Exception as exc:
        logger.exception("readiness_check_failed")
        db.log_error("api.readiness", exc)
        return jsonify({"status": "degraded"}), 503
    finally:
        session.close()
