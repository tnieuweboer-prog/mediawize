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


# ---------- Hulpfuncties ----------

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


def _img_infos_for_paragraph(para, doc: Document) -> List[Dict]:
    """
    Zoek alle afbeeldingen in een paragraaf en retourneer info.

    In plaats van upload naar Cloudinary wordt de afbeelding:
    - als base64 data-URL in de HTML opgenomen.
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

            # Geen Cloudinary meer → direct base64 data-URL
            b64 = base64.b64encode(blob).decode("ascii")
            url = f"data:image/png;base64,{b64}"

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


# ---------- Hoofdconverter ----------

def docx_to_html(file_like) -> str:
    """
    DOCX → HTML met 1 overkoepelende groene div.
    - Koppen blijven koppen (h1/h2/h3)
    - Paragrafen worden <p>
    - Afbeeldingen worden als base64 data-URLs ingevoegd
    """

    doc = Document(file_like)

    out = [
        "<html>",
        "<head>",
        "<meta charset='utf-8' />",
        "<style>",

        "body { margin: 0; padding: 0; }",

        ".green {",
        "    background-image: url('YOUR_ASSET_URL_HERE');",  # pas hier desnoods een eigen achtergrond aan
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

    # Verwerking tekst + afbeeldingen
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

        # Afbeeldingen in deze paragraaf
        imgs = _img_infos_for_paragraph(para, doc)
        if not imgs:
            continue

        small = [i for i in imgs if i["small"]]
        big = [i for i in imgs if not i["small"]]

        # Kleine plaatjes in een rij
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

        # Grotere plaatjes apart
        for i in big:
            out.append(
                f'<p><img src="{i["url"]}" alt="" '
                f'style="max-width:300px;max-height:300px;object-fit:contain;" /></p>'
            )

    out.append("</div>")
    out.append("</body>")
    out.append("</html>")

    return "\n".join(out)
