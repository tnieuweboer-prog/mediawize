# modules/workbook/routes.py
from __future__ import annotations

from flask import Blueprint, render_template, request, send_file
from werkzeug.datastructures import MultiDict

from workbook_builder import build_workbook_docx_front_and_steps

bp = Blueprint("workbook", __name__, url_prefix="/workbook")


def _to_values(form: MultiDict) -> dict:
    """
    Zet request.form om naar een simpele dict die templates kunnen gebruiken.
    Checkboxen bestaan niet in form als ze uit staan -> die vangen we op.
    """
    values = dict(form)
    values["include_materiaalstaat"] = bool(form.get("include_materiaalstaat"))
    return values


@bp.get("/")
def index_get():
    # start met 1 stap
    return render_template("workbook/index.html", step_count=1, values={}, error=None)


@bp.post("/")
def index_post():
    step_count = int(request.form.get("stepCount", "1") or "1")
    values = _to_values(request.form)

    # Als gebruiker op "Nieuwe stap toevoegen" klikt, post hij ook.
    # We herkennen dat door het ontbreken van titel (zelfde als jouw oude logica).
    if not request.form.get("titel"):
        return render_template("workbook/index.html", step_count=step_count, values=values, error=None)

    try:
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

        # Materiaalstaat (nu simpel: later echte velden per regel)
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
        )

