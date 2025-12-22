# modules/core/auth.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint("auth", __name__, url_prefix="")

# ---------- storage helpers ----------
def _data_dir() -> Path:
    # app.py zet app.config["DATA_DIR"] = "/opt/mediawize/data"
    data_dir = current_app.config.get("DATA_DIR", "/opt/mediawize/data")
    p = Path(data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p

def _users_path() -> Path:
    return _data_dir() / "users.json"

def _load_users() -> Dict[str, Dict[str, Any]]:
    """
    Returns dict keyed by email.
    Value example:
    {
      "email": "...",
      "password_hash": "...",
      "role": "docent" | "leerling",
      "is_admin": bool
    }
    """
    p = _users_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # als bestand corrupt is, liever niet crashen
        return {}

def _save_users(users: Dict[str, Dict[str, Any]]) -> None:
    p = _users_path()
    p.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")

def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()

# ---------- routes ----------
@bp.get("/login")
def login():
    if session.get("user"):
        # al ingelogd -> naar dashboard
        if session.get("role") == "docent":
            return redirect(url_for("docent.dashboard"))
        if session.get("role") == "leerling":
            return redirect(url_for("leerling.dashboard"))
        return redirect(url_for("home"))
    return render_template("auth/login.html", page_title="Inloggen")

@bp.post("/login")
def login_post():
    email = _normalize_email(request.form.get("email", ""))
    password = request.form.get("password", "")

    users = _load_users()
    user = users.get(email)

    if not user or not check_password_hash(user.get("password_hash", ""), password):
        flash("Onjuiste inloggegevens.", "error")
        return redirect(url_for("auth.login"))

    # session vullen
    session["user"] = user["email"]
    session["role"] = user.get("role", "docent")
    session["is_admin"] = bool(user.get("is_admin", False))

    # doorsturen
    if session["role"] == "docent":
        return redirect(url_for("docent.dashboard"))
    return redirect(url_for("leerling.dashboard"))

@bp.get("/signup")
def signup():
    if session.get("user"):
        return redirect(url_for("home"))
    return render_template("auth/signup.html", page_title="Account maken")

@bp.post("/signup")
def signup_post():
    email = _normalize_email(request.form.get("email", ""))
    password = request.form.get("password", "")
    role = (request.form.get("role") or "leerling").strip().lower()

    if role not in ("docent", "leerling"):
        role = "leerling"

    if not email or "@" not in email:
        flash("Vul een geldig e-mailadres in.", "error")
        return redirect(url_for("auth.signup"))

    if not password or len(password) < 6:
        flash("Wachtwoord moet minimaal 6 tekens zijn.", "error")
        return redirect(url_for("auth.signup"))

    users = _load_users()
    if email in users:
        flash("Dit e-mailadres bestaat al. Log in.", "error")
        return redirect(url_for("auth.login"))

    users[email] = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "role": role,
        "is_admin": False,
    }

    # eerste account automatisch admin maken (handig op een nieuwe installatie)
    if len(users) == 1:
        users[email]["is_admin"] = True
        users[email]["role"] = "docent"

    _save_users(users)

    flash("Account aangemaakt. Je kunt nu inloggen.", "ok")
    return redirect(url_for("auth.login"))

@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

