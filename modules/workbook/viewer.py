# modules/workbook/viewer.py (NEW FILE)
"""
Online workbook viewer with Bluetooth Speaker design colors.
Displays workbooks with interactive step navigation.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# DESIGN COLORS (Bluetooth Speaker Theme)
# ============================================================

DESIGN_COLORS = {
    "primary": "#1a3a52",        # Navy Blue
    "accent": "#ff6b35",         # Warm Orange
    "background": "#ffffff",     # White
    "text": "#2c3e50",          # Dark Charcoal
    "border": "#e0e0e0",        # Light Gray
    "secondary": "#f5f5f5",     # Secondary Gray
}


# ============================================================
# WORKBOOK STORAGE
# ============================================================

class WorkbookStorage:
    """Handle workbook persistence (JSON-based for now)."""
    
    def __init__(self, data_dir: str = "/opt/mediawize/data/workbooks"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def save_workbook(self, workbook_id: str, data: dict[str, Any]) -> bool:
        """
        Save workbook data to JSON file.
        
        Args:
            workbook_id: Unique workbook identifier
            data: Workbook data dictionary
            
        Returns:
            True if successful
        """
        try:
            filepath = os.path.join(self.data_dir, f"{workbook_id}.json")
            
            # Add metadata
            data["id"] = workbook_id
            data["created_at"] = datetime.utcnow().isoformat()
            data["updated_at"] = datetime.utcnow().isoformat()
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Workbook saved: {workbook_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving workbook {workbook_id}: {e}")
            return False
    
    def load_workbook(self, workbook_id: str) -> dict[str, Any] | None:
        """
        Load workbook data from JSON file.
        
        Args:
            workbook_id: Unique workbook identifier
            
        Returns:
            Workbook data dictionary or None if not found
        """
        try:
            filepath = os.path.join(self.data_dir, f"{workbook_id}.json")
            
            if not os.path.exists(filepath):
                logger.warning(f"Workbook not found: {workbook_id}")
                return None
            
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            logger.error(f"Error loading workbook {workbook_id}: {e}")
            return None
    
    def delete_workbook(self, workbook_id: str) -> bool:
        """Delete workbook file."""
        try:
            filepath = os.path.join(self.data_dir, f"{workbook_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Workbook deleted: {workbook_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting workbook {workbook_id}: {e}")
            return False
    
    def list_workbooks(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """
        List all workbooks, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of workbook metadata
        """
        try:
            workbooks = []
            for filename in os.listdir(self.data_dir):
                if filename.endswith(".json"):
                    workbook_id = filename[:-5]
                    data = self.load_workbook(workbook_id)
                    if data:
                        if user_id is None or data.get("user_id") == user_id:
                            workbooks.append({
                                "id": workbook_id,
                                "title": data.get("opdracht_titel", "Untitled"),
                                "vak": data.get("vak", ""),
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                            })
            return sorted(workbooks, key=lambda x: x.get("created_at", ""), reverse=True)
        except Exception as e:
            logger.error(f"Error listing workbooks: {e}")
            return []


# ============================================================
# WORKBOOK RENDERER
# ============================================================

class WorkbookRenderer:
    """Render workbook data to HTML."""
    
    @staticmethod
    def render_step_html(step_number: int, step: dict[str, Any]) -> str:
        """
        Render a single step as HTML.
        
        Args:
            step_number: Step number (1-based)
            step: Step data dictionary
            
        Returns:
            HTML string
        """
        title = step.get("title", "")
        text_blocks = step.get("text_blocks", [])
        images = step.get("images", [])
        
        html = f"""
        <div class="step-card">
            <div class="step-header">
                <div class="step-number">{step_number}</div>
                <h3 class="step-title">{title or f'Stap {step_number}'}</h3>
            </div>
            
            <div class="step-content">
        """
        
        # Add text blocks
        for block in text_blocks:
            if block:
                html += f'<p class="step-text">{block}</p>'
        
        # Add images
        if images:
            html += '<div class="step-images">'
            for i, img_data in enumerate(images):
                # In real implementation, convert img_bytes to base64 or URL
                html += f'<div class="step-image"><img src="data:image/jpeg;base64,{img_data}" alt="Step {step_number} image {i+1}"></div>'
            html += '</div>'
        
        html += """
            </div>
        </div>
        """
        return html
    
    @staticmethod
    def render_workbook_html(workbook: dict[str, Any]) -> str:
        """
        Render complete workbook as HTML.
        
        Args:
            workbook: Workbook data dictionary
            
        Returns:
            Complete HTML page
        """
        title = workbook.get("opdracht_titel", "Werkboekje")
        vak = workbook.get("vak", "")
        docent = workbook.get("docent", "")
        duur = workbook.get("duur", "")
        steps = workbook.get("steps", [])
        
        steps_html = ""
        for i, step in enumerate(steps, start=1):
            steps_html += WorkbookRenderer.render_step_html(i, step)
        
        html = f"""
        <!DOCTYPE html>
        <html lang="nl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                :root {{
                    --primary: {DESIGN_COLORS['primary']};
                    --accent: {DESIGN_COLORS['accent']};
                    --background: {DESIGN_COLORS['background']};
                    --text: {DESIGN_COLORS['text']};
                    --border: {DESIGN_COLORS['border']};
                    --secondary: {DESIGN_COLORS['secondary']};
                }}
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: var(--background);
                    color: var(--text);
                    line-height: 1.6;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 1rem;
                }}
                
                /* Header */
                header {{
                    background: var(--primary);
                    color: white;
                    padding: 2rem 0;
                    border-bottom: 4px solid var(--accent);
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                
                header h1 {{
                    font-size: 2rem;
                    margin-bottom: 0.5rem;
                }}
                
                header p {{
                    opacity: 0.9;
                    font-size: 0.95rem;
                }}
                
                .header-meta {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 1rem;
                    margin-top: 1rem;
                    padding-top: 1rem;
                    border-top: 1px solid rgba(255,255,255,0.2);
                }}
                
                .meta-item {{
                    font-size: 0.85rem;
                }}
                
                .meta-label {{
                    opacity: 0.8;
                    display: block;
                    font-weight: 600;
                }}
                
                .meta-value {{
                    display: block;
                    margin-top: 0.25rem;
                }}
                
                /* Main content */
                main {{
                    padding: 2rem 0;
                }}
                
                /* Steps */
                .steps-container {{
                    display: flex;
                    flex-direction: column;
                    gap: 2rem;
                }}
                
                .step-card {{
                    background: var(--background);
                    border: 1px solid var(--border);
                    border-left: 4px solid var(--accent);
                    border-radius: 0.5rem;
                    padding: 2rem;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    transition: box-shadow 0.2s ease;
                }}
                
                .step-card:hover {{
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}
                
                .step-header {{
                    display: flex;
                    align-items: center;
                    gap: 1.5rem;
                    margin-bottom: 1.5rem;
                }}
                
                .step-number {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 3rem;
                    height: 3rem;
                    border-radius: 50%;
                    background: var(--primary);
                    color: white;
                    font-weight: bold;
                    font-size: 1.25rem;
                    flex-shrink: 0;
                }}
                
                .step-title {{
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: var(--primary);
                }}
                
                .step-content {{
                    margin-left: 4.5rem;
                }}
                
                .step-text {{
                    margin-bottom: 1rem;
                    color: var(--text);
                }}
                
                .step-images {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 1rem;
                    margin-top: 1.5rem;
                }}
                
                .step-image {{
                    background: var(--secondary);
                    border-radius: 0.5rem;
                    overflow: hidden;
                    border: 1px solid var(--border);
                }}
                
                .step-image img {{
                    width: 100%;
                    height: auto;
                    display: block;
                }}
                
                /* Footer */
                footer {{
                    background: var(--primary);
                    color: white;
                    padding: 2rem 0;
                    margin-top: 4rem;
                    text-align: center;
                    font-size: 0.9rem;
                    opacity: 0.9;
                }}
                
                /* Responsive */
                @media (max-width: 768px) {{
                    header h1 {{
                        font-size: 1.5rem;
                    }}
                    
                    .header-meta {{
                        grid-template-columns: repeat(2, 1fr);
                    }}
                    
                    .step-header {{
                        flex-direction: column;
                        align-items: flex-start;
                    }}
                    
                    .step-content {{
                        margin-left: 0;
                    }}
                    
                    .step-images {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <header>
                <div class="container">
                    <h1>{title}</h1>
                    <p>Interactief werkboekje</p>
                    <div class="header-meta">
                        {f'<div class="meta-item"><span class="meta-label">Vak</span><span class="meta-value">{vak}</span></div>' if vak else ''}
                        {f'<div class="meta-item"><span class="meta-label">Docent</span><span class="meta-value">{docent}</span></div>' if docent else ''}
                        {f'<div class="meta-item"><span class="meta-label">Duur</span><span class="meta-value">{duur}</span></div>' if duur else ''}
                    </div>
                </div>
            </header>
            
            <main>
                <div class="container">
                    <div class="steps-container">
                        {steps_html}
                    </div>
                </div>
            </main>
            
            <footer>
                <div class="container">
                    <p>Werkboekje gegenereerd op {datetime.utcnow().strftime('%d-%m-%Y %H:%M')}</p>
                </div>
            </footer>
        </body>
        </html>
        """
        return html


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def generate_workbook_id(user_id: str, title: str) -> str:
    """
    Generate unique workbook ID.
    
    Args:
        user_id: User identifier
        title: Workbook title
        
    Returns:
        Unique workbook ID
    """
    import hashlib
    import time
    
    # Create hash from user_id, title, and timestamp
    content = f"{user_id}:{title}:{time.time()}"
    hash_obj = hashlib.md5(content.encode())
    return hash_obj.hexdigest()[:12]
