from flask import Flask, render_template, redirect, url_for, session

# Blueprints (moeten in jouw project bestaan)
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
    # HOME (Landing page)
    # -------------------------
    @app.route("/")
    def home():
        """
        Landing page (GEEN dashboard).
        Toont uitleg + knoppen naar login/signup.
        In public_base.html kun je de content mooi maken.
        """
        modules = [
            {
                "title": "DOCX → HTML (Stermonitor)",
                "desc": "Zet Word-bestanden om naar nette Stermonitor-HTML met jouw styling.",
                "href": url_for("html_tool.index"),
            },
            {
                "title": "Werkboek generator",
                "desc": "Maak automatisch een werkboekje (voorblad + stappen) vanuit DOCX.",
                "href": url_for("workbook.index"),
            },
            {
                "title": "Toetsen",
                "desc": "Docent maakt toetsen, leerling maakt ze online. (PDF export later)",
                "href": url_for("docent.dashboard"),
            },
        ]

        return render_template(
            "public_base.html",
            modules=modules,
            login_url=url_for("auth.login"),
            signup_url=url_for("auth.signup"),
        )

    # -------------------------
    # DASHBOARD redirect helper
    # -------------------------
    @app.route("/dashboard")
    def dashboard():
        """
        1 centrale route om na login naartoe te sturen.
        Op basis van session['role'] (docent/leerling) redirecten.
        """
        role = session.get("role")
        if role == "docent":
            return redirect(url_for("docent.dashboard"))
        if role == "leerling":
            return redirect(url_for("leerling.dashboard"))
        return redirect(url_for("auth.login"))

    # -------------------------
    # REGISTER BLUEPRINTS
    # -------------------------
    app.register_blueprint(auth_bp)  # /login /signup /logout
    app.register_blueprint(html_bp, url_prefix="/html")
    app.register_blueprint(workbook_bp, url_prefix="/workbook")
    app.register_blueprint(docent_bp, url_prefix="/docent")
    app.register_blueprint(leerling_bp, url_prefix="/leerling")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


# Gunicorn entrypoint
app = create_app()


