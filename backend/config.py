"""
Configuration for Southeast Landmark CRM.
Designed for cPanel / PythonAnywhere (no Docker/Redis/MinIO needed).
"""

import os
from datetime import timedelta
from pathlib import Path

# Base directory of this file
BASE_DIR = Path(__file__).resolve().parent


class Config:
    # ------------------------------------------------------------------
    # Flask Core
    # ------------------------------------------------------------------
    SECRET_KEY = os.environ.get('SECRET_KEY', 'CHANGE-THIS-BEFORE-GOING-LIVE-USE-64-RANDOM-CHARS')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'CHANGE-THIS-JWT-SECRET-ALSO-64-RANDOM-CHARS')
    DEBUG = False
    TESTING = False

    # ------------------------------------------------------------------
    # Database
    # PythonAnywhere / cPanel → MySQL  (most common)
    # Use:  mysql+pymysql://username:password@hostname/dbname
    # If host offers PostgreSQL:  postgresql://user:pass@localhost/dbname
    # ------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://crm_user:yourpassword@localhost/crm_southeast'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,   # Reconnect before MySQL's 5-min timeout
        'pool_pre_ping': True,
    }

    # ------------------------------------------------------------------
    # APScheduler (replaces Celery — runs inside the Flask process)
    # Jobs are stored in the same database so they survive restarts
    # ------------------------------------------------------------------
    SCHEDULER_API_ENABLED = False          # Don't expose /scheduler HTTP API
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': os.environ.get('DATABASE_URL',
                                  'mysql+pymysql://crm_user:yourpassword@localhost/crm_southeast')
        }
    }
    SCHEDULER_EXECUTORS = {
        'default': {'type': 'threadpool', 'max_workers': 5}
    }
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 300,  # 5 minutes grace for missed jobs
    }
    SCHEDULER_TIMEZONE = 'Asia/Dhaka'

    # ------------------------------------------------------------------
    # Call Recording Storage — Local Filesystem
    # Recordings are stored in uploads/recordings/ inside backend/
    # Access is always via time-limited signed tokens, never direct URL
    # ------------------------------------------------------------------
    UPLOAD_FOLDER = os.environ.get(
        'UPLOAD_FOLDER',
        str(BASE_DIR / 'uploads')
    )
    if not os.path.isabs(UPLOAD_FOLDER):
        UPLOAD_FOLDER = str(BASE_DIR / UPLOAD_FOLDER)

    RECORDINGS_FOLDER = os.environ.get(
        'RECORDINGS_FOLDER',
        str(BASE_DIR / 'uploads' / 'recordings')
    )
    if not os.path.isabs(RECORDINGS_FOLDER):
        RECORDINGS_FOLDER = str(BASE_DIR / RECORDINGS_FOLDER)
    AVATARS_FOLDER = os.environ.get(
        'AVATARS_FOLDER',
        str(BASE_DIR / 'uploads' / 'avatars')
    )
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024   # 50 MB max file upload
    RECORDING_LINK_EXPIRY_SECONDS = 900      # 15-minute signed URL

    # ------------------------------------------------------------------
    # MEGA Cloud Storage — for call recording uploads
    # Create a free MEGA account at https://mega.nz and put credentials here
    # ------------------------------------------------------------------
    MEGA_EMAIL = os.environ.get('MEGA_EMAIL', '')
    MEGA_PASSWORD = os.environ.get('MEGA_PASSWORD', '')
    MEGA_FOLDER = os.environ.get('MEGA_FOLDER', 'CRM-Recordings')  # top-level MEGA folder

    # ------------------------------------------------------------------
    # Email (SMTP) — Gmail App Password recommended
    # ------------------------------------------------------------------
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        f"Southeast Landmark CRM <{os.environ.get('MAIL_USERNAME', 'noreply@southeast.com')}>"
    )

    # ------------------------------------------------------------------
    # Meta Lead Ads Webhook
    # ------------------------------------------------------------------
    META_VERIFY_TOKEN = os.environ.get('META_VERIFY_TOKEN', 'set-a-random-string-here')
    META_PAGE_ACCESS_TOKEN = os.environ.get('META_PAGE_ACCESS_TOKEN', '')
    META_APP_SECRET = os.environ.get('META_APP_SECRET', '')
    META_APP_ID = os.environ.get('META_APP_ID', '')

    # ------------------------------------------------------------------
    # JWT Settings
    # ------------------------------------------------------------------
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # ------------------------------------------------------------------
    # SLA Timer Settings (minutes)
    # ------------------------------------------------------------------
    SLA_NOTIFY_MINUTES = int(os.environ.get('SLA_NOTIFY_MINUTES', 0))
    SLA_REMINDER_MINUTES = int(os.environ.get('SLA_REMINDER_MINUTES', 10))
    SLA_MANAGER_ALERT_MINUTES = int(os.environ.get('SLA_MANAGER_ALERT_MINUTES', 20))
    SLA_ESCALATE_MINUTES = int(os.environ.get('SLA_ESCALATE_MINUTES', 30))

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_ENABLED = False     # Using JWT, not session CSRF


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    JWT_COOKIE_SECURE = False
    # Use SQLite for local dev if you don't have MySQL installed
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{BASE_DIR / 'crm_dev.db'}"
    )
    # SQLite doesn't support the MySQL pool_recycle trick — use NullPool instead
    # This prevents "no such table" errors caused by stale cross-thread connections
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': __import__('sqlalchemy.pool', fromlist=['NullPool']).NullPool,
    }
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': os.environ.get('DATABASE_URL', f"sqlite:///{BASE_DIR / 'crm_dev.db'}")
        }
    }


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    JWT_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SCHEDULER_JOBSTORES = {'default': {'type': 'memory'}}
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
