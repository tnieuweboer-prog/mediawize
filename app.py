# app.py
from __future__ import annotations

import os
from datetime import datetime

from flask import Flask, render_template, session

# Blueprints
from modules.core.auth import bp as auth_bp
from modules.docent.routes import bp as docent_bp
from modules.leerling.routes import bp as leerling_bp
from modules.html_tool.routes import bp as html_bp
from modules.workbook.routes import bp as workbook_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Secret key (liefst uit env)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")

    # Data dir (voor users.json / toetsen storage etc)
    app.config["DATA_DIR"] = os.environ.get("DATA_DIR", "/opt/mediawize/data")

    # ---- helpers voor session compatibiliteit ----
    def _session_user_email() -> str | None:
        """
        Ondersteunt:
        - session["user"] = "mail@..."
        - session["user"] = {"email": "...", "role": "..."}
        """
        u = session.get("user")
        if isinstance(u, dict):
            return u.get("email")
        if isinstance(u, str):
            return u
        return None

    def _session_role() -> str | None:
        """
        Ondersteunt:
        - session["role"] = "docent"/"leerling" (oude stijl)
        - session["user"] dict met role (nieuwe stijl)
        """
        role = session.get("role")
        if role:
            return role
        u = session.get("user")
        if isinstance(u, dict):
            return u.get("role")
        return None

    def _is_admin() -> bool:
        return bool(session.get("is_admin"))

    # ---- globals voor templates ----
    @app.context_processor
    def inject_globals():
        email = _session_user_email()
        role = _session_role()

        # school-branding alleen voor docent/leerling, niet voor admin
        school = None
        if role in ("docent", "leerling"):
            s = session.get("school")
            if isinstance(s, dict):
                school = s

        return {
            "now_year": datetime.utcnow().year,
            "current_user": {
                "email": email,
                "role": role,
                "is_authenticated": bool(email),
                "is_admin": _is_admin(),
            },
            "school": school,
        }

    # ---- Publieke landingspagina ----
    @app.get("/")
    def home():
        return render_template("public/home.html", page_title="Mediawize")

    # ---- Register blueprints ----
    app.register_blueprint(auth_bp)

    # dashboards
    app.register_blueprint(docent_bp)
    app.register_blueprint(leerling_bp)

    # tools
    app.register_blueprint(html_bp)
    app.register_blueprint(workbook_bp)

    # admin
    app.register_blueprint(admin_bp)

    return app


# Gunicorn entrypoint verwacht "app"
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)
