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
    default_limits=["200 per hour", "50 per minute"]
)

# APScheduler — replaces Celery entirely
# Runs SLA timers and periodic checks inside the Flask web process
scheduler = BackgroundScheduler()

# ------------------------------------------------------------------
# SQL Query Profiling
# ------------------------------------------------------------------
import time
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask import g, has_request_context

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    # Add to global request context if inside a request
    if has_request_context():
        if hasattr(g, 'sql_time'):
            g.sql_time += (total * 1000)
            g.sql_queries += 1
    
    # Log individual slow queries if they take more than 50ms
    if total > 0.05:
        logger.warning(f"[SQL] Slow query ({total * 1000:.2f}ms): {statement}")
