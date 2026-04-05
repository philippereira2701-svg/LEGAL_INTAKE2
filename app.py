import os
from flask import Flask, render_template, redirect, url_for, request, g
from dotenv import load_dotenv
from database import engine, Base, SessionLocal
from api import api_bp
from auth import require_auth
from workers import celery

load_dotenv()

def create_app():
    """Flask application factory"""
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    # Verify critical environment variables
    required_vars = [
        "DATABASE_URL", "REDIS_URL", "GEMINI_API_KEY", 
        "JWT_SECRET_KEY", "FLASK_SECRET_KEY"
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    # Register Blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    # Frontend Routes
    @app.route('/')
    def index():
        return redirect(url_for('login_page'))

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/intake/<firm_slug>')
    def intake_page(firm_slug):
        return render_template('form.html', firm_slug=firm_slug)

    @app.route('/dashboard')
    @require_auth
    def dashboard_page():
        return render_template('dashboard.html')

    @app.route('/leads/<lead_id>')
    @require_auth
    def lead_detail_page(lead_id):
        return render_template('lead_detail.html')

    @app.route('/logout')
    def logout():
        resp = redirect(url_for('login_page'))
        resp.set_cookie('access_token', '', expires=0)
        return resp

    # Database setup check
    try:
        with engine.connect() as conn:
            pass
    except Exception as e:
        print(f"CRITICAL: Could not connect to database: {e}")

    return app

app = create_app()

if __name__ == "__main__":
    # Use 0.0.0.0 to ensure it works on all local interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)
