from __future__ import annotations

from flask import Blueprint, render_template, session, redirect, url_for

bp = Blueprint("leerling", __name__, url_prefix="/leerling")


def _login_required_leerling():
    if not session.get("user"):
        return redirect(url_for("auth.login_get"))
    if session.get("role") != "leerling":
        return redirect(url_for("home"))
    return None


@bp.get("/")
def dashboard():
    guard = _login_required_leerling()
    if guard:
        return guard

    # template: templates/leerling/dashboard.html
    return render_template("leerling/dashboard.html", page_title="Leerling dashboard")
