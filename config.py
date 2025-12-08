import logging
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database: Use DATABASE_URL for cloud (PostgreSQL), fallback to local SQLite
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Supabase/Heroku use postgres://, SQLAlchemy needs postgresql://
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'file_exchange.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max file size
    # Allow all common file types - add more as needed
    ALLOWED_EXTENSIONS = {
        # Documents
        'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf', 'csv',
        # Images
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff', 'tif', 'heic', 'raw',
        # Archives
        'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz',
        # Audio
        'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma',
        # Video
        'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v',
        # Code
        'py', 'js', 'html', 'css', 'json', 'xml', 'yaml', 'yml', 'md', 'sql', 'sh', 'bat', 'ps1',
        'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt', 'ts', 'jsx', 'tsx',
        # Other
        'exe', 'msi', 'dmg', 'apk', 'iso', 'bin', 'dll', 'so', 'deb', 'rpm',
        'ttf', 'otf', 'woff', 'woff2', 'eot',
        'psd', 'ai', 'sketch', 'fig', 'xd',
        'db', 'sqlite', 'bak', 'log', 'cfg', 'ini', 'env',
    }
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 's3')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
    S3_REGION = os.environ.get('S3_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_SESSION_TOKEN = os.environ.get('AWS_SESSION_TOKEN')
    S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL')
    S3_PRESIGNED_TTL = int(os.environ.get('S3_PRESIGNED_TTL', '900'))

    if STORAGE_BACKEND.lower() == 'local':
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    elif not S3_BUCKET_NAME:
        log.warning('STORAGE_BACKEND is s3 but S3_BUCKET_NAME is missing; uploads will fail until configured.')
    os.makedirs(LOG_FOLDER, exist_ok=True)
