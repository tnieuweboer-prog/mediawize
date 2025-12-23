# protected/admin/routes.py
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

from flask import render_template, request, redirect, url_for, session, flash

from . import admin_bp
from .decorators import admin_required


# -------------------------------------------------
# Admin credentials via Environment Variables
# -------------------------------------------------
# Zet deze op je VPS (NIET in code):
#   ADMIN_EMAIL=...
#   ADMIN_PASSWORD=...
# -------------------------------------------------
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


# =================================================
# AUTH
# =================================================

@admin_bp.get("/login")
def admin_login():
    # Al ingelogd? → direct naar dashboard
    if session.get("is_admin") is True:
        return redirect(url_for("admin.admin_dashboard"))

    next_url = request.args.get("next") or url_for("admin.admin_dashboard")
    return render_template("login.html", next_url=next_url)


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
    return redirect(url_for("admin.admin_login", next=next_url))


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
    return render_template("dashboard.html")


# =================================================
# SCHOOLS – opslag helpers (JSON)
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
    p.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# =================================================
# SCHOOLS – routes
# =================================================

@admin_bp.get("/schools")
@admin_required
def admin_schools():
    schools = _load_schools()
    schools = sorted(schools, key=lambda s: (s.get("name") or "").lower())
    return render_template("admin/schools.html", schools=schools)


@admin_bp.post("/schools")
@admin_required
def admin_schools_create():
    name = (request.form.get("name") or "").strip()
    slug = (request.form.get("slug") or "").strip().lower()
    primary = (request.form.get("primary_color") or "").strip()
    secondary = (request.form.get("secondary_color") or "").strip()

    if not name:
        flash("Naam is verplicht.", "error")
        return redirect(url_for("admin.admin_schools"))

    if not slug:
        slug = "-".join(name.lower().split())

    schools = _load_schools()

    if any(s.get("slug") == slug for s in schools):
        flash("Slug bestaat al. Kies een unieke slug.", "error")
        return redirect(url_for("admin.admin_schools"))

    schools.append({
        "id": uuid.uuid4().hex,
        "name": name,
        "slug": slug,
        "primary_color": primary or "#22c55e",
        "secondary_color": secondary or "#86efac",
        "logo_path": "",
        "tools": {
            "docx_html": True,
            "workbook": True,
            "toetsen": True
        },
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    _save_schools(schools)
    flash("School toegevoegd.", "success")
    return redirect(url_for("admin.admin_schools"))

