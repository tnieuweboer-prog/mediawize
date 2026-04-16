# Mediawize Workbook Module - Implementation Guide

## 📋 Overview

This guide explains how to integrate the improved workbook module into your existing Mediawize application. The enhancements include:

- ✅ Security hardening (input validation, file upload protection)
- ✅ Online workbook viewer with Bluetooth Speaker design colors
- ✅ Workbook storage and management
- ✅ Both DOCX download and online publishing options
- ✅ Comprehensive error handling and logging

---

## 🔧 Installation Steps

### Step 1: Backup Current Files

```bash
cd /path/to/mediawize
cp modules/workbook/routes.py modules/workbook/routes.py.backup
cp modules/workbook/builder.py modules/workbook/builder.py.backup
```

### Step 2: Replace Core Files

Replace the following files with improved versions:

1. **modules/workbook/routes.py** → Use `enhanced-routes.py`
2. **modules/workbook/builder.py** → Use `improved-builder.py`

### Step 3: Add New Viewer Module

Create new file: `modules/workbook/viewer.py`
- Copy content from `workbook-viewer.py`
- This handles storage, rendering, and design colors

### Step 4: Update Templates

Replace/update these template files:

1. **templates/workbook/index.html** → Use `workbook-index-template.html`
   - Adds "Online publiceren" and "Als DOCX downloaden" buttons
   - Improved form layout

2. **templates/workbook/list.html** (NEW) → Use `workbook-list-template.html`
   - Shows all user's workbooks
   - Delete functionality
   - View online links

3. Create **templates/workbook/not_found.html**:
```html
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h1>Werkboekje niet gevonden</h1>
  <p>Het werkboekje dat je zoekt bestaat niet of is verwijderd.</p>
  <a href="{{ url_for('workbook.workbook_get') }}" class="btn">Terug naar werkboekjes</a>
</div>
{% endblock %}
```

4. Create **templates/workbook/error.html**:
```html
{% extends "base.html" %}
{% block content %}
<div class="card">
  <h1>Fout</h1>
  <p>Er is een fout opgetreden. Probeer later opnieuw.</p>
  <a href="{{ url_for('workbook.workbook_get') }}" class="btn">Terug</a>
</div>
{% endblock %}
```

### Step 5: Create Data Directory

```bash
mkdir -p /opt/mediawize/data/workbooks
chmod 755 /opt/mediawize/data/workbooks
```

### Step 6: Update Requirements

Add to `requirements.txt`:
```
python-docx>=0.8.11
werkzeug>=2.0.0
```

Then install:
```bash
pip install -r requirements.txt
```

### Step 7: Update app.py (Optional)

If you want to add logging configuration:

```python
import logging

# Add to create_app() function:
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/mediawize/logs/workbook.log'),
        logging.StreamHandler()
    ]
)
```

---

## 🎨 Design Colors

The online workbook viewer uses the Bluetooth Speaker design colors:

```python
DESIGN_COLORS = {
    "primary": "#1a3a52",        # Navy Blue
    "accent": "#ff6b35",         # Warm Orange
    "background": "#ffffff",     # White
    "text": "#2c3e50",          # Dark Charcoal
    "border": "#e0e0e0",        # Light Gray
    "secondary": "#f5f5f5",     # Secondary Gray
}
```

These colors are automatically applied to all online workbooks.

---

## 🔐 Security Features

### Input Validation
- Step count limited to 50 (prevents DOS)
- Text fields limited to 5000 characters
- Titles limited to 500 characters
- Materials rows limited to 20

### File Upload Security
- Only PNG, JPG, JPEG allowed
- Maximum file size: 10MB
- Filename sanitization
- File type validation before processing

### Memory Management
- BytesIO objects properly closed
- No memory leaks from file uploads
- Efficient image handling

### Error Handling
- All exceptions logged with context
- Generic error messages to users
- No sensitive info in error responses

---

## 📊 Database Schema (JSON Storage)

Each workbook is stored as a JSON file:

```json
{
  "id": "abc123def456",
  "vak": "BWI",
  "opdracht_titel": "Bluetooth Speaker bouwen",
  "profieldeel": "Elektronica",
  "docent": "Jan Jansen",
  "duur": "10 x 45 minuten",
  "user_id": "teacher@school.nl",
  "include_materiaalstaat": true,
  "materialen": [...],
  "steps": [
    {
      "title": "Bekijk de onderdelen",
      "text_blocks": ["Controleer alle componenten..."],
      "images": []
    }
  ],
  "created_at": "2026-04-16T12:00:00",
  "updated_at": "2026-04-16T12:00:00"
}
```

### Future: Database Migration

To migrate from JSON to database, create a migration script:

```python
# scripts/migrate_workbooks_to_db.py
import json
import os
from models import Workbook  # Your database model

data_dir = "/opt/mediawize/data/workbooks"

for filename in os.listdir(data_dir):
    if filename.endswith(".json"):
        with open(os.path.join(data_dir, filename)) as f:
            data = json.load(f)
        
        workbook = Workbook(**data)
        db.session.add(workbook)

db.session.commit()
```

---

## 🚀 New Routes

### Existing Routes (Enhanced)
- `GET /workbook/` - Show creation form
- `POST /workbook/` - Generate workbook (DOCX or save online)

### New Routes
- `GET /workbook/view/<workbook_id>` - View workbook online
- `GET /workbook/list` - List user's workbooks
- `POST /workbook/delete/<workbook_id>` - Delete workbook

---

## 🧪 Testing

### Test Input Validation
```python
# Test with large step count
POST /workbook/ with stepCount=1000
# Should be capped at 50

# Test with malicious file
POST /workbook/ with cover=malicious.exe
# Should reject with error message
```

### Test Online Viewer
```bash
# Create a workbook and save online
# Visit: /workbook/view/<workbook_id>
# Should display with Navy + Orange colors
```

### Test Error Handling
```python
# Test with missing title
POST /workbook/ without titel field
# Should re-render form without error

# Test with large file
POST /workbook/ with 50MB image
# Should reject with size error
```

---

## 📝 Logging

Logs are written to:
- Console (development)
- File: `/opt/mediawize/logs/workbook.log` (production)

### Log Levels
- **ERROR**: Critical failures (file read errors, generation failures)
- **WARNING**: Suspicious activity (invalid file types, access denied)
- **INFO**: Normal operations (workbook saved, workbook viewed)

### Example Log Output
```
2026-04-16 12:00:00 - modules.workbook.routes - INFO - Workbook saved online: abc123def456
2026-04-16 12:00:01 - modules.workbook.routes - WARNING - Invalid file type: malicious.exe
2026-04-16 12:00:02 - modules.workbook.builder - ERROR - Error adding image: [error details]
```

---

## 🐛 Troubleshooting

### Issue: "Workbook not found" when viewing

**Cause**: Workbook JSON file doesn't exist or wrong ID

**Solution**:
1. Check `/opt/mediawize/data/workbooks/` directory
2. Verify workbook ID in URL
3. Check file permissions

### Issue: Images not displaying in online viewer

**Cause**: Images stored as bytes, not converted to base64

**Solution**: Update `workbook-viewer.py` to convert image bytes:
```python
import base64

for img_bytes in images:
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    html += f'<img src="data:image/jpeg;base64,{img_base64}">'
```

### Issue: "File too large" error

**Cause**: File exceeds 10MB limit

**Solution**: Increase `MAX_FILE_SIZE` in routes.py (not recommended)

### Issue: CSRF token error

**Cause**: Flask-WTF CSRF protection enabled

**Solution**: Add CSRF token to form template:
```html
<form method="POST">
    {{ csrf_token() }}
    <!-- form fields -->
</form>
```

---

## 📚 Code Review Findings

See `/home/ubuntu/code-review.md` for detailed analysis of:
- 10 bugs/security issues found
- Severity levels and fixes
- Recommendations for future improvements

---

## 🔄 Migration Path

### Phase 1: Current (Immediate)
- JSON-based storage
- File-based persistence
- Single server deployment

### Phase 2: Future
- Database storage (PostgreSQL/MySQL)
- Multi-server support
- Caching layer (Redis)
- CDN for images

### Phase 3: Advanced
- Collaborative editing
- Version history
- Template library
- Analytics

---

## 📞 Support

For issues or questions:
1. Check logs: `/opt/mediawize/logs/workbook.log`
2. Review code comments in improved files
3. Test with provided test cases
4. Check troubleshooting section above

---

## ✅ Checklist Before Going Live

- [ ] Backup current files
- [ ] Replace all 3 core files (routes, builder, viewer)
- [ ] Create new templates
- [ ] Create data directory with correct permissions
- [ ] Install/update dependencies
- [ ] Test input validation
- [ ] Test file uploads
- [ ] Test online viewer
- [ ] Test error handling
- [ ] Review logs for errors
- [ ] Test on mobile devices
- [ ] Load test with multiple users

---

## 📄 Files Provided

1. **code-review.md** - Detailed code analysis
2. **improved-routes.py** - Enhanced routes with validation
3. **improved-builder.py** - Improved DOCX builder
4. **workbook-viewer.py** - Online viewer module
5. **enhanced-routes.py** - Routes with viewer integration
6. **workbook-index-template.html** - Updated form template
7. **workbook-list-template.html** - New list template
8. **IMPLEMENTATION-GUIDE.md** - This file

---

## 🎯 Next Steps

1. Review code-review.md
2. Follow installation steps above
3. Test thoroughly
4. Deploy to staging
5. Monitor logs
6. Gather user feedback
7. Plan Phase 2 improvements

Good luck! 🚀
