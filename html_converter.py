import base64
from html import escape
from typing import List, Dict, Optional
from docx import Document

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False


def _image_size(img_bytes: bytes) -> Optional[tuple]:
    """Bepaal (breedte, hoogte) van afbeelding met Pillow."""
    if not PIL_OK:
        return None

    try:
        from io import BytesIO
        with Image.open(BytesIO(img_bytes)) as im:
            return im.width, im.height
    except Exception:
        return None


def _img_infos_for_paragraph(para, doc: Document) -> List[Dict]:
    """Zoek alle afbeeldingen in paragraaf en retourneer info."""
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

            # Altijd base64 inline, geen Cloudinary
            b64 = base64.b64encode(blob).decode("ascii")
            url = f"data:image/png;base64,{b64}"

            infos.append({"url": url, "w": w, "h": h, "small": small})

    return infos


def _is_heading(para) -> int:
    name = (para.style.name or "").lower()

    if name.startswith("heading") or name.startswith("kop"):
        for n in ("1", "2", "3"):
            if n in name:
                return int(n)
        return 1

    return 0


def docx_to_html(path: str) -> str:
    """DOCX → HTML met simpele layout en inline afbeeldingen."""
    doc = Document(path)

    out = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>DOCX naar HTML</title>",
        "<style>",
        "body { margin: 0; padding: 0; font-family: Arial, sans-serif; }",
        ".page { max-width: 900px; margin: 0 auto; padding: 2rem; "
        "background: #e5f7e5; }",
        "img { display: block; margin: 0.5rem 0; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class='page'>",
    ]

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        level = _is_heading(para)

        # Koppen
        if level and text:
            lvl = min(level, 3)
            out.append(f"<h{lvl}>{escape(text)}</h{lvl}>")
        # Normale tekst
        elif text:
            out.append(f"<p>{escape(text)}</p>")

        # Afbeeldingen in deze paragraaf
        imgs = _img_infos_for_paragraph(para, doc)
        for i in imgs:
            style_bits = []
            if i["w"]:
                style_bits.append(f"max-width:{i['w']}px")
            if i["h"]:
                style_bits.append(f"max-height:{i['h']}px")
            style = ";".join(style_bits) if style_bits else "max-width:300px;max-height:300px"
            out.append(
                f'<img src="{i["url"]}" alt="" style="{style};object-fit:contain;">'
            )

    out.append("</div>")
    out.append("</body>")
    out.append("</html>")

    return "\n".join(out)

