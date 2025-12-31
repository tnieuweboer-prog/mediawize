# protected/admin/routes.py
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from . import admin_bp
from .decorators import admin_required


# =================================================
# ADMIN CREDENTIALS (via environment)
# =================================================

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


# =================================================
# AUTH
# =================================================

@admin_bp.get("/login")
def admin_login():
    if session.get("is_admin") is True:
        return redirect(url_for("admin.admin_dashboard"))

    next_url = request.args.get("next") or url_for("admin.admin_dashboard")
    return render_template("admin/login.html", next_url=next_url)


@admin_bp.post("/login")
def admin_login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_url = request.form.get("next_url") or url_for("admin.admin_dashboard")

    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        flash("Admin login is nog niet geconfigureerd op de server.", "error")
        return redirect(url_for("admin.admin_login"))

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session.clear()
        session["is_admin"] = True
        session["admin_email"] = email
        return redirect(next_url)

    flash("Onjuiste inloggegevens.", "error")
    return redirect(url_for("admin.admin_login"))


@admin_bp.get("/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))


# =================================================
# DASHBOARD
# =================================================

@admin_bp.get("/")
@admin_required
def admin_dashboard():
    return render_template(
        "admin/dashboard.html",
        active_tab="admin",
        page_title="Beheer",
    )


# =================================================
# DATA HELPERS – SCHOOLS
# =================================================

def _schools_path() -> Path:
    data_dir = os.environ.get("DATA_DIR", "/opt/mediawize/data")
    return Path(data_dir) / "schools.json"


def _load_schools() -> list[dict]:
    p = _schools_path()
    if not p.exists():
        return []
    raw = p.read_text(encoding="utf-8").strip()
    return json.loads(raw) if raw else []


def _save_schools(items: list[dict]) -> None:
    p = _schools_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


# =================================================
# SCHOOLS – ROUTES
# =================================================

@admin_bp.get("/schools")
@admin_required
def admin_schools():
    schools = sorted(
        _load_schools(),
        key=lambda s: (s.get("name") or "").lower(),
    )
    return render_template(
        "admin/schools.html",
        schools=schools,
        active_tab="schools",
        page_title="Scholen",
    )


# =================================================
# DATA HELPERS – TEACHERS
# =================================================

def _teachers_path() -> Path:
    data_dir = os.environ.get("DATA_DIR", "/opt/mediawize/data")
    return Path(data_dir) / "teachers.json"


def _load_teachers() -> list[dict]:
    p = _teachers_path()
    if not p.exists():
        return []
    raw = p.read_text(encoding="utf-8").strip()
    return json.loads(raw) if raw else []


def _save_teachers(items: list[dict]) -> None:
    p = _teachers_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


# =================================================
# TEACHERS – ROUTES
# =================================================

@admin_bp.get("/teachers")
@admin_required
def admin_teachers():
    schools = _load_schools()
    teachers = _load_teachers()
    school_map = {s["id"]: s["name"] for s in schools}

    return render_template(
        "admin/teachers.html",
        teachers=teachers,
        schools=schools,
        school_map=school_map,
        active_tab="teachers",
        page_title="Docenten",
    )

