# html_converter.py
import os
import uuid
from html import escape
from typing import List, Dict, Optional, Any
from docx import Document

# Pillow optioneel (niet vereist)
try:
    from PIL import Image  # noqa: F401
    PIL_OK = True
except Exception:
    PIL_OK = False


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Map waar images fysiek opgeslagen worden
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# Stermonitor heeft absolute URL nodig
UPLOAD_BASE_URL = "https://app.mediawize.nl/uploads"

# Linkerkolom image styling
IMG_MAX_WIDTH_PX = 360  # past in linkercel (371px) met padding
IMG_BLOCK_MARGIN_PX = 10


# =========================
# Helpers
# =========================
def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_image(blob: bytes, content_type: Optional[str]) -> Optional[str]:
    """Sla image blob op in UPLOAD_DIR en retourneer absolute URL."""
    try:
        _ensure_upload_dir()

        ct = (content_type or "").lower()
        ext = "png"
        if "jpeg" in ct or "jpg" in ct:
            ext = "jpg"
        elif "png" in ct:
            ext = "png"
        elif "gif" in ct:
            ext = "gif"
        elif "webp" in ct:
            ext = "webp"

        fname = f"docx_{uuid.uuid4().hex}.{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)

        with open(fpath, "wb") as f:
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
    if ("list" in name) and (("bullet" in name) or ("opsom" in name) or ("bollet" in name)):
        return True
    return text.strip().startswith("-")


def _get_images_from_paragraph(p, doc: Document) -> List[str]:
    urls: List[str] = []
    for run in p.runs:
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
                url = _save_image(part.blob, getattr(part, "content_type", None))
                if url:
                    urls.append(url)
            except Exception:
                continue
    return urls


def _is_caption_paragraph(p) -> bool:
    """Caption detectie: cursief of vet (zoals je gebruikte)."""
    try:
        return any((r.italic or r.bold) for r in p.runs)
    except Exception:
        return False


# =========================
# HTML builder (images LEFT, text RIGHT)
# =========================
def _step_table_html(step: Dict[str, Any]) -> str:
    title = escape(step.get("title") or "Stap")

    leerdoelen = step.get("leerdoelen") or []
    begrippen = step.get("begrippen") or []
    blocks = step.get("blocks") or []

    leerdoelen_li = "".join(f"<li>{escape(x)}</li>" for x in leerdoelen)
    begrippen_divs = "".join(f"<div>&nbsp;- {escape(x)}</div>" for x in begrippen)

    # Verzamel alle afbeeldingen (met captions) uit blocks -> links
    left_parts: List[str] = []
    for b in blocks:
        imgs = b.get("images") or []
        cap = (b.get("caption") or "").strip()

        for u in imgs:
            left_parts.append(
                f'<div style="margin-bottom:{IMG_BLOCK_MARGIN_PX}px;">'
                f'  <img src="{escape(u)}" alt="" '
                f'       style="display:block;max-width:{IMG_MAX_WIDTH_PX}px;height:auto;object-fit:contain;" />'
                f'</div>'
            )

        if cap and imgs:
            left_parts.append(
                f'<p style="text-align:center;margin:0 0 {IMG_BLOCK_MARGIN_PX}px 0;">'
                f'<em><strong>{escape(cap)}</strong></em></p>'
            )

    left_img_html = "\n".join(left_parts)

    # Tekst rechts (alle block teksten)
    right_text_html = "".join(
        f"<p>{escape((b.get('text') or '').strip())}</p>"
        for b in blocks
        if (b.get("text") or "").strip()
    )

    return f"""
<table style="width: 875px; background-color: rgba(250, 227, 200, 1); border-color: rgba(250, 227, 200, 1)" border="ja" cellpadding="10" class="striped bordered compressed margin-bottom">
<tbody>
<tr style="height: 139px">
  <td style="border-color: rgba(0, 0, 0, 1); background-color: rgba(212, 150, 74, 1); height: 139px; width: 944.5px" colspan="2" class="black-border">
    <h4><span style="color: rgba(0, 0, 0, 1)"><em><strong>{title}</strong></em></span></h4>
    <p><strong>Leerdoelen bij deze stap:</strong></p>
    <ol>
      {leerdoelen_li}
    </ol>
  </td>
  <td style="border-color: rgba(0, 0, 0, 1); background-color: rgba(212, 150, 74, 1); vertical-align: top; height: 139px; width: 304.5px" class="black-border">
    <p><strong>Belangrijke begrippen:</strong></p>
    {begrippen_divs}
  </td>
</tr>

<tr style="height: 306px">
  <!-- ✅ LINKS: ALLE AFBEELDINGEN -->
  <td style="height: 306px; width: 371px; vertical-align: top;">
    {left_img_html}
  </td>

  <!-- ✅ RECHTS: ALLE TEKST -->
  <td style="height: 306px; width: 878px; vertical-align: top;" colspan="2">
    {right_text_html}
  </td>
</tr>
</tbody>
</table>

<div class="clearfix"></div>
<div class="clearfix"></div>
<div class="clearfix"></div>
""".strip()


# =========================
# Main converter
# =========================
def docx_to_html(path: str) -> str:
    """
    DOCX -> Stermonitor-stijl HTML
    - Elke Kop1 = nieuwe stap
    - Leerdoelen: na 'Leerdoelen...' en genummerde lijst
    - Begrippen: na 'Belangrijke begrippen...' en bullets of '-'
    - Uitleg: elke tekstparagraaf => block
    - Afbeelding in dezelfde paragraaf => aan block gekoppeld
    - Afbeelding op volgende lege paragraaf => aan vorige block gekoppeld
    - Caption (cursief/vet) na image-only paragraaf => caption op vorige block
    - Geen Kop1? => 1 stap 'Les'
    """
    doc = Document(path)

    steps: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    def new_step(title: str):
        nonlocal current
        current = {
            "title": title.strip() or "Stap",
            "leerdoelen": [],
            "begrippen": [],
            "blocks": [],
            "_mode": None,
            "_last_block": None,
            "_pending_image_block": None,
        }
        steps.append(current)

    def ensure_last_block():
        if current is None:
            return None
        if not current["_last_block"]:
            b = {"text": "", "images": [], "caption": ""}
            current["blocks"].append(b)
            current["_last_block"] = b
        return current["_last_block"]

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        imgs = _get_images_from_paragraph(p, doc)

        # Start stap
        if _is_heading1(p) and text:
            new_step(text)
            continue

        # Fallback stap
        if current is None and (text or imgs):
            new_step("Les")

        if current is None:
            continue

        low = text.lower()

        # Mode switches
        if text:
            if low.startswith("leerdoelen"):
                current["_mode"] = "leerdoelen"
                continue
            if low.startswith("belangrijke begrippen") or low.startswith("begrippen"):
                current["_mode"] = "begrippen"
                continue

        # Image-only paragraph -> bij vorige block
        if imgs and not text:
            b = ensure_last_block()
            if b is not None:
                b["images"].extend(imgs)
                current["_pending_image_block"] = b
            continue

        # Caption na image-only
        if text and current.get("_pending_image_block") is not None and _is_caption_paragraph(p):
            current["_pending_image_block"]["caption"] = text
            current["_pending_image_block"] = None
            continue

        # Leerdoelen
        if current.get("_mode") == "leerdoelen" and text and _looks_like_numbered_item(p):
            current["leerdoelen"].append(text)
            continue

        # Begrippen
        if current.get("_mode") == "begrippen" and text and _looks_like_bullet_item(p, text):
            current["begrippen"].append(text.lstrip("- ").strip())
            continue

        # Uitleg tekst -> nieuw block (met images als ze in dezelfde paragraaf zitten)
        if text:
            b = {"text": text, "images": [], "caption": ""}
            if imgs:
                b["images"].extend(imgs)
                current["_pending_image_block"] = b
            current["blocks"].append(b)
            current["_last_block"] = b
            continue

    return "\n\n".join(_step_table_html(s) for s in steps)

