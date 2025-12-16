import os
import uuid
from html import escape
from typing import List, Dict, Optional
from docx import Document

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False


# Absolute map waar images opgeslagen worden (zelfde projectmap als app.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")  # -> /opt/mediawize/uploads
UPLOAD_URL_PREFIX = "/uploads"  # nginx serveert dit naar /opt/mediawize/uploads/


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _image_size(img_bytes: bytes) -> Optional[tuple]:
    """Bepaal (breedte, hoogte) van afbeelding met Pillow (optioneel)."""
    if not PIL_OK:
        return None
    try:
        from io import BytesIO
        with Image.open(BytesIO(img_bytes)) as im:
            return im.width, im.height
    except Exception:
        return None


def _ext_from_content_type(content_type: Optional[str]) -> str:
    """Bepaal extensie op basis van mime type."""
    if not content_type:
        return "bin"
    ct = content_type.lower().strip()

    mapping = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
        "image/x-emf": "emf",
        "image/x-wmf": "wmf",
        "image/svg+xml": "svg",
    }
    return mapping.get(ct, "bin")


def _save_image_to_uploads(blob: bytes, content_type: Optional[str]) -> str:
    """
    Slaat de afbeelding op in UPLOAD_DIR en retourneert de publieke URL (/uploads/..).
    """
    _ensure_upload_dir()

    ext = _ext_from_content_type(content_type)

    # fallback: als content_type onbekend is, probeer met Pillow te raden
    if ext == "bin" and PIL_OK:
        try:
            from io import BytesIO
            with Image.open(BytesIO(blob)) as im:
                fmt = (im.format or "").lower()
                if fmt in ("jpeg", "jpg"):
                    ext = "jpg"
                elif fmt in ("png", "gif", "webp", "bmp", "tiff"):
                    ext = fmt
        except Exception:
            pass

    fname = f"docx_{uuid.uuid4().hex}.{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)

    with open(fpath, "wb") as f:
        f.write(blob)

    return f"{UPLOAD_URL_PREFIX}/{fname}"


def _img_infos_for_paragraph(para, doc: Document) -> List[Dict]:
    """
    Zoek alle afbeeldingen in paragraaf en retourneer info.
    We schrijven nu bestanden weg naar server i.p.v. base64.
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
                content_type = getattr(part, "content_type", None)
            except Exception:
                continue

            size = _image_size(blob)
            w = size[0] if size else None
            h = size[1] if size else None
            small = (w and h and w < 100 and h < 100)

            try:
                url = _save_image_to_uploads(blob, content_type)
            except Exception:
                # Als wegschrijven faalt, sla hem over
                continue

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
    """DOCX → HTML met simpele layout en afbeeldingen als server-URL."""
    doc = Document(path)

    out = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>DOCX naar HTML</title>",
        "<style>",
        "body { margin: 0; padding: 0; font-family: Arial, sans-serif; }",
        ".page { max-width: 900px; margin: 0 auto; padding: 2rem; background: #e5f7e5; }",
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


