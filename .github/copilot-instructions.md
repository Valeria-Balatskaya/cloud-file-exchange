# Cloud File Exchange – Agent Guide

## Project Structure
```
cloud-file-exchange/
├── app.py                  # Flask app (routes, views, 600+ lines)
├── config.py               # Configuration (DB, S3, extensions)
├── models.py               # SQLAlchemy models
├── storage.py              # Storage abstraction (S3/Local)
├── requirements.txt        # Dependencies
├── .env                    # Environment variables (not in git)
├── .env.example            # Template for .env
├── templates/
│   ├── base.html           # Bootstrap 5 base + dark mode
│   ├── dashboard.html      # Main file dashboard
│   ├── login.html, register.html, logs.html
│   ├── profile.html        # User profile & password change
│   ├── share.html, shared.html  # File sharing UI
│   └── admin/              # Admin dashboard, users, files, logs
└── uploads/                # Local storage (when STORAGE_BACKEND=local)
```

## Architecture Overview
Single Flask app (`app.py`) with SQLAlchemy models (`models.py`), pluggable storage (`storage.py`), and Jinja2 templates. **Cloud-native stack:** Supabase PostgreSQL (database) + AWS S3 (file storage).

**Key relationships (cascade delete):**
- `User` → `File` → `FilePermission`
- `User` → `LogBook`

Removing a user cleans up all their files, logs, and permissions automatically.

## Dev Workflow
```powershell
pip install -r requirements.txt   # Flask, SQLAlchemy, boto3, Pillow, psycopg2
cp .env.example .env              # Configure database & storage
python app.py                     # Dev server at 127.0.0.1:5000
```
Default admin: `admin` / `admin`. Database configured via `DATABASE_URL` env var.

## Configuration (`config.py`)

**Database:** Supabase PostgreSQL
- `DATABASE_URL` → PostgreSQL connection string (use pooler URL for IPv4 compatibility)
- Format: `postgresql://user:pass@aws-1-region.pooler.supabase.com:6543/postgres`

**Storage:** AWS S3
- `S3_BUCKET_NAME` → Your S3 bucket name
- `S3_REGION` → Bucket region (e.g., `eu-north-1`)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` → IAM credentials
- Required S3 permissions: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`

**File Extensions:** 80+ types including documents, images, archives, audio, video, code files

**Limits:** `MAX_CONTENT_LENGTH = 100MB`

## Storage Abstraction (AWS S3)
Routes use `storage_backend` instance—never direct filesystem calls. S3Storage implements:
```python
storage_backend.save(file_storage, filename, user_id) → StorageResult(key=...)
storage_backend.delete(key) → removes from S3
storage_backend.download(file_record) → redirect to presigned URL
storage_backend.get_file_content(file_record) → raw bytes for ZIP/thumbnails
```

```python
# Files stored as: user-{id}/{timestamp}_{filename}
storage_result = storage_backend.save(file, filename, current_user.id)
new_file = File(file_path=storage_result.key, ...)  # Store S3 key in DB
```

**S3 Configuration:** Uses regional endpoint with signature v4, virtual-hosted addressing.

## Models (`models.py`)

| Model | Fields | Relationships |
|-------|--------|---------------|
| `User` | id, username, email, password_hash, role, created_at | files, logs |
| `File` | id, filename, original_filename, file_size, file_path, version, upload_date, user_id | permissions |
| `FilePermission` | id, file_id, user_id, can_read, can_write, can_delete, granted_by, granted_at | file, user |
| `LogBook` | id, user_id, action, details, ip_address, timestamp | user |

## File Versioning
Version auto-increments per user+filename:
```python
existing = File.query.filter_by(user_id=current_user.id, original_filename=name).order_by(File.version.desc()).first()
version = existing.version + 1 if existing else 1
```

## Authorization (Read/Write/Delete Rights)
Use `can_access_file(file, permission_type)` helper:
```python
if not can_access_file(file, 'read'):   # 'read', 'write', or 'delete'
    flash('Unauthorized access', 'danger')
    return redirect(url_for('dashboard'))
```
- Owner has full access
- Admin role (`User.role == 'admin'`) has full access to all files
- `FilePermission` grants granular R/W/D to specific users

## Activity Logging
Call `log_action(action, details)` for state-changing operations:
```python
log_action('upload', f'Uploaded {original_filename} (v{version}, {file_size} bytes)')
```
Captures: `current_user.id`, `request.remote_addr`, timestamp

## Routes Reference

### Public Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/login` | GET/POST | User authentication |
| `/register` | GET/POST | New user registration |
| `/logout` | GET | End session |

### User Routes (`@login_required`)
| Route | Method | Purpose |
|-------|--------|---------|
| `/dashboard` | GET | File list with thumbnails, search, actions |
| `/upload` | POST | Single file upload |
| `/upload-multiple` | POST | Bulk file upload |
| `/download/<id>` | GET | Download file (permission check) |
| `/download-zip` | POST | Bulk download as ZIP |
| `/delete/<id>` | POST | Delete file (permission check) |
| `/rename/<id>` | POST | Rename file (write permission) |
| `/thumbnail/<id>` | GET | Image thumbnail (80x80) |
| `/preview/<id>` | GET | File content for modal preview |
| `/share/<id>` | GET/POST | Share file with R/W/D permissions |
| `/shared-with-me` | GET | Files shared with current user |
| `/logs` | GET | User activity history |
| `/profile` | GET/POST | Profile & password change |

### Admin Routes (`@admin_required`)
| Route | Method | Purpose |
|-------|--------|---------|
| `/admin` | GET | Dashboard with stats |
| `/admin/users` | GET | User management list |
| `/admin/users/<id>/toggle-role` | POST | Promote/demote user |
| `/admin/users/<id>/delete` | POST | Delete user + their files |
| `/admin/files` | GET | System-wide file browser |
| `/admin/logs` | GET | All activity logs |

## Templates
Extend `templates/base.html` (Bootstrap 5 + dark mode). Use flash categories: `success`, `danger`, `info`, `warning`.
```html
{% extends "base.html" %}
{% block title %}Page Title{% endblock %}
{% block content %}...{% endblock %}
```

## Key Decorators
```python
@login_required          # Requires authenticated user
@admin_required          # Requires user.role == 'admin'
```

## Extension Checklist
- [ ] **New file extensions:** add to `Config.ALLOWED_EXTENSIONS` in `config.py`
- [ ] **New routes:** use `@login_required`, call `log_action()` for mutations, use `can_access_file()` for shared resources
- [ ] **New models:** add cascade relationship if user-owned, run `db.create_all()` (no migrations)
- [ ] **Admin routes:** add `@admin_required` decorator after `@login_required`
- [ ] **Background scripts:** wrap in `with app.app_context():` for DB access
- [ ] **File handling:** use `secure_filename()` + storage abstraction, never raw `os.path`

## Environment Variables (`.env`)
```bash
# Supabase PostgreSQL (use pooler URL)
DATABASE_URL=postgresql://postgres.xxxx:password@aws-1-eu-central-1.pooler.supabase.com:6543/postgres

# AWS S3 Storage
S3_BUCKET_NAME=your-bucket
S3_REGION=eu-north-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Flask
SECRET_KEY=your-secret-key
```

**Note:** URL-encode special characters in passwords (e.g., `!` → `%21`).

