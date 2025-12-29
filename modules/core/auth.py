# modules/core/auth.py
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from datetime import datetime
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

def _schools_path() -> Path:
    return _data_dir() / "schools.json"

def _teachers_path() -> Path:
    return _data_dir() / "teachers.json"

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

def _load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8").strip()
        return json.loads(raw) if raw else []
    except Exception:
        return []

def _save_list(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def _schools_sorted() -> list[dict]:
    schools = _load_list(_schools_path())
    return sorted(schools, key=lambda s: (s.get("name") or "").lower())

def _upsert_teacher(email: str, name: str, school_id: str) -> None:
    """
    Zorgt dat teachers.json een record heeft voor deze docent.
    Upsert op email.
    """
    teachers = _load_list(_teachers_path())
    email_lc = _normalize_email(email)

    found = next((t for t in teachers if _normalize_email(t.get("email", "")) == email_lc), None)
    if found:
        found["name"] = name or found.get("name") or ""
        found["school_id"] = school_id
        found["active"] = True
        found["updated_at"] = datetime.utcnow().isoformat() + "Z"
    else:
        teachers.append({
            "id": uuid.uuid4().hex,
            "name": name or "",
            "email": email_lc,
            "school_id": school_id,
            "role": "docent",
            "active": True,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })

    _save_list(_teachers_path(), teachers)

def _find_teacher_by_email(email: str) -> dict | None:
    teachers = _load_list(_teachers_path())
    email_lc = _normalize_email(email)
    return next((t for t in teachers if _normalize_email(t.get("email", "")) == email_lc), None)

def _find_school_by_id(school_id: str) -> dict | None:
    schools = _load_list(_schools_path())
    return next((s for s in schools if s.get("id") == school_id), None)

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

    # -----------------------------
    # School branding in session
    # -----------------------------
    session.pop("school", None)

    if session["role"] == "docent":
        t = _find_teacher_by_email(email)
        if t and t.get("school_id"):
            s = _find_school_by_id(t["school_id"])
            if s:
                session["school"] = {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "logo_path": s.get("logo_path") or "",
                    "primary_color": s.get("primary_color") or "#22c55e",
                    "secondary_color": s.get("secondary_color") or "#86efac",
                }

    # doorsturen
    if session["role"] == "docent":
        return redirect(url_for("docent.dashboard"))
    return redirect(url_for("leerling.dashboard"))

@bp.get("/signup")
def signup():
    if session.get("user"):
        return redirect(url_for("home"))

    # scholen naar template zodat docent er één kan kiezen
    schools = _schools_sorted()
    return render_template("auth/signup.html", page_title="Account maken", schools=schools)

@bp.post("/signup")
def signup_post():
    email = _normalize_email(request.form.get("email", ""))
    password = request.form.get("password", "")
    role = (request.form.get("role") or "leerling").strip().lower()

    # (optioneel) naamveld ondersteunen als het in je template zit
    name = (request.form.get("name") or "").strip()

    if role not in ("docent", "leerling"):
        role = "leerling"

    if not email or "@" not in email:
        flash("Vul een geldig e-mailadres in.", "error")
        return redirect(url_for("auth.signup"))

    if not password or len(password) < 6:
        flash("Wachtwoord moet minimaal 6 tekens zijn.", "error")
        return redirect(url_for("auth.signup"))

    # als docent -> school verplicht
    school_id = (request.form.get("school_id") or "").strip()
    if role == "docent":
        schools = _load_list(_schools_path())
        if not school_id:
            flash("Kies een school.", "error")
            return redirect(url_for("auth.signup"))
        if not any(s.get("id") == school_id for s in schools):
            flash("Kies een geldige school.", "error")
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
        role = "docent"  # zodat onderstaande logic klopt

        # als eerste account admin wordt, moet er ook een school gekozen zijn
        # (anders krijg je direct een docent zonder school)
        if not school_id:
            flash("Als eerste account (admin) moet je een school kiezen.", "error")
            return redirect(url_for("auth.signup"))

    _save_users(users)

    # docent -> ook in teachers.json zetten/updaten
    if role == "docent":
        _upsert_teacher(email=email, name=name, school_id=school_id)

    flash("Account aangemaakt. Je kunt nu inloggen.", "ok")
    return redirect(url_for("auth.login"))

@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

