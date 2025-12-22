# modules/admin/routes.py
from __future__ import annotations

from functools import wraps
from flask import Blueprint, render_template, request, session, redirect, url_for

bp = Blueprint("admin", __name__, url_prefix="/admin")


# ------------------------------------------------------------
# Mini-guards (zelfstandig werkend)
# Later vervangen door modules/core/permissions.py
# ------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("auth.login_get"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # inject_globals zet current_user.is_admin op basis van session["is_admin"]
        if not session.get("is_admin"):
            return redirect(url_for("docent.dashboard"))
        return fn(*args, **kwargs)
    return wrapper


@bp.get("/")
@login_required
@admin_required
def index():
    # Voor nu: alleen een placeholder beheerpagina
    return render_template(
        "admin/index.html",
        active_tab="admin",
        page_title="Beheer",
    )

