import os
import json
from functools import wraps
from flask import Flask, render_template, jsonify, request, abort
from database import DatabaseManager
from intake_scorer import IntakeScorer
from action_router import ActionRouter
from lawyer_notifier import LawyerNotifier
from logger import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "legal_prj_ultra_secret_2025")

# Architecture Singleton Initialization
db = DatabaseManager()
db.seed_data()
scorer = IntakeScorer()
router = ActionRouter()
notifier = LawyerNotifier()

# Security Configuration
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "lex_admin_secure_key_99")

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get('X-API-KEY') or request.args.get('key')
        if key != ADMIN_API_KEY:
            logger.warning(f"UNAUTHORIZED ACCESS | IP:{request.remote_addr} | Path:{request.path}")
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
@require_auth
def admin_dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats')
@require_auth
def get_stats():
    return jsonify(db.get_dashboard_stats())

@app.route('/api/leads')
@require_auth
def get_leads():
    leads = db.get_all_leads()
    leads_list = []
    for l in leads:
        leads_list.append({
            "id": l.id,
            "created_at": l.created_at.isoformat(),
            "client_name": l.client_name,
            "ai_score": l.ai_score,
            "ai_tier": l.ai_tier,
            "action_taken": l.action_taken,
            "status": l.status
        })
    return jsonify(leads_list)

@app.post('/intake')
def process_intake():
    data = request.json
    if not data:
        logger.error("INTAKE FAILURE | Missing Payload")
        return jsonify({"status": "error", "message": "Missing payload"}), 400

    logger.info(f"INTAKE START | Client:{data.get('name')}")

    try:
        # AI Triage
        ai_input = f"Name: {data.get('name')}\nDesc: {data.get('description')}\nInjuries: {data.get('injuries')}"
        score_result = scorer.score_lead(ai_input)

        # Architectural Save
        lead_id = db.insert_lead({
            "client_name": data.get('name'),
            "client_phone": data.get('phone'),
            "client_email": data.get('email'),
            "incident_date": data.get('date'),
            "incident_description": data.get('description'),
            "incident_location": data.get('location'),
            "injuries_sustained": data.get('injuries'),
            "police_report_filed": data.get('police_report') == 'yes',
            "medical_treatment_received": data.get('medical') == 'yes',
            "ai_score": score_result.lead_score,
            "ai_tier": score_result.tier,
            "ai_summary": score_result.summary,
            "liability_score": score_result.liability.score,
            "damages_score": score_result.damages.score,
            "sol_score": score_result.statute_of_limitations.score,
            "red_flags": json.dumps(score_result.red_flags),
            "recommended_action": score_result.recommended_action
        })

        logger.audit_lead(lead_id, "Inscribed to Database")

        # Prep for Async Actions
        lead_dict = {
            "id": lead_id,
            "client_name": data.get('name'),
            "client_phone": data.get('phone'),
            "client_email": data.get('email'),
            "ai_score": score_result.lead_score,
            "ai_summary": score_result.summary,
            "liability_score": score_result.liability.score,
            "damages_score": score_result.damages.score,
            "sol_score": score_result.statute_of_limitations.score,
            "red_flags": score_result.red_flags,
            "recommended_action": score_result.recommended_action
        }

        # Fire Orchestrations
        notifier.notify_lawyer(lead_dict)
        router.route_action(lead_dict)

        logger.info(f"INTAKE COMPLETE | LeadID:{lead_id} | Tier:{score_result.tier}")
        return jsonify({
            "status": "success",
            "lead_id": lead_id,
            "action": score_result.recommended_action
        })

    except Exception as e:
        logger.error(f"INTAKE CRITICAL ERROR | {str(e)}")
        return jsonify({"status": "error", "message": "Internal processing failure"}), 500

if __name__ == "__main__":
    logger.info("LEGAL_PRJ CORE STARTING | Port:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
