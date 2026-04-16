# Mediawize Workbook Module - Code Review & Bug Analysis

## 🔍 CRITICAL ISSUES FOUND

### 1. **Security: Missing Input Validation** ⚠️ HIGH PRIORITY
**File:** `modules/workbook/routes.py` (lines 66, 115-116)

**Issue:** Form inputs are not validated before processing
```python
step_count = int(request.form.get("stepCount", "1") or "1")  # Could fail silently
title = request.form.get(f"step_title_{i}", "")  # No length check
text = request.form.get(f"step_text_{i}", "")    # No sanitization
```

**Risk:** 
- Malicious users could inject very large step counts → Memory exhaustion
- No XSS protection on text fields
- No file size limits on uploads

**Fix Needed:**
```python
# Add validation
MAX_STEP_COUNT = 50
MAX_TEXT_LENGTH = 5000
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

step_count = min(int(request.form.get("stepCount", "1") or "1"), MAX_STEP_COUNT)
if step_count < 1:
    step_count = 1
```

---

### 2. **File Upload Security** ⚠️ HIGH PRIORITY
**File:** `modules/workbook/routes.py` (lines 94-96, 117-126)

**Issue:** No file type validation, no size limits
```python
cover_file = request.files.get("cover")
if cover_file and cover_file.filename:
    meta["cover_bytes"] = cover_file.read()  # No validation!
```

**Risk:**
- User could upload malicious files (not just images)
- Large files could crash the server
- No filename sanitization

**Fix Needed:**
```python
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

cover_file = request.files.get("cover")
if cover_file and cover_file.filename:
    if not allowed_file(cover_file.filename):
        raise ValueError("Invalid file type. Only PNG, JPG allowed.")
    
    cover_file.seek(0, 2)  # Seek to end
    file_size = cover_file.tell()
    cover_file.seek(0)  # Seek back to start
    
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large. Max {MAX_FILE_SIZE / 1024 / 1024}MB")
    
    meta["cover_bytes"] = cover_file.read()
```

---

### 3. **Missing Error Handling for Integer Conversion** ⚠️ MEDIUM PRIORITY
**File:** `modules/workbook/routes.py` (line 66, 99)

**Issue:** `int()` conversion could fail
```python
step_count = int(request.form.get("stepCount", "1") or "1")  # Could raise ValueError
mat_rows = int((request.form.get("mat_rows", "0") or "0").strip() or "0")  # Complex logic
```

**Fix Needed:**
```python
def safe_int(value, default=0, min_val=0, max_val=None):
    try:
        result = int((value or "").strip() or default)
        if result < min_val:
            result = min_val
        if max_val is not None and result > max_val:
            result = max_val
        return result
    except (ValueError, TypeError):
        return default

step_count = safe_int(request.form.get("stepCount"), default=1, min_val=1, max_val=50)
mat_rows = safe_int(request.form.get("mat_rows"), default=0, min_val=0, max_val=20)
```

---

### 4. **Memory Leak: BytesIO Not Closed** ⚠️ MEDIUM PRIORITY
**File:** `modules/workbook/builder.py` (lines 51-53, 125-128)

**Issue:** BytesIO objects created but not explicitly closed
```python
bio = io.BytesIO(img_bytes)
bio.seek(0)
doc.add_picture(bio, width=Inches(2.0))
# bio is never closed!
```

**Risk:** Memory accumulation in long-running server

**Fix Needed:**
```python
def _try_add_image(doc: Document, img_bytes: bytes, width_inches: float) -> None:
    bio = io.BytesIO(img_bytes)
    try:
        bio.seek(0)
        doc.add_picture(bio, width=Inches(width_inches))
    finally:
        bio.close()

# And in _add_step:
if images:
    # ...
    for i, img_bytes in enumerate(images):
        if i % cols == 0:
            row = table.add_row().cells
        
        cell = row[i % cols]
        try:
            bio = io.BytesIO(img_bytes)
            bio.seek(0)
            cell.paragraphs[0].add_run().add_picture(bio, width=Inches(2.0))
        except Exception:
            cell.text = "(afbeelding kon niet worden ingeladen)"
        finally:
            bio.close()
```

---

### 5. **Missing CSRF Protection** ⚠️ MEDIUM PRIORITY
**File:** `modules/workbook/routes.py` (lines 45, 62)

**Issue:** POST endpoint has no CSRF token validation
```python
@bp.post("/")
@login_required
@role_required("docent")
def workbook_post():
    # No CSRF check!
```

**Fix Needed:**
```python
from flask_wtf.csrf import csrf_protect

@bp.post("/")
@login_required
@role_required("docent")
@csrf_protect  # Add this
def workbook_post():
    # ...
```

And in template:
```html
<form id="wbForm" method="POST" enctype="multipart/form-data">
    {{ csrf_token() }}  <!-- Add this -->
    <!-- rest of form -->
</form>
```

---

### 6. **No Logging for Errors** ⚠️ MEDIUM PRIORITY
**File:** `modules/workbook/routes.py` (lines 142-150)

**Issue:** Errors are caught but not logged
```python
except Exception as e:
    return render_template(
        "workbook/index.html",
        step_count=step_count,
        values=values,
        error=f"Fout bij genereren: {e}",  # Shows to user, not logged
        active_tab="workbook",
        page_title="Werkboekjes",
    )
```

**Fix Needed:**
```python
import logging

logger = logging.getLogger(__name__)

except Exception as e:
    logger.error(f"Workbook generation failed for user {session.get('user')}: {e}", exc_info=True)
    return render_template(
        "workbook/index.html",
        step_count=step_count,
        values=values,
        error="Fout bij genereren. Probeer later opnieuw.",  # Generic message
        active_tab="workbook",
        page_title="Werkboekjes",
    )
```

---

### 7. **Type Hints Missing** ⚠️ LOW PRIORITY
**File:** `modules/workbook/routes.py` (line 36)

**Issue:** Function parameters lack type hints
```python
def _values_from_form():  # Should have return type
    values = dict(request.form)
    # ...
    return values
```

**Fix Needed:**
```python
def _values_from_form() -> dict[str, Any]:
    values = dict(request.form)
    values["include_materiaalstaat"] = bool(request.form.get("include_materiaalstaat"))
    return values
```

---

### 8. **Hardcoded Strings** ⚠️ LOW PRIORITY
**File:** `modules/workbook/builder.py` (line 101)

**Issue:** Magic strings scattered throughout
```python
run = heading.add_run(f"Stap {idx}: {title}" if title else f"Stap {idx}")
```

**Fix Needed:**
```python
STEP_LABEL = "Stap"  # At module level
run = heading.add_run(f"{STEP_LABEL} {idx}: {title}" if title else f"{STEP_LABEL} {idx}")
```

---

### 9. **No Validation for Empty Steps** ⚠️ LOW PRIORITY
**File:** `modules/workbook/routes.py` (lines 114-130)

**Issue:** Empty steps are filtered but silently
```python
if step["title"] or step["text_blocks"] or step["images"]:
    steps.append(step)
```

**Better:** Warn user if steps are empty

---

### 10. **Inconsistent Error Messages** ⚠️ LOW PRIORITY
**File:** `modules/workbook/builder.py` (line 130)

**Issue:** Hardcoded Dutch error message
```python
cell.text = "(afbeelding kon niet worden ingeladen)"
```

**Better:** Use i18n or constants

---

## 📊 Summary

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 HIGH | 2 | Input validation, File upload security |
| 🟠 MEDIUM | 4 | Error handling, Memory leaks, CSRF, Logging |
| 🟡 LOW | 4 | Type hints, Hardcoded strings, Empty validation |

---

## ✅ Recommendations

1. **Immediate:** Add input validation and file upload security
2. **Soon:** Implement proper error logging and CSRF protection
3. **Nice-to-have:** Add type hints and refactor magic strings
4. **Future:** Add unit tests for all validation functions

---

## 📝 Next Steps

I will now:
1. Create improved versions of these files with fixes
2. Add a workbook storage system (JSON/Database)
3. Build the online viewer with Bluetooth Speaker design colors
4. Integrate everything together
