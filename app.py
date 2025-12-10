from flask import Flask, request, Response
from html_converter import docx_to_html
import tempfile
import os

app = Flask(__name__)

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DOCX → HTML converter</title>
</head>
<body style="font-family: Arial; padding: 2rem;">
    <h2>DOCX → HTML converter</h2>
    {error_block}
    <form method="POST" enctype="multipart/form-data">
        <p>
            <input type="file" name="file" accept=".docx" required>
        </p>
        <button type="submit">Converteer</button>
    </form>
</body>
</html>
"""

def render_page(error: str | None = None):
    if error:
        error_html = f"<p style='color:red;'><strong>Fout:</strong> {error}</p>"
    else:
        error_html = ""
    return PAGE_TEMPLATE.format(error_block=error_html)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return Response(render_page(), mimetype="text/html")

    # POST: verwerk upload
    # Debug: laat zien welke velden Flask ziet
    field_names = list(request.files.keys())

    if "file" not in request.files:
        error = f"Geen bestand geüpload. Ontvangen bestand-velden: {field_names}"
        return Response(render_page(error), mimetype="text/html")

    file = request.files["file"]

    if file.filename == "":
        error = "Geen geldig bestand gekozen."
        return Response(render_page(error), mimetype="text/html")

    # Tijdelijk DOCX opslaan
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file.save(tmp.name)
        temp_path = tmp.name

    try:
        html_output = docx_to_html(temp_path)
        # Geef direct de gegenereerde HTML terug
        return Response(html_output, mimetype="text/html")
    except Exception as e:
        error = f"Fout tijdens converteren: {e}"
        return Response(render_page(error), mimetype="text/html")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)
