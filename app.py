from flask import Flask, request, Response
from html_converter import docx_to_html
import tempfile
import os

app = Flask(__name__)


UPLOAD_FORM = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DOCX → HTML converter</title>
</head>
<body style="font-family: Arial; padding: 2rem;">
    <h2>Upload een Word-bestand (.docx)</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".docx" required>
        <button type="submit">Converteer</button>
    </form>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return UPLOAD_FORM

    # POST: verwerk DOCX
    if "file" not in request.files:
        return "Geen bestand geüpload", 400

    file = request.files["file"]
    if file.filename == "":
        return "Geen geldig bestand gekozen", 400

    # Tijdelijk bestand opslaan
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file.save(tmp.name)
        temp_path = tmp.name

    try:
        html_output = docx_to_html(temp_path)
        return Response(html_output, mimetype="text/html")
    except Exception as e:
        return f"Fout tijdens converteren: {e}", 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

