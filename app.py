from flask import Flask, render_template, request, send_file
from markupsafe import Markup
from html_converter import docx_to_html
import os
import tempfile

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    html_output = None
    filename = None

    if request.method == "POST":
        if "file" not in request.files:
            return render_template("index.html", error="Geen bestand geüpload")

        file = request.files["file"]

        if file.filename == "":
            return render_template("index.html", error="Geen geldig bestand gekozen")

        # Tijdelijke opslag
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
            file.save(temp_docx.name)
            temp_path = temp_docx.name

        try:
            # Converteren
            html_content = docx_to_html(temp_path)

            # Opslaan voor download
            out_path = os.path.join("/tmp", os.path.basename(temp_path) + ".html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            html_output = Markup(html_content)
            filename = os.path.basename(out_path)

        except Exception as e:
            return render_template("index.html", error=str(e))

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return render_template("index.html", html_output=html_output, filename=filename)

    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join("/tmp", filename)
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)


