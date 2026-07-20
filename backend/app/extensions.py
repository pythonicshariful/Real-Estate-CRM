"""
Flask extensions — initialized without app, then bound in app factory.
No Celery, no Redis, no MinIO — works on cPanel / PythonAnywhere.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Core extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()
cors = CORS()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://",   # In-memory rate limiting — fine for single-process
)

# APScheduler — replaces Celery entirely
# Runs SLA timers and periodic checks inside the Flask web process
scheduler = BackgroundScheduler()
