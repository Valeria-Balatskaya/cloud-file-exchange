# Cloud File Exchange System

A secure cloud-based file exchange system with user authentication, file versioning, sharing permissions, and comprehensive activity logging.

## Features

### Core Features
- ✅ User registration and authentication
- ✅ Secure file upload/download (single & bulk)
- ✅ File versioning control
- ✅ Activity logging (LogBook)
- ✅ File sharing with granular permissions (Read/Write/Delete)
- ✅ ZIP download for multiple files

### User Experience
- ✅ Dark mode toggle
- ✅ Drag & drop file upload
- ✅ Bulk file upload (multiple files at once)
- ✅ File rename
- ✅ Thumbnail previews for images
- ✅ File preview modal (images, PDFs, text files)
- ✅ File search/filter
- ✅ Responsive Bootstrap 5 UI

### Admin Features
- ✅ Admin dashboard with system stats
- ✅ User management (promote/demote/delete)
- ✅ View all files in system
- ✅ System-wide activity logs with filtering

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Flask App     │     │    Supabase      │     │    AWS S3       │
│   (Python)      │────▶│   (PostgreSQL)   │     │   (Storage)     │
│                 │     │                  │     │                 │
│   • Routes      │     │   • Users        │     │   • Actual      │
│   • Auth        │     │   • File meta    │     │     files       │
│   • Logic       │     │   • Logs         │     │                 │
│                 │     │   • Permissions  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Technologies

- **Backend**: Python Flask, Flask-Login, Flask-SQLAlchemy
- **Database**: PostgreSQL (Supabase) - cloud hosted
- **Storage**: AWS S3 - cloud file storage
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **Image Processing**: Pillow (thumbnails)

## Setup Instructions

### Prerequisites
- Python 3.8+
- AWS Account (for S3 storage)
- Supabase Account (for PostgreSQL database)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Valeria-Balatskaya/cloud-file-exchange.git
   cd cloud-file-exchange
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   # Database: Supabase PostgreSQL (required)
   DATABASE_URL=postgresql://postgres.xxxx:pass@aws-1-region.pooler.supabase.com:6543/postgres
   
   # AWS S3 Storage (required)
   S3_BUCKET_NAME=your-bucket
   S3_REGION=eu-north-1
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Open browser:** http://127.0.0.1:5000

## Default Login

- **Username:** `admin`
- **Password:** `admin`

## Project Structure

```
cloud-file-exchange/
├── app.py              # Main Flask application & routes
├── models.py           # SQLAlchemy database models
├── config.py           # Configuration settings
├── storage.py          # S3/Local storage abstraction
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not in git)
├── .env.example        # Environment template
└── templates/          # Jinja2 HTML templates
    ├── admin/          # Admin dashboard templates
    ├── base.html       # Base layout with navbar
    ├── dashboard.html  # Main file manager
    ├── login.html      # Login page
    ├── register.html   # Registration page
    ├── profile.html    # User profile
    ├── logs.html       # Activity logs
    ├── share.html      # File sharing
    └── shared.html     # Shared files view
```

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Redirect to dashboard/login |
| `/login` | GET/POST | User login |
| `/register` | GET/POST | User registration |
| `/logout` | GET | Logout user |
| `/dashboard` | GET | Main file manager |
| `/upload-multiple` | POST | Upload files (multipart) |
| `/download/<id>` | GET | Download single file |
| `/download-zip` | POST | Download multiple as ZIP |
| `/delete/<id>` | POST | Delete file |
| `/rename/<id>` | POST | Rename file |
| `/share/<id>` | GET/POST | Share file with user |
| `/shared-with-me` | GET | View shared files |
| `/preview/<id>` | GET | Preview file content |
| `/thumbnail/<id>` | GET | Get image thumbnail |
| `/profile` | GET/POST | User profile & password |
| `/logs` | GET | View activity logs |
| `/admin` | GET | Admin dashboard |
| `/admin/users` | GET | Manage users |
| `/admin/files` | GET | View all files |
| `/admin/logs` | GET | System logs |

## Team Members

- Valeriia Balatska
- Vladyslav Dubenchuk
- Szymon Mela
- Marcin Kaczmarek
- Mateusz Mrowicki

## License

MIT License - Educational project for Cloud Computing Systems course.
