# Cloud File Exchange – Agent Guide

## Architecture Overview
Single Flask app (`app.py`) with SQLAlchemy models (`models.py`), pluggable storage (`storage.py`), and Jinja2 templates. Side effects occur on module load: SQLite created, admin user seeded, storage backend validated.

**Key relationships:** `User` → `File` → cascade delete; `User` → `LogBook` → cascade delete; `File` → `FilePermission` → cascade delete. Removing a user cleans up all their files, logs, and permissions automatically.

## Dev Workflow
```bash
pip install -r requirements.txt   # Flask, Flask-Login, Flask-SQLAlchemy, boto3, Pillow
cp .env.example .env              # Configure storage backend
python app.py                     # Dev server at 127.0.0.1:5000
```
Default admin: `admin` / `admin`. Database: `file_exchange.db` (delete to reset).

## Storage Abstraction (Critical Pattern)
Routes use `storage_backend` instance—never direct filesystem calls. Both backends implement:
- `save(file_storage, filename, user_id)` → `StorageResult(key=...)`
- `delete(key)` → removes from storage
- `download(file_record)` → Flask response (redirect for S3 presigned URL, `send_from_directory` for local)
- `get_file_content(file_record)` → raw bytes for ZIP packaging

```python
# S3: files stored as user-{id}/{timestamp}_{filename}
# Local: files stored as uploads/{timestamp}_{filename}
storage_result = storage_backend.save(file, filename, current_user.id)
new_file = File(file_path=storage_result.key, ...)  # Store the key, not physical path
```

Set `STORAGE_BACKEND=local` in `.env` for disk storage; `s3` (default) requires `S3_BUCKET_NAME` and AWS credentials with `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`.

## File Versioning
Version auto-increments per user+filename. Query pattern for new uploads:
```python
existing = File.query.filter_by(user_id=current_user.id, original_filename=name).order_by(File.version.desc()).first()
version = existing.version + 1 if existing else 1
```

## Authorization (Read/Write/Delete Rights)
Use `can_access_file(file, permission_type)` helper for permission checks:
```python
if not can_access_file(file, 'read'):   # 'read', 'write', or 'delete'
    flash('Unauthorized access', 'danger')
    return redirect(url_for('dashboard'))
```
- Owner has full access to their files
- Admin role (`User.role == 'admin'`) has full access to all files
- `FilePermission` model grants granular `can_read`, `can_write`, `can_delete` to other users

## Activity Logging
Call `log_action(action, details)` for state-changing operations. It captures `current_user.id`, `request.remote_addr`, and timestamp:
```python
log_action('upload', f'Uploaded {original_filename} (v{version}, {file_size} bytes)')
```

## Routes & Auth
All protected routes use `@login_required`. Key endpoints:
| Route | Method | Purpose |
|-------|--------|---------|
| `/upload` | POST | File upload (multipart form) |
| `/download/<file_id>` | GET | Download file (ownership/permission check) |
| `/download-zip` | POST | Bulk download as ZIP (form with `file_ids[]`) |
| `/delete/<file_id>` | POST | Delete file (ownership/permission check) |
| `/share/<file_id>` | GET/POST | Share file with permissions |
| `/shared-with-me` | GET | View files shared with current user |
| `/logs` | GET | View user activity history |

## Templates
Extend `templates/base.html` (Bootstrap 5 CDN). Use flash categories: `success`, `danger`, `info`.
```html
{% extends "base.html" %}
{% block title %}Page Title{% endblock %}
{% block content %}...{% endblock %}
```

## Extension Checklist
- [ ] New file extensions: add to `Config.ALLOWED_EXTENSIONS` in `config.py`
- [ ] New routes: use `@login_required`, call `log_action()` for mutations, use `can_access_file()` for shared resources
- [ ] New models: add cascade relationship if user-owned, run `db.create_all()` (no migrations)
- [ ] Background scripts: wrap in `with app.app_context():` for DB access
- [ ] File handling: use `secure_filename()` + storage abstraction, never raw `os.path`
