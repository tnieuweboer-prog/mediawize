from docx import Document
from html import escape

def docx_to_html(path):
    doc = Document(path)

    html = []
    html.append("<html>")
    html.append("<head><meta charset='utf-8'></head>")
    html.append("<body style='font-family:Arial; padding:20px;'>")

    for para in doc.paragraphs:
        text = para.text.strip()

        # Als paragraaf leeg is → overslaan
        if not text:
            continue

        style = para.style.name.lower()

        # KOPPEN
        if style.startswith("heading") or style.startswith("kop"):
            level = "1"
            for n in ["1", "2", "3"]:
                if n in style:
                    level = n
            html.append(f"<h{level}>{escape(text)}</h{level}>")

        # GEWONE ALINEA
        else:
            html.append(f"<p>{escape(text)}</p>")

    html.append("</body></html>")
    return "\n".join(html)


