from flask import Flask, request, send_file, redirect, url_for, session
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
import tempfile
import os
import secrets
from functools import wraps

app = Flask(__name__)

# ------------------------------------------------------------
# SECRET KEY (zet dit als ENV VAR op je VPS voor productie)
# export FLASK_SECRET_KEY="..."
# ------------------------------------------------------------
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))


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


def role_required(role_name: str):
    @wraps
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role_name:
                return base_message_page(
                    title="Geen toegang",
                    message="Je hebt geen rechten voor deze pagina.",
                    tab="extra",
                    status_code=403,
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ------------------------------------------------------------
# UI BASE (sidebar tabs uitgebreid met Extra/Login)
# ------------------------------------------------------------
BASE_PAGE = """
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Triade Tools</title>

<style>
:root {{
  --sidebar:#0f172a;
  --sidebar-text:#e5e7eb;
  --accent:#22c55e;
  --bg:#f1f5f9;
  --card:#ffffff;
  --border:#e5e7eb;
  --text:#0f172a;
  --muted:#64748b;
}}

* {{ box-sizing:border-box; }}

body {{
  margin:0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  background:var(--bg);
}}

.app {{
  display:flex;
  min-height:100vh;
}}

.sidebar {{
  width:280px;
  background:var(--sidebar);
  color:var(--sidebar-text);
  padding:18px;
  display:flex;
  flex-direction:column;
}}

.logo {{
  display:flex;
  gap:12px;
  margin-bottom:24px;
}}

.logo img {{
  width:60px;
  height:60px;
  border-radius:12px;
}}

.logo-title {{
  font-weight:800;
}}

.logo-sub {{
  font-size:12px;
  color:#94a3b8;
}}

.nav a {{
  display:block;
  padding:12px;
  margin-bottom:6px;
  border-radius:12px;
  text-decoration:none;
  color:var(--sidebar-text);
  font-weight:600;
}}

.nav a.active {{
  background:rgba(34,197,94,0.25);
}}

.nav a:hover {{
  background:rgba(255,255,255,0.08);
}}

.content {{
  flex:1;
  padding:24px;
}}

.card {{
  background:var(--card);
  border-radius:18px;
  border:1px solid var(--border);
  padding:24px;
  max-width:1150px;
}}

h1 {{
  margin-top:0;
}}

p.lead {{
  color:var(--muted);
}}

label {{
  font-size:12px;
  font-weight:700;
  color:var(--muted);
  display:block;
  margin-top:12px;
}}

input[type="text"], input[type="password"], textarea, select {{
  width:100%;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--border);
  margin-top:6px;
}}

button {{
  margin-top:14px;
  background:var(--accent);
  color:white;
  border:none;
  padding:10px 18px;
  border-radius:999px;
  font-weight:800;
  cursor:pointer;
}}

.row {{
  display:grid;
  grid-template-columns: repeat(2, 1fr);
  gap:12px;
}}

.section {{
  margin-top:16px;
  padding-top:16px;
  border-top:1px solid var(--border);
}}

.result-header {{
  display:flex;
  justify-content:space-between;
  margin-top:20px;
  margin-bottom:10px;
}}

.code-area textarea {{
  height: calc(100vh - 360px);
  min-height:320px;
  max-height:900px;
  background:#0b1120;
  color:#e5e7eb;
  font-family:monospace;
  font-size:12px;
  border-radius:14px;
  padding:14px;
  white-space:pre;
}}

.btn-copy {{
  background:#1e293b;
  padding:8px 14px;
}}

.badge {{
  display:inline-block;
  font-size:12px;
  padding:4px 10px;
  border-radius:999px;
  background:#e2e8f0;
  color:#0f172a;
  margin-left:8px;
}}

.topline {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:10px;
  margin-bottom:16px;
}}

.topline small {{
  color: var(--muted);
}}

@media (max-width:900px) {{
  .sidebar {{ display:none; }}
  .code-area textarea {{ height:420px; }}
}}
</style>
</head>

<body>
<div class="app">

<aside class="sidebar">
  <div class="logo">
    <img src="/static/assets/logo.png" alt="Logo">
    <div>
      <div class="logo-title">Triade Tools</div>
      <div class="logo-sub">DOCX & Werkboekjes</div>
    </div>
  </div>

  <nav class="nav">
    <a href="/" class="{tab_html}">💚 DOCX → HTML</a>
    <a href="/workbook" class="{tab_workbook}">📘 Werkboekjes</a>
    <a href="/extra" class="{tab_extra}">🔒 Extra</a>
    <a href="/login" class="{tab_login}">{login_label}</a>
  </nav>

  <div style="margin-top:auto; padding-top:14px; border-top:1px solid rgba(255,255,255,0.12);">
    <div style="font-weight:700;">
      {user_line}
    </div>
    <small style="color:#94a3b8;">{role_line}</small>
  </div>
</aside>

<main class="content">
{content}
</main>

</div>

<script>
async function copyHTML() {{
  const el = document.getElementById("htmlResult");
  if (!el) return;
  const text = el.value;
  try {{
    await navigator.clipboard.writeText(text);
  }} catch {{
    el.select();
    document.execCommand("copy");
  }}
}}

function addStep() {{
  const form = document.getElementById("wbForm");
  const stepCount = parseInt(document.getElementById("stepCount").value || "0", 10);
  document.getElementById("stepCount").value = String(stepCount + 1);
  form.submit();
}}
</script>

</body>
</html>
"""


def render_base(content: str, tab: str):
    tab_html = "active" if tab == "html" else ""
    tab_workbook = "active" if tab == "workbook" else ""
    tab_extra = "active" if tab == "extra" else ""
    tab_login = "active" if tab == "login" else ""

    if session.get("user"):
        login_label = "🚪 Uitloggen"
        user_line = f"Ingelogd"
        role_line = f"Rol: {session.get('role','-')}"
    else:
        login_label = "🔑 Inloggen"
        user_line = "Niet ingelogd"
        role_line = "Rol: -"

    return BASE_PAGE.format(
        tab_html=tab_html,
        tab_workbook=tab_workbook,
        tab_extra=tab_extra,
        tab_login=tab_login,
        login_label=login_label,
        user_line=user_line,
        role_line=role_line,
        content=content,
    )


def base_message_page(title: str, message: str, tab: str, status_code: int = 200):
    content = f"""
    <div class="card">
      <h1>{title}</h1>
      <p class="lead">{message}</p>
    </div>
    """
    return render_base(content, tab), status_code


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
    return render_base(content, "html")


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
      <p class="lead">Templates blijven leidend (BWI/PIE/MVI). We vullen nu cover, materiaalstaat en stappen. Later breiden we dit verder uit.</p>
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
          <p class="lead" style="margin-top:8px;">(We bouwen de invoervelden per regel later dynamischer; nu is dit een snelle basis.)</p>
        </div>

        {step_blocks}

        <div class="section">
          <button type="button" class="btn-copy" onclick="addStep()">➕ Nieuwe stap toevoegen</button>
          <button type="submit">📘 Werkboekje genereren</button>
        </div>

      </form>
    </div>
    """
    return render_base(content, "workbook")


# ------------------------------------------------------------
# ROUTES: Existing
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


@app.route("/workbook", methods=["GET", "POST"])
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
# ROUTES: Login / Logout (dummy)
# - GET /login: form
# - POST /login: sets session
# - GET /logout: clears session
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
        <p class="lead">Tip: als je later Microsoft SSO toevoegt, blijft de rest (extra/dashboard) hetzelfde.</p>
      </div>
    </div>
    """
    return render_base(content, "login")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Als je al ingelogd bent -> logout knop laten werken via /login
    if request.method == "GET" and session.get("user"):
        return redirect(url_for("logout"))

    if request.method == "GET":
        return login_page(next_url=request.args.get("next", "/extra"))

    # POST
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

    # basic dashboard
    if role == "docent":
        content = f"""
        <div class="card">
          <h1>Extra – Docent</h1>
          <p class="lead">Hier komt straks de toets-generator (upload → controle → klaarzetten → submissions).</p>

          <div class="section">
            <h3>Status</h3>
            <p class="lead">Ingelogd als <b>{session.get("user","")}</b> (docent).</p>
            <p class="lead">Volgende stap: een pagina voor “Toetsen” + “Inzendingen”.</p>
          </div>

          <div class="section">
            <a href="/logout"><button type="button" class="btn-copy">Uitloggen</button></a>
          </div>
        </div>
        """
        return render_base(content, "extra")

    if role == "leerling":
        content = f"""
        <div class="card">
          <h1>Extra – Leerling</h1>
          <p class="lead">Hier komt straks “Toetscode invoeren” → toets maken → verzenden.</p>

          <div class="section">
            <p class="lead">Ingelogd als <b>{session.get("user","")}</b> (leerling).</p>
            <p class="lead">Volgende stap: toetscode + startknop.</p>
          </div>

          <div class="section">
            <a href="/logout"><button type="button" class="btn-copy">Uitloggen</button></a>
          </div>
        </div>
        """
        return render_base(content, "extra")

    return base_message_page(
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


