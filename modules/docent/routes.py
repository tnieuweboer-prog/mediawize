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

    # template: templates/docent/dashboard.html
    return render_template("docent/dashboard.html", page_title="Docent dashboard")
