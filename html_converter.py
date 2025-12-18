# html_converter.py
import os
import uuid
from html import escape
from typing import List, Dict, Optional, Any
from docx import Document

# Pillow voor image size (aanrader)
try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
UPLOAD_BASE_URL = "https://app.mediawize.nl/uploads"

# Linkerkolom breedte ≈ 371px
IMG_MAX_WIDTH_PX = 360

# Kleine thumbnails (strak raster)
SMALL_MAX_PX = 120            # <=120x120 → "klein"
SMALL_THUMB_H_PX = 90         # vaste hoogte
SMALL_THUMB_W_MAX_PX = 120    # max breedte
SMALL_GAP_PX = 8


# =========================
# Helpers
# =========================
def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _image_size(blob: bytes) -> Optional[tuple]:
    if not PIL_OK:
        return None
    try:
        from io import BytesIO
        with Image.open(BytesIO(blob)) as im:
            return im.width, im.height
    except Exception:
        return None


def _save_image(blob: bytes, content_type: Optional[str]) -> Optional[str]:
    try:
        _ensure_upload_dir()
        ct = (content_type or "").lower()

        ext = "png"
        if "jpeg" in ct or "jpg" in ct:
            ext = "jpg"
        elif "gif" in ct:
            ext = "gif"
        elif "webp" in ct:
            ext = "webp"

        fname = f"docx_{uuid.uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_DIR, fname)

        with open(path, "wb") as f:
            f.write(blob)

        return f"{UPLOAD_BASE_URL}/{fname}"
    except Exception:
        return None


def _is_heading1(p) -> bool:
    name = (getattr(p.style, "name", "") or "").lower()
    return name.startswith("heading 1") or name.startswith("kop 1")


def _looks_like_numbered_item(p) -> bool:
    name = (getattr(p.style, "name", "") or "").lower()
    return ("list" in name) and (("number" in name) or ("nummer" in name))


def _looks_like_bullet_item(p, text: str) -> bool:
    name = (getattr(p.style, "name", "") or "").lower()
    if ("list" in name) and (("bullet" in name) or ("opsom" in name)):
        return True
    return text.strip().startswith("-")


def _is_caption_paragraph(p) -> bool:
    try:
        return any((r.italic or r.bold) for r in p.runs)
    except Exception:
        return False


def _get_images_from_paragraph(p, doc: Document) -> List[Dict[str, Any]]:
    infos: List[Dict[str, Any]] = []

    for run in p.runs:
        blips = run._r.xpath(".//a:blip")
        for blip in blips:
            rId = blip.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
            )
            if not rId:
                continue
            try:
                part = doc.part.related_parts[rId]
                blob = part.blob
                url = _save_image(blob, getattr(part, "content_type", None))
                if not url:
                    continue

                size = _image_size(blob)
                w = size[0] if size else None
                h = size[1] if size else None
                small = bool(w and h and w <= SMALL_MAX_PX and h <= SMALL_MAX_PX)

                infos.append({
                    "url": url,
                    "small": small
                })
            except Exception:
                continue

    return infos


# =========================
# HTML rendering
# =========================
def _render_left_images(blocks: List[Dict[str, Any]]) -> str:
    parts: List[str] = []

    for b in blocks:
        imgs = b.get("images") or []
        cap = (b.get("caption") or "").strip()
        if not imgs:
            continue

        small_imgs = [i for i in imgs if i["small"]]
        big_imgs = [i for i in imgs if not i["small"]]

        # Kleine thumbnails → strak raster
        if small_imgs:
            thumbs = []
            for i in small_imgs:
                thumbs.append(
                    f'<img src="{escape(i["url"])}" alt="" '
                    f'style="height:{SMALL_THUMB_H_PX}px; width:auto; '
                    f'max-width:{SMALL_THUMB_W_MAX_PX}px; '
                    f'object-fit:contain; display:block;">'
                )
            parts.append(
                f'<div style="display:flex;flex-wrap:wrap;gap:{SMALL_GAP_PX}px; '
                f'margin-bottom:{SMALL_GAP_PX}px;">'
                + "".join(thumbs) +
                "</div>"
            )

        # Grote afbeeldingen → onder elkaar
        for i in big_imgs:
            parts.append(
                f'<div style="margin-bottom:{SMALL_GAP_PX}px;">'
                f'<img src="{escape(i["url"])}" alt="" '
                f'style="max-width:{IMG_MAX_WIDTH_PX}px;height:auto;object-fit:contain;">'
                f'</div>'
            )

        # Caption
        if cap:
            parts.append(
                f'<p style="text-align:center;margin:0 0 {SMALL_GAP_PX}px 0;">'
                f'<em><strong>{escape(cap)}</strong></em></p>'
            )

    return "\n".join(parts)


def _step_table_html(step: Dict[str, Any]) -> str:
    title = escape(step["title"])

    leerdoelen = "".join(f"<li>{escape(x)}</li>" for x in step["leerdoelen"])
    begrippen = "".join(f"<div>&nbsp;- {escape(x)}</div>" for x in step["begrippen"])

    left_html = _render_left_images(step["blocks"])
    right_html = "".join(
        f"<p>{escape(b['text'])}</p>" for b in step["blocks"] if b["text"]
    )

    return f"""
<table style="width:875px;background-color:rgba(250,227,200,1)" cellpadding="10">
<tbody>
<tr>
<td colspan="2" style="background-color:rgba(212,150,74,1)">
<h4><em><strong>{title}</strong></em></h4>
<p><strong>Leerdoelen:</strong></p>
<ol>{leerdoelen}</ol>
</td>
<td style="background-color:rgba(212,150,74,1)">
<p><strong>Begrippen:</strong></p>
{begrippen}
</td>
</tr>

<tr>
<td style="width:371px;vertical-align:top">{left_html}</td>
<td colspan="2" style="vertical-align:top">{right_html}</td>
</tr>
</tbody>
</table>

<div class="clearfix"></div>
""".strip()


# =========================
# Main
# =========================
def docx_to_html(path: str) -> str:
    doc = Document(path)
    steps = []
    current = None

    def new_step(title):
        nonlocal current
        current = {
            "title": title or "Stap",
            "leerdoelen": [],
            "begrippen": [],
            "blocks": [],
            "_mode": None,
            "_last": None,
            "_pending": None,
        }
        steps.append(current)

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        imgs = _get_images_from_paragraph(p, doc)

        if _is_heading1(p) and text:
            new_step(text)
            continue

        if current is None and (text or imgs):
            new_step("Les")

        if current is None:
            continue

        low = text.lower()

        if text and low.startswith("leerdoelen"):
            current["_mode"] = "leerdoelen"
            continue

        if text and low.startswith("begrippen"):
            current["_mode"] = "begrippen"
            continue

        if imgs and not text:
            if current["_last"]:
                current["_last"]["images"].extend(imgs)
                current["_pending"] = current["_last"]
            continue

        if text and current["_pending"] and _is_caption_paragraph(p):
            current["_pending"]["caption"] = text
            current["_pending"] = None
            continue

        if current["_mode"] == "leerdoelen" and text and _looks_like_numbered_item(p):
            current["leerdoelen"].append(text)
            continue

        if current["_mode"] == "begrippen" and text and _looks_like_bullet_item(p, text):
            current["begrippen"].append(text.lstrip("- ").strip())
            continue

        if text:
            b = {"text": text, "images": [], "caption": ""}
            if imgs:
                b["images"].extend(imgs)
                current["_pending"] = b
            current["blocks"].append(b)
            current["_last"] = b

    return "\n\n".join(_step_table_html(s) for s in steps)


