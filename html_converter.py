from docx import Document
from html import escape

def docx_to_html(path):
    doc = Document(path)

    html = []
    html.append("<html><body style='font-family:Arial;'>")

    for para in doc.paragraphs:
        text = escape(para.text.strip())

        if not text:
            continue

        style = para.style.name.lower()

        # koppen detecteren
        if style.startswith("heading") or style.startswith("kop"):
            level = "1"
            for n in ["1", "2", "3"]:
                if n in style:
                    level = n
            html.append(f"<h{level}>{text}</h{level}>")

        else:
            html.append(f"<p>{text}</p>")

    html.append("</body></html>")
    return "\n".join(html)

