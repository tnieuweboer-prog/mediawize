# modules/html_tool/routes.py
from __future__ import annotations

import os
import tempfile
from functools import wraps

from flask import Blueprint, render_template, request, session, redirect, url_for

from .converter import docx_to_html

bp = Blueprint("html_tool", __name__, url_prefix="/html")


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


def role_required(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                return redirect(url_for("auth.login_get"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ------------------------------------------------------------
# GET /html
# ------------------------------------------------------------
@bp.get("/")
@login_required
@role_required("docent")
def index_get():
    return render_template(
        "html_tool/index.html",
        result=None,
        error=None,
        active_tab="html",
        page_title="DOCX → HTML",
    )


# ------------------------------------------------------------
# POST /html
# ------------------------------------------------------------
@bp.post("/")
@login_required
@role_required("docent")
def index_post():
    if "file" not in request.files:
        return render_template(
            "html_tool/index.html",
            result=None,
            error="Geen bestand geüpload",
            active_tab="html",
            page_title="DOCX → HTML",
        )

    f = request.files["file"]
    if not f or not f.filename:
        return render_template(
            "html_tool/index.html",
            result=None,
            error="Geen geldig bestand gekozen",
            active_tab="html",
            page_title="DOCX → HTML",
        )

    # Alleen .docx toestaan
    if not f.filename.lower().endswith(".docx"):
        return render_template(
            "html_tool/index.html",
            result=None,
            error="Upload een .docx bestand",
            active_tab="html",
            page_title="DOCX → HTML",
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name

        html = docx_to_html(tmp_path)

        return render_template(
            "html_tool/index.html",
            result=html,
            error=None,
            active_tab="html",
            page_title="DOCX → HTML",
        )

    except Exception as e:
        return render_template(
            "html_tool/index.html",
            result=None,
            error=f"Fout: {e}",
            active_tab="html",
            page_title="DOCX → HTML",
        )

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

