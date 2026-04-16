# modules/workbook/routes.py (ENHANCED VERSION WITH VIEWER)
"""
Enhanced workbook routes with both DOCX generation and online viewing.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any
import uuid

from flask import Blueprint, render_template, request, send_file, session, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

from .builder import build_workbook_docx_front_and_steps
from .viewer import WorkbookStorage, WorkbookRenderer, generate_workbook_id

logger = logging.getLogger(__name__)

bp = Blueprint("workbook", __name__, url_prefix="/workbook")

# Initialize storage
storage = WorkbookStorage()

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_STEP_COUNT = 50
MAX_TEXT_LENGTH = 5000
MAX_TITLE_LENGTH = 500
MAX_MATERIALEN_ROWS = 20

# ============================================================
# SECURITY & VALIDATION HELPERS
# ============================================================

def safe_int(value: str | None, default: int = 0, min_val: int = 0, max_val: int | None = None) -> int:
    """Safely convert string to int with bounds checking."""
    try:
        result = int((value or "").strip() or default)
        if result < min_val:
            result = min_val
        if max_val is not None and result > max_val:
            result = max_val
        return result
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert '{value}' to int, using default {default}")
        return default


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_file_size(file_obj) -> bool:
    """Validate file size without loading entire file into memory."""
    try:
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)
        return file_size <= MAX_FILE_SIZE
    except Exception as e:
        logger.error(f"Error validating file size: {e}")
        return False


def sanitize_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Sanitize and truncate text input."""
    if not text:
        return ""
    
    text = text.strip()
    
    if len(text) > max_length:
        logger.warning(f"Text truncated from {len(text)} to {max_length} chars")
        text = text[:max_length]
    
    return text


# ============================================================
# GUARDS
# ============================================================

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapper


def role_required(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                logger.warning(f"Access denied for role {session.get('role')}, required {role}")
                return redirect(url_for("auth.login"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _values_from_form() -> dict[str, Any]:
    """Extract and validate form values."""
    values = dict(request.form)
    values["include_materiaalstaat"] = bool(request.form.get("include_materiaalstaat"))
    return values


def _get_user_id() -> str:
    """Get user ID from session."""
    user = session.get("user")
    if isinstance(user, dict):
        return user.get("email", "unknown")
    return user or "unknown"


# ============================================================
# ROUTES
# ============================================================

@bp.get("/")
@login_required
@role_required("docent")
def workbook_get():
    """Display workbook creation form."""
    return render_template(
        "workbook/index.html",
        step_count=1,
        values={},
        error=None,
        active_tab="workbook",
        page_title="Werkboekjes",
    )


@bp.post("/")
@login_required
@role_required("docent")
def workbook_post():
    """Generate workbook with option to save online or download DOCX."""
    try:
        # Validate step count
        step_count = safe_int(
            request.form.get("stepCount", "1"),
            default=1,
            min_val=1,
            max_val=MAX_STEP_COUNT
        )
        
        values = _values_from_form()
        
        # Check if title is provided
        titel = sanitize_text(request.form.get("titel", ""), MAX_TITLE_LENGTH)
        if not titel:
            logger.info("Form submission without title, re-rendering form")
            return render_template(
                "workbook/index.html",
                step_count=step_count,
                values=values,
                error=None,
                active_tab="workbook",
                page_title="Werkboekjes",
            )
        
        # Build metadata
        meta = {
            "vak": request.form.get("vak", "BWI"),
            "opdracht_titel": titel,
            "profieldeel": sanitize_text(request.form.get("profieldeel", "")),
            "docent": sanitize_text(request.form.get("docent", "")),
            "duur": sanitize_text(request.form.get("duur", "")),
            "include_materiaalstaat": bool(request.form.get("include_materiaalstaat")),
            "materialen": [],
            "user_id": _get_user_id(),
        }
        
        # Validate and process cover image
        cover_file = request.files.get("cover")
        if cover_file and cover_file.filename:
            if not allowed_file(cover_file.filename):
                error_msg = "Ongeldig bestandstype. Alleen PNG, JPG toegestaan."
                logger.warning(f"Invalid file type: {cover_file.filename}")
                return render_template(
                    "workbook/index.html",
                    step_count=step_count,
                    values=values,
                    error=error_msg,
                    active_tab="workbook",
                    page_title="Werkboekjes",
                )
            
            if not validate_file_size(cover_file):
                error_msg = f"Bestand te groot. Maximum {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
                logger.warning(f"File too large: {cover_file.filename}")
                return render_template(
                    "workbook/index.html",
                    step_count=step_count,
                    values=values,
                    error=error_msg,
                    active_tab="workbook",
                    page_title="Werkboekjes",
                )
            
            try:
                meta["cover_bytes"] = cover_file.read()
            except Exception as e:
                logger.error(f"Error reading cover file: {e}")
                error_msg = "Fout bij lezen cover-afbeelding"
                return render_template(
                    "workbook/index.html",
                    step_count=step_count,
                    values=values,
                    error=error_msg,
                    active_tab="workbook",
                    page_title="Werkboekjes",
                )
        
        # Process materiaalstaat
        mat_rows = safe_int(
            request.form.get("mat_rows", "0"),
            default=0,
            min_val=0,
            max_val=MAX_MATERIALEN_ROWS
        )
        
        if meta["include_materiaalstaat"] and mat_rows > 0:
            for _ in range(mat_rows):
                meta["materialen"].append({
                    "Nummer": "",
                    "Aantal": "",
                    "Benaming": "",
                    "Lengte": "",
                    "Breedte": "",
                    "Dikte": "",
                    "Materiaal": "",
                })
        
        # Process steps
        steps = []
        for i in range(step_count):
            title = sanitize_text(request.form.get(f"step_title_{i}", ""), MAX_TITLE_LENGTH)
            text = sanitize_text(request.form.get(f"step_text_{i}", ""), MAX_TEXT_LENGTH)
            
            step = {
                "title": title,
                "text_blocks": [text] if text else [],
                "images": [],
            }
            
            # Validate and process step image
            img_file = request.files.get(f"step_img_{i}")
            if img_file and img_file.filename:
                if not allowed_file(img_file.filename):
                    logger.warning(f"Invalid image type in step {i}: {img_file.filename}")
                    continue
                
                if not validate_file_size(img_file):
                    logger.warning(f"Image too large in step {i}: {img_file.filename}")
                    continue
                
                try:
                    step["images"].append(img_file.read())
                except Exception as e:
                    logger.error(f"Error reading image in step {i}: {e}")
                    continue
            
            # Add step if it has content
            if step["title"] or step["text_blocks"] or step["images"]:
                steps.append(step)
        
        # Determine action
        action = request.form.get("action", "download")
        
        if action == "save_online":
            # Save to storage and redirect to viewer
            workbook_id = generate_workbook_id(_get_user_id(), titel)
            workbook_data = {
                **meta,
                "steps": steps,
            }
            
            if storage.save_workbook(workbook_id, workbook_data):
                logger.info(f"Workbook saved online: {workbook_id}")
                return redirect(url_for("workbook.view_workbook", workbook_id=workbook_id))
            else:
                error_msg = "Fout bij opslaan werkboekje"
                return render_template(
                    "workbook/index.html",
                    step_count=step_count,
                    values=values,
                    error=error_msg,
                    active_tab="workbook",
                    page_title="Werkboekjes",
                )
        else:
            # Download as DOCX
            output = build_workbook_docx_front_and_steps(meta, steps)
            vak = (meta.get("vak") or "BWI").upper()
            
            logger.info(f"Workbook downloaded: {vak} with {len(steps)} steps")
            
            return send_file(
                output,
                as_attachment=True,
                download_name=f"werkboekje_{vak}.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
    
    except Exception as e:
        logger.error(f"Workbook generation failed: {e}", exc_info=True)
        return render_template(
            "workbook/index.html",
            step_count=1,
            values={},
            error="Fout bij genereren werkboekje. Probeer later opnieuw.",
            active_tab="workbook",
            page_title="Werkboekjes",
        )


@bp.get("/view/<workbook_id>")
def view_workbook(workbook_id: str):
    """Display workbook online."""
    try:
        # Load workbook from storage
        workbook_data = storage.load_workbook(workbook_id)
        
        if not workbook_data:
            logger.warning(f"Workbook not found: {workbook_id}")
            return render_template("workbook/not_found.html"), 404
        
        # Render to HTML
        html_content = WorkbookRenderer.render_workbook_html(workbook_data)
        
        # Return as HTML response
        from flask import Response
        return Response(html_content, mimetype="text/html")
    
    except Exception as e:
        logger.error(f"Error viewing workbook {workbook_id}: {e}")
        return render_template("workbook/error.html"), 500


@bp.get("/list")
@login_required
@role_required("docent")
def list_workbooks():
    """List user's workbooks."""
    try:
        user_id = _get_user_id()
        workbooks = storage.list_workbooks(user_id=user_id)
        
        return render_template(
            "workbook/list.html",
            workbooks=workbooks,
            active_tab="workbook",
            page_title="Mijn Werkboekjes",
        )
    except Exception as e:
        logger.error(f"Error listing workbooks: {e}")
        return render_template("workbook/error.html"), 500


@bp.post("/delete/<workbook_id>")
@login_required
@role_required("docent")
def delete_workbook(workbook_id: str):
    """Delete a workbook."""
    try:
        # Verify ownership
        workbook_data = storage.load_workbook(workbook_id)
        if not workbook_data or workbook_data.get("user_id") != _get_user_id():
            logger.warning(f"Unauthorized delete attempt: {workbook_id}")
            return jsonify({"error": "Unauthorized"}), 403
        
        if storage.delete_workbook(workbook_id):
            logger.info(f"Workbook deleted: {workbook_id}")
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to delete"}), 500
    
    except Exception as e:
        logger.error(f"Error deleting workbook {workbook_id}: {e}")
        return jsonify({"error": str(e)}), 500
