# modules/core/auth.py
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint("auth", __name__)


# ------------------------------------------------------------
# Login
# ------------------------------------------------------------
@auth_bp.get("/login")
def login_get():
    """
    Toon loginpagina.
    Als gebruiker al ingelogd is, direct doorsturen naar dashboard.
    """
    role = session.get("role")

    if role == "docent":
        return redirect(url_for("docent.dashboard"))
    if role == "leerling":
        return redirect(url_for("leerling.dashboard"))

    return render_template(
        "auth/login.html",
        active_tab="login",
        error=None,
    )


@auth_bp.post("/login")
def login_post():
    """
    Dummy login:
    - docent / leerling
    - naam opslaan in session
    """
    role = (request.form.get("role") or "").strip()
    name = (request.form.get("name") or "").strip()

    if role not in ("docent", "leerling"):
        return render_template(
            "auth/login.html",
            active_tab="login",
            error="Kies docent of leerling.",
        )

    if not name:
        return render_template(
            "auth/login.html",
            active_tab="login",
            error="Vul je naam in.",
        )

    # Session opslaan
    session.clear()
    session["user"] = name
    session["role"] = role
    session["is_admin"] = False  # later via admin module

    if role == "docent":
        return redirect(url_for("docent.dashboard"))

    return redirect(url_for("leerling.dashboard"))


# ------------------------------------------------------------
# Logout
# ------------------------------------------------------------
@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_get"))


