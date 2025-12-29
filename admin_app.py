# admin_app.py
from __future__ import annotations

import os
from datetime import datetime
from flask import Flask, render_template, redirect, request, url_for, session, flash

from protected.admin import admin_bp  # jouw bestaande admin blueprint

def create_admin_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Eigen secret key voor admin-app (los van docent-app)
    app.secret_key = os.environ.get("ADMIN_SECRET_KEY", "admin-dev-change-me")

    # Eigen cookie naam zodat het nooit botst met docent-app
    app.config["SESSION_COOKIE_NAME"] = "mediawize_admin_session"

    # Data dir blijft hetzelfde (scholen.json/teachers.json)
    app.config["DATA_DIR"] = os.environ.get("DATA_DIR", "/opt/mediawize/data")

    # (optioneel maar netter) forceer cookie security
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    @app.context_processor
    def inject_globals():
        return {
            "now_year": datetime.utcnow().year,
            "current_user": {
                "is_admin": bool(session.get("is_admin")),
                "email": session.get("admin_email"),
            },
            "school": None,  # admin gebruikt geen school branding
        }

    @app.get("/")
    def root():
        # altijd naar admin dashboard
        return redirect("/admin/login")

    # Alleen admin blueprint registreren
    app.register_blueprint(admin_bp, url_prefix="")  # jouw bp heeft al /admin prefix? Zo niet: zie note hieronder.

    return app

app = create_admin_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8502, debug=True)
