# modules/workbook/builder.py
from __future__ import annotations

import io
from typing import Any

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _add_title(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(title.strip() if title else "Werkboekje")
    run.bold = True
    run.font.size = Pt(20)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _add_meta_block(doc: Document, meta: dict[str, Any]) -> None:
    vak = (meta.get("vak") or "").upper()
    profieldeel = meta.get("profieldeel") or ""
    docent = meta.get("docent") or ""
    duur = meta.get("duur") or ""

    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"

    def row(k: str, v: str) -> None:
        r = table.add_row().cells
        r[0].text = k
        r[1].text = v

    if vak:
        row("Vak", vak)
    if profieldeel:
        row("Profieldeel", profieldeel)
    if docent:
        row("Docent", docent)
    if duur:
        row("Duur", duur)

    doc.add_paragraph()  # witruimte


def _try_add_image(doc: Document, img_bytes: bytes, width_inches: float) -> None:
    """
    python-docx kan add_picture() met file-like.
    We zetten de stream terug op 0 en voegen toe.
    """
    bio = io.BytesIO(img_bytes)
    bio.seek(0)
    doc.add_picture(bio, width=Inches(width_inches))


def _add_cover(doc: Document, meta: dict[str, Any]) -> None:
    cover = meta.get("cover_bytes")
    if not cover:
        return
    try:
        _try_add_image(doc, cover, width_inches=6.5)
        doc.add_paragraph()
    except Exception:
        # Cover is optioneel; bij fout gewoon doorgaan
        doc.add_paragraph()


def _add_materiaalstaat(doc: Document, meta: dict[str, Any]) -> None:
    if not meta.get("include_materiaalstaat"):
        return

    materialen = meta.get("materialen") or []
    doc.add_paragraph().add_run("Materiaalstaat").bold = True

    headers = ["Nummer", "Aantal", "Benaming", "Lengte", "Breedte", "Dikte", "Materiaal"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"

    # header row
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        run = hdr_cells[i].paragraphs[0].add_run(h)
        run.bold = True

    # rows
    for item in materialen:
        row_cells = table.add_row().cells
        for i, h in enumerate(headers):
            row_cells[i].text = str(item.get(h, "") or "")

    doc.add_paragraph()


def _add_step(doc: Document, idx: int, step: dict[str, Any]) -> None:
    title = (step.get("title") or "").strip()
    text_blocks = step.get("text_blocks") or []
    images = step.get("images") or []

    # Stap titel
    heading = doc.add_paragraph()
    run = heading.add_run(f"Stap {idx}: {title}" if title else f"Stap {idx}")
    run.bold = True
    run.font.size = Pt(14)

    # Tekst
    for block in text_blocks:
        b = (block or "").strip()
        if b:
            doc.add_paragraph(b)

    # Afbeeldingen (max 3 naast elkaar; daarna nieuwe rij)
    # We gebruiken een tabel om het strak te houden.
    if images:
        cols = 3
        table = doc.add_table(rows=0, cols=cols)
        table.autofit = True

        row = None
        for i, img_bytes in enumerate(images):
            if i % cols == 0:
                row = table.add_row().cells

            cell = row[i % cols]
            try:
                bio = io.BytesIO(img_bytes)
                bio.seek(0)
                # iets kleiner zodat 3 naast elkaar past
                cell.paragraphs[0].add_run().add_picture(bio, width=Inches(2.0))
            except Exception:
                cell.text = "(afbeelding kon niet worden ingeladen)"

        doc.add_paragraph()

    # scheiding
    doc.add_paragraph()


def build_workbook_docx_front_and_steps(meta: dict[str, Any], steps: list[dict[str, Any]]) -> io.BytesIO:
    """
    Bouwt een DOCX en geeft een BytesIO terug (geschikt voor Flask send_file).
    meta: dict met o.a. vak, opdracht_titel, profieldeel, docent, duur,
          include_materiaalstaat, materialen (list), cover_bytes (bytes optioneel)
    steps: list van dicts met:
          title (str), text_blocks (list[str]), images (list[bytes])
    """
    doc = Document()

    # Front / cover
    _add_title(doc, meta.get("opdracht_titel") or "Werkboekje")
    _add_cover(doc, meta)
    _add_meta_block(doc, meta)
    _add_materiaalstaat(doc, meta)

    # Stappen
    if steps:
        doc.add_paragraph().add_run("Stappen").bold = True
        doc.add_paragraph()

    for i, step in enumerate(steps, start=1):
        _add_step(doc, i, step)

    # Export naar BytesIO
    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out

