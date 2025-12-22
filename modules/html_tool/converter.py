# modules/html_tool/converter.py
from __future__ import annotations

from docx import Document
import html


def _is_heading(paragraph) -> bool:
    try:
        name = paragraph.style.name or ""
        return name.lower().startswith("heading")
    except Exception:
        return False


def docx_to_html(docx_path: str) -> str:
    """
    Minimale, stabiele DOCX -> HTML converter.
    Doel: weer online krijgen en basis output voor Stermonitor.
    Later breiden we uit met:
    - tabellen + jouw Triade styling
    - afbeeldingen in tabel links / tekst rechts
    - meerdere afbeeldingen naast elkaar met vaste hoogte
    """
    doc = Document(docx_path)

    parts: list[str] = []
    parts.append('<div class="triade-docx">')

    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue

        safe = html.escape(text)

        if _is_heading(p):
            parts.append(f"<h2>{safe}</h2>")
        else:
            parts.append(f"<p>{safe}</p>")

    parts.append("</div>")
    return "\n".join(parts)

