def docx_to_html(path):
    return """
    <html>
    <head>
        <meta charset='utf-8'>
        <style>
            body { background: #e5ffd5; padding: 40px; font-family: Arial; }
            h1 { color: #27632a; }
            p { font-size: 18px; }
            .box {
                background: white;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #5a9448;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>✔ HTML werkt!</h1>
            <p>Deze HTML komt NIET uit het Word-bestand maar direct uit html_converter.py.</p>
            <p>Als je dit als mooie pagina ziet, dan werkt de HTML-keten.</p>
        </div>
    </body>
    </html>
    """

