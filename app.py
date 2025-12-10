from flask import Flask, render_template, request, send_file
from markupsafe import Markup
from html_converter import docx_to_html
import os
import tempfile

app = Flask(__name__)

TMP_DIR = "/tmp"  # hier slaan we de .html bestanden tijdelijk op


@app.route("/", methods=["GET", "POST"])
def index():
    filename = None  # naam van het .html-bestand in /tmp

    if request.method == "POST":
        if "file" not in request.files:
            return render_template("index.html", error="Geen bestand geüpload")

        file = request.files["file"]

        if file.filename == "":
            return render_template("index.html", error="Geen geldig bestand gekozen")

        # Tijdelijke opslag van de DOCX
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
            file.save(temp_docx.name)
            temp_path = temp_docx.name

        try:
            # DOCX → HTML
            html_content = docx_to_html(temp_path)

            # HTML-bestand opslaan in /tmp
            base_name = os.path.basename(temp_path)
            out_path = os.path.join(TMP_DIR, base_name + ".html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            filename = os.path.basename(out_path)

        except Exception as e:
            return render_template("index.html", error=str(e))

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # Geef alleen de bestandsnaam door; preview en download gebruiken de routes hieronder
        return render_template("index.html", filename=filename)

    return render_template("index.html")


@app.route("/preview/<filename>")
def preview_file(filename):
    """
    Toon de HTML in de browser (zoals Streamlit dat deed).
    Dit is puur view, geen download.
    """
    path = os.path.join(TMP_DIR, filename)
    # as_attachment=False → browser rendert het als HTML-pagina
    return send_file(path, mimetype="text/html", as_attachment=False)


@app.route("/download/<filename>")
def download_file(filename):
    """
    Deze route is echt voor downloaden van het HTML-bestand.
    """
    path = os.path.join(TMP_DIR, filename)
    return send_file(path, mimetype="text/html", as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)


