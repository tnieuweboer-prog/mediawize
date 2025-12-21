# app.py
from flask import Flask
import os

from modules.core.auth import auth_bp
from modules.core.layout import inject_globals
from modules.workbook.routes import bp as workbook_bp
from modules.html_tool.routes import bp as html_bp
from modules.admin.routes import bp as admin_bp
from modules.toetsen.docent_routes import bp as toetsen_docent_bp
from modules.toetsen.leerling_routes import bp as toetsen_leerling_bp


def create_app():
    app = Flask(__name__)

    # -------------------------------------------------
    # Config
    # -------------------------------------------------
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

    # -------------------------------------------------
    # Template globals (menu, user, role)
    # -------------------------------------------------
    inject_globals(app)

    # -------------------------------------------------
    # Core auth (login / logout)
    # -------------------------------------------------
    app.register_blueprint(auth_bp)

    # -------------------------------------------------
    # Modules
    # -------------------------------------------------
    app.register_blueprint(html_bp)             # /html
    app.register_blueprint(workbook_bp)         # /workbook
    app.register_blueprint(toetsen_docent_bp)   # /docent/...
    app.register_blueprint(toetsen_leerling_bp) # /leerling/...
    app.register_blueprint(admin_bp)             # /admin

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)
