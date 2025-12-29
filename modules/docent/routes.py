# modules/docent/routes.py
from __future__ import annotations

from flask import Blueprint, render_template, session, redirect, url_for

bp = Blueprint("docent", __name__, url_prefix="/docent")


def _login_required_docent():
    if not session.get("user"):
        return redirect(url_for("auth.login"))
    if session.get("role") != "docent":
        return redirect(url_for("home"))
    return None


@bp.get("/")
def dashboard():
    guard = _login_required_docent()
    if guard:
        return guard

    # school info komt uit session["school"] (gezet bij login)
    school = session.get("school") if isinstance(session.get("school"), dict) else None
    brand_name = (school.get("name") if school else None) or "Docent dashboard"

    return render_template(
        "docent/dashboard.html",
        page_title=brand_name,
        active_tab="docent",
    )
