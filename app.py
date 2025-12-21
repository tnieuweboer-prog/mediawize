from flask import (
    Flask, request, send_file, redirect, url_for,
    session, render_template_string
)
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps

import tempfile
import os
import secrets
from functools import wraps

# ============================================================
# App setup
# ============================================================
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))


# ============================================================
# Render helpers (2 layouts)
# ============================================================
def render_app_page(inner_html: str, active_tab: str):
    tpl = """
    {% extends "base.html" %}
    {% block content %}
    """ + inner_html + """
    {% endblock %}
    """
    return render_template_string(tpl, active_tab=active_tab)


def render_public_page(inner_html: str, active_tab: str):
    tpl = """
    {% extends "public_base.html" %}
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
    return render_app_page(content, tab), status_code


# ============================================================
# Auth helpers (dummy auth)
# ============================================================
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def role_required(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                return message_page(
                    "Geen toegang",
                    "Je hebt geen rechten voor deze pagina.",
                    "home",
                    403
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# PUBLIC PAGES
# ============================================================
@app.route("/", methods=["GET"])
def home():
    content = """
    <div class="pub-hero">
      <h1>Triade Tools</h1>
      <p>
        Eén plek voor docenten en leerlingen. Werkboekjes, DOCX → HTML
        en (binnenkort) toetsen — veilig en mobielvriendelijk.
      </p>

      <div class="pub-cta">
        <a class="btn-link" href="/login"><button>Inloggen</button></a>
        <a class="btn-link" href="/signup"><button class="btn-ghost">Account maken</button></a>
      </div>
    </div>

    <div class="pub-modules">
      <div class="pub-module">
        <h3>💚 DOCX → HTML</h3>
        <p>Word omzetten naar Stermonitor HTML.</p>
      </div>
      <div class="pub-module">
        <h3>📘 Werkboekjes</h3>
        <p>Werkboekjes genereren vanuit BWI/PIE/MVI templates.</p>
      </div>
      <div class="pub-module">
        <h3>📝 Toetsen</h3>
        <p>Docent zet klaar, leerling maakt, docent downloadt.</p>
      </div>
    </div>
    """
    return render_public_page(content, "home")


# ------------------------------------------------------------
# Signup
# ------------------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_public_page("""
        <div class="card">
          <h1>Account maken</h1>
          <form method="POST">
            <label>Rol</label>
            <select name="role" required>
              <option value="docent">Docent</option>
              <option value="leerling">Leerling</option>
            </select>

            <label>Naam</label>
            <input type="text" name="name" required>

            <button>Account maken</button>
          </form>
        </div>
        """, "signup")

    session["user"] = request.form["name"]
    session["role"] = request.form["role"]

    return redirect(
        url_for("docent_dashboard")
        if session["role"] == "docent"
        else url_for("leerling_dashboard")
    )


# ------------------------------------------------------------
# Login / Logout
# ------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_public_page("""
        <div class="card">
          <h1>Inloggen</h1>
          <form method="POST">
            <label>Rol</label>
            <select name="role">
              <option value="docent">Docent</option>
              <option value="leerling">Leerling</option>
            </select>

            <label>Naam</label>
            <input type="text" name="name">

            <button>Inloggen</button>
          </form>
        </div>
        """, "login")

    session["user"] = request.form.get("name", "user")
    session["role"] = request.form.get("role")

    return redirect(
        url_for("docent_dashboard")
        if session["role"] == "docent"
        else url_for("leerling_dashboard")
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ============================================================
# DASHBOARDS
# ============================================================
@app.route("/docent")
@login_required
@role_required("docent")
def docent_dashboard():
    return render_app_page("""
    <div class="card">
      <h1>Docent dashboard</h1>
      <a href="/html"><button>DOCX → HTML</button></a>
      <a href="/workbook"><button>Werkboekjes</button></a>
      <a href="/toetsen"><button>Toetsen</button></a>
    </div>
    """, "docent")


@app.route("/leerling")
@login_required
@role_required("leerling")
def leerling_dashboard():
    return render_app_page("""
    <div class="card">
      <h1>Leerling dashboard</h1>
      <a href="/toets-maken"><button>Toets maken</button></a>
    </div>
    """, "leerling")


# ============================================================
# DOCX → HTML
# ============================================================
@app.route("/html", methods=["GET", "POST"])
@login_required
@role_required("docent")
def html_tool():
    if request.method == "GET":
        return render_app_page("""
        <div class="card">
          <h1>DOCX → HTML</h1>
          <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept=".docx" required>
            <button>Converteren</button>
          </form>
        </div>
        """, "html")

    file = request.files["file"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file.save(tmp.name)
        html = docx_to_html(tmp.name)
        os.remove(tmp.name)

    return render_app_page(f"""
    <div class="card">
      <h1>Resultaat</h1>
      <textarea style="width:100%;height:400px;">{html}</textarea>
    </div>
    """, "html")


# ============================================================
# WERKBOEKJES (ongewijzigd basis)
# ============================================================
@app.route("/workbook", methods=["GET", "POST"])
@login_required
@role_required("docent")
def workbook():
    return render_app_page("""
    <div class="card">
      <h1>Werkboekjes</h1>
      <p>Deze module werkt nog via je bestaande code.</p>
    </div>
    """, "workbook")


# ============================================================
# TOETSEN (placeholder)
# ============================================================
@app.route("/toetsen")
@login_required
@role_required("docent")
def toetsen_docent():
    return render_app_page("""
    <div class="card">
      <h1>Toetsen</h1>
      <p>Toetsmodule volgt hier.</p>
    </div>
    """, "toetsen")


@app.route("/toets-maken")
@login_required
@role_required("leerling")
def toets_maken():
    return render_app_page("""
    <div class="card">
      <h1>Toets maken</h1>
      <p>Toetscode invoeren komt hier.</p>
    </div>
    """, "toets_maken")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)
