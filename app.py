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
from modules.admin.routes import bp as admin_bp

app.config["DATA_DIR"] = "/opt/mediawize/data"

def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Secret key (liefst uit env)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")

    # ---- globals voor templates ----
    @app.context_processor
    def inject_globals():
        role = session.get("role")
        return {
            "now_year": datetime.utcnow().year,
            "current_user": {
                "email": session.get("user"),
                "role": role,
                "is_authenticated": bool(session.get("user")),
                "is_admin": bool(session.get("is_admin")),
            },
        }

    # ---- Publieke landingspagina ----
    @app.get("/")
    def home():
        # Als iemand al ingelogd is, stuur direct naar juiste dashboard
        if session.get("user"):
            if session.get("role") == "docent":
                return render_template(
                    "public/home.html",
                    page_title="Triade Tools",
                )
            if session.get("role") == "leerling":
                return render_template(
                    "public/home.html",
                    page_title="Triade Tools",
                )
        return render_template("public/home.html", page_title="Triade Tools")

    # ---- Register blueprints ----
    app.register_blueprint(auth_bp)       # /login, /logout
    app.register_blueprint(docent_bp)     # /docent/
    app.register_blueprint(leerling_bp)   # /leerling/
    app.register_blueprint(html_bp)       # /html/
    app.register_blueprint(workbook_bp)   # /workbook/
    app.register_blueprint(admin_bp)      # /admin/

    return app


# Gunicorn entrypoint verwacht "app"
app = create_app()

if __name__ == "__main__":
    # lokaal debuggen
    app.run(host="0.0.0.0", port=8501, debug=True)


