from flask import Flask, render_template, request, send_file, send_from_directory
from markupsafe import Markup
from html_converter import docx_to_html
import os
import tempfile

app = Flask(__name__)

OUTPUT_DIR = "/tmp/mediawize_html"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    filename = None

    if request.method == "POST":
        if "file" not in request.files:
            return render_template("index.html", error="Geen bestand geüpload")

        file = request.files["file"]

        if file.filename == "":
            return render_template("index.html", error="Geen geldig bestand gekozen")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        try:
            html_output = docx_to_html(temp_path)

            # Maak output-bestandsnaam
            base = os.path.splitext(os.path.basename(file.filename))[0]
            filename = f"{base}.html"
            out_path = os.path.join(OUTPUT_DIR, filename)

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_output)

        except Exception as e:
            return render_template("index.html", error=str(e))

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # Toon nu de preview in een iframe
        return render_template("index.html", filename=filename)

    return render_template("index.html")


# Route voor iframe rendering
@app.route("/preview/<path:filename>")
def preview(filename):
    return send_from_directory(OUTPUT_DIR, filename)


# Download route
@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(port=8501, debug=True)


