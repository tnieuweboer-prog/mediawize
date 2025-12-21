# app.py
from __future__ import annotations

import os
from flask import Flask

# Core
from modules.core.layout import inject_globals
from modules.core.auth import auth_bp

# Modules
from modules.html_tool.routes import bp as html_bp
from modules.workbook.routes import bp as workbook_bp
from modules.toetsen.docent_routes import bp as toetsen_docent_bp
from modules.toetsen.leerling_routes import bp as toetsen_leerling_bp
from modules.admin.routes import bp as admin_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # SECRET (zet dit op VPS als env var: FLASK_SECRET_KEY)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

    # Globale template variabelen (current_user etc.)
    inject_globals(app)

    # Core auth/login/logout
    app.register_blueprint(auth_bp)

    # Tools/modules
    # Belangrijk: html tool staat NIET op "/" maar op "/html" zodat home/login niet botst
    app.register_blueprint(html_bp)              # /html
    app.register_blueprint(workbook_bp)          # /workbook
    app.register_blueprint(toetsen_docent_bp)    # /docent/...
    app.register_blueprint(toetsen_leerling_bp)  # /leerling/...
    app.register_blueprint(admin_bp)             # /admin

    return app


app = create_app()

if __name__ == "__main__":
    # Dev-run (systemd/gunicorn gebruikt app:app)
    app.run(host="0.0.0.0", port=8501, debug=True)

