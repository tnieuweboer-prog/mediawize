from flask import Flask, request
from html_converter import docx_to_html
from html import escape   # om de HTML veilig als tekst te tonen
import tempfile
import os

app = Flask(__name__)

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DOCX → HTML converter (codeblok)</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 2rem;
            background: #f5f5f5;
        }}
        h2 {{
            margin-top: 0;
        }}
        .error {{
            color: red;
            font-weight: bold;
        }}
        textarea {{
            width: 100%;
            height: 400px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre;
        }}
        .section {{
            background: #ffffff;
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            box-shadow: 0 0 5px rgba(0,0,0,0.05);
        }}
    </style>
</head>
<body>
    <h2>DOCX → HTML converter (codeblok)</h2>
    {error_block}
    <div class="section">
        <form method="POST" enctype="multipart/form-data">
            <p>
                <input type="file" name="file" accept=".docx" required>
            </p>
            <button type="submit">Converteer</button>
        </form>
    </div>
    {result_block}
</body>
</html>
"""

def render_page(error: str | None = None, html_out: str | None = None) -> str:
    if error:
        error_block = f"<p class='error'>Fout: {error}</p>"
    else:
        error_block = ""

    if html_out:
        # Net als st.code(): HTML laten zien als tekst
        escaped = escape(html_out)
        result_block = f"""
        <div class="section">
            <h3>Gegenereerde HTML</h3>
            <p>Kopieer de HTML hieronder en plak hem in Stermonitor / Elodigitaal.</p>
            <textarea readonly>{escaped}</textarea>
        </div>
        """
    else:
        result_block = ""

    return PAGE_TEMPLATE.format(error_block=error_block, result_block=result_block)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_page()

    if "file" not in request.files:
        return render_page(f"Geen bestand geüpload. request.files = {list(request.files.keys())}")

    file = request.files["file"]

    if file.filename == "":
        return render_page("Geen geldig bestand gekozen.")

    # Tijdelijk opslaan zoals in je werkende test
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file.save(tmp.name)
        temp_path = tmp.name

    try:
        html_output = docx_to_html(temp_path)
        # 👉 HTML als codeblok tonen, NIET renderen
        return render_page(html_out=html_output)
    except Exception as e:
        return render_page(f"Fout tijdens converteren: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

