from flask import Flask, request, Response, render_template_string
from html_converter import docx_to_html
import tempfile
import os

app = Flask(__name__)

UPLOAD_FORM = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Mediawize DOCX → HTML Converter (TEST)</title>
</head>
<body>
<h1>DOCX → HTML Converter (TEST)</h1>
<p>Upload een DOCX-bestand. Na upload krijg je direct de HTML-pagina te zien.</p>
<form method="POST" enctype="multipart/form-data">
    <input type="file" name="file" accept=".docx">
    <button type="submit">Converteren</button>
</form>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        # Alleen een klein uploadformulier tonen
        return render_template_string(UPLOAD_FORM)

    # POST: bestand ontvangen en direct omzetten naar HTML
    if "file" not in request.files:
        return "Geen bestand geüpload", 400

    file = request.files["file"]
    if file.filename == "":
        return "Geen geldig bestand gekozen", 400

    # Tijdelijk opslaan zodat python-docx ermee kan werken
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
        file.save(temp_docx.name)
        temp_path = temp_docx.name

    try:
        # Hier doen we precies wat Streamlit ook deed: DOCX → HTML-string
        html_content = docx_to_html(temp_path)
    except Exception as e:
        return f"Fout bij converteren: {e}", 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # ⬇️ Belangrijk: we geven direct de HTML terug aan de browser
    return Response(html_content, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)



