from flask import Flask, request, send_file, redirect, url_for, session, render_template_string
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
import tempfile
import os
import secrets
from functools import wraps

app = Flask(__name__)

# Secret key voor sessions (zet dit als ENV VAR op VPS voor productie)
# export FLASK_SECRET_KEY="..."
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))


# ------------------------------------------------------------
# Helpers: render binnen base.html
# ------------------------------------------------------------
def render_page(inner_html: str, active_tab: str):
    tpl = """
    {% extends "base.html" %}
    {% block content %}
    """ + inner_html + """
    {% endblock %}
    """
    return render_template_string(tpl, active_tab=active_tab)


def message_page(title: str, message: str, tab: str, status_code: int = 200):
    content = f"""
    <div class="card">
      <h1>{title}</h1>
      <p class="lead">{message}</p>
    </div>
    """
    return render_page(content, tab), status_code


# ------------------------------------------------------------
# AUTH HELPERS (dummy login: docent/leerling kiezen)
# ------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


# ------------------------------------------------------------
# PAGES: DOCX → HTML
# ------------------------------------------------------------
def html_page(result=None, error=None):
    error_block = f"<p style='color:red;font-weight:700'>{error}</p>" if error else ""

    result_block = ""
    if result:
        safe = result.replace("</textarea", "</text_area")
        result_block = f"""
        <div class="result-header">
          <h2>Gegenereerde HTML</h2>
          <button type="button" class="btn-copy" onclick="copyHTML()">📋 Kopiëren</button>
        </div>
        <div class="code-area">
          <textarea id="htmlResult" readonly>{safe}</textarea>
        </div>
        """

    content = f"""
    <div class="card">
      <h1>DOCX → HTML</h1>
      <p class="lead">Upload een Word-bestand en kopieer de HTML.</p>
      {error_block}
      <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".docx" required>
        <button type="submit">Converteren</button>
      </form>
      {result_block}
    </div>
    """
    return render_page(content, "html")


# ------------------------------------------------------------
# PAGES: Werkboekjes
# ------------------------------------------------------------
def workbook_page(step_count=1, error=None, values=None):
    values = values or {}
    error_block = f"<p style='color:red;font-weight:700'>{error}</p>" if error else ""

    step_blocks = ""
    for i in range(step_count):
        step_blocks += f"""
        <div class="section">
          <h3>Stap {i+1}</h3>
          <label>Titel</label>
          <input type="text" name="step_title_{i}" value="{values.get(f"step_title_{i}", "")}">
          <label>Tekst</label>
          <textarea name="step_text_{i}" rows="4">{values.get(f"step_text_{i}", "")}</textarea>
          <label>Afbeelding (optioneel)</label>
          <input type="file" name="step_img_{i}" accept=".png,.jpg,.jpeg">
        </div>
        """

    content = f"""
    <div class="card">
      <h1>Werkboekjes-generator</h1>
      <p class="lead">Templates blijven leidend (BWI/PIE/MVI). We vullen nu cover, materiaalstaat en stappen.</p>
      {error_block}

      <form id="wbForm" method="POST" enctype="multipart/form-data">

        <input type="hidden" id="stepCount" name="stepCount" value="{step_count}">

        <label>Vak (template)</label>
        <select name="vak" required>
          <option value="BWI" {"selected" if values.get("vak","BWI")=="BWI" else ""}>BWI</option>
          <option value="PIE" {"selected" if values.get("vak")=="PIE" else ""}>PIE</option>
          <option value="MVI" {"selected" if values.get("vak")=="MVI" else ""}>MVI</option>
        </select>

        <div class="row">
          <div>
            <label>Opdracht titel</label>
            <input type="text" name="titel" required value="{values.get("titel","")}">
          </div>
          <div>
            <label>Profieldeel (optioneel)</label>
            <input type="text" name="profieldeel" value="{values.get("profieldeel","")}">
          </div>
        </div>

        <div class="row">
          <div>
            <label>Docent</label>
            <input type="text" name="docent" value="{values.get("docent","")}">
          </div>
          <div>
            <label>Duur</label>
            <input type="text" name="duur" value="{values.get("duur","10 x 45 minuten")}">
          </div>
        </div>

        <div class="section">
          <h3>Omslag</h3>
          <label>Cover-afbeelding (optioneel)</label>
          <input type="file" name="cover" accept=".png,.jpg,.jpeg">
        </div>

        <div class="section">
          <h3>Materiaalstaat</h3>
          <label><input type="checkbox" name="include_materiaalstaat" {"checked" if values.get("include_materiaalstaat") else ""}> Materiaalstaat toevoegen</label>

          <label>Aantal regels (bijv. 5)</label>
          <input type="text" name="mat_rows" value="{values.get("mat_rows","3")}">
          <p class="lead" style="margin-top:8px;">(Later maken we echte velden per regel; nu is dit een snelle basis.)</p>
        </div>

        {step_blocks}

        <div class="section">
          <button type="button" class="btn-copy" onclick="addStep()">➕ Nieuwe stap toevoegen</button>
          <button type="submit">📘 Werkboekje genereren</button>
        </div>

      </form>
    </div>
    """
    return render_page(content, "workbook")


# ------------------------------------------------------------
# ROUTES: DOCX → HTML
# ------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return html_page()

    if "file" not in request.files:
        return html_page(error="Geen bestand geüpload")

    file = request.files["file"]
    if not file or file.filename == "":
        return html_page(error="Geen geldig bestand gekozen")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file.save(tmp.name)
        path = tmp.name

    try:
        html = docx_to_html(path)
        return html_page(result=html)
    except Exception as e:
        return html_page(error=f"Fout: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)


# ------------------------------------------------------------
# ROUTES: Werkboekjes
# ------------------------------------------------------------
@app.route("/workbook", methods=["GET", "POST"])
def workbook():
    if request.method == "GET":
        return workbook_page(step_count=1)

    step_count = int(request.form.get("stepCount", "1") or "1")

    # Als je op "Nieuwe stap" klikt (submit zonder titel) -> alleen rerenderen
    if not request.form.get("titel"):
        values = dict(request.form)
        values["include_materiaalstaat"] = bool(request.form.get("include_materiaalstaat"))
        return workbook_page(step_count=step_count, values=values)

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

        cover_file = request.files.get("cover")
        if cover_file and cover_file.filename:
            meta["cover_bytes"] = cover_file.read()

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
        values = dict(request.form)
        values["include_materiaalstaat"] = bool(request.form.get("include_materiaalstaat"))
        return workbook_page(step_count=step_count, error=f"Fout bij genereren: {e}", values=values)


# ------------------------------------------------------------
# ROUTES: Login / Logout (dummy)
# ------------------------------------------------------------
def login_page(error: str = None, next_url: str = "/extra"):
    error_block = f"<p style='color:red;font-weight:700'>{error}</p>" if error else ""
    next_safe = next_url or "/extra"

    content = f"""
    <div class="card">
      <div class="topline">
        <div>
          <h1>Inloggen</h1>
          <p class="lead">Tijdelijk: kies een rol. Later vervangen door Microsoft (Atlas) login.</p>
        </div>
        <div>
          <span class="badge">dummy login</span>
        </div>
      </div>

      {error_block}

      <form method="POST">
        <input type="hidden" name="next" value="{next_safe}">
        <label>Rol</label>
        <select name="role" required>
          <option value="docent">Docent</option>
          <option value="leerling">Leerling</option>
        </select>

        <label>Naam (optioneel)</label>
        <input type="text" name="name" placeholder="bijv. Tom">

        <button type="submit">Inloggen</button>
      </form>

      <div class="section">
        <p class="lead">Tip: later kun je dit 1-op-1 vervangen door Microsoft SSO.</p>
      </div>
    </div>
    """
    return render_page(content, "login")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Als je al ingelogd bent en je gaat naar /login -> logout flow
    if request.method == "GET" and session.get("user"):
        return redirect(url_for("logout"))

    if request.method == "GET":
        return login_page(next_url=request.args.get("next", "/extra"))

    role = (request.form.get("role") or "").strip()
    name = (request.form.get("name") or "user").strip() or "user"
    next_url = request.form.get("next") or "/extra"

    if role not in ("docent", "leerling"):
        return login_page(error="Kies een geldige rol.", next_url=next_url)

    session["user"] = name
    session["role"] = role
    return redirect(next_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ------------------------------------------------------------
# ROUTES: Extra (afgeschermd)
# ------------------------------------------------------------
@app.route("/extra", methods=["GET"])
@login_required
def extra():
    role = session.get("role")

    if role == "docent":
        content = f"""
        <div class="card">
          <h1>Extra – Docent</h1>
          <p class="lead">Hier komt straks de toets-generator (upload → controle → klaarzetten → inzendingen).</p>

          <div class="section">
            <h3>Status</h3>
            <p class="lead">Ingelogd als <b>{session.get("user","")}</b> (docent).</p>
            <p class="lead">Volgende stap: pagina’s /docent en /leerling bouwen zonder data-opslag van leerlingnamen.</p>
          </div>
        </div>
        """
        return render_page(content, "extra")

    if role == "leerling":
        content = f"""
        <div class="card">
          <h1>Extra – Leerling</h1>
          <p class="lead">Hier komt straks “Toetscode invoeren” → toets maken → verzenden.</p>

          <div class="section">
            <p class="lead">Ingelogd als <b>{session.get("user","")}</b> (leerling).</p>
            <p class="lead">Volgende stap: toetscode + startknop.</p>
          </div>
        </div>
        """
        return render_page(content, "extra")

    return message_page(
        title="Rol ontbreekt",
        message="Je rol is niet gezet. Log opnieuw in.",
        tab="extra",
        status_code=400
    )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
if __name__ == "__main__":
    # debug True alleen lokaal. Op VPS achter gunicorn: debug=False
    app.run(host="0.0.0.0", port=8501, debug=True)

