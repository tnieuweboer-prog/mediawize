from flask import Flask, request, send_file
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
from html import escape
import tempfile
import os

app = Flask(__name__)

# -------------------------------------------------
# BASE DASHBOARD TEMPLATE
# Let op: we gebruiken .format(), dus ALLE { } in CSS/JS moeten {{ }} zijn.
# -------------------------------------------------
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
  color:var(--text);
}}

.app {{
  display:flex;
  min-height:100vh;
}}

.sidebar {{
  width:280px;
  background:var(--sidebar);
  color:var(--sidebar-text);
  display:flex;
  flex-direction:column;
  padding:18px;
}}

.logo {{
  display:flex;
  align-items:center;
  gap:12px;
  margin-bottom:24px;
}}

.logo img {{
  width:58px;
  height:58px;
  border-radius:12px;
  background: rgba(255,255,255,0.06);
}}

.logo-title {{
  font-weight:850;
  font-size:16px;
  line-height:1.1;
}}

.logo-sub {{
  font-size:11px;
  color:#94a3b8;
  margin-top:2px;
}}

.nav a {{
  display:block;
  padding:12px 14px;
  margin-bottom:8px;
  border-radius:12px;
  color:var(--sidebar-text);
  text-decoration:none;
  font-weight:650;
  font-size:14px;
}}

.nav a.active {{
  background:rgba(34,197,94,0.22);
  color:#bbf7d0;
}}

.nav a:hover {{
  background:rgba(255,255,255,0.08);
}}

.sidebar-footer {{
  margin-top:auto;
  font-size:12px;
  color:#94a3b8;
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
  margin:0 0 6px 0;
  font-size:20px;
}}

p.lead {{
  color:var(--muted);
  margin:0 0 18px 0;
}}

.error {{
  background:#fee2e2;
  color:#991b1b;
  padding:12px;
  border-radius:12px;
  font-weight:650;
  margin-bottom:16px;
}}

label {{
  display:block;
  font-size:12px;
  color:var(--muted);
  font-weight:700;
  margin: 10px 0 6px 0;
}}

input[type="text"], textarea {{
  width:100%;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--border);
  margin-bottom:8px;
  font-size:14px;
}}

input[type="text"]:focus, textarea:focus {{
  outline:none;
  border-color: rgba(34,197,94,0.5);
  box-shadow: 0 0 0 4px rgba(34,197,94,0.14);
}}

.row {{
  display:grid;
  grid-template-columns: repeat(2, 1fr);
  gap:12px;
}}

.actions {{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  margin-top:10px;
}}

.btn-primary {{
  background:var(--accent);
  color:white;
  border:none;
  padding:10px 18px;
  border-radius:999px;
  font-weight:800;
  cursor:pointer;
}}

.btn-primary:hover {{
  filter:brightness(1.05);
}}

.btn-copy {{
  background:#1e293b;
  color:#e5e7eb;
  border:none;
  padding:9px 14px;
  border-radius:999px;
  font-weight:800;
  cursor:pointer;
}}

.btn-copy:hover {{
  background:#334155;
}}

.result-header {{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:12px;
  margin-top:14px;
  margin-bottom:10px;
}}

.result-header h2 {{
  margin:0;
  font-size:16px;
}}

.result-header .sub {{
  margin:4px 0 0 0;
  font-size:12px;
  color:var(--muted);
}}

.code-area textarea {{
  width:100%;
  height: calc(100vh - 360px);
  min-height: 320px;
  max-height: 900px;
  background:#0b1120;
  color:#e5e7eb;
  border:1px solid rgba(255,255,255,0.08);
  border-radius:14px;
  padding:14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size:12px;
  line-height:1.45;
  white-space:pre;
}}

@media (max-width: 1000px) {{
  .row {{ grid-template-columns: 1fr; }}
}}

@media (max-width:900px) {{
  .sidebar {{ display:none; }}
  .code-area textarea {{ height: 420px; }}
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

  <div class="sidebar-footer">
    SG De Triade · interne tool
  </div>
</aside>

<main class="content">
{content}
</main>

</div>

<script>
function copyHTML() {{
  const el = document.getElementById("htmlResult");
  if (!el) return;
  el.select();
  el.setSelectionRange(0, 999999);
  document.execCommand("copy");
}}
</script>

</body>
</html>
"""

# -------------------------------------------------
# DOCX → HTML PAGE
# -------------------------------------------------
def html_page(error: str | None = None, result: str | None = None):
    error_block = f"<div class='error'>{escape(error)}</div>" if error else ""

    # Result block: ALLEEN tonen als result bestaat
    if result:
        result_block = f"""
        <div class="result-header">
          <div>
            <h2>Gegenereerde HTML</h2>
            <p class="sub">Klik op kopiëren en plak in Stermonitor / ELO</p>
          </div>
          <button type="button" class="btn-copy" onclick="copyHTML()">📋 Kopiëren</button>
        </div>

        <div class="code-area">
          <textarea id="htmlResult" readonly>{escape(result)}</textarea>
        </div>
        """
    else:
        result_block = ""

    content = f"""
    <div class="card">
      <h1>DOCX → HTML</h1>
      <p class="lead">Upload een Word-bestand en kopieer de HTML-code.</p>

      {error_block}

      <form method="POST" enctype="multipart/form-data">
        <label>Word-bestand (.docx)</label>
        <input type="file" name="file" accept=".docx" required>

        <div class="actions">
          <button class="btn-primary" type="submit">Converteren</button>
        </div>
      </form>

      {result_block}
    </div>
    """

    return BASE_PAGE.format(tab_html="active", tab_workbook="", content=content)

# -------------------------------------------------
# WERKBOEKJES PAGE (A + beetje C)
# -------------------------------------------------
def workbook_page(error: str | None = None):
    error_block = f"<div class='error'>{escape(error)}</div>" if error else ""

    content = f"""
    <div class="card">
      <h1>Werkboekjes-generator</h1>
      <p class="lead">Eenvoudige basisversie. Vul de kerngegevens in en download direct een Word-werkboekje.</p>

      {error_block}

      <form method="POST">
        <label>Opdracht titel</label>
        <input type="text" name="titel" required placeholder="Bijv. Recyclelamp ontwerpen">

        <div class="row">
          <div>
            <label>Vak</label>
            <input type="text" name="vak" value="BWI">
          </div>
          <div>
            <label>Docent</label>
            <input type="text" name="docent" placeholder="Naam docent">
          </div>
        </div>

        <label>Duur van de opdracht</label>
        <input type="text" name="duur" value="10 x 45 minuten">

        <div class="actions">
          <button class="btn-primary" type="submit">📘 Werkboekje genereren</button>
        </div>
      </form>
    </div>
    """

    return BASE_PAGE.format(tab_html="", tab_workbook="active", content=content)

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return html_page()

    if "file" not in request.files:
        return html_page(error="Geen bestand geüpload.")

    file = request.files["file"]
    if not file or file.filename == "":
        return html_page(error="Geen geldig bestand gekozen.")

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
        return workbook_page()

    try:
        meta = {
            "opdracht_titel": (request.form.get("titel") or "").strip(),
            "vak": (request.form.get("vak") or "BWI").strip(),
            "docent": (request.form.get("docent") or "").strip(),
            "duur": (request.form.get("duur") or "").strip(),
            "include_materiaalstaat": False,
        }

        # A-versie: geen stappen, maar builder maakt wel een nette cover
        steps = []

        output = build_workbook_docx_front_and_steps(meta, steps)

        return send_file(
            output,
            as_attachment=True,
            download_name="werkboekje.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        return workbook_page(error=f"Fout bij genereren: {e}")

# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

