from flask import Flask, request, send_file
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
import tempfile
import os

app = Flask(__name__)

# -------------------------------------------------
# BASE TEMPLATE
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

input[type="text"], textarea {{
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
    <img src="/static/assets/logo.png">
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
</script>

</body>
</html>
"""

# -------------------------------------------------
# HTML PAGE
# -------------------------------------------------
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

# -------------------------------------------------
# WORKBOOK PAGE
# -------------------------------------------------
def workbook_page(error=None):
    error_block = f"<p style='color:red;font-weight:700'>{error}</p>" if error else ""

    content = f"""
    <div class="card">
      <h1>Werkboekjes-generator</h1>
      <p class="lead">Basisversie om snel een werkboekje te maken.</p>
      {error_block}
      <form method="POST">
        <label>Opdracht titel</label>
        <input type="text" name="titel" required>

        <label>Vak</label>
        <input type="text" name="vak" value="BWI">

        <label>Docent</label>
        <input type="text" name="docent">

        <label>Duur</label>
        <input type="text" name="duur" value="10 x 45 minuten">

        <button type="submit">📘 Werkboekje genereren</button>
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
    finally:
        os.remove(path)

@app.route("/workbook", methods=["GET", "POST"])
def workbook():
    if request.method == "GET":
        return workbook_page()

    meta = {
        "opdracht_titel": request.form.get("titel",""),
        "vak": request.form.get("vak",""),
        "docent": request.form.get("docent",""),
        "duur": request.form.get("duur",""),
        "include_materiaalstaat": False,
    }

    output = build_workbook_docx_front_and_steps(meta, [])
    return send_file(
        output,
        as_attachment=True,
        download_name="werkboekje.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)


