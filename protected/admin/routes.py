# protected/admin/routes.py
import os
from flask import render_template, request, redirect, url_for, session, flash
from . import admin_bp
from .decorators import admin_required

# --------------------------------------------
# Admin credentials via Environment Variables
# --------------------------------------------
# Zet deze op je VPS, NIET in je code/repo:
#   ADMIN_EMAIL=...
#   ADMIN_PASSWORD=...
#
# (In stap 2B maken we dit netter met hash+DB, maar dit is veilig als env vars goed staan.)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

@admin_bp.get("/login")
def admin_login():
    # als je al ingelogd bent, ga door
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

@admin_bp.get("/")
@admin_required
def admin_dashboard():
    return render_template("dashboard.html")

@admin_bp.get("/")
def admin_dashboard():
    # Stap 1: alleen bevestigen dat admin blueprint werkt
    return render_template("dashboard.html")

