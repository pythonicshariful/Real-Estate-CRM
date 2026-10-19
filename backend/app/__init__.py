"""
Flask App Factory — Southeast Landmark CRM
Designed for cPanel / PythonAnywhere deployment.
No Docker, no Celery, no Redis required.
"""

import os
import logging
from flask import Flask, jsonify
from config import config
from app.extensions import db, migrate, jwt, mail, limiter, cors, scheduler


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ------------------------------------------------------------------
    # Ensure upload directories exist
    # ------------------------------------------------------------------
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('RECORDINGS_FOLDER', 'uploads/recordings'), exist_ok=True)

    # ------------------------------------------------------------------
    # Initialize extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', '*')}})
    
    # Configure rate limiter to use the database
    from app.utils import limiter_storage # Registers the sqlalchemy storage schemes
    app.config.setdefault('RATELIMIT_STORAGE_URI', app.config.get('SQLALCHEMY_DATABASE_URI'))
    limiter.init_app(app)

    # ------------------------------------------------------------------
    # Configure logging
    # ------------------------------------------------------------------
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s : %(message)s'
        )

    # ------------------------------------------------------------------
    # Start APScheduler (SLA timers — runs in background thread)
    # Only start once, not during testing or migrations
    # ------------------------------------------------------------------
    if not app.config.get('TESTING') and not app.config.get('DISABLE_SCHEDULER'):
        _configure_scheduler(app)

    # ------------------------------------------------------------------
    # JWT error handlers
    # ------------------------------------------------------------------
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from app.models import TokenBlocklist
        jti = jwt_payload["jti"]
        return TokenBlocklist.is_jti_blacklisted(jti)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'status': 'error', 'code': 401, 'message': 'Token has expired', 'details': 'token_expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'status': 'error', 'code': 401, 'message': 'Invalid token', 'details': 'invalid_token'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'status': 'error', 'code': 401, 'message': 'No access token', 'details': 'authorization_required'}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({'status': 'error', 'code': 401, 'message': 'Token has been revoked', 'details': 'token_revoked'}), 401

    # ------------------------------------------------------------------
    # HTTP error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'status': 'error', 'code': 400, 'message': 'Bad Request', 'details': str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'status': 'error', 'code': 401, 'message': 'Unauthorized', 'details': str(e)}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'status': 'error', 'code': 403, 'message': 'Forbidden', 'details': str(e)}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'status': 'error', 'code': 404, 'message': 'Not Found', 'details': str(e)}), 404

    @app.errorhandler(429)
    def ratelimit_error(e):
        return jsonify({'status': 'error', 'code': 429, 'message': 'Too Many Requests', 'details': 'Slow down'}), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Server Error: {e}')
        db.session.rollback()
        return jsonify({'status': 'error', 'code': 500, 'message': 'Internal Server Error', 'details': 'Something went wrong'}), 500

    # ------------------------------------------------------------------
    # Performance Profiling (Request Timing)
    # ------------------------------------------------------------------
    import time
    from flask import g, request

    @app.before_request
    def start_timer():
        g.start_time = time.time()
        g.sql_time = 0.0
        g.sql_queries = 0

    @app.after_request
    def log_request_performance(response):
        if hasattr(g, 'start_time'):
            duration = (time.time() - g.start_time) * 1000
            sql_time = getattr(g, 'sql_time', 0.0)
            sql_queries = getattr(g, 'sql_queries', 0)
            app.logger.info(f'[PERF] {request.method} {request.path} | DB: {sql_time:.2f}ms ({sql_queries}q) | Total Request: {duration:.2f}ms')
        return response

    # ------------------------------------------------------------------
    # Register all 17 module blueprints
    # ------------------------------------------------------------------
    _register_blueprints(app)

    # ------------------------------------------------------------------
    # Register CLI commands
    # ------------------------------------------------------------------
    from app.commands import register_commands
    register_commands(app)

    # ------------------------------------------------------------------
    # Health check endpoint (useful for monitoring on cPanel)
    # ------------------------------------------------------------------
    @app.route('/health')
    def health_check():
        return jsonify({'status': 'ok', 'version': '2.0'}), 200

    @app.route('/')
    def root():
        """Serve index.html at root."""
        from flask import send_from_directory
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/assets/<path:filename>')
    @limiter.exempt
    def serve_assets(filename):
        """Serve assets directly from app/static/assets."""
        from flask import send_from_directory
        return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)

    @app.route('/uploads/<path:filename>')
    @limiter.exempt
    def serve_uploads(filename):
        """Serve uploaded files."""
        from flask import send_from_directory
        import os
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        return send_from_directory(upload_folder, filename)

    @app.route('/<path:filename>')
    @limiter.exempt
    def serve_static_page(filename):
        """Serve static HTML pages and root assets."""
        from flask import send_from_directory
        if not filename.startswith('api/') and not filename.startswith('health'):
            file_path = os.path.join(app.static_folder, filename)
            if os.path.isfile(file_path):
                return send_from_directory(app.static_folder, filename)
        return jsonify({'error': 'Not Found', 'message': f'File {filename} not found'}), 404

    # ------------------------------------------------------------------
    # Auto-migrate database schema (creates tables & adds missing columns)
    # ------------------------------------------------------------------
    _auto_migrate_db(app)

    return app


def _auto_migrate_db(app):
    """
    Auto-migrate database schema on startup:
    1. Runs db.create_all() to ensure all tables exist.
    2. Inspects existing tables and adds any missing columns automatically.
    3. Seeds default activity labels & questionnaire questions if not present.
    """
    with app.app_context():
        from sqlalchemy import inspect, text
        try:
            db.create_all()
            inspector = inspect(db.engine)
            existing_tables = set(inspector.get_table_names())
            
            for table_name, table in db.metadata.tables.items():
                if table_name not in existing_tables:
                    continue
                existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in existing_cols:
                        type_str = str(col.type).upper()
                        if 'JSON' in type_str:
                            sql_type = 'TEXT'
                        elif 'DATETIME' in type_str or 'DATE' in type_str or 'TIME' in type_str:
                            sql_type = 'DATETIME'
                        elif 'INT' in type_str:
                            sql_type = 'INTEGER'
                        elif 'BOOL' in type_str:
                            sql_type = 'BOOLEAN'
                        else:
                            sql_type = 'TEXT'
                        
                        try:
                            with db.engine.connect() as conn:
                                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {sql_type}"))
                                conn.commit()
                            app.logger.info(f"Auto-migrated: added column '{col.name}' to table '{table_name}'")
                        except Exception as ex:
                            app.logger.warning(f"Failed to add column '{col.name}' to table '{table_name}': {ex}")

            # Seed defaults
            try:
                from app.models import ActivityLabel, LeadQuestionnaireQuestion, Contact, SystemSetting
                from app.utils.phone import normalize_phone
                ActivityLabel.seed_defaults()
                LeadQuestionnaireQuestion.seed_defaults()
                SystemSetting.set('otp_enabled', 'false')

                # Auto-heal any contacts with unnormalized or raw phone numbers
                unnorm_contacts = Contact.query.filter(
                    (Contact.phone_normalized == None) | 
                    (~Contact.phone_normalized.like('+%'))
                ).limit(1000).all()
                updated_count = 0
                for c in unnorm_contacts:
                    norm = normalize_phone(c.phone_raw or c.phone_normalized)
                    if norm and norm != c.phone_normalized:
                        c.phone_normalized = norm
                        updated_count += 1
                if updated_count > 0:
                    db.session.commit()
                    app.logger.info(f"Auto-healed {updated_count} contact phone numbers to E.164 normalized format.")
            except Exception as seed_err:
                app.logger.warning(f"Seed/backfill step note: {seed_err}")
        except Exception as e:
            app.logger.warning(f"Auto-migration check skipped/failed: {e}")


def _configure_scheduler(app):
    """Configure and start APScheduler with SQLAlchemy jobstore."""
    from app.tasks import check_sla_compliance, send_daily_summary, check_appointment_reminders, retry_failed_webhooks, auto_update_scheduled_lead_statuses
    from filelock import FileLock, Timeout

    scheduler.app = app
    jobstore_url = app.config['SQLALCHEMY_DATABASE_URI']

    # Update scheduler jobstore to use the app's DB
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    scheduler.configure(
        jobstores={'default': SQLAlchemyJobStore(url=jobstore_url)},
        executors={'default': {'type': 'threadpool', 'max_workers': 5}},
        job_defaults={'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 300},
        timezone='Asia/Dhaka'
    )

    # Periodic SLA compliance sweep — runs every 5 minutes
    scheduler.add_job(
        func=check_sla_compliance,
        trigger='interval',
        minutes=5,
        id='sla_compliance_sweep',
        replace_existing=True
    )

    # Daily summary email — runs at 8:00 PM Dhaka time
    scheduler.add_job(
        func=send_daily_summary,
        trigger='cron',
        hour=20,
        minute=0,
        id='daily_summary',
        replace_existing=True
    )

    # Appointment reminders (24h and 2h) — runs every 10 minutes
    scheduler.add_job(
        func=check_appointment_reminders,
        trigger='interval',
        minutes=10,
        id='appointment_reminders',
        replace_existing=True
    )

    # Webhook retry backoff worker — runs every 5 minutes
    scheduler.add_job(
        func=retry_failed_webhooks,
        trigger='interval',
        minutes=5,
        id='webhook_retries',
        replace_existing=True
    )

    # Scheduled lead pipeline stage & deadline auto-updater — runs every 5 minutes
    scheduler.add_job(
        func=auto_update_scheduled_lead_statuses,
        trigger='interval',
        minutes=5,
        id='scheduled_lead_status_updates',
        replace_existing=True
    )

    if not scheduler.running:
        # Use filelock to ensure only one worker starts the scheduler
        lock_file = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'scheduler.lock')
        lock = FileLock(lock_file, timeout=0)
        try:
            lock.acquire()
            # Store the lock on the app object so it's not garbage collected
            app.scheduler_lock = lock
            scheduler.start()
            app.logger.info('APScheduler started — SLA timers active')
        except Timeout:
            app.logger.info('Scheduler lock already held by another worker. Skipping scheduler start.')


def _register_blueprints(app):
    """Register all Flask blueprints."""
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.leads import leads_bp
    from app.blueprints.contacts import contacts_bp
    from app.blueprints.projects import projects_bp
    from app.blueprints.tasks import tasks_bp
    from app.blueprints.team import team_bp
    from app.blueprints.finance import finance_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.webhooks import webhooks_bp
    from app.blueprints.settings import settings_bp
    from app.blueprints.security import security_bp
    from app.blueprints.events import events_bp
    from app.blueprints.notes import notes_bp
    from app.blueprints.messages import messages_bp
    from app.blueprints.tickets import tickets_bp
    from app.blueprints.expenses import expenses_bp
    from app.blueprints.prospects import prospects_bp
    from app.blueprints.help import help_bp

    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(leads_bp,     url_prefix='/api/leads')
    app.register_blueprint(contacts_bp,  url_prefix='/api/contacts')
    app.register_blueprint(projects_bp,  url_prefix='/api/projects')
    app.register_blueprint(tasks_bp,     url_prefix='/api/tasks')
    app.register_blueprint(team_bp,      url_prefix='/api/team')
    app.register_blueprint(finance_bp,   url_prefix='/api/finance')
    app.register_blueprint(reports_bp,   url_prefix='/api/reports')
    app.register_blueprint(webhooks_bp,  url_prefix='/api/webhooks')
    app.register_blueprint(settings_bp,  url_prefix='/api/settings')
    app.register_blueprint(security_bp,  url_prefix='/api/security')
    app.register_blueprint(events_bp,    url_prefix='/api/events')
    app.register_blueprint(notes_bp,     url_prefix='/api/notes')
    app.register_blueprint(messages_bp,  url_prefix='/api/messages')
    app.register_blueprint(tickets_bp,   url_prefix='/api/tickets')
    app.register_blueprint(expenses_bp,  url_prefix='/api/expenses')
    app.register_blueprint(prospects_bp, url_prefix='/api/prospects')
    app.register_blueprint(help_bp,      url_prefix='/api/help')
