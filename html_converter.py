# html_converter.py
import os
import uuid
from html import escape
from typing import List, Dict, Optional, Any
from docx import Document

# Pillow (optioneel) – niet nodig voor werking, wel handig later
try:
    from PIL import Image  # noqa: F401
    PIL_OK = True
except Exception:
    PIL_OK = False


# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Nginx moet /uploads/ mappen naar deze map (bij jou: /opt/mediawize/uploads)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# Voor Stermonitor moet dit ABSOLUUT zijn
UPLOAD_BASE_URL = "https://app.mediawize.nl/uploads"

# Afbeelding styling in kolom rechts
IMG_COL_WIDTH_PX = 320
IMG_MAX_WIDTH_PX = 300


# =========================
# Helpers
# =========================
def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_image(blob: bytes, content_type: Optional[str]) -> Optional[str]:
    """
    Sla image blob op in UPLOAD_DIR en retourneer absolute URL.
    """
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
    """
    Robuust voor NL/EN Word: style bevat vaak list + number/nummer.
    """
    name = (getattr(p.style, "name", "") or "").lower()
    return ("list" in name) and (("number" in name) or ("nummer" in name))


def _looks_like_bullet_item(p, text: str) -> bool:
    name = (getattr(p.style, "name", "") or "").lower()
    if ("list" in name) and (("bullet" in name) or ("opsom" in name) or ("bollet" in name)):
        return True
    if text.strip().startswith("-"):
        return True
    return False


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
                blob = part.blob
                ctype = getattr(part, "content_type", None)
                url = _save_image(blob, ctype)
                if url:
                    urls.append(url)
            except Exception:
                continue
    return urls


def _is_caption_paragraph(p) -> bool:
    """
    Simpele caption detectie: cursief of vet (zoals je eerder deed).
    """
    try:
        return any((r.italic or r.bold) for r in p.runs)
    except Exception:
        return False


# =========================
# HTML builders
# =========================
def _step_table_html(step: Dict[str, Any]) -> str:
    """
    Bouwt jouw Stermonitor-stijl stap-blok:
    - header rij met titel/leerdoelen + begrippen
    - content rij met links (eventuele header image) en rechts nested table per tekstblok + image(s)
    """

    title = escape(step.get("title") or "Stap")

    leerdoelen = step.get("leerdoelen") or []
    begrippen = step.get("begrippen") or []
    blocks = step.get("blocks") or []

    leerdoelen_li = "".join(f"<li>{escape(x)}</li>" for x in leerdoelen)
    begrippen_divs = "".join(f"<div>&nbsp;- {escape(x)}</div>" for x in begrippen)

    # LEFT cell: “header image” (eerste image van eerste block, als je wilt)
    # Jij wil vooral “naast elk stukje tekst”, dus we laten links leeg OF tonen alleen als er echt iets is.
    left_img_html = ""
    if step.get("left_image_url"):
        left_img_html = (
            f'<p><img src="{escape(step["left_image_url"])}" alt="" '
            f'style="max-width:{IMG_MAX_WIDTH_PX}px;height:auto;object-fit:contain;" /></p>'
        )
        if step.get("left_caption"):
            left_img_html += (
                f'<p style="text-align:center"><em><strong>{escape(step["left_caption"])}</strong></em></p>'
            )

    # RIGHT cell content: nested table with rows:
    # - if block has images => 2 columns (text | image column)
    # - else => 1 column spanning 2 columns
    nested_rows: List[str] = []
    for b in blocks:
        txt = (b.get("text") or "").strip()
        imgs = b.get("images") or []
        cap = (b.get("caption") or "").strip()

        text_html = ""
        if txt:
            # behoud simpele alineas; je kunt later <br> logica toevoegen als je wil
            text_html = f"<p>{escape(txt)}</p>"

        imgcol_html = ""
        if imgs:
            # meerdere afbeeldingen onder elkaar in rechter kolom
            img_parts = []
            for u in imgs:
                img_parts.append(
                    f'<img src="{escape(u)}" alt="" '
                    f'style="display:block;margin:0 0 8px 0;max-width:{IMG_MAX_WIDTH_PX}px;height:auto;object-fit:contain;" />'
                )
            if cap:
                img_parts.append(
                    f'<p style="text-align:center;margin:0;"><em><strong>{escape(cap)}</strong></em></p>'
                )
            imgcol_html = "\n".join(img_parts)

        if imgs:
            nested_rows.append(
                "<tr>"
                f'<td style="vertical-align:top;">{text_html}</td>'
                f'<td style="vertical-align:top;width:{IMG_COL_WIDTH_PX}px;">{imgcol_html}</td>'
                "</tr>"
            )
        else:
            # geen image: volle breedte
            nested_rows.append(
                "<tr>"
                f'<td colspan="2" style="vertical-align:top;">{text_html}</td>'
                "</tr>"
            )

    nested_table = (
        '<table style="width:100%;border-collapse:collapse;" cellpadding="6">'
        + "".join(nested_rows)
        + "</table>"
    )

    return f"""
<table style="width: 875px; background-color: rgba(250, 227, 200, 1); border-color: rgba(250, 227, 200, 1)"
       border="ja" cellpadding="10" class="striped bordered compressed margin-bottom">
<tbody>

<tr style="height: 139px">
  <td style="border-color: rgba(0, 0, 0, 1); background-color: rgba(212, 150, 74, 1); height: 139px; width: 944.5px"
      colspan="2" class="black-border">
    <h4><span style="color: rgba(0, 0, 0, 1)"><em><strong>{title}</strong></em></span></h4>
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
    {left_img_html}
  </td>

  <td style="height: 306px; width: 878px" colspan="2">
    {nested_table}
  </td>
</tr>

</tbody>
</table>

<div class="clearfix"></div><div class="clearfix"></div><div class="clearfix"></div>
""".strip()


# =========================
# Main converter
# =========================
def docx_to_html(path: str) -> str:
    """
    DOCX -> Stermonitor-stijl HTML.

    Belangrijkste regels:
    - Elke Kop1/Heading1 start een nieuwe stap.
    - 'Leerdoelen...' zet mode leerdoelen: p in numbered list wordt leerdoel.
    - 'Belangrijke begrippen...' of 'Begrippen...' zet mode begrippen: bullets / '-' regels worden begrippen.
    - Voor de uitleg maken we BLOCKS:
        * elke tekstparagraaf is een block
        * afbeeldingen in dezelfde paragraaf -> horen bij die block
        * afbeelding in volgende paragraaf met geen tekst -> hoort bij vorige block
        * caption (cursief/vet) direct na een image-only paragraaf -> caption op vorige block
    - Als er geen Kop1 in het document zit: alles wordt 1 stap 'Les'.
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
            "_last_block": None,          # laatste uitleg block
            "_pending_image_block": None, # block dat net images kreeg en wacht op caption
            "left_image_url": None,
            "left_caption": None,
        }
        steps.append(current)

    # Helper: maak/haal laatste block
    def ensure_last_block():
        if current is None:
            return None
        if not current["_last_block"]:
            b = {"text": "", "images": [], "caption": ""}
            current["blocks"].append(b)
            current["_last_block"] = b
        return current["_last_block"]

    # Itereer door paragraphs
    for p in doc.paragraphs:
        text_raw = p.text or ""
        text = text_raw.strip()
        imgs = _get_images_from_paragraph(p, doc)

        # Start stap
        if _is_heading1(p) and text:
            new_step(text)
            continue

        # Fallback: geen step yet, maar wél content => maak 'Les'
        if current is None and (text or imgs):
            new_step("Les")

        if current is None:
            continue

        low = text.lower()

        # Mode switches (alleen als er tekst is)
        if text:
            if low.startswith("leerdoelen"):
                current["_mode"] = "leerdoelen"
                continue
            if low.startswith("belangrijke begrippen") or low.startswith("begrippen"):
                current["_mode"] = "begrippen"
                continue

        # Image-only paragraph: koppel aan vorige block (naast tekst)
        if imgs and not text:
            b = ensure_last_block()
            if b is not None:
                b["images"].extend(imgs)
                current["_pending_image_block"] = b
            continue

        # Caption: tekst met italic/bold en er is een pending image-block
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

        # UITLEG: tekstparagraaf => nieuw block
        if text:
            b = {"text": text, "images": [], "caption": ""}
            if imgs:
                # images in dezelfde paragraaf naast deze tekst
                b["images"].extend(imgs)
                current["_pending_image_block"] = b
            current["blocks"].append(b)
            current["_last_block"] = b
            continue

        # Als hier niets matcht: negeren (lege paragrafen zonder images)
        continue

    # Optional: zet eerste image als left_image (zoals in voorbeeld), maar alleen als je dat wil.
    # Jij wilt vooral “naast elk stukje tekst”. Daarom laten we left leeg.
    # Wil je wél: pak de eerste image uit eerste block en haal hem uit de block images.
    # (zet hieronder True om dit te activeren)
    USE_LEFT_IMAGE = False
    if USE_LEFT_IMAGE:
        for step in steps:
            if step["blocks"]:
                b0 = step["blocks"][0]
                if b0.get("images"):
                    step["left_image_url"] = b0["images"][0]
                    if b0.get("caption"):
                        step["left_caption"] = b0["caption"]
                        b0["caption"] = ""
                    b0["images"] = b0["images"][1:]

    # Bouw output
    html_blocks = [_step_table_html(s) for s in steps]
    return "\n\n".join(html_blocks)

