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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
UPLOAD_BASE_URL = "https://app.mediawize.nl/uploads"

SMALL_W = 100
SMALL_H = 100


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_image(blob: bytes, content_type: Optional[str]) -> Optional[str]:
    try:
        _ensure_upload_dir()
        ext = "png"
        if content_type and "jpeg" in content_type.lower():
            ext = "jpg"
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
    """Robuust: style kan NL/anders heten. We checken op 'number'/'nummer' in style naam."""
    name = (getattr(p.style, "name", "") or "").lower()
    if "list" in name and ("number" in name or "nummer" in name):
        return True
    return False


def _looks_like_bullet_item(p, text: str) -> bool:
    name = (getattr(p.style, "name", "") or "").lower()
    if "list" in name and ("bullet" in name or "opsom" in name or "bolletje" in name):
        return True
    if text.strip().startswith("-"):
        return True
    return False


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


def docx_to_html(path: str) -> str:
    doc = Document(path)

    steps: List[Dict] = []
    current: Optional[Dict] = None

    def _new_step(title: str):
        nonlocal current
        current = {
            "title": title,
            "leerdoelen": [],
            "begrippen": [],
            "uitleg": [],
            "images": [],
            "onderschrift": None,
            "_mode": None,
        }
        steps.append(current)

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text and not p.runs:
            continue

        # Start nieuwe stap op Kop 1
        if _is_heading1(p):
            _new_step(text or "Stap")
            continue

        # Fallback: als er nog geen stap is, maak er eentje
        if current is None and text:
            _new_step("Les")

        if current is None:
            continue

        if not text:
            # maar afbeeldingen kunnen wel in lege paragrafen zitten
            imgs = _get_images_from_paragraph(p, doc)
            if imgs:
                current["images"].extend(imgs)
            continue

        low = text.lower()

        # Modus switches
        if low.startswith("leerdoelen"):
            current["_mode"] = "leerdoelen"
            continue

        if low.startswith("belangrijke begrippen") or low.startswith("begrippen"):
            current["_mode"] = "begrippen"
            continue

        # Afbeeldingen eerst pakken
        imgs = _get_images_from_paragraph(p, doc)
        if imgs:
            current["images"].extend(imgs)
            continue

        # Leerdoelen items
        if current.get("_mode") == "leerdoelen" and _looks_like_numbered_item(p):
            current["leerdoelen"].append(text)
            continue

        # Begrippen items
        if current.get("_mode") == "begrippen" and _looks_like_bullet_item(p, text):
            current["begrippen"].append(text.lstrip("- ").strip())
            continue

        # Onderschrift: cursief/vet (eerste keer)
        if current["onderschrift"] is None and any((r.italic or r.bold) for r in p.runs):
            current["onderschrift"] = text
            continue

        # Uitleg
        current["uitleg"].append(text)

    # Bouw HTML in jouw Stermonitor tabelstijl
    out = []
    for step in steps:
        leerdoelen_li = "".join(f"<li>{escape(x)}</li>" for x in step["leerdoelen"])
        begrippen_divs = "".join(f"<div>&nbsp;- {escape(x)}</div>" for x in step["begrippen"])

        img_html = ""
        if step["images"]:
            img_html = f'<p><img src="{step["images"][0]}" alt="" width="362" height="258"></p>'

        onderschrift_html = ""
        if step["onderschrift"]:
            onderschrift_html = (
                f'<p style="text-align: center"><em><strong>{escape(step["onderschrift"])}</strong></em></p>'
            )

        uitleg_html = "".join(f"<p>{escape(t)}</p>" for t in step["uitleg"])

        out.append(f"""
<table style="width: 875px; background-color: rgba(250, 227, 200, 1); border-color: rgba(250, 227, 200, 1)"
       border="ja" cellpadding="10" class="striped bordered compressed margin-bottom">
<tbody>
<tr style="height: 139px">
  <td style="border-color: rgba(0, 0, 0, 1); background-color: rgba(212, 150, 74, 1); height: 139px; width: 944.5px"
      colspan="2" class="black-border">
    <h4><span style="color: rgba(0, 0, 0, 1)"><em><strong>{escape(step["title"])}</strong></em></span></h4>
    <p><strong>Leerdoelen bij deze stap:</strong></p>
    <ol>
      {leerdoelen_li}
    </ol>
  </td>
  <td style="border-color: rgba(0, 0, 0, 1); background-color: rgba(212, 150, 74, 1); vertical-align: top; height: 139px; width: 304.5px"
      class="black-border">
    <p><strong>Belangrijke begrippen:</strong></p>
    {begrippen_divs}
  </td>
</tr>
<tr style="height: 306px">
  <td style="height: 306px; width: 371px">
    {img_html}
    {onderschrift_html}
  </td>
  <td style="height: 306px; width: 878px" colspan="2">
    {uitleg_html}
  </td>
</tr>
</tbody>
</table>

<div class="clearfix"></div><div class="clearfix"></div><div class="clearfix"></div>
""")

    return "\n".join(out)
