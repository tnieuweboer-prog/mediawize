from flask import Flask, render_template

# blueprints
from modules.core.auth import bp as auth_bp
from modules.html_tool.routes import bp as html_bp
from modules.workbook.routes import bp as workbook_bp
from modules.toetsen.docent_routes import bp as docent_bp
from modules.toetsen.leerling_routes import bp as leerling_bp
from modules.admin.routes import bp as admin_bp


def create_app():
    app = Flask(__name__)

    # -------------------------
    # CONFIG
    # -------------------------
    app.secret_key = "change-this-secret"  # later via env var
    app.config["DATA_DIR"] = "/opt/mediawize/data"

    # -------------------------
    # PUBLIC ROUTES
    # -------------------------
    @app.route("/")
    def home():
        return render_template("public_base.html")

    # -------------------------
    # REGISTER BLUEPRINTS
    # -------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(html_bp, url_prefix="/html")
    app.register_blueprint(workbook_bp, url_prefix="/workbook")
    app.register_blueprint(docent_bp, url_prefix="/docent")
    app.register_blueprint(leerling_bp, url_prefix="/leerling")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


# -------------------------
# GUNICORN ENTRYPOINT
# -------------------------
app = create_app()



