from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint("auth", __name__)

# =========================
# Database helpers
# =========================

def _data_dir():
    return current_app.config.get("DATA_DIR", os.path.join(os.getcwd(), "data"))

def _db_path():
    os.makedirs(_data_dir(), exist_ok=True)
    return os.path.join(_data_dir(), "app.db")

def _get_conn():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'docent',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

@bp.before_app_request
def ensure_db():
    try:
        init_db()
    except Exception:
        # bij import-fouten of migraties niet hard crashen
        pass

# =========================
# Login
# =========================

@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        conn = _get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            error = "Onjuiste e-mail of wachtwoord."
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            if user["role"] == "docent":
                return redirect("/docent/")
            else:
                return redirect("/leerling/")

    return render_template("auth/login.html", error=error)

# =========================
# Signup
# =========================

@bp.route("/signup", methods=["GET", "POST"])
def signup():
    error = None

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "docent").lower()

        if role not in ("docent", "leerling"):
            role = "docent"

        if not email or "@" not in email:
            error = "Vul een geldig e-mailadres in."
        elif len(password) < 8:
            error = "Wachtwoord moet minimaal 8 tekens zijn."
        else:
            try:
                pw_hash = generate_password_hash(password)
                conn = _get_conn()
                conn.execute(
                    "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
                    (email, pw_hash, role)
                )
                conn.commit()

                user = conn.execute(
                    "SELECT * FROM users WHERE email = ?",
                    (email,)
                ).fetchone()
                conn.close()

                session.clear()
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session["role"] = user["role"]

                if user["role"] == "docent":
                    return redirect("/docent/")
                else:
                    return redirect("/leerling/")

            except sqlite3.IntegrityError:
                error = "Dit e-mailadres bestaat al."
            except Exception as e:
                error = f"Fout bij registreren: {e}"

    return render_template("auth/signup.html", error=error)

# =========================
# Logout
# =========================

@bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


