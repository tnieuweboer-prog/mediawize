# modules/docent/routes.py
from __future__ import annotations

from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for

bp = Blueprint("docent", __name__, url_prefix="/docent")


# ------------------------------------------------------------
# Mini-guards
# ------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapper


def role_required(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                return redirect(url_for("auth.login"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ------------------------------------------------------------
# Dashboard
# Endpoint: docent.dashboard
# Route: /docent/
# ------------------------------------------------------------
@bp.get("/")
@login_required
@role_required("docent")
def dashboard():
    school = session.get("school") if isinstance(session.get("school"), dict) else None
    brand_name = (school.get("name") if school else None) or "Docent dashboard"

    return render_template(
        "docent/dashboard.html",
        active_tab="docent",
        page_title=brand_name,
    )


# ------------------------------------------------------------
# (Placeholder) Toetsen pagina docent
# Route: /docent/toetsen
# ------------------------------------------------------------
@bp.get("/toetsen")
@login_required
@role_required("docent")
def toetsen_overzicht():
    return render_template(
        "toetsen/docent_overzicht.html",
        active_tab="toetsen",
        page_title="Toetsen",
    )
