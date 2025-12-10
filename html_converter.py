import os
import base64
from html import escape
from typing import Optional, List, Dict
from docx import Document

# Pillow voor beeldmaten (optioneel)
try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False

# Basispad voor statische afbeeldingen op de server
BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _image_size(img_bytes: bytes) -> Optional[tuple]:
    """Bepaal (breedte, hoogte) van afbeelding met Pillow."""
    if not PIL_OK:
        return None

    try:
        from io import BytesIO
        with Image.open(BytesIO(img_bytes)) as im:
            return im.width, im.height
    except:  # noqa: E722
        return None


def _save_image_locally(img_bytes: bytes) -> str:
    """
    Sla de afbeelding op in static/uploads en geef de URL terug
    die in HTML gebruikt kan worden.
    """
    import uuid

    filename = f"img_{uuid.uuid4().hex}.png"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(img_bytes)

    # URL zoals de browser hem ziet (Flask serveert /static)
    return f"/static/uploads/{filename}"


def _img_infos_for_paragraph(para, doc: Document) -> List[Dict]:
    """
    Zoek alle afbeeldingen in een paragraaf en retourneer info.
    Nu worden ze lokaal opgeslagen i.p.v. naar Cloudinary geüpload.
    """
    infos: List[Dict] = []

    for run in para.runs:
        blips = run._r.xpath(".//a:blip")
        if not blips:
            continue

        for blip in blips:
            rId = blip.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
            )
            if not rId:
                continue

            try:
                part = doc.part.related_parts[rId]
                blob = part.blob
            except Exception:
                continue

            size = _image_size(blob)
            w = size[0] if size else None
            h = size[1] if size else None
            small = (w and h and w < 100 and h < 100)

            url = _save_image_locally(blob)
            infos.append({"url": url, "w": w, "h": h, "small": small})

    return infos


def _is_heading(para) -> int:
    """Herken kopstijlen (Heading 1/2/3, Kop 1/2/3)."""
    name = (para.style.name or "").lower()

    if name.startswith("heading") or name.startswith("kop"):
        for n in ("1", "2", "3"):
            if n in name:
                return int(n)
        return 1

    return 0


def docx_to_html(file_like) -> str:
    """
    DOCX → HTML met 1 overkoepelende groene div.
    - Koppen blijven koppen (h1/h2/h3)
    - Paragrafen worden <p>
    - Afbeeldingen worden op de server opgeslagen en via /static/... geladen
    """

    doc = Document(file_like)

    out = [
        "<html>",
        "<head>",
        "<meta charset='utf-8' />",
        "<style>",

        "body { margin: 0; padding: 0; }",

        ".green {",
        "    background-image: url('YOUR_ASSET_URL_HERE');",  # pas hier je eigen achtergrond aan
        "    background-size: cover;",
        "    background-repeat: no-repeat;",
        "    background-position: center;",
        "}",

        ".lesson {",
        "    max-width: 900px;",
        "    margin: 0;",
        "    padding: 1rem;",
        "    font-family: Arial, sans-serif;",
        "    text-align: left;",
        "    background: rgba(198,217,170,0.6);",
        "    backdrop-filter: blur(2px);",
        "    border-radius: 6px;",
        "}",

        "</style>",
        "</head>",

        "<body class='green'>",
        "<div class='lesson light-green'>"
    ]

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        level = _is_heading(para)

        # Koppen
        if level and text:
            h = min(level, 3)
            out.append(f"<h{h}>{escape(text)}</h{h}>")

        # Normale paragrafen
        elif text:
            out.append(f"<p>{escape(text)}</p>")

        # Afbeeldingen
        imgs = _img_infos_for_paragraph(para, doc)
        if not imgs:
            continue

        small = [i for i in imgs if i["small"]]
        big = [i for i in imgs if not i["small"]]

        if small:
            out.append(
                '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0;">'
            )
            for i in small:
                out.append(
                    f'<img src="{i["url"]}" alt="" '
                    f'style="max-width:{i["w"] or 100}px;'
                    f'max-height:{i["h"] or 100}px;object-fit:contain;" />'
                )
            out.append("</div>")

        for i in big:
            out.append(
                f'<p><img src="{i["url"]}" alt="" '
                f'style="max-width:300px;max-height:300px;object-fit:contain;" /></p>'
            )

    out.append("</div>")
    out.append("</body>")
    out.append("</html>")

    return "\n".join(out)
