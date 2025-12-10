from docx import Document
from html import escape
# + jouw _img_infos_for_paragraph, _is_heading, etc.

def docx_to_html(file_like) -> str:
    """ DOCX → HTML met 1 overkoepelende groene div. """

    doc = Document(file_like)

    out = [
        "<html>",
        "<head>",
        "<style>",
        "body { margin: 0; padding: 0; }",
        ".green { ... }",
        ".lesson { ... }",
        "</style>",
        "</head>",
        "<body class='green'>",
        "<div class='lesson light-green'>"
    ]

    # ... hier jouw koppen, paragrafen, afbeeldingen ...

    out.append("</div>")
    out.append("</body>")
    out.append("</html>")

    return "\n".join(out)
