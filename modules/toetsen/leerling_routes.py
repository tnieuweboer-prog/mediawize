# modules/toetsen/leerling_routes.py
from __future__ import annotations

from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for

bp = Blueprint("leerling", __name__, url_prefix="/leerling")


# ------------------------------------------------------------
# Mini-guards (zodat dit bestand zelfstandig werkt)
# Later vervangen door modules/core/permissions.py
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
# Endpoint: leerling.dashboard
# Route: /leerling
# ------------------------------------------------------------
@bp.get("/")
@login_required
@role_required("leerling")
def dashboard():
    return render_template(
        "leerling/dashboard.html",
        active_tab="leerling",
        page_title="Leerling dashboard",
    )


# ------------------------------------------------------------
# (Placeholder) Toets maken
# Route: /leerling/toets
# ------------------------------------------------------------
@bp.get("/toets")
@login_required
@role_required("leerling")
def toets_maken():
    # Later: toetscode invoer + random volgorde + verzenden
    return render_template(
        "toetsen/leerling_toets.html",
        active_tab="toets_maken",
        page_title="Toets maken",
    )

