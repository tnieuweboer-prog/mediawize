# modules/workbook/routes.py
from __future__ import annotations

from functools import wraps
from flask import Blueprint, render_template, request, send_file, session, redirect, url_for

from .builder import build_workbook_docx_front_and_steps

bp = Blueprint("workbook", __name__, url_prefix="/workbook")


# ------------------------------------------------------------
# Mini-guards (zelfstandig werkend)
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


def _values_from_form():
    values = dict(request.form)
    values["include_materiaalstaat"] = bool(request.form.get("include_materiaalstaat"))
    return values


# ------------------------------------------------------------
# GET /workbook
# ------------------------------------------------------------
@bp.get("/")
@login_required
@role_required("docent")
def workbook_get():
    return render_template(
        "workbook/index.html",
        step_count=1,
        values={},
        error=None,
        active_tab="workbook",
        page_title="Werkboekjes",
    )


# ------------------------------------------------------------
# POST /workbook
# ------------------------------------------------------------
@bp.post("/")
@login_required
@role_required("docent")
def workbook_post():
    step_count = int(request.form.get("stepCount", "1") or "1")
    values = _values_from_form()

    # "Nieuwe stap toevoegen" submit ook het form.
    # Net als je oude logica: als titel ontbreekt, rerender.
    if not request.form.get("titel"):
        return render_template(
            "workbook/index.html",
            step_count=step_count,
            values=values,
            error=None,
            active_tab="workbook",
            page_title="Werkboekjes",
        )

    try:
        # Meta
        meta = {
            "vak": request.form.get("vak", "BWI"),
            "opdracht_titel": request.form.get("titel", ""),
            "profieldeel": request.form.get("profieldeel", ""),
            "docent": request.form.get("docent", ""),
            "duur": request.form.get("duur", ""),
            "include_materiaalstaat": bool(request.form.get("include_materiaalstaat")),
            "materialen": [],
        }

        # Cover image bytes (optioneel)
        cover_file = request.files.get("cover")
        if cover_file and cover_file.filename:
            meta["cover_bytes"] = cover_file.read()

        # Materiaalstaat (nu simpel placeholders)
        mat_rows = int((request.form.get("mat_rows", "0") or "0").strip() or "0")
        if meta["include_materiaalstaat"] and mat_rows > 0:
            for _ in range(mat_rows):
                meta["materialen"].append({
                    "Nummer": "",
                    "Aantal": "",
                    "Benaming": "",
                    "Lengte": "",
                    "Breedte": "",
                    "Dikte": "",
                    "Materiaal": "",
                })

        # Steps bouwen
        steps = []
        for i in range(step_count):
            title = request.form.get(f"step_title_{i}", "")
            text = request.form.get(f"step_text_{i}", "")
            img_file = request.files.get(f"step_img_{i}")

            step = {
                "title": title.strip(),
                "text_blocks": [text.strip()] if text.strip() else [],
                "images": [],
            }

            if img_file and img_file.filename:
                step["images"].append(img_file.read())

            # voeg toe als er iets in staat
            if step["title"] or step["text_blocks"] or step["images"]:
                steps.append(step)

        output = build_workbook_docx_front_and_steps(meta, steps)
        vak = (meta.get("vak") or "BWI").upper()

        return send_file(
            output,
            as_attachment=True,
            download_name=f"werkboekje_{vak}.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except Exception as e:
        return render_template(
            "workbook/index.html",
            step_count=step_count,
            values=values,
            error=f"Fout bij genereren: {e}",
            active_tab="workbook",
            page_title="Werkboekjes",
        )
