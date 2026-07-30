from __future__ import annotations
"""
SLA & Background Tasks using APScheduler.
Replaces Celery entirely — no Redis or separate worker process needed.
Runs inside the Flask web process as background threads.
"""

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)



def _get_app(app=None):
    """Retrieve the Flask application instance."""
    if app is not None:
        return app
    from app.extensions import scheduler
    if hasattr(scheduler, 'app') and scheduler.app:
        return scheduler.app
    from flask import current_app
    try:
        if current_app and current_app.has_app_context:
            return current_app._get_current_object()
    except Exception:
        pass
    from app import create_app
    import os
    return create_app(os.environ.get('FLASK_CONFIG', 'development'))


# ---------------------------------------------------------------------------
# SLA Timer Functions (scheduled by APScheduler)
# Each function gets `app` dynamically and creates its own app context.
# ---------------------------------------------------------------------------

def schedule_sla_chain(opportunity_id: int, app=None):
    """
    Schedule the full SLA escalation chain for a newly assigned lead.
    Called immediately when a lead is assigned to an executive.

    Chain:
      T+0   → notify executive (immediate call, not scheduled)
      T+10  → sla_reminder job
      T+20  → sla_manager_alert job
      T+30  → sla_escalate job
    """
    from app.extensions import scheduler
    app = _get_app(app)

    sla_remind_min = app.config.get('SLA_REMINDER_MINUTES', 10)
    sla_alert_min = app.config.get('SLA_MANAGER_ALERT_MINUTES', 20)
    sla_escalate_min = app.config.get('SLA_ESCALATE_MINUTES', 30)

    now = datetime.now(timezone.utc)

    scheduler.add_job(
        func=sla_reminder,
        trigger='date',
        run_date=now + timedelta(minutes=sla_remind_min),
        id=f'sla_reminder_{opportunity_id}',
        replace_existing=True,
        args=[opportunity_id],
        misfire_grace_time=300,
    )
    scheduler.add_job(
        func=sla_manager_alert,
        trigger='date',
        run_date=now + timedelta(minutes=sla_alert_min),
        id=f'sla_manager_alert_{opportunity_id}',
        replace_existing=True,
        args=[opportunity_id],
        misfire_grace_time=300,
    )
    scheduler.add_job(
        func=sla_escalate,
        trigger='date',
        run_date=now + timedelta(minutes=sla_escalate_min),
        id=f'sla_escalate_{opportunity_id}',
        replace_existing=True,
        args=[opportunity_id],
        misfire_grace_time=300,
    )

    logger.info(
        f'SLA chain scheduled for opportunity {opportunity_id}: '
        f'remind@{sla_remind_min}min, alert@{sla_alert_min}min, escalate@{sla_escalate_min}min'
    )


def cancel_sla_chain(opportunity_id: int, app=None):
    """Cancel all pending SLA jobs for a lead (called when lead is contacted)."""
    from app.extensions import scheduler

    for job_id in [
        f'sla_reminder_{opportunity_id}',
        f'sla_manager_alert_{opportunity_id}',
        f'sla_escalate_{opportunity_id}',
    ]:
        try:
            scheduler.remove_job(job_id)
            logger.info(f'Cancelled SLA job: {job_id}')
        except Exception:
            pass  # Job may have already fired


def sla_reminder(opportunity_id: int, app=None):
    """T+10 min: Remind the assigned executive."""
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import Opportunity, SLAEvent, SLAStatus, PipelineStage

        opp = Opportunity.query.get(opportunity_id)
        if not opp:
            return

        # Only act if lead is still in initial uncontacted stages
        uncontacted_stages = {
            PipelineStage.NEW,
            PipelineStage.ASSIGNED,
            PipelineStage.FIRST_CONTACT_PENDING,
        }
        if opp.pipeline_stage not in uncontacted_stages:
            logger.info(f'SLA reminder skipped — lead {opportunity_id} already contacted')
            _mark_sla_resolved(opp.id)
            return

        sla = SLAEvent.query.filter_by(opportunity_id=opportunity_id).first()
        if sla:
            sla.reminded_at = datetime.now(timezone.utc)
            sla.status = SLAStatus.REMINDED
            db.session.commit()

        if opp.assigned_to:
            _send_email_notification(
                app,
                opp.assigned_to.email,
                subject='⚠️ SLA Reminder — Lead Not Yet Contacted',
                body=(
                    f'Hello {opp.assigned_to.full_name},\n\n'
                    f'Lead #{opportunity_id} has not been contacted yet. '
                    f'Please call immediately to avoid escalation.\n\n'
                    f'Contact: {opp.contact.full_name if opp.contact else "N/A"}\n'
                    f'Phone: {opp.contact.phone_normalized if opp.contact else "N/A"}'
                )
            )
        logger.info(f'SLA reminder sent for opportunity {opportunity_id}')


def sla_manager_alert(opportunity_id: int, app=None):
    """T+20 min: Alert the manager."""
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import Opportunity, SLAEvent, SLAStatus, PipelineStage, User, UserRole

        opp = Opportunity.query.get(opportunity_id)
        if not opp:
            return

        uncontacted_stages = {
            PipelineStage.NEW,
            PipelineStage.ASSIGNED,
            PipelineStage.FIRST_CONTACT_PENDING,
        }
        if opp.pipeline_stage not in uncontacted_stages:
            _mark_sla_resolved(opp.id)
            return

        sla = SLAEvent.query.filter_by(opportunity_id=opportunity_id).first()
        if sla:
            sla.manager_alerted_at = datetime.now(timezone.utc)
            sla.status = SLAStatus.MANAGER_ALERTED
            db.session.commit()

        # Find all active admins to notify
        managers = User.query.filter_by(
            role=UserRole.ADMIN, is_active=True
        ).all()

        exec_name = opp.assigned_to.full_name if opp.assigned_to else 'Unknown'
        for manager in managers:
            _send_email_notification(
                app,
                manager.email,
                subject='🚨 SLA BREACH ALERT — Lead Not Contacted (20 min)',
                body=(
                    f'Dear {manager.full_name},\n\n'
                    f'Lead #{opportunity_id} assigned to {exec_name} has NOT been contacted '
                    f'after 20 minutes. Immediate intervention required.\n\n'
                    f'Contact: {opp.contact.full_name if opp.contact else "N/A"}\n'
                    f'Phone: {opp.contact.phone_normalized if opp.contact else "N/A"}\n\n'
                    f'The lead will be auto-reassigned in 10 more minutes if not acted upon.'
                )
            )
        logger.warning(f'SLA manager alert fired for opportunity {opportunity_id}')


def sla_escalate(opportunity_id: int, app=None):
    """T+30 min: Reassign the lead to the next available executive."""
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import (
            Opportunity, SLAEvent, SLAStatus, PipelineStage,
            User, UserRole, PipelineHistory, AuditLog
        )

        opp = Opportunity.query.get(opportunity_id)
        if not opp:
            return

        uncontacted_stages = {
            PipelineStage.NEW,
            PipelineStage.ASSIGNED,
            PipelineStage.FIRST_CONTACT_PENDING,
        }
        if opp.pipeline_stage not in uncontacted_stages:
            _mark_sla_resolved(opp.id)
            return

        # Find next available executive with capacity
        old_exec_id = opp.assigned_to_id
        new_exec = _find_available_executive(old_exec_id)

        sla = SLAEvent.query.filter_by(opportunity_id=opportunity_id).first()

        if new_exec:
            opp.assigned_to_id = new_exec.id
            if sla:
                sla.escalated_at = datetime.now(timezone.utc)
                sla.status = SLAStatus.ESCALATED
                sla.escalated_to_id = new_exec.id

            # Audit log
            audit = AuditLog(
                table_name='opportunities',
                record_id=opp.id,
                action='UPDATE',
                field_name='assigned_to_id',
                old_value=str(old_exec_id),
                new_value=str(new_exec.id),
            )
            db.session.add(audit)
            db.session.commit()

            _send_email_notification(
                app,
                new_exec.email,
                subject='📲 Lead Reassigned to You — Act Immediately',
                body=(
                    f'Hello {new_exec.full_name},\n\n'
                    f'Lead #{opportunity_id} has been reassigned to you due to SLA breach.\n'
                    f'Please contact this lead IMMEDIATELY.\n\n'
                    f'Contact: {opp.contact.full_name if opp.contact else "N/A"}\n'
                    f'Phone: {opp.contact.phone_normalized if opp.contact else "N/A"}'
                )
            )
            logger.warning(
                f'Lead {opportunity_id} escalated and reassigned from exec {old_exec_id} '
                f'to exec {new_exec.id}'
            )
        else:
            # No exec available — mark for manager review
            if sla:
                sla.status = SLAStatus.ESCALATED
                sla.escalated_at = datetime.now(timezone.utc)
                db.session.commit()
            logger.error(
                f'Lead {opportunity_id} SLA breached — no available exec to reassign to!'
            )


def check_sla_compliance(app=None):
    """
    Periodic fallback sweep (every 5 minutes via APScheduler cron).
    Catches any SLA events that the date-based jobs may have missed
    (e.g., if the server restarted and the job was lost before DB jobstore was set up).
    """
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import SLAEvent, SLAStatus, Opportunity, PipelineStage

        now = datetime.now(timezone.utc)
        remind_cutoff = now - timedelta(minutes=app.config.get('SLA_REMINDER_MINUTES', 10))
        alert_cutoff = now - timedelta(minutes=app.config.get('SLA_MANAGER_ALERT_MINUTES', 20))
        escalate_cutoff = now - timedelta(minutes=app.config.get('SLA_ESCALATE_MINUTES', 30))

        # Find events that should have been reminded but weren't
        pending_events = SLAEvent.query.filter(
            SLAEvent.status == SLAStatus.NOTIFIED,
            SLAEvent.assigned_at <= remind_cutoff
        ).all()

        for event in pending_events:
            opp = Opportunity.query.get(event.opportunity_id)
            if opp and opp.pipeline_stage in {
                PipelineStage.NEW,
                PipelineStage.ASSIGNED,
                PipelineStage.FIRST_CONTACT_PENDING,
            }:
                if event.assigned_at <= escalate_cutoff:
                    sla_escalate(event.opportunity_id, app=app)
                elif event.assigned_at <= alert_cutoff:
                    sla_manager_alert(event.opportunity_id, app=app)
                else:
                    sla_reminder(event.opportunity_id, app=app)


def send_daily_summary(app=None):
    """
    Daily summary email to all managers — sent at 8 PM Dhaka time.
    Shows today's lead count, SLA compliance, and overdue leads.
    """
    app = _get_app(app)
    with app.app_context():
        from app.models import Opportunity, User, UserRole, SLAEvent, SLAStatus, PipelineStage
        from datetime import date

        today = date.today()
        managers = User.query.filter_by(role=UserRole.ADMIN, is_active=True).all()

        total_today = Opportunity.query.filter(
            db_cast_date('opportunities.created_at') == today
        ).count()

        overdue = Opportunity.query.filter(
            Opportunity.next_action_deadline < datetime.now(timezone.utc),
            Opportunity.final_result.is_(None),
        ).count()

        for manager in managers:
            _send_email_notification(
                app,
                manager.email,
                subject=f'📊 Daily CRM Summary — {today.strftime("%d %b %Y")}',
                body=(
                    f'Good evening {manager.full_name},\n\n'
                    f'Here is your daily summary:\n\n'
                    f'  • New leads today: {total_today}\n'
                    f'  • Overdue follow-ups: {overdue}\n\n'
                    f'Log in to the CRM for full details.\n\n'
                    f'Southeast Landmark CRM'
                )
            )


# ---------------------------------------------------------------------------
# Meta Webhook Processor (synchronous — called from route handler)
# ---------------------------------------------------------------------------

def process_meta_webhook(payload_dict: dict, app=None):
    """
    Process a Meta Lead Ads webhook payload.
    Runs synchronously (called directly from webhook route).
    On cPanel/PythonAnywhere this is fine — webhook should respond quickly.
    """
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import Contact, Inquiry, Opportunity, PipelineStage, SLAEvent, SLAStatus
        from app.utils.phone import normalize_phone
        import requests as http_req

        entries = payload_dict.get('entry', [])
        for entry in entries:
            for change in entry.get('changes', []):
                value = change.get('value', {})
                if change.get('field') != 'leadgen':
                    continue

                leadgen_id = value.get('leadgen_id')
                form_id = value.get('form_id')
                page_id = value.get('page_id')
                ad_id = value.get('ad_id')
                adset_id = value.get('adset_id')
                campaign_id = value.get('campaign_id')

                # Fetch full lead data from Meta Graph API
                lead_data = _fetch_meta_lead(app, leadgen_id)
                if not lead_data:
                    logger.error(f'Could not fetch lead data for leadgen_id={leadgen_id}')
                    continue

                # Parse field data
                field_data = {
                    f['name']: f['values'][0]
                    for f in lead_data.get('field_data', [])
                    if f.get('values')
                }

                full_name = field_data.get('full_name', field_data.get('name', 'Unknown'))
                email = field_data.get('email', '')
                phone_raw = field_data.get('phone_number', field_data.get('phone', ''))
                phone_norm = normalize_phone(phone_raw) if phone_raw else None

                # Deduplicate contact
                contact = None
                if phone_norm:
                    contact = Contact.query.filter_by(phone_normalized=phone_norm).first()
                if not contact and email:
                    contact = Contact.query.filter_by(email=email).first()

                if not contact:
                    contact = Contact(
                        full_name=full_name,
                        email=email,
                        phone_raw=phone_raw,
                        phone_normalized=phone_norm,
                        source='Meta Lead Ads',
                        facebook_lead_id=leadgen_id,
                        consent_given=True,
                        consent_date=datetime.now(timezone.utc),
                    )
                    db.session.add(contact)
                    db.session.flush()
                else:
                    logger.info(f'Duplicate contact found: {contact.id} — creating new inquiry')

                # Create immutable Inquiry record
                inquiry = Inquiry(
                    contact_id=contact.id,
                    campaign_id=campaign_id,
                    adset_id=adset_id,
                    ad_id=ad_id,
                    form_id=form_id,
                    raw_payload=payload_dict,
                    submitted_at=datetime.now(timezone.utc),
                )
                db.session.add(inquiry)
                db.session.flush()

                # Auto-assign lead owner based on date/time schedule or equal round-robin
                assigned_owner = assign_lead_owner_auto(app=app)

                # Create Opportunity
                opp = Opportunity(
                    inquiry_id=inquiry.id,
                    contact_id=contact.id,
                    assigned_to_id=assigned_owner.id if assigned_owner else None,
                    pipeline_stage=PipelineStage.NEW if assigned_owner else PipelineStage.NEW,
                )
                db.session.add(opp)
                db.session.flush()

                # Create SLA event
                sla = SLAEvent(
                    opportunity_id=opp.id,
                    assigned_at=datetime.now(timezone.utc),
                    status=SLAStatus.NOTIFIED,
                )
                db.session.add(sla)
                db.session.commit()

                # Schedule SLA chain (APScheduler)
                schedule_sla_chain(opp.id, app=app)

                logger.info(
                    f'Meta lead processed: contact={contact.id}, '
                    f'inquiry={inquiry.id}, opportunity={opp.id}'
                )


# ---------------------------------------------------------------------------
# Call Recording — Local Filesystem Secure Links
# ---------------------------------------------------------------------------

def generate_secure_recording_url(call_log_id: int, user_id: int, app=None) -> str | None:
    """
    Generate a time-limited signed URL for a call recording.
    Uses HMAC signature + expiry timestamp — no MinIO/S3 needed.
    The actual file is served by the /api/security/recordings/<token> route.
    """
    app = _get_app(app)
    with app.app_context():
        from app.models import CallLog, RecordingDownloadLog
        from app.extensions import db
        import hmac
        import hashlib
        import time
        import base64

        log = CallLog.query.get(call_log_id)
        if not log or not log.recording_filename:
            return None

        # Create HMAC-signed token: expiry|call_log_id|user_id
        expiry = int(time.time()) + app.config.get('RECORDING_LINK_EXPIRY_SECONDS', 900)
        payload = f'{expiry}|{call_log_id}|{user_id}'
        secret = app.config['SECRET_KEY'].encode()
        sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
        token = base64.urlsafe_b64encode(f'{payload}|{sig}'.encode()).decode()

        # Log this access
        dl_log = RecordingDownloadLog(
            call_log_id=call_log_id,
            downloaded_by_id=user_id,
            downloaded_at=datetime.now(timezone.utc),
        )
        db.session.add(dl_log)
        db.session.commit()

        return token


def verify_recording_token(token: str, app=None) -> dict | None:
    """Verify and decode a recording token. Returns dict or None if invalid/expired."""
    app = _get_app(app)
    import hmac
    import hashlib
    import time
    import base64

    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.split('|')
        if len(parts) != 4:
            return None

        expiry, call_log_id, user_id, provided_sig = parts
        payload = f'{expiry}|{call_log_id}|{user_id}'
        secret = app.config['SECRET_KEY'].encode()
        expected_sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return None

        if int(time.time()) > int(expiry):
            return None

        return {'call_log_id': int(call_log_id), 'user_id': int(user_id)}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _send_email_notification(app, recipient_email: str, subject: str, body: str):
    """Send an email notification via Flask-Mail."""
    try:
        from flask_mail import Message as MailMessage
        from app.extensions import mail

        with app.app_context():
            msg = MailMessage(
                subject=subject,
                recipients=[recipient_email],
                body=body,
            )
            mail.send(msg)
    except Exception as e:
        logger.error(f'Failed to send email to {recipient_email}: {e}')


def _fetch_meta_lead(app, leadgen_id: str) -> dict | None:
    """Fetch full lead details from Meta Graph API."""
    import requests
    token = app.config.get('META_PAGE_ACCESS_TOKEN')
    if not token:
        return None

    url = f'https://graph.facebook.com/v19.0/{leadgen_id}'
    try:
        resp = requests.get(url, params={
            'access_token': token,
            'fields': 'field_data,created_time,ad_id,adset_id,campaign_id,form_id'
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f'Meta Graph API error for leadgen {leadgen_id}: {e}')
        return None


def assign_lead_owner_auto(exclude_user_id: int | None = None, app=None):
    """
    Assign incoming Meta lead to a Lead Owner.
    1. If a Lead Owner is within their configured date & time schedule, assign to them.
    2. Otherwise, divide leads equally among all active Lead Owners (round-robin / lowest lead count).
    """
    from app.models import User, UserRole, Opportunity
    from app.extensions import db
    from sqlalchemy import func
    from datetime import datetime

    app = _get_app(app)
    with app.app_context():
        active_owners = (
            User.query
            .filter(User.role == UserRole.LEAD_OWNER)
            .filter(User.is_active == True)
            .filter(User.id != exclude_user_id if exclude_user_id else True)
            .all()
        )

        if not active_owners:
            return None

        now = datetime.now()
        cur_date = now.date()
        cur_time = now.time()

        matching_scheduled_owners = []

        for owner in active_owners:
            has_date_config = owner.schedule_from_date is not None or owner.schedule_to_date is not None
            has_time_config = owner.schedule_start_time is not None or owner.schedule_end_time is not None

            if not has_date_config and not has_time_config:
                continue

            date_ok = True
            if owner.schedule_from_date and cur_date < owner.schedule_from_date:
                date_ok = False
            if owner.schedule_to_date and cur_date > owner.schedule_to_date:
                date_ok = False

            time_ok = True
            if owner.schedule_start_time and owner.schedule_end_time:
                if owner.schedule_start_time <= owner.schedule_end_time:
                    time_ok = owner.schedule_start_time <= cur_time <= owner.schedule_end_time
                else:
                    time_ok = cur_time >= owner.schedule_start_time or cur_time <= owner.schedule_end_time
            elif owner.schedule_start_time:
                time_ok = cur_time >= owner.schedule_start_time
            elif owner.schedule_end_time:
                time_ok = cur_time <= owner.schedule_end_time

            if date_ok and time_ok:
                matching_scheduled_owners.append(owner)

        if len(matching_scheduled_owners) == 1:
            logger.info(f"Auto-assigned lead to scheduled Lead Owner: {matching_scheduled_owners[0].full_name}")
            return matching_scheduled_owners[0]

        # If 0 or >1 scheduled owners match, divide equally among active owners (or matching scheduled owners)
        candidate_pool = matching_scheduled_owners if len(matching_scheduled_owners) > 1 else active_owners
        candidate_ids = [u.id for u in candidate_pool]

        lead_counts = (
            db.session.query(Opportunity.assigned_to_id, func.count(Opportunity.id).label('cnt'))
            .filter(Opportunity.assigned_to_id.in_(candidate_ids))
            .filter(Opportunity.is_deleted == False)
            .group_by(Opportunity.assigned_to_id)
            .subquery()
        )

        selected = (
            User.query
            .outerjoin(lead_counts, User.id == lead_counts.c.assigned_to_id)
            .filter(User.id.in_(candidate_ids))
            .order_by(func.coalesce(lead_counts.c.cnt, 0).asc(), User.id.asc())
            .first()
        )

        if selected:
            logger.info(f"Auto-assigned lead to Lead Owner (equal distribution): {selected.full_name}")
        return selected


def _find_available_executive(exclude_user_id: int | None):
    return assign_lead_owner_auto(exclude_user_id=exclude_user_id)



def _mark_sla_resolved(opportunity_id: int):
    """Mark the SLA event as resolved (lead was contacted in time)."""
    from app.models import SLAEvent, SLAStatus
    from app.extensions import db

    sla = SLAEvent.query.filter_by(opportunity_id=opportunity_id).first()
    if sla and sla.status not in {SLAStatus.ESCALATED, SLAStatus.RESOLVED}:
        sla.status = SLAStatus.RESOLVED
        sla.resolved_at = datetime.now(timezone.utc)
        db.session.commit()


def db_cast_date(column_expr):
    """SQLAlchemy date cast helper."""
    from sqlalchemy import func
    return func.date(column_expr)


# ---------------------------------------------------------------------------
# MEGA Cloud Storage — call recording upload
# ---------------------------------------------------------------------------

def upload_recording_to_mega(local_path: str, filename: str, app=None) -> str | None:
    """
    Upload a call recording file to MEGA cloud storage.

    Returns:
        str: Public MEGA share link if upload succeeded.
        None: If MEGA credentials are missing or upload failed.

    The upload is intentionally synchronous (runs in the request thread) because
    it's fast for audio files (<50 MB). Move into a background thread if needed.
    """
    app = _get_app(app)
    email = app.config.get('MEGA_EMAIL', '').strip()
    password = app.config.get('MEGA_PASSWORD', '').strip()
    folder_name = app.config.get('MEGA_FOLDER', 'CRM-Recordings')

    if not email or not password:
        logger.warning('MEGA_EMAIL / MEGA_PASSWORD not configured — skipping cloud upload')
        return None

    try:
        from mega import Mega
        mega = Mega()
        m = mega.login(email, password)

        # Find or create the target folder
        folder = m.find(folder_name, exclude_deleted=True)
        if folder is None:
            folder = m.create_folder(folder_name)
            # find() returns None, create_folder returns the new folder dict;
            # re-fetch so we have a consistent object
            folder = m.find(folder_name, exclude_deleted=True)

        # Upload the file into the folder
        uploaded = m.upload(local_path, folder[0] if isinstance(folder, tuple) else folder)
        share_link = m.get_upload_link(uploaded)
        logger.info(f'Recording uploaded to MEGA: {filename} → {share_link}')
        return share_link

    except Exception as e:
        logger.error(f'MEGA upload failed for {filename}: {e}')
        return None

