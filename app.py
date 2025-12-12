from flask import Flask, request
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
from html import escape
import tempfile
import os

app = Flask(__name__)

# -----------------------------
# DASHBOARD BASE TEMPLATE
# -----------------------------
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

/* ---------- SIDEBAR ---------- */
.sidebar {{
  width:260px;
  background:var(--sidebar);
  color:var(--sidebar-text);
  display:flex;
  flex-direction:column;
  padding:18px;
}}

.logo img {{
  width:52px;
  height:52px;
  border-radius:10px;
}}

.logo-text {{
  display:flex;
  flex-direction:column;
}}

.logo-title {{
  font-weight:800;
  font-size:16px;
  line-height:1.1;
}}

.nav a {{
  display:block;
  padding:12px 14px;
  margin-bottom:6px;
  border-radius:10px;
  color:var(--sidebar-text);
  text-decoration:none;
  font-weight:600;
  font-size:14px;
}}

.nav a.active {{
  background:rgba(34,197,94,0.2);
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

/* ---------- CONTENT ---------- */
.content {{
  flex:1;
  padding:24px;
}}

.card {{
  background:var(--card);
  border-radius:16px;
  border:1px solid var(--border);
  padding:24px;
  max-width:1100px;
}}

h1 {{
  margin-top:0;
  font-size:20px;
}}

p.lead {{
  color:var(--muted);
  margin-bottom:20px;
}}

.error {{
  background:#fee2e2;
  color:#991b1b;
  padding:12px;
  border-radius:10px;
  font-weight:600;
  margin-bottom:16px;
}}

input[type="text"], textarea {{
  width:100%;
  padding:10px 12px;
  border-radius:10px;
  border:1px solid var(--border);
  margin-bottom:12px;
}}

.code-area textarea {{
  width:100%;
  height: calc(100vh - 360px); /* 👈 schaalt met scherm */
  min-height:320px;
  max-height:900px;
  background:#0f172a;
  color:#e5e7eb;
  border:1px solid rgba(255,255,255,0.08);
  border-radius:14px;
  padding:14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size:12px;
  line-height:1.45;
  white-space:pre;
}}


button {{
  background:var(--accent);
  color:white;
  border:none;
  padding:10px 16px;
  border-radius:999px;
  font-weight:700;
  cursor:pointer;
}}

button:hover {{
  filter:brightness(1.05);
}}

.file {{
  margin-bottom:14px;
}}

.download {{
  margin-top:14px;
}}
.result-header {{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:12px;
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

.btn-copy {{
  background:#1e293b;
  color:#e5e7eb;
  border:none;
  border-radius:999px;
  padding:8px 14px;
  font-weight:700;
  cursor:pointer;
}}

.btn-copy:hover {{
  background:#334155;
}}


/* ---------- MOBILE ---------- */
.mobile-toggle {{
  display:none;
}}

@media (max-width:900px) {{
  .sidebar {{
    position:fixed;
    left:-260px;
    top:0;
    height:100%;
    transition:0.2s;
    z-index:10;
  }}
  .sidebar.open {{
    left:0;
  }}
  .mobile-toggle {{
    display:block;
    margin-bottom:16px;
  }}
}}
</style>

<script>
function toggleSidebar() {{
  document.querySelector('.sidebar').classList.toggle('open');
}}
</script>

<script>
function copyHTML() {
  const el = document.getElementById("htmlResult");
  el.select();
  el.setSelectionRange(0, 999999);
  document.execCommand("copy");
}
</script>

</head>
<body>

<div class="app">

  <aside class="sidebar">
    <div class="logo">
      <!-- Zet hier later je echte logo -->
      <img src="/static/assets/logo.png" alt="Logo">
      <div class="logo-title">Triade Tools</div>
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
    <button class="mobile-toggle" onclick="toggleSidebar()">☰ Menu</button>
    {content}
  </main>

</div>

</body>
</html>
"""

# -----------------------------
# PAGES
# -----------------------------
def html_page(error=None, result=None):
    error_block = f"<div class='error'>{error}</div>" if error else ""
    result_block = ""
    if result:
        result_block = f"""
        <div class="result-header">
          <div>
            <h2>Gegenereerde HTML</h2>
            <p class="sub">Klik om te kopiëren en plak in Stermonitor / ELO</p>
          </div>
          <button class="btn-copy" onclick="copyHTML()">📋 Kopiëren</button>
        </div>

<div class="code-area">
  <textarea id="htmlResult" readonly>...</textarea>
</div>
        """
    return BASE_PAGE.format(
        tab_html="active",
        tab_workbook="",
        content=f"""
        <div class="card">
          <h1>DOCX → HTML</h1>
          <p class="lead">Zet Word-bestanden om naar HTML voor Stermonitor / ELO.</p>
          {error_block}
          <form method="POST" enctype="multipart/form-data">
            <div class="file">
              <input type="file" name="file" accept=".docx" required>
            </div>
            <button type="submit">Converteren</button>
          </form>
          {result_block}
        </div>
        """
    )

def workbook_page(error=None):
    error_block = f"<div class='error'>{error}</div>" if error else ""
    return BASE_PAGE.format(
        tab_html="",
        tab_workbook="active",
        content=f"""
        <div class="card">
          <h1>Werkboekjes-generator</h1>
          <p class="lead">Maak automatisch Word-werkboekjes voor lessen.</p>
          {error_block}
          <p>Deze tool gebruikt dezelfde logica als je Streamlit-versie.</p>
          <p>(Formulier kun je hier stap voor stap verder uitbreiden.)</p>
        </div>
        """
    )

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return html_page()

    if "file" not in request.files:
        return html_page("Geen bestand geüpload.")

    file = request.files["file"]
    if file.filename == "":
        return html_page("Geen geldig bestand gekozen.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file.save(tmp.name)
        path = tmp.name

    try:
        html = docx_to_html(path)
        return html_page(result=html)
    except Exception as e:
        return html_page(f"Fout: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)

@app.route("/workbook", methods=["GET"])
def workbook():
    return workbook_page()

# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

