# modules/toetsen/docent_routes.py
from __future__ import annotations

from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, request

bp = Blueprint("docent", __name__, url_prefix="/docent")


# ------------------------------------------------------------
# Mini-guards (zodat dit bestand zelfstandig werkt)
# Later kunnen we dit vervangen door modules/core/permissions.py
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
# Route: /docent
# ------------------------------------------------------------
@bp.get("/")
@login_required
@role_required("docent")
def dashboard():
    # active_tab gebruik je in base.html om menu-item actief te maken
    return render_template(
        "docent/dashboard.html",
        active_tab="docent",
        page_title="Docent dashboard",
    )


# ------------------------------------------------------------
# (Placeholder) Toetsen pagina docent
# Route: /docent/toetsen
# ------------------------------------------------------------
@bp.get("/toetsen")
@login_required
@role_required("docent")
def toetsen_overzicht():
    # Later vullen we dit met: lijst toetsen, nieuwe toets aanmaken, etc.
    return render_template(
        "toetsen/docent_overzicht.html",
        active_tab="toetsen",
        page_title="Toetsen",
    )

