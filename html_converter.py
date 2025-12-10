from docx import Document
from html import escape
import base64

def safe_style(para):
    """Geeft een veilige style-naam terug, voorkomt crashes."""
    try:
        if para.style and para.style.name:
            return para.style.name.lower()
    except:
        pass
    return ""

def extract_images(para, doc):
    """Zoekt afbeeldingen in runs, zet om naar base64."""
    out = []
    for run in para.runs:
        blips = run._r.xpath(".//a:blip")
        for blip in blips:
            rId = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            if not rId:
                continue

            part = doc.part.related_parts[rId]
            blob = part.blob
            b64 = base64.b64encode(blob).decode("ascii")

            out.append(
                f"<img src='data:image/png;base64,{b64}' "
                f"style='max-width:300px;height:auto;'/><br>"
            )
    return out


def docx_to_html(path):
    doc = Document(path)

    html = []
    html.append("<html>")
    html.append("<head><meta charset='utf-8'>")
    html.append("<style>body{font-family:Arial;padding:20px;}</style>")
    html.append("</head><body>")

    for para in doc.paragraphs:
        text = para.text.strip()
        style = safe_style(para)
        images = extract_images(para, doc)

        # Headers
        if text and (style.startswith("heading") or style.startswith("kop")):
            level = "1"
            for n in ["1", "2", "3"]:
                if n in style:
                    level = n
            html.append(f"<h{level}>{escape(text)}</h{level}>")

        # Normal text
        elif text:
            html.append(f"<p>{escape(text)}</p>")

        # Images
        if images:
            html.extend(images)

    html.append("</body></html>")
    return "\n".join(html)

