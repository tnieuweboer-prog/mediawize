# modules/core/auth.py
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, session

bp = Blueprint("auth", __name__)


# ------------------------------------------------------------
# Login pagina
# ------------------------------------------------------------
@bp.get("/login")
def login_get():
    # Als al ingelogd: stuur naar dashboard
    if session.get("user"):
        if session.get("role") == "docent":
            return redirect(url_for("docent.dashboard"))
        if session.get("role") == "leerling":
            return redirect(url_for("leerling.dashboard"))
    return render_template("auth/login.html", page_title="Inloggen")


@bp.post("/login")
def login_post():
    """
    Dummy login:
    - docent: email + wachtwoord (mag leeg voor nu)
    - leerling: naam/kode mag ook, maar we houden het simpel
    Later vervangen door Microsoft OAuth.
    """
    email = (request.form.get("email") or "").strip().lower()
    role = (request.form.get("role") or "").strip().lower()

    if role not in ("docent", "leerling"):
        return render_template("auth/login.html", page_title="Inloggen", error="Kies docent of leerling.")

    if not email:
        return render_template("auth/login.html", page_title="Inloggen", error="Vul een e-mailadres in.")

    # Session zetten
    session["user"] = email
    session["role"] = role

    # Simpele admin regel (later netjes in admin module)
    # Bijvoorbeeld: jouw eigen account als admin
    admin_emails = {"tom@atlascollege.nl", "emy@atlascollege.nl"}  # pas aan
    session["is_admin"] = email in admin_emails

    # Redirect naar juiste dashboard
    if role == "docent":
        return redirect(url_for("docent.dashboard"))
    return redirect(url_for("leerling.dashboard"))


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

