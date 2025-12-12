from flask import Flask, request, send_file
from html_converter import docx_to_html
from workbook_builder import build_workbook_docx_front_and_steps
from html import escape
import tempfile
import os

app = Flask(__name__)

BASE_PAGE = """
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <title>{page_title}</title>
    <style>
        :root {{
            --bg: #f3f7fb;
            --card-bg: #ffffff;
            --accent: #0fa14b;
            --accent-soft: #e5f7ee;
            --accent-dark: #0b6f35;
            --border-soft: #dde5f0;
            --text-main: #1f2933;
            --text-muted: #6b7280;
            --danger: #e11d48;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: radial-gradient(circle at top left, #e0f7ff 0, #f3f7fb 45%, #eef7f0 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            color: var(--text-main);
        }}
        .app-shell {{ width: 100%; max-width: 1040px; }}
        .app-header {{ margin-bottom: 0.75rem; }}
        .badge {{
            display: inline-flex; align-items: center; gap: 0.4rem;
            background: var(--accent-soft); color: var(--accent-dark);
            padding: 0.3rem 0.75rem; border-radius: 999px;
            font-size: 0.8rem; font-weight: 600;
        }}
        .badge-dot {{ width: 8px; height: 8px; border-radius: 999px; background: var(--accent); }}
        .app-title {{ font-size: 1.6rem; margin: 0.6rem 0 0.25rem 0; }}
        .app-subtitle {{ margin: 0; font-size: 0.95rem; color: var(--text-muted); }}
        .tabs {{
            margin-top: 0.9rem; display: inline-flex;
            background: rgba(255,255,255,0.9);
            border-radius: 999px; padding: 0.12rem;
            box-shadow: 0 8px 20px rgba(15,24,41,0.12);
        }}
        .tab {{
            border: none; padding: 0.35rem 1.2rem; font-size: 0.85rem;
            border-radius: 999px; background: transparent; cursor: pointer;
            color: var(--text-muted); text-decoration: none;
            display: inline-flex; align-items: center; gap: 0.35rem;
        }}
        .tab-active {{ background: #0f172a; color: #e5e7eb; }}
        .card {{
            margin-top: 1.1rem; background: var(--card-bg); border-radius: 18px;
            box-shadow: 0 18px 45px rgba(15, 24, 41, 0.12), 0 0 0 1px rgba(209, 213, 219, 0.3);
            padding: 1.5rem 1.75rem;
        }}
        .two-cols {{
            display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.35fr);
            gap: 1.5rem;
        }}
        @media (max-width: 860px) {{
            .two-cols {{ grid-template-columns: minmax(0, 1fr); }}
        }}
        .col-left {{
            border-right: 1px solid var(--border-soft);
            padding-right: 1.25rem;
        }}
        @media (max-width: 860px) {{
            .col-left {{
                border-right: none; border-bottom: 1px solid var(--border-soft);
                padding-right: 0; padding-bottom: 1.25rem;
            }}
        }}
        .col-right {{ padding-left: 0.25rem; }}
        .section-title {{ font-size: 1.05rem; margin: 0 0 0.4rem 0; }}
        .section-text {{ margin: 0 0 0.6rem 0; font-size: 0.9rem; color: var(--text-muted); }}
        .error {{
            margin: 0.2rem 0 0.75rem 0; font-size: 0.85rem; color: var(--danger);
            background: #fee2e2; border-radius: 10px; padding: 0.45rem 0.75rem;
        }}
        form {{ margin-top: 0.5rem; }}
        label.small {{
            display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.1rem;
        }}
        input[type="text"], textarea {{
            width: 100%; border-radius: 10px; border: 1px solid #e5e7eb;
            padding: 0.4rem 0.55rem; font-size: 0.9rem; font-family: inherit;
        }}
        textarea {{ resize: vertical; }}
        .row {{
            display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 0.55rem;
        }}
        .file-label {{
            display: inline-flex; align-items: center; gap: 0.5rem;
            background: #f3f4ff; border-radius: 999px; padding: 0.4rem 0.85rem;
            border: 1px dashed #cbd5f5; font-size: 0.8rem; cursor: pointer; color: #374151;
            margin-top: 0.25rem;
        }}
        .file-label span.icon {{
            width: 18px; height: 18px; border-radius: 999px; background: #e0e7ff;
            display: inline-flex; align-items: center; justify-content: center; font-size: 12px;
        }}
        input[type="file"] {{ display: none; }}
        .file-name {{
            display: block; margin-top: 0.25rem; font-size: 0.75rem;
            color: var(--text-muted); min-height: 1rem;
        }}
        .actions {{ margin-top: 0.9rem; display: flex; gap: 0.5rem; }}
        .btn-primary {{
            border: none; outline: none; cursor: pointer;
            background: linear-gradient(135deg, var(--accent), #12b981);
            color: white; font-weight: 600; font-size: 0.9rem;
            padding: 0.5rem 1.1rem; border-radius: 999px;
            display: inline-flex; align-items: center; gap: 0.4rem;
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.35);
        }}
        .btn-secondary {{
            border: none; outline: none; cursor: pointer;
            background: #e5e7eb; color: #374151;
            font-weight: 500; font-size: 0.8rem;
            padding: 0.4rem 0.85rem; border-radius: 999px;
            display: inline-flex; align-items: center; gap: 0.35rem;
        }}
        .btn-secondary[disabled] {{ opacity: 0.6; cursor: default; }}
        .result-header {{
            display: flex; align-items: center; justify-content: space-between;
            gap: 0.75rem; margin-bottom: 0.4rem;
        }}
        .result-title {{ margin: 0; font-size: 1rem; }}
        .result-subtitle {{ margin: 0; font-size: 0.8rem; color: var(--text-muted); }}
        .code-area textarea {{
            width: 100%; height: 360px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 12px; line-height: 1.4; white-space: pre;
            border-radius: 12px; border: 1px solid #e5e7eb;
            padding: 0.75rem 0.85rem; resize: vertical;
            background: #0b1120; color: #e5e7eb;
        }}
        .hint-list {{ margin: 0.75rem 0 0 0; padding-left: 1.1rem; font-size: 0.8rem; color: var(--text-muted); }}
        .hint-list li {{ margin-bottom: 0.2rem; }}
        .footer-note {{ margin-top: 0.75rem; font-size: 0.75rem; color: var(--text-muted); text-align: right; }}
    </style>
</head>
<body>
<div class="app-shell">
    <div class="app-header">
        <div class="badge"><span class="badge-dot"></span><span>Triade DOCX tools</span></div>
        <h1 class="app-title">Lesmateriaal generator</h1>
        <p class="app-subtitle">Kies een tool: HTML-code voor Stermonitor / ELO of een compleet werkboekje in Word.</p>
        <div class="tabs">
            <a href="/" class="tab {tab_html}"><span>💚</span><span>DOCX → HTML</span></a>
            <a href="/workbook" class="tab {tab_workbook}"><span>📘</span><span>Werkboekjes-maker</span></a>
        </div>
    </div>

    <div class="card">{card_content}</div>
</div>
{extra_js}
</body>
</html>
"""


def render_html_converter_page(error=None, html_out=None):
    error_block = f"<p class='error'>Fout: {escape(error)}</p>" if error else ""

    if html_out:
        result_block = f"<textarea id='html-output' readonly>{escape(html_out)}</textarea>"
        copy_disabled = ""
    else:
        result_block = "<textarea id='html-output' readonly placeholder=\"HTML verschijnt hier na het converteren.\"></textarea>"
        copy_disabled = "disabled"

    card_content = f"""
    <div class="two-cols">
        <div class="col-left">
            <h2 class="section-title">DOCX → HTML (Stermonitor / Elodigitaal)</h2>
            <p class="section-text">
                Upload een Word-bestand. De tekst en koppen worden omgezet naar eenvoudige HTML,
                afbeeldingen worden inline als base64 opgenomen.
            </p>
            {error_block}
            <form method="POST" enctype="multipart/form-data">
                <label class="file-label">
                    <span class="icon">📄</span>
                    <span>Kies een Word-bestand (.docx)</span>
                    <input type="file" name="file" accept=".docx" required>
                </label>
                <span class="file-name">Gebruik .docx uit Word of LibreOffice.</span>
                <div class="actions">
                    <button type="submit" class="btn-primary"><span>Converteer</span><span>⚡</span></button>
                </div>
            </form>
            <ul class="hint-list">
                <li>Gebruik “Kop 1, Kop 2” in Word voor nette koppen.</li>
                <li>Afbeeldingen komen inline, dus geen gedoe met hosting.</li>
            </ul>
        </div>
        <div class="col-right">
            <div class="result-header">
                <div>
                    <h2 class="result-title">HTML-resultaat</h2>
                    <p class="result-subtitle">Kopieer de code en plak in Stermonitor/ELO.</p>
                </div>
                <button class="btn-secondary" id="copy-btn" {copy_disabled}><span>📋</span><span>Kopieer</span></button>
            </div>
            <div class="code-area">{result_block}</div>
            <p class="footer-note">Tip: sla de HTML op als .html-bestand.</p>
        </div>
    </div>
    """

    extra_js = """
    <script>
    document.addEventListener('DOMContentLoaded', function () {
        const textarea = document.getElementById('html-output');
        const copyBtn = document.getElementById('copy-btn');
        if (!textarea || !copyBtn || copyBtn.hasAttribute('disabled')) return;
        copyBtn.addEventListener('click', function () {
            textarea.select();
            textarea.setSelectionRange(0, 999999);
            try {
                const ok = document.execCommand('copy');
                if (ok) {
                    const old = copyBtn.innerHTML;
                    copyBtn.innerHTML = "<span>✅</span><span>Gekopieerd</span>";
                    setTimeout(() => { copyBtn.innerHTML = old; }, 1500);
                }
            } catch (e) {}
        });
    });
    </script>
    """

    return BASE_PAGE.format(
        page_title="DOCX → HTML",
        tab_html="tab-active",
        tab_workbook="",
        card_content=card_content,
        extra_js=extra_js,
    )


@app.route("/", methods=["GET", "POST"])
def html_index():
    if request.method == "GET":
        return render_html_converter_page()

    if "file" not in request.files:
        return render_html_converter_page(
            error=f"Geen bestand geüpload. request.files = {list(request.files.keys())}"
        )

    file = request.files["file"]
    if file.filename == "":
        return render_html_converter_page(error="Geen geldig bestand gekozen.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        file.save(tmp.name)
        temp_path = tmp.name

    try:
        html_output = docx_to_html(temp_path)
        return render_html_converter_page(html_out=html_output)
    except Exception as e:
        return render_html_converter_page(error=f"Fout tijdens converteren: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def render_workbook_page(error=None):
    error_block = f"<p class='error'>Fout: {escape(error)}</p>" if error else ""

    card_content = f"""
    <div class="two-cols">
        <div class="col-left">
            <h2 class="section-title">Werkboekjes-maker (Word)</h2>
            <p class="section-text">
                Maak een Word-werkboekje met voorpagina, optioneel materiaalstaat en enkele stappen.
            </p>
            {error_block}
            <form method="POST" enctype="multipart/form-data">
                <div class="row">
                    <div>
                        <label class="small">Opdracht titel</label>
                        <input type="text" name="opdracht_titel" placeholder="Bijv. Recyclelamp ontwerpen">
                    </div>
                    <div>
                        <label class="small">Vak</label>
                        <input type="text" name="vak" value="BWI">
                    </div>
                </div>
                <div class="row" style="margin-top:0.45rem;">
                    <div>
                        <label class="small">Keuze/profieldeel</label>
                        <input type="text" name="profieldeel" placeholder="Bijv. Profieldeel BWI">
                    </div>
                    <div>
                        <label class="small">Docent</label>
                        <input type="text" name="docent" placeholder="Naam docent">
                    </div>
                </div>
                <div style="margin-top:0.45rem;">
                    <label class="small">Duur</label>
                    <input type="text" name="duur" value="11 x 45 minuten">
                </div>

                <div style="margin-top:0.7rem;">
                    <label class="small">Logo (optioneel, PNG/JPG)</label>
                    <label class="file-label">
                        <span class="icon">🏫</span><span>Upload logo</span>
                        <input type="file" name="logo" accept=".png,.jpg,.jpeg">
                    </label>
                    <span class="file-name">Tip: liever klein bestand (max ~200KB).</span>
                </div>

                <div style="margin-top:0.5rem;">
                    <label class="small">Omslagfoto (optioneel, PNG/JPG)</label>
                    <label class="file-label">
                        <span class="icon">🖼️</span><span>Upload omslagfoto</span>
                        <input type="file" name="cover" accept=".png,.jpg,.jpeg">
                    </label>
                </div>

                <div style="margin-top:0.9rem;">
                    <label class="small">
                        Materiaalstaat (optioneel) – één regel per materiaal, gescheiden door ;
                        <br>Formaat: Nummer;Aantal;Benaming;Lengte;Breedte;Dikte;Materiaal
                    </label>
                    <textarea name="materialen" rows="4"
                        placeholder="1;2;Plaat MDF;400;300;12;MDF&#10;2;4;Lat vuren;500;45;18;Vuren"></textarea>
                </div>

                <div style="margin-top:0.9rem;">
                    <label class="small">Stappen (max 3)</label>
                    <div style="margin-top:0.35rem;">
                        <label class="small">Stap 1 titel</label>
                        <input type="text" name="step1_title" placeholder="Bijv. Oriëntatie & eisen">
                        <label class="small" style="margin-top:0.25rem;">Stap 1 tekst</label>
                        <textarea name="step1_text" rows="3" placeholder="Korte tekst..."></textarea>
                    </div>
                    <div style="margin-top:0.45rem;">
                        <label class="small">Stap 2 titel</label>
                        <input type="text" name="step2_title" placeholder="Bijv. Ontwerp & schetsen">
                        <label class="small" style="margin-top:0.25rem;">Stap 2 tekst</label>
                        <textarea name="step2_text" rows="3" placeholder="Korte tekst..."></textarea>
                    </div>
                    <div style="margin-top:0.45rem;">
                        <label class="small">Stap 3 titel</label>
                        <input type="text" name="step3_title" placeholder="Bijv. Maken & reflectie">
                        <label class="small" style="margin-top:0.25rem;">Stap 3 tekst</label>
                        <textarea name="step3_text" rows="3" placeholder="Korte tekst..."></textarea>
                    </div>
                </div>

                <div class="actions">
                    <button type="submit" class="btn-primary"><span>Maak werkboekje</span><span>📘</span></button>
                </div>
            </form>

            <ul class="hint-list">
                <li>Als logo/cover niet goed is, wordt het automatisch overgeslagen (geen crash).</li>
                <li>Laat velden leeg als je ze niet nodig hebt.</li>
            </ul>
        </div>

        <div class="col-right">
            <h2 class="section-title">Wat krijg je?</h2>
            <p class="section-text">
                Een Word-document met voorpagina, optioneel materiaalstaat en pagina’s per stap.
            </p>
            <ul class="hint-list">
                <li>Voorpagina met opdracht, vak, docent en duur</li>
                <li>Materiaalstaat in tabelvorm (optioneel)</li>
                <li>1–3 stappenpagina’s met titel en tekst</li>
            </ul>
            <p class="footer-note">Tip: open het document in Word en pas aan waar nodig.</p>
        </div>
    </div>
    """

    return BASE_PAGE.format(
        page_title="Werkboekjes-maker",
        tab_html="",
        tab_workbook="tab-active",
        card_content=card_content,
        extra_js="",
    )


@app.route("/workbook", methods=["GET", "POST"])
def workbook_index():
    if request.method == "GET":
        return render_workbook_page()

    form = request.form

    meta = {
        "opdracht_titel": (form.get("opdracht_titel") or "").strip(),
        "vak": ((form.get("vak") or "").strip() or "BWI"),
        "profieldeel": (form.get("profieldeel") or "").strip(),
        "docent": (form.get("docent") or "").strip(),
        "duur": ((form.get("duur") or "").strip() or "11 x 45 minuten"),
        "include_materiaalstaat": False,
        "materialen": [],
        "logo": None,
        "cover_bytes": None,
    }

    # Materiaalstaat parsen (veilig)
    materialen_raw = (form.get("materialen") or "").strip()
    if materialen_raw:
        meta["include_materiaalstaat"] = True
        materialen = []
        cols = ["Nummer", "Aantal", "Benaming", "Lengte", "Breedte", "Dikte", "Materiaal"]
        for line in materialen_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(";")]
            item = {cols[i]: (parts[i] if i < len(parts) else "") for i in range(len(cols))}
            materialen.append(item)
        meta["materialen"] = materialen

    # Logo & cover (veilig)
    logo_file = request.files.get("logo")
    if logo_file and logo_file.filename:
        meta["logo"] = logo_file.read()

    cover_file = request.files.get("cover")
    if cover_file and cover_file.filename:
        meta["cover_bytes"] = cover_file.read()

    # Stappen
    steps = []
    for i in (1, 2, 3):
        title = (form.get(f"step{i}_title") or "").strip()
        text = (form.get(f"step{i}_text") or "").strip()
        if not title and not text:
            continue
        steps.append({
            "title": title or f"Pagina {i}",
            "text_blocks": [text] if text else [],
            "images": [],
        })

    if not steps:
        steps.append({
            "title": meta["opdracht_titel"] or "Opdracht",
            "text_blocks": [],
            "images": [],
        })

    # Bouw docx en lever als download
    try:
        docx_bytes = build_workbook_docx_front_and_steps(meta, steps)
    except Exception as e:
        return render_workbook_page(error=f"Fout tijdens bouwen van werkboekje: {e}")

    return send_file(
        docx_bytes,
        as_attachment=True,
        download_name="werkboekje.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=True)

