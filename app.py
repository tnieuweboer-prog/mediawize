from flask import Flask, request, send_file
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
import tempfile
import os

app = Flask(__name__)

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

input[type="text"], textarea, select {{
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
  </nav>
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
    return BASE_PAGE.format(tab_html="active", tab_workbook="", content=content)


def workbook_page(step_count=1, error=None, values=None):
    values = values or {}
    error_block = f"<p style='color:red;font-weight:700'>{error}</p>" if error else ""

    # stapvelden renderen
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
    return BASE_PAGE.format(tab_html="", tab_workbook="active", content=content)


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

    # Als je op "Nieuwe stap" klikt, submit hij ook -> dan alleen rerenderen
    step_count = int(request.form.get("stepCount", "1") or "1")

    # Als er geen "titel" is, nemen we aan dat dit een "addStep" refresh is
    if not request.form.get("titel"):
        values = dict(request.form)
        values["include_materiaalstaat"] = bool(request.form.get("include_materiaalstaat"))
        return workbook_page(step_count=step_count, values=values)

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

        # Materiaalstaat (nu simpel: later bouwen we dit uit)
        mat_rows = int((request.form.get("mat_rows", "0") or "0").strip() or "0")
        if meta["include_materiaalstaat"] and mat_rows > 0:
            # voorlopig lege rijen, later echte velden toevoegen
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
        values = dict(request.form)
        values["include_materiaalstaat"] = bool(request.form.get("include_materiaalstaat"))
        return workbook_page(step_count=step_count, error=f"Fout bij genereren: {e}", values=values)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

