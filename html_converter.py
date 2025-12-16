import os
import uuid
import base64
from html import escape
from typing import Optional, List, Dict
from docx import Document

# Pillow voor beeldmaten
try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Map op VPS waar nginx /uploads/ naar wijst
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")  # -> /opt/mediawize/uploads

# Voor Stermonitor: absolute URL nodig
UPLOAD_BASE_URL = "https://app.mediawize.nl/uploads"

# Fallback: als wegschrijven faalt, toch base64 gebruiken
FALLBACK_TO_BASE64 = True

# Small threshold (zoals in jouw code)
SMALL_W = 100
SMALL_H = 100


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


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


def _guess_ext(blob: bytes, content_type: Optional[str]) -> str:
    """Bepaal bestands-extensie op basis van content_type of Pillow."""
    if content_type:
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
        if ct in mapping:
            return mapping[ct]

    # probeer via Pillow
    if PIL_OK:
        try:
            from io import BytesIO
            with Image.open(BytesIO(blob)) as im:
                fmt = (im.format or "").lower()
                if fmt in ("jpeg", "jpg"):
                    return "jpg"
                if fmt in ("png", "gif", "webp", "bmp", "tiff"):
                    return fmt
        except Exception:
            pass

    return "bin"


def _save_image_and_get_url(blob: bytes, content_type: Optional[str]) -> Optional[str]:
    """Sla blob op in UPLOAD_DIR en retourneer absolute URL voor Stermonitor."""
    try:
        _ensure_upload_dir()
        ext = _guess_ext(blob, content_type)
        fname = f"docx_{uuid.uuid4().hex}.{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(blob)
        return f"{UPLOAD_BASE_URL}/{fname}"
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
                content_type = getattr(part, "content_type", None)
            except Exception:
                continue

            size = _image_size(blob)
            w = size[0] if size else None
            h = size[1] if size else None
            small = bool(w and h and w < SMALL_W and h < SMALL_H)

            # 1) probeer opslaan op server
            url = _save_image_and_get_url(blob, content_type)

            # 2) fallback base64 (optioneel)
            if not url and FALLBACK_TO_BASE64:
                b64 = base64.b64encode(blob).decode("ascii")
                # mime wat netter:
                mime = (content_type or "image/png").split(";")[0]
                url = f"data:{mime};base64,{b64}"

            if not url:
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


def docx_to_html(path_or_filelike) -> str:
    """
    DOCX → HTML
    - Tekst als h1/h2/h3/p
    - Afbeeldingen: small samen in flex-rij, big apart (zoals jouw voorwaarden)
    - Afbeeldingen via server URLs (absolute) voor Stermonitor
    """
    doc = Document(path_or_filelike)

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

        # Afbeeldingen (voorwaarden overnemen)
        imgs = _img_infos_for_paragraph(para, doc)
        if not imgs:
            continue

        small_imgs = [i for i in imgs if i["small"]]
        big_imgs = [i for i in imgs if not i["small"]]

        # Small: samen in flex
        if small_imgs:
            out.append('<div style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0;">')
            for i in small_imgs:
                out.append(
                    f'<img src="{i["url"]}" alt="" '
                    f'style="max-width:{i["w"] or 100}px;max-height:{i["h"] or 100}px;object-fit:contain;" />'
                )
            out.append("</div>")

        # Big: apart
        for i in big_imgs:
            out.append(
                f'<p><img src="{i["url"]}" alt="" '
                f'style="max-width:300px;max-height:300px;object-fit:contain;" /></p>'
            )

    out.append("</div>")
    out.append("</body>")
    out.append("</html>")

    return "\n".join(out)

