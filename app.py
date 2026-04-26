from flask import Flask, redirect, render_template, url_for
from sqlalchemy import text

from api import api_bp
from auth import require_auth
from config import load_settings
from database import engine


def create_app() -> Flask:
    settings = load_settings()
    app = Flask(__name__)
    app.secret_key = settings.flask_secret_key
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return redirect(url_for("login_page"))

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/intake/<firm_slug>")
    def intake_page(firm_slug: str):
        return render_template("form.html", firm_slug=firm_slug)

    @app.route("/dashboard")
    @require_auth
    def dashboard_page():
        return render_template("dashboard.html")

    @app.route("/leads/<lead_id>")
    @require_auth
    def lead_detail_page(lead_id: str):
        return render_template("lead_detail.html", lead_id=lead_id)

    @app.route("/logout")
    def logout():
        resp = redirect(url_for("login_page"))
        resp.set_cookie("access_token", "", expires=0)
        return resp

    @app.route("/health/live")
    def health_live():
        return {"status": "live"}

    @app.route("/health/ready")
    def health_ready():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app
