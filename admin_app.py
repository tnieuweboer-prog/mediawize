# admin_app.py
from __future__ import annotations

import os
from flask import Flask, redirect

from protected.admin import admin_bp

def create_admin_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # secret key (sessie/flash)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me")

    # eigen cookie naam zodat admin nooit botst met app.mediawize.nl
    app.config["SESSION_COOKIE_NAME"] = "mediawize_admin_session"

    # data dir (zelfde als main app)
    app.config["DATA_DIR"] = os.environ.get("DATA_DIR", "/opt/mediawize/data")

    # admin routes
    app.register_blueprint(admin_bp)

    @app.get("/")
    def root():
        return redirect("/admin/login")

    return app

app = create_admin_app()


app = create_admin_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8502, debug=True)
