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

from werkzeug.utils import secure_filename

def _logos_dir() -> Path:
    data_dir = os.environ.get("DATA_DIR", "/opt/mediawize/data")
    return Path(data_dir) / "logos"

def _allowed_logo(filename: str) -> bool:
    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    return ext in {"png", "jpg", "jpeg", "webp"}


@admin_bp.post("/schools/<school_id>/logo")
@admin_required
def admin_school_logo_upload(school_id: str):
    file = request.files.get("logo")
    if not file or not file.filename:
        flash("Kies een bestand om te uploaden.", "error")
        return redirect(url_for("admin.admin_schools"))

    if not _allowed_logo(file.filename):
        flash("Alleen PNG, JPG of WEBP toegestaan.", "error")
        return redirect(url_for("admin.admin_schools"))

    schools = _load_schools()
    school = next((s for s in schools if s.get("id") == school_id), None)
    if not school:
        flash("School niet gevonden.", "error")
        return redirect(url_for("admin.admin_schools"))

    # veilige naam + vaste bestandsnaam per school
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()

    logos_dir = _logos_dir()
    logos_dir.mkdir(parents=True, exist_ok=True)

    # bijv: <school_id>.png (altijd 1 logo per school)
    saved_name = f"{school_id}.{ext}"
    save_path = logos_dir / saved_name
    file.save(str(save_path))

    # we slaan een web-pad op dat je direct kunt gebruiken in <img src="">
    school["logo_path"] = f"/data/logos/{saved_name}"
    _save_schools(schools)

    flash("Logo geüpload.", "success")
    return redirect(url_for("admin.admin_schools"))

# =================================================
# TEACHERS – opslag helpers (JSON)
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
    p.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


# =================================================
# TEACHERS – routes
# =================================================

@admin_bp.get("/teachers")
@admin_required
def admin_teachers():
    schools = _load_schools()
    teachers = _load_teachers()

    school_map = {s.get("id"): s.get("name") for s in schools}

    teachers = sorted(teachers, key=lambda t: (t.get("name") or "").lower())
    schools = sorted(schools, key=lambda s: (s.get("name") or "").lower())

    return render_template(
        "admin/teachers.html",
        teachers=teachers,
        schools=schools,
        school_map=school_map
    )


@admin_bp.post("/teachers")
@admin_required
def admin_teachers_create():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    school_id = (request.form.get("school_id") or "").strip()

    if not name or not email or not school_id:
        flash("Naam, e-mail en school zijn verplicht.", "error")
        return redirect(url_for("admin.admin_teachers"))

    schools = _load_schools()
    if not any(s.get("id") == school_id for s in schools):
        flash("Gekozen school bestaat niet.", "error")
        return redirect(url_for("admin.admin_teachers"))

    teachers = _load_teachers()

    if any((t.get("email") or "").lower() == email for t in teachers):
        flash("Deze e-mail bestaat al als docent.", "error")
        return redirect(url_for("admin.admin_teachers"))

    teachers.append({
        "id": uuid.uuid4().hex,
        "name": name,
        "email": email,
        "school_id": school_id,
        "role": "docent",
        "active": True,
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    _save_teachers(teachers)
    flash("Docent toegevoegd.", "success")
    return redirect(url_for("admin.admin_teachers"))

@admin_bp.post("/teachers/<teacher_id>/delete")
@admin_required
def admin_teachers_delete(teacher_id: str):
    teachers = _load_teachers()
    before = len(teachers)
    teachers = [t for t in teachers if t.get("id") != teacher_id]

    if len(teachers) == before:
        flash("Docent niet gevonden.", "error")
        return redirect(url_for("admin.admin_teachers"))

    _save_teachers(teachers)
    flash("Docent verwijderd.", "success")
    return redirect(url_for("admin.admin_teachers"))
