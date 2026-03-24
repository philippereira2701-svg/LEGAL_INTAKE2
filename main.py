import os
import json
from flask import Flask, render_template, jsonify, request
from database import DatabaseManager
from intake_scorer import IntakeScorer
from action_router import ActionRouter
from lawyer_notifier import LawyerNotifier
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key_9921")

# Initialize Architecture
db = DatabaseManager()
scorer = IntakeScorer()
router = ActionRouter()
notifier = LawyerNotifier()

# Seed DB with new schema
db.seed_data()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/apply')
def client_form():
    return render_template('form.html')

@app.route('/api/stats')
def get_stats():
    return jsonify(db.get_dashboard_stats())

@app.route('/api/leads')
def get_leads():
    leads = db.get_all_leads()
    leads_list = []
    for l in leads:
        leads_list.append({
            "id": l.id,
            "created_at": l.created_at.isoformat(),
            "client_name": l.client_name,
            "client_phone": l.client_phone,
            "client_email": l.client_email,
            "incident_date": l.incident_date,
            "incident_description": l.incident_description,
            "incident_location": l.incident_location,
            "injuries_sustained": l.injuries_sustained,
            "insurance_info": l.insurance_info,
            "ai_score": l.ai_score,
            "ai_tier": l.ai_tier,
            "ai_summary": l.ai_summary,
            "liability_score": l.liability_score,
            "damages_score": l.damages_score,
            "sol_score": l.sol_score,
            "red_flags": l.red_flags,
            "action_taken": l.action_taken,
            "lawyer_notified": l.lawyer_notified
        })
    return jsonify(leads_list)

@app.post('/intake')
def process_intake():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Missing payload"}), 400

    # Technical Specifications Compilation
    description = data.get('description')
    location = data.get('location')
    injuries = data.get('injuries')
    insurance = data.get('insurance', 'Not provided')
    
    # AI Input String
    ai_input = (
        f"Client: {data.get('name')}\n"
        f"Description: {description}\n"
        f"Location: {location}\n"
        f"Injuries: {injuries}\n"
        f"Insurance: {insurance}\n"
        f"Police Report: {data.get('police_report')}\n"
        f"Medical: {data.get('medical')}"
    )

    try:
        # AI Triage
        score_result = scorer.score_lead(ai_input)

        # Architectural Save
        lead_id = db.insert_lead({
            "client_name": data.get('name'),
            "client_phone": data.get('phone'),
            "client_email": data.get('email'),
            "incident_date": data.get('date'),
            "incident_description": description,
            "incident_location": location,
            "injuries_sustained": injuries,
            "insurance_info": insurance,
            "police_report_filed": data.get('police_report') == 'yes',
            "medical_treatment_received": data.get('medical') == 'yes',
            "ai_score": score_result.lead_score,
            "ai_tier": score_result.tier,
            "ai_summary": score_result.summary,
            "liability_score": score_result.liability.score,
            "damages_score": score_result.damages.score,
            "sol_score": score_result.statute_of_limitations.score,
            "red_flags": json.dumps(score_result.red_flags),
            "recommended_action": score_result.recommended_action,
            "action_taken": "Automated Response Sent"
        })

        # Fetch full object for notifier/router
        all_leads = db.get_all_leads()
        lead_obj = next(l for l in all_leads if l.id == lead_id)
        
        # Prepare for notification
        lead_dict = {
            "id": lead_obj.id,
            "client_name": lead_obj.client_name,
            "client_phone": lead_obj.client_phone,
            "client_email": lead_obj.client_email,
            "ai_score": lead_obj.ai_score,
            "ai_summary": lead_obj.ai_summary,
            "liability_score": lead_obj.liability_score,
            "damages_score": lead_obj.damages_score,
            "sol_score": lead_obj.sol_score,
            "red_flags": lead_obj.red_flags,
            "recommended_action": lead_obj.recommended_action
        }

        # Fire Automations
        notifier.notify_lawyer(lead_dict)
        router.route_action(lead_dict)

        return jsonify({
            "status": "success",
            "lead_id": lead_id,
            "action": score_result.recommended_action
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.post('/api/lead/<int:lead_id>/override')
def override_lead(lead_id):
    status = request.json.get('status')
    db.update_lead_action(lead_id, f"Manual Override: {status}")
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
