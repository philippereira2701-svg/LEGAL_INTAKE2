from flask import Blueprint, request, jsonify, g
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
import uuid
import logging
from database import SessionLocal, DatabaseManager, Tenant, User
from auth import require_auth, require_role, verify_password, create_access_token
from workers import process_intake_task

logger = logging.getLogger("API")
api_bp = Blueprint('api', __name__)

# --- Optimized Schemas ---

class IntakeFormSchema(BaseModel):
    client_name: str = Field(min_length=2, max_length=100)
    client_phone: Optional[str] = None
    client_email: Optional[EmailStr] = None
    incident_description: str = Field(min_length=20, max_length=2000)
    police_report_filed: bool = False
    medical_treatment_received: bool = False
    hospitalized: bool = False
    incident_date_raw: str = Field(max_length=100)
    already_represented: bool = False
    estimated_medical_bills: Optional[str] = Field(None, max_length=50)

# --- Dependency Injection Simulation ---

def get_db_manager():
    """Context-aware DB manager factory"""
    session = SessionLocal()
    # If authenticated, g.tenant_id is set by @require_auth
    tenant_id = getattr(g, 'tenant_id', None)
    return DatabaseManager(session, tenant_id), session

# --- Routes ---

@api_bp.route('/intake/<firm_slug>', methods=['POST'])
def submit_intake(firm_slug):
    """Public submission with slug-based tenant lookup"""
    db, session = get_db_manager()
    try:
        tenant = session.query(Tenant).filter(Tenant.firm_slug == firm_slug).first()
        if not tenant:
            return jsonify({"msg": "Firm not found"}), 404
        
        form = IntakeFormSchema(**request.json)
        if not form.client_phone and not form.client_email:
            return jsonify({"msg": "Contact info required"}), 400

        process_intake_task.delay(str(tenant.id), form.model_dump())
        return jsonify({"status": "received"}), 200
    except Exception as e:
        logger.error(f"Intake error: {e}")
        return jsonify({"msg": "Invalid submission"}), 400
    finally:
        session.close()

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Secure login with httpOnly cookie issuance"""
    data = request.json
    db, session = get_db_manager()
    try:
        user = session.query(User).filter(User.email == data.get('email')).first()
        if user and verify_password(data.get('password'), user.password_hash):
            token = create_access_token({
                "tenant_id": str(user.tenant_id),
                "user_id": str(user.id),
                "role": user.role
            })
            resp = jsonify({"msg": "ok", "role": user.role})
            resp.set_cookie('access_token', token, httponly=True, secure=True, samesite='Lax')
            return resp, 200
        return jsonify({"msg": "Unauthorized"}), 401
    finally:
        session.close()

@api_bp.route('/dashboard/stats', methods=['GET'])
@require_auth
def get_stats():
    """Authenticated dashboard metrics"""
    db, session = get_db_manager()
    try:
        return jsonify(db.get_dashboard_stats(g.tenant_id))
    finally:
        session.close()

@api_bp.route('/leads', methods=['GET'])
@require_auth
def get_leads():
    """RLS-protected lead list with pagination"""
    page = request.args.get('page', 1, type=int)
    db, session = get_db_manager()
    try:
        leads = db.get_all_leads(g.tenant_id, page)
        return jsonify([{
            "id": str(l.id),
            "created_at": l.created_at.isoformat(),
            "client_name": l.client_name,
            "final_score": l.final_score,
            "status": l.status,
            "ai_summary": l.ai_summary
        } for l in leads])
    finally:
        session.close()

@api_bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "live"})
