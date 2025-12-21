# modules/core/auth.py
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login_get():
    # Als je al ingelogd bent, stuur door
    role = session.get("role")
    if role == "docent":
        return redirect(url_for("docent.dashboard"))
    if role == "leerling":
        return redirect(url_for("leerling.dashboard"))
    return render_template("auth/login.html", active_tab="login", error=None)


@auth_bp.post("/login")
def login_post():
    role = (request.form.get("role") or "").strip()
    name = (request.form.get("name") or "").strip() or "user"

    if role not in ("docent", "leerling"):
        return render_template("auth/login.html", active_tab="login", error="Kies docent of leerling.")

    # Dummy sessie login
    session["user"] = name
    session["role"] = role
    session.setdefault("is_admin", False)

    if role == "docent":
        return redirect(url_for("docent.dashboard"))
    return redirect(url_for("leerling.dashboard"))


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("public.home"))

