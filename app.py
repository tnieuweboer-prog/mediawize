from flask import (
    Flask, request, send_file, redirect, url_for, session, render_template_string
)
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
# Render helper: content strings in templates/base.html
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
# Auth helpers (dummy login / signup)
# ------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def role_required(role_name: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role_name:
                return message_page(
                    title="Geen toegang",
                    message="Je hebt geen rechten voor deze pagina.",
                    tab="home",
                    status_code=403
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ------------------------------------------------------------
# Landing page (publiek)
# ------------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    content = """
    <div class="pub-hero">
      <h1>Tools voor lessen, opdrachten en toetsen</h1>
      <p>
        Triade Tools helpt docenten bij het omzetten van lesmateriaal (DOCX → HTML),
        het genereren van werkboekjes en het klaarzetten van toetsen.
        Leerlingen maken toetsen online en leveren in via de leerlingomgeving.
      </p>

      <div class="pub-cta">
        <a class="btn-link" href="/login"><button type="button">🔑 Inloggen</button></a>
        <a class="btn-link" href="/signup"><button type="button" class="btn-ghost">✨ Account maken</button></a>
      </div>
    </div>

    <div class="pub-modules">
      <div class="pub-module">
        <h3>💚 DOCX → HTML</h3>
        <p>Word omzetten naar Stermonitor-HTML met kopieerknop en nette opmaak.</p>
      </div>
      <div class="pub-module">
        <h3>📘 Werkboekjes</h3>
        <p>Werkboekjes maken op basis van BWI/PIE/MVI templates, met cover en stappen.</p>
      </div>
      <div class="pub-module">
        <h3>📝 Toetsen</h3>
        <p>Docent zet klaar, leerling maakt, docent downloadt — daarna opruimen.</p>
      </div>
    </div>
    """
    return render_public_page(content, "home")

# ------------------------------------------------------------
# Signup (publiek) - dummy “account maken”
# ------------------------------------------------------------
def signup_page(error: str = None):
    error_block = f"<p style='color:red;font-weight:700'>{error}</p>" if error else ""
    content = f"""
    <div class="card">
      <h1>Account maken</h1>
      <p class="lead">Tijdelijk: maak een account aan door rol + naam te kiezen. Later Microsoft (Atlas) login.</p>
      {error_block}

      <form method="POST">
        <label>Ik ben</label>
        <select name="role" required>
          <option value="docent">Docent</option>
          <option value="leerling">Leerling</option>
        </select>

        <label>Naam</label>
        <input type="text" name="name" placeholder="bijv. Tom of Emy" required>

        <button type="submit">Account maken</button>
      </form>

      <div class="section">
        <p class="lead">Heb je al een account? <a href="/login">Inloggen</a></p>
      </div>
    </div>
    """
    return render_page(content, "signup")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return signup_page()

    role = (request.form.get("role") or "").strip()
    name = (request.form.get("name") or "").strip()

    if role not in ("docent", "leerling"):
        return signup_page("Kies een geldige rol.")
    if not name:
        return signup_page("Vul je naam in.")

    # Dummy: “account” = sessie
    session["user"] = name
    session["role"] = role

    # Na signup direct naar juiste dashboard
    if role == "docent":
        return redirect(url_for("docent_dashboard"))
    return redirect(url_for("leerling_dashboard"))


# ------------------------------------------------------------
# Login / Logout (publiek) - dummy
# ------------------------------------------------------------
def login_page(error: str = None, next_url: str = None):
    error_block = f"<p style='color:red;font-weight:700'>{error}</p>" if error else ""
    next_safe = next_url or "/"

    content = f"""
    <div class="card">
      <h1>Inloggen</h1>
      <p class="lead">Tijdelijk: kies een rol. Later vervangen door Microsoft (Atlas) login.</p>
      {error_block}

      <form method="POST">
        <input type="hidden" name="next" value="{next_safe}">

        <label>Rol</label>
        <select name="role" required>
          <option value="docent">Docent</option>
          <option value="leerling">Leerling</option>
        </select>

        <label>Naam (optioneel)</label>
        <input type="text" name="name" placeholder="bijv. Tom of Emy">

        <button type="submit">Inloggen</button>
      </form>

      <div class="section">
        <p class="lead">Nog geen account? <a href="/signup">Account maken</a></p>
      </div>
    </div>
    """
    return render_page(content, "login")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Als je al ingelogd bent en je gaat naar /login: stuur naar dashboard
    if request.method == "GET" and session.get("user"):
        if session.get("role") == "docent":
            return redirect(url_for("docent_dashboard"))
        if session.get("role") == "leerling":
            return redirect(url_for("leerling_dashboard"))
        return redirect(url_for("home"))

    if request.method == "GET":
        return login_page(next_url=request.args.get("next", "/"))

    role = (request.form.get("role") or "").strip()
    name = (request.form.get("name") or "user").strip() or "user"

    if role not in ("docent", "leerling"):
        return login_page(error="Kies een geldige rol.", next_url=request.form.get("next", "/"))

    session["user"] = name
    session["role"] = role

    # Na login altijd naar dashboard (zoals jij wilt)
    if role == "docent":
        return redirect(url_for("docent_dashboard"))
    return redirect(url_for("leerling_dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ------------------------------------------------------------
# Dashboards
# ------------------------------------------------------------
@app.route("/docent", methods=["GET"])
@login_required
@role_required("docent")
def docent_dashboard():
    content = f"""
    <div class="card">
      <h1>Docent dashboard</h1>
      <p class="lead">Kies een module om mee te werken.</p>

      <div class="module-grid">
        <div class="module-card">
          <p class="module-title">💚 DOCX → HTML</p>
          <p class="module-desc">Converteren naar Stermonitor HTML.</p>
          <div class="cta-row">
            <a class="btn-link" href="/html"><button type="button">Open module</button></a>
          </div>
        </div>

        <div class="module-card">
          <p class="module-title">📘 Werkboekjes</p>
          <p class="module-desc">Werkboekjes genereren vanuit templates.</p>
          <div class="cta-row">
            <a class="btn-link" href="/workbook"><button type="button">Open module</button></a>
          </div>
        </div>

        <div class="module-card">
          <p class="module-title">📝 Toetsen</p>
          <p class="module-desc">Toetsen klaarzetten en inzendingen beheren.</p>
          <div class="cta-row">
            <a class="btn-link" href="/toetsen"><button type="button">Open module</button></a>
          </div>
        </div>
      </div>

      <div class="section">
        <p class="lead">Ingelogd als <b>{session.get("user","")}</b> (docent).</p>
      </div>
    </div>
    """
    return render_page(content, "docent")


@app.route("/leerling", methods=["GET"])
@login_required
@role_required("leerling")
def leerling_dashboard():
    content = f"""
    <div class="card">
      <h1>Leerling dashboard</h1>
      <p class="lead">Start een toets met een toetscode.</p>

      <div class="module-grid">
        <div class="module-card">
          <p class="module-title">📝 Toets maken</p>
          <p class="module-desc">Voer de toetscode in en start.</p>
          <div class="cta-row">
            <a class="btn-link" href="/toets-maken"><button type="button">Start</button></a>
          </div>
        </div>
      </div>

      <div class="section">
        <p class="lead">Ingelogd als <b>{session.get("user","")}</b> (leerling).</p>
      </div>
    </div>
    """
    return render_page(content, "leerling")


# ------------------------------------------------------------
# DOCX → HTML module (docent-only)
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


@app.route("/html", methods=["GET", "POST"])
@login_required
@role_required("docent")
def html_tool():
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
# Werkboekjes module (docent-only)
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


@app.route("/workbook", methods=["GET", "POST"])
@login_required
@role_required("docent")
def workbook():
    if request.method == "GET":
        return workbook_page(step_count=1)

    step_count = int(request.form.get("stepCount", "1") or "1")

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
# Toets module (placeholder)
# ------------------------------------------------------------
@app.route("/toetsen", methods=["GET"])
@login_required
@role_required("docent")
def toetsen_docent():
    content = """
    <div class="card">
      <h1>Toetsen</h1>
      <p class="lead">Hier bouwen we straks: Nieuwe toets → vragen → toetscode → inzendingen.</p>

      <div class="section">
        <button type="button" class="btn-secondary" disabled>➕ Nieuwe toets (komt zo)</button>
      </div>
    </div>
    """
    return render_page(content, "toetsen")


@app.route("/toets-maken", methods=["GET"])
@login_required
@role_required("leerling")
def toets_maken_leerling():
    content = """
    <div class="card">
      <h1>Toets maken</h1>
      <p class="lead">Hier komt straks: toetscode invoeren → start → vragen → verzenden.</p>

      <div class="section">
        <label>Toetscode</label>
        <input type="text" placeholder="bijv. TRIADE-7H2-AB12" disabled>
        <button type="button" disabled>Start</button>
      </div>
    </div>
    """
    return render_page(content, "toets_maken")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

