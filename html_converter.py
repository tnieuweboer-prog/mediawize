from docx import Document  # mag blijven staan, ook al gebruiken we het straks niet

def docx_to_html(file_like) -> str:
    # TIJDELIJKE TESTVERSIE
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HTML TEST VANUIT VPS</title>
</head>
<body style="background: #cde; font-family: Arial, sans-serif;">
    <h1>✅ HTML KOMT BINNEN VANUIT docx_to_html()</h1>
    <p>Als je dit ziet, werkt Flask + Nginx + app.py gewoon goed.</p>
</body>
</html>
"""

