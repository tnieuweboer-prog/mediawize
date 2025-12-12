from flask import Flask, request, send_file
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
from html import escape
import tempfile
import os
import io

app = Flask(__name__)

# -------------------------------------------------
# BASE DASHBOARD TEMPLATE
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
  width:260px;
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
  width:52px;
  height:52px;
  border-radius:10px;
}}

.logo-title {{
  font-weight:800;
  font-size:16px;
}}

.logo-sub {{
  font-size:11px;
  color:#94a3b8;
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

textarea {{
  min-height:160px;
  font-family:monospace;
  font-size:13px;
}}

button {{
  background:var(--accent);
  color:white;
  border:none;
  padding:10px 18px;
  border-radius:999px;
  font-weight:700;
  cursor:pointer;
}}

button:hover {{
  filter:brightness(1.05);
}}

.row {{
  display:grid;
  grid-template-columns: repeat(2, 1fr);
  gap:12px;
}}

@media (max-width:900px) {{
  .sidebar {{
    display:none;
  }}
  .row {{
    grid-template-columns:1fr;
  }}
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
</body>
</html>
"""

# -------------------------------------------------
# DOCX → HTML PAGE
# -------------------------------------------------
def html_page(error=None, result=None):
    error_block = f"<div class='error'>{error}</div>" if error else ""
    result_block = ""

    if result:
        result_block = f"""
        <h2>Gegenereerde HTML</h2>
        <textarea readonly>{escape(result)}</textarea>
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
            <input type="file" name="file" accept=".docx" required>
            <button type="submit">Converteren</button>
          </form>
          {result_block}
        </div>
        """
    )

# -------------------------------------------------
# WERKBOEKJES PAGE (A + C)
# -------------------------------------------------
def workbook_page(error=None):
    error_block = f"<div class='error'>{error}</div>" if error else ""

    return BASE_PAGE.format(
        tab_html="",
        tab_workbook="active",
        content=f"""
        <div class="card">
          <h1>Werkboekjes-generator</h1>
          <p class="lead">
            Maak snel een basis-werkboekje in Word.
            Deze versie is bewust eenvoudig en vormt de basis voor uitbreiding.
          </p>

          {error_block}

          <form method="POST">
            <label>Opdracht titel</label>
            <input type="text" name="titel" required>

            <div class="row">
              <div>
                <label>Vak</label>
                <input type="text" name="vak" value="BWI">
              </div>
              <div>
                <label>Docent</label>
                <input type="text" name="docent">
              </div>
            </div>

            <label>Duur van de opdracht</label>
            <input type="text" name="duur" value="10 x 45 minuten">

            <button type="submit">📘 Werkboekje genereren</button>
          </form>
        </div>
        """
    )

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
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

@app.route("/workbook", methods=["GET", "POST"])
def workbook():
    if request.method == "GET":
        return workbook_page()

    try:
        meta = {
            "opdracht_titel": request.form.get("titel", ""),
            "vak": request.form.get("vak", ""),
            "docent": request.form.get("docent", ""),
            "duur": request.form.get("duur", ""),
            "include_materiaalstaat": False,
        }

        steps = []  # A-versie: nog geen stappen

        output = build_workbook_docx_front_and_steps(meta, steps)

        return send_file(
            output,
            as_attachment=True,
            download_name="werkboekje.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except Exception as e:
        return workbook_page(f"Fout bij genereren: {e}")

# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

