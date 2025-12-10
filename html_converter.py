from docx import Document

def docx_to_html(docx_path: str) -> str:
    """
    Eenvoudige DOCX → HTML converter.
    Zet alle paragrafen om naar <p>-tags.
    Later kun je dit uitbreiden met tabellen, koppen, lijstjes, etc.
    """
    doc = Document(docx_path)
    html_parts = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            html_parts.append(f"<p>{text}</p>")

    # Als er niets is, toch iets teruggeven
    if not html_parts:
        return "<p>(Geen inhoud gevonden in dit document)</p>"

    return "\n".join(html_parts)
