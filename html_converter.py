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


# ================= CONFIG =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
UPLOAD_BASE_URL = "https://app.mediawize.nl/uploads"

SMALL_W = 100
SMALL_H = 100


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
        ext = "png"
        if content_type and "jpeg" in content_type:
            ext = "jpg"
        fname = f"docx_{uuid.uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            f.write(blob)
        return f"{UPLOAD_BASE_URL}/{fname}"
    except Exception:
        return None


def _is_heading1(p) -> bool:
    return (p.style.name or "").lower().startswith("heading 1") or \
           (p.style.name or "").lower().startswith("kop 1")


def _get_images_from_paragraph(p, doc: Document) -> List[str]:
    urls = []
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
                url = _save_image(part.blob, getattr(part, "content_type", None))
                if url:
                    urls.append(url)
            except Exception:
                continue
    return urls


# ================= CONVERTER =================
def docx_to_html(path: str) -> str:
    doc = Document(path)

    # Stap-structuur
    steps: List[Dict] = []
    current = None

    for p in doc.paragraphs:
        text = (p.text or "").strip()

        if _is_heading1(p):
            current = {
                "title": text,
                "leerdoelen": [],
                "begrippen": [],
                "uitleg": [],
                "images": [],
                "onderschrift": None,
            }
            steps.append(current)
            continue

        if not current or not text:
            continue

        # Leerdoelen
        if text.lower().startswith("leerdoelen"):
            current["_mode"] = "leerdoelen"
            continue

        # Begrippen
        if text.lower().startswith("belangrijke begrippen"):
            current["_mode"] = "begrippen"
            continue

        mode = current.get("_mode")

        if mode == "leerdoelen" and p.style.name.startswith("List Number"):
            current["leerdoelen"].append(text)
            continue

        if mode == "begrippen" and (
            p.style.name.startswith("List Bullet") or text.startswith("-")
        ):
            current["begrippen"].append(text.lstrip("- ").strip())
            continue

        # Afbeeldingen
        imgs = _get_images_from_paragraph(p, doc)
        if imgs:
            current["images"].extend(imgs)
            continue

        # Onderschrift (cursief of vet)
        if any(run.italic or run.bold for run in p.runs):
            if not current["onderschrift"]:
                current["onderschrift"] = text
                continue

        # Uitleg
        current["uitleg"].append(text)

    # ================= HTML OPBOUW =================
    out = []

    for step in steps:
        leerdoelen_html = "".join(
            f"<li>{escape(ld)}</li>" for ld in step["leerdoelen"]
        )
        begrippen_html = "".join(
            f"<div>&nbsp;- {escape(b)}</div>" for b in step["begrippen"]
        )

        img_html = ""
        if step["images"]:
            img_html = (
                f'<p><img src="{step["images"][0]}" width="362" height="258"></p>'
            )

        onderschrift_html = ""
        if step["onderschrift"]:
            onderschrift_html = (
                f'<p style="text-align:center"><em><strong>{escape(step["onderschrift"])}</strong></em></p>'
            )

        uitleg_html = "".join(f"<p>{escape(t)}</p>" for t in step["uitleg"])

        out.append(f"""
<table style="width: 875px; background-color: rgba(250,227,200,1); border-color: rgba(250,227,200,1)"
       border="ja" cellpadding="10" class="striped bordered compressed margin-bottom">
<tbody>

<tr style="height:139px">
<td colspan="2" style="background-color: rgba(212,150,74,1)" class="black-border">
<h4><em><strong>{escape(step["title"])}</strong></em></h4>
<p><strong>Leerdoelen bij deze stap:</strong></p>
<ol>{leerdoelen_html}</ol>
</td>

<td style="background-color: rgba(212,150,74,1); vertical-align:top" class="black-border">
<p><strong>Belangrijke begrippen:</strong></p>
{begrippen_html}
</td>
</tr>

<tr style="height:306px">
<td style="width:371px">
{img_html}
{onderschrift_html}
</td>

<td colspan="2" style="width:878px">
{uitleg_html}
</td>
</tr>

</tbody>
</table>

<div class="clearfix"></div><div class="clearfix"></div><div class="clearfix"></div>
""")

    return "\n".join(out)
