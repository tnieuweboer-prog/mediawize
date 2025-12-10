from docx import Document
from html import escape
import base64

def docx_to_html(path):
    """
    Convertert een DOCX naar HTML.
    - Tekst → <p> of <h1/h2/h3>
    - Afbeeldingen → base64 inline
    """

    doc = Document(path)

    html = []
    html.append("<html>")
    html.append("<head><meta charset='utf-8'>")
    html.append("<style>body{font-family:Arial;padding:20px;}</style>")
    html.append("</head>")
    html.append("<body>")

    for para in doc.paragraphs:
        text = para.text.strip()
        style = para.style.name.lower()

        # Koppen herkennen
        if text and (style.startswith("heading") or style.startswith("kop")):
            level = "1"
            for n in ["1", "2", "3"]:
                if n in style:
                    level = n
            html.append(f"<h{level}>{escape(text)}</h{level}>")

        # Gewone tekst
        elif text:
            html.append(f"<p>{escape(text)}</p>")

        # Afbeeldingen in de runs
        for run in para.runs:
            blips = run._r.xpath(".//a:blip")
            for blip in blips:
                rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                if not rId:
                    continue

                part = doc.part.related_parts[rId]
                blob = part.blob

                b64 = base64.b64encode(blob).decode("ascii")
                html.append(
                    f"<p><img src='data:image/png;base64,{b64}' "
                    f"style='max-width:300px;height:auto;'/></p>"
                )

    html.append("</body></html>")
    return "\n".join(html)

