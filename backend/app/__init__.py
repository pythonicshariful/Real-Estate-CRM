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
    limiter.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

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
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'message': 'Token has expired', 'error': 'token_expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'message': 'Invalid token', 'error': 'invalid_token'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'message': 'No access token', 'error': 'authorization_required'}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({'message': 'Token has been revoked', 'error': 'token_revoked'}), 401

    # ------------------------------------------------------------------
    # HTTP error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad Request', 'message': str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Unauthorized', 'message': str(e)}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Forbidden', 'message': str(e)}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not Found', 'message': str(e)}), 404

    @app.errorhandler(429)
    def ratelimit_error(e):
        return jsonify({'error': 'Too Many Requests', 'message': 'Slow down'}), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Server Error: {e}')
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'message': 'Something went wrong'}), 500

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
        app.logger.info(f"Serving upload: folder={upload_folder}, filename={filename}")
        app.logger.info(f"File exists? {os.path.exists(os.path.join(upload_folder, filename))}")
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

    return app


def _configure_scheduler(app):
    """Configure and start APScheduler with SQLAlchemy jobstore."""
    from app.tasks import check_sla_compliance, send_daily_summary

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

    if not scheduler.running:
        scheduler.start()
        app.logger.info('APScheduler started — SLA timers active')


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
