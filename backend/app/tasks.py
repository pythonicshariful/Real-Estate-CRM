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
    from flask import current_app, has_app_context
    try:
        if has_app_context():
            return current_app._get_current_object()
    except Exception:
        pass
    from app.extensions import scheduler
    if hasattr(scheduler, 'app') and scheduler.app:
        return scheduler.app
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
        misfire_grace_time=86400,
    )
    scheduler.add_job(
        func=sla_manager_alert,
        trigger='date',
        run_date=now + timedelta(minutes=sla_alert_min),
        id=f'sla_manager_alert_{opportunity_id}',
        replace_existing=True,
        args=[opportunity_id],
        misfire_grace_time=86400,
    )
    scheduler.add_job(
        func=sla_escalate,
        trigger='date',
        run_date=now + timedelta(minutes=sla_escalate_min),
        id=f'sla_escalate_{opportunity_id}',
        replace_existing=True,
        args=[opportunity_id],
        misfire_grace_time=86400,
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
    import time
    start_time = time.time()
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
                assigned_at = event.assigned_at
                if assigned_at and assigned_at.tzinfo is None:
                    assigned_at = assigned_at.replace(tzinfo=timezone.utc)
                if assigned_at and assigned_at <= escalate_cutoff:
                    sla_escalate(event.opportunity_id, app=app)
                elif assigned_at and assigned_at <= alert_cutoff:
                    sla_manager_alert(event.opportunity_id, app=app)
                elif assigned_at:
                    sla_reminder(event.opportunity_id, app=app)
                    
        duration = (time.time() - start_time) * 1000
        if pending_events:
            logger.info(f'[SCHEDULER] Job: check_sla_compliance | Processed {len(pending_events)} events | Duration: {duration:.2f}ms')
        else:
            logger.info(f'[SCHEDULER] Job: check_sla_compliance | Duration: {duration:.2f}ms')


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
        from app.models import Contact, Inquiry, Opportunity, PipelineStage, SLAEvent, SLAStatus, Note, AuditLog
        from app.utils.phone import normalize_phone, find_existing_contact
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

                # Support embedded field_data (for in-CRM simulation or offline testing)
                if value.get('field_data'):
                    lead_data = {
                        'field_data': value.get('field_data'),
                        'ad_id': ad_id,
                        'adset_id': adset_id,
                        'campaign_id': campaign_id,
                        'form_id': form_id
                    }
                else:
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
                contact = find_existing_contact(phone=phone_raw, email=email)

                profession = field_data.get('profession', field_data.get('job_title', field_data.get('occupation')))
                service_type = field_data.get('service_type', field_data.get('service', field_data.get('property_type')))

                # Extract all custom questionnaire responses
                ignored_keys = {'full_name', 'name', 'first_name', 'last_name', 'email', 'phone_number', 'phone'}
                questionnaire_answers = {
                    k: v for k, v in field_data.items() if k not in ignored_keys
                }

                if not contact:
                    contact = Contact(
                        full_name=full_name,
                        email=email,
                        phone_raw=phone_raw,
                        phone_normalized=phone_norm,
                        profession=profession,
                        service_type=service_type,
                        source='Meta Lead Ads',
                        facebook_lead_id=leadgen_id,
                        consent_given=True,
                        consent_date=datetime.now(timezone.utc),
                    )
                    db.session.add(contact)
                    db.session.flush()
                else:
                    if profession and not contact.profession:
                        contact.profession = profession
                    if service_type and not getattr(contact, 'service_type', None):
                        contact.service_type = service_type
                    if email and not contact.email:
                        contact.email = email
                    if phone_norm and not contact.phone_normalized:
                        contact.phone_normalized = phone_norm
                    logger.info(f'Existing contact found: {contact.id} — deduplicating')

                # Create immutable Inquiry record
                inquiry = Inquiry(
                    contact_id=contact.id,
                    campaign_id=campaign_id,
                    adset_id=adset_id,
                    ad_id=ad_id,
                    form_id=form_id,
                    utm_source='meta',
                    utm_medium='paid_social',
                    utm_campaign=campaign_id,
                    utm_content=ad_id,
                    project_interest=field_data.get('project_interest', field_data.get('project', None)),
                    raw_payload={"webhook_payload": payload_dict, "lead_data": lead_data, "questionnaire": questionnaire_answers},
                    submitted_at=datetime.now(timezone.utc),
                )
                db.session.add(inquiry)
                db.session.flush()

                # Check if contact already has an active Opportunity
                terminal_stages = ['SOLD', 'CLOSED_LOST', 'INVALID', 'BOUGHT_ELSEWHERE', 'UNREACHABLE']
                active_opp = Opportunity.query.filter_by(
                    contact_id=contact.id,
                    is_deleted=False
                ).filter(~Opportunity.pipeline_stage.in_(terminal_stages)).order_by(Opportunity.created_at.desc()).first()

                if active_opp:
                    # Merge inquiry into existing active opportunity instead of creating a duplicate card
                    if questionnaire_answers:
                        curr_answers = dict(active_opp.questionnaire_answers or {})
                        curr_answers.update(questionnaire_answers)
                        active_opp.questionnaire_answers = curr_answers

                    qa_summary = "\n".join([f"• {k}: {v}" for k, v in questionnaire_answers.items()]) if questionnaire_answers else "None"
                    note = Note(
                        opportunity_id=active_opp.id,
                        contact_id=contact.id,
                        created_by_id=active_opp.assigned_to_id or 1,
                        content=f"📌 [Meta Lead Ads Re-submission]\nExisting lead submitted another form.\n• Campaign: {campaign_id or 'N/A'}\n• Form: {form_id or 'N/A'}\n• Answers:\n{qa_summary}"
                    )
                    db.session.add(note)

                    audit = AuditLog(
                        user_id=active_opp.assigned_to_id or 1,
                        table_name='opportunities',
                        record_id=active_opp.id,
                        action='UPDATE',
                        field_name='inquiry',
                        activity_label='Meta Re-submission',
                        new_value=f"Merged inquiry {inquiry.id} from Meta Lead Ads into existing lead #{active_opp.id}"
                    )
                    db.session.add(audit)
                    db.session.commit()

                    logger.info(
                        f'Duplicate Meta lead merged: contact={contact.id}, '
                        f'inquiry={inquiry.id}, merged_into_opp={active_opp.id}'
                    )
                    continue

                # Auto-assign lead owner based on date/time schedule or equal round-robin
                assigned_owner = assign_lead_owner_auto(app=app)

                # Create Opportunity with questionnaire answers
                opp = Opportunity(
                    inquiry_id=inquiry.id,
                    contact_id=contact.id,
                    assigned_to_id=assigned_owner.id if assigned_owner else None,
                    pipeline_stage=PipelineStage.NEW if assigned_owner else PipelineStage.NEW,
                    service_type=service_type,
                    questionnaire_answers=questionnaire_answers,
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
                
                saved_contact_id = contact.id
                saved_inquiry_id = inquiry.id
                saved_opp_id = opp.id

                db.session.commit()

                # Schedule SLA chain (APScheduler)
                schedule_sla_chain(saved_opp_id, app=app)

                logger.info(
                    f'Meta lead processed: contact={saved_contact_id}, '
                    f'inquiry={saved_inquiry_id}, opportunity={saved_opp_id}'
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
    """Send an email notification using SMTP settings from SystemSetting."""
    try:
        with app.app_context():
            from app.models import SystemSetting
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            host = SystemSetting.get('smtp_host', '').strip()
            port = SystemSetting.get('smtp_port', '587').strip()
            username = SystemSetting.get('smtp_username', '').strip()
            password = SystemSetting.get('smtp_password', '').strip()
            sender = SystemSetting.get('sender_email', 'noreply@southeast.com').strip()

            if not host:
                logger.warning("SMTP host not configured. Skipping email to " + recipient_email)
                return

            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            port = int(port) if port.isdigit() else 587
            
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
                
    except Exception as e:
        logger.error(f'Failed to send email to {recipient_email}: {e}')


def _fetch_meta_lead(app, leadgen_id: str) -> dict | None:
    """Fetch full lead details from Meta Graph API."""
    import requests
    from app.models import SystemSetting
    token = SystemSetting.get('meta_page_access_token') or app.config.get('META_PAGE_ACCESS_TOKEN')
    if not token:
        return None

    url = f'https://graph.facebook.com/v19.0/{leadgen_id}'
    import time
    start_time = time.time()
    try:
        resp = requests.get(url, params={
            'access_token': token,
            'fields': 'field_data,created_time,ad_id,adset_id,campaign_id,form_id'
        }, timeout=10)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f'[API] Meta Graph API | Duration: {duration:.2f}ms | Status: {resp.status_code}')
        
        if not resp.ok:
            logger.error(f'Meta Graph API error for leadgen {leadgen_id}: {resp.status_code} - {resp.text}')
            resp.raise_for_status()
            
        return resp.json()
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f'[API] Meta Graph API request failed after {duration:.2f}ms for leadgen {leadgen_id}: {e}')
        return None


def assign_lead_owner_auto(exclude_user_id: int | None = None, app=None):
    """
    Auto-assignment rule (client requirement 4), documented in one place:
    Candidate pool = active users with role LEAD_OWNER or EXECUTIVE
    (executives are real assignees, not just lead owners).
    1. If a candidate is within their configured date & time schedule
       (schedule_from/to_date, schedule_start/end_time), restrict the
       pool to those in-window candidates. Schedules are evaluated in
       Bangladesh time (Asia/Dhaka), not server-local time, so a
       9am-6pm schedule means 9am-6pm in Bangladesh.
    2. Otherwise fall back to the full active candidate pool.
    3. Pick by persisted SystemSetting 'auto_assign_mode':
       - 'lowest_count' (default): lowest active (non-terminal, non-deleted)
         lead count, ties broken by lowest user id, skipping anyone at or
         over max_lead_capacity (default 30).
       - 'round_robin': next candidate in id order after the persisted
         'auto_assign_rr_index' pointer, skipping full candidates; the
         pointer advances only on a successful pick and is persisted via
         SystemSetting (flushed here, committed by the caller's transaction).
    Returns the selected User, or None if the pool is empty / all full.
    """
    # PipelineStage was missing from this import, so the very next use of it
    # (building the terminal-stage filter below) raised NameError and the whole
    # auto-assignment silently failed. Every lead stayed unassigned.
    from app.models import User, UserRole, Opportunity, PipelineStage
    from app.extensions import db
    from sqlalchemy import func
    from datetime import datetime

    # BUG FIX (pre-existing, found while testing): this function used to
    # always push a NEW app context, even when called from inside a request
    # (manual lead create, CSV/Excel import, Meta webhook). Flask-SQLAlchemy
    # tears the session down when that nested context exits, rolling back
    # the caller's still-uncommitted Contact flush — the lead was then
    # committed with a contact_id pointing at a row that never existed
    # (500 ObjectDeletedError on create_lead). Reuse the existing context
    # when there is one; only push a new one for scheduler/background calls.
    from contextlib import nullcontext
    from flask import has_app_context
    app = _get_app(app)
    ctx = nullcontext() if has_app_context() else app.app_context()
    with ctx:
        active_owners = (
            User.query
            .filter(User.role.in_([UserRole.LEAD_OWNER, UserRole.EXECUTIVE]))
            .filter(User.is_active == True)
            .filter(User.id != exclude_user_id if exclude_user_id else True)
            .all()
        )

        if not active_owners:
            return None

        # Schedule windows are Bangladesh wall-clock times. The VPS runs
        # on UTC, so naive server-local now() would shift every window
        # by 6 hours. Use Asia/Dhaka (fixed +06:00 fallback if tzdata
        # is missing) and drop tzinfo before comparing with the naive
        # schedule time columns.
        try:
            from zoneinfo import ZoneInfo
            _dhaka_tz = ZoneInfo("Asia/Dhaka")
        except Exception:
            from datetime import timezone as _tz, timedelta as _td
            _dhaka_tz = _tz(_td(hours=6))
        now = datetime.now(_dhaka_tz).replace(tzinfo=None)
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

        if len(matching_scheduled_owners) > 0:
            candidate_pool = matching_scheduled_owners
        else:
            # No owner currently falls inside their configured date/time window
            # (or nobody has a schedule set up at all). Falling back to the full
            # pool of active Lead Owners — this is what the docstring above
            # promises (even distribution by lowest active lead count).
            # Returning None here left every inbound Meta lead unassigned.
            logger.info("No Lead Owner within schedule window — falling back to all active Lead Owners.")
            candidate_pool = active_owners
            
        candidate_ids = [u.id for u in candidate_pool]

        # Count active opportunities per candidate (non-deleted, non-terminal stages)
        terminal_stages = [
            PipelineStage.SOLD,
            PipelineStage.CLOSED_LOST,
            PipelineStage.INVALID,
            PipelineStage.BOUGHT_ELSEWHERE,
            PipelineStage.UNREACHABLE
        ]
        lead_counts = (
            db.session.query(Opportunity.assigned_to_id, func.count(Opportunity.id).label('cnt'))
            .filter(Opportunity.assigned_to_id.in_(candidate_ids))
            .filter(Opportunity.is_deleted == False)
            .filter(~Opportunity.pipeline_stage.in_(terminal_stages))
            .group_by(Opportunity.assigned_to_id)
            .subquery()
        )

        candidates_with_counts = (
            db.session.query(User, func.coalesce(lead_counts.c.cnt, 0).label('active_leads'))
            .outerjoin(lead_counts, User.id == lead_counts.c.assigned_to_id)
            .filter(User.id.in_(candidate_ids))
            .order_by(func.coalesce(lead_counts.c.cnt, 0).asc(), User.id.asc())
            .all()
        )

        # Pick candidate with available capacity, per the persisted mode.
        mode = 'lowest_count'
        try:
            from app.models import SystemSetting
            mode = SystemSetting.get('auto_assign_mode', 'lowest_count') or 'lowest_count'
        except Exception:
            mode = 'lowest_count'
        selected = None
        if mode == 'round_robin':
            pool_by_id = sorted(candidates_with_counts, key=lambda x: x[0].id)
            try:
                rr_index = int(SystemSetting.get('auto_assign_rr_index', '0') or 0)
            except Exception:
                rr_index = 0
            for offset in range(len(pool_by_id)):
                user, active_cnt = pool_by_id[(rr_index + offset) % len(pool_by_id)] if pool_by_id else (None, 0)
                if user is None:
                    break
                max_cap = user.max_lead_capacity if user.max_lead_capacity is not None else 30
                if active_cnt < max_cap:
                    selected = user
                    try:
                        SystemSetting.set('auto_assign_rr_index', str((rr_index + offset + 1) % len(pool_by_id)))
                        db.session.flush()
                    except Exception:
                        pass
                    break
        else:
            for user, active_cnt in candidates_with_counts:
                max_cap = user.max_lead_capacity if user.max_lead_capacity is not None else 30
                if active_cnt < max_cap:
                    selected = user
                    break

        if selected:
            logger.info(f"Auto-assigned lead to {selected.full_name} ({selected.role.value})")
        else:
            logger.warning("All auto-assign candidates have reached maximum capacity. Leaving lead unassigned.")
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
# Backblaze B2 Cloud Storage — call recording upload
# ---------------------------------------------------------------------------

def upload_recording_to_b2(local_path: str, filename: str, app=None) -> str | None:
    """
    Upload a call recording file to Backblaze B2 cloud storage via S3 API.

    Returns:
        str: Public B2 share link if upload succeeded.
        None: If B2 credentials are missing or upload failed.
    """
    app = _get_app(app)
    with app.app_context():
        from app.models import SystemSetting
        key_id = SystemSetting.get('b2_key_id', '').strip()
        app_key = SystemSetting.get('b2_application_key', '').strip()
        bucket = SystemSetting.get('b2_bucket_name', '').strip()
        endpoint = SystemSetting.get('b2_endpoint', '').strip() # e.g. https://s3.us-east-005.backblazeb2.com

    if not key_id or not app_key or not bucket or not endpoint:
        logger.warning('B2 credentials not fully configured — skipping cloud upload')
        return None

    try:
        import boto3
        from botocore.config import Config
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            config=Config(signature_version='s3v4')
        )
        
        from boto3.s3.transfer import TransferConfig
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'video/mp4' if filename.lower().endswith(('.mp4', '.mov', '.webm', '.mkv', '.avi', '.wmv')) else 'audio/mpeg'
        
        # B2 supports standard S3 upload_file.
        # We disable use_threads because boto3 spawning its own sub-threads 
        # from within our background thread can crash if the main WSGI request ends.
        s3.upload_file(
            Filename=local_path,
            Bucket=bucket,
            Key=filename,
            ExtraArgs={'ContentType': content_type},
            Config=TransferConfig(use_threads=False)
        )
        
        # In AWS SigV4, maximum presigned URL lifetime is 7 days (604800 seconds)
        try:
            share_link = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': filename},
                ExpiresIn=604800
            )
        except Exception:
            endpoint_cleaned = endpoint.rstrip('/')
            share_link = f"{endpoint_cleaned}/{bucket}/{filename}"
        
        logger.info(f'Recording uploaded to B2: {filename} → {share_link}')
        return share_link

    except Exception as e:
        logger.error(f'B2 upload failed for {filename}: {e}')
        raise Exception(f"B2 upload failed: {e}")


def generate_b2_presigned_url(filename: str, expires_in: int = 3600) -> str | None:
    """Generate a temporary signed URL for a private B2 recording."""
    try:
        from app.models import SystemSetting
        key_id = SystemSetting.get('b2_key_id', '').strip()
        app_key = SystemSetting.get('b2_application_key', '').strip()
        bucket = SystemSetting.get('b2_bucket_name', '').strip()
        endpoint = SystemSetting.get('b2_endpoint', '').strip()

        if not all([key_id, app_key, bucket, endpoint]):
            return None

        import boto3
        from botocore.config import Config
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            config=Config(signature_version='s3v4')
        )
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': filename},
            ExpiresIn=expires_in
        )
    except Exception as e:
        logger.warning(f"Could not generate presigned URL for {filename}: {e}")
        return None


def check_appointment_reminders(app=None):
    """
    Check upcoming appointments for 24h and 2h reminders.
    Runs every 10 minutes via APScheduler.
    """
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import Appointment, AppointmentStatus, Opportunity

        now = datetime.now(timezone.utc)
        t_24h = now + timedelta(hours=24)
        t_2h = now + timedelta(hours=2)

        # 24h reminders (appointments between now and 24 hours from now)
        appts_24h = Appointment.query.filter(
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
            Appointment.appointment_datetime <= t_24h,
            Appointment.appointment_datetime > now,
            Appointment.reminder_24h_sent == False,
            Appointment.is_deleted == False
        ).all()

        for appt in appts_24h:
            appt.reminder_24h_sent = True
            logger.info(f"Sent 24h reminder for Appointment #{appt.id}")

        # 2h reminders (appointments between now and 2 hours from now)
        appts_2h = Appointment.query.filter(
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
            Appointment.appointment_datetime <= t_2h,
            Appointment.appointment_datetime > now,
            Appointment.reminder_2h_sent == False,
            Appointment.is_deleted == False
        ).all()

        for appt in appts_2h:
            appt.reminder_2h_sent = True
            logger.info(f"Sent 2h reminder for Appointment #{appt.id}")

        db.session.commit()


def check_event_reminders(app=None):
    """
    Create in-app notifications for calendar Events whose reminder time
    has arrived. Runs every 5 minutes via APScheduler.

    An Event qualifies when: status is SCHEDULED, reminder_minutes is set,
    reminder_sent is False, and (start - reminder_minutes) <= now < start.
    Times are stored naive-UTC (frontends send ISO UTC), so a naive
    start_datetime is treated as UTC. Events that already started without
    a reminder being sent are marked sent (missed) so they are not
    re-checked forever. reminder_sent + an existing-notification check
    together guarantee exactly one notification per event.
    """
    from zoneinfo import ZoneInfo

    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import Event, Notification

        now = datetime.now(timezone.utc)
        dhaka = ZoneInfo("Asia/Dhaka")
        candidates = Event.query.filter(
            Event.reminder_minutes.isnot(None),
            Event.reminder_sent == False,
            Event.status == "SCHEDULED",
        ).all()

        created = 0
        for ev in candidates:
            start = ev.start_datetime
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            remind_at = start - timedelta(minutes=ev.reminder_minutes)
            if now < remind_at:
                continue  # reminder time has not arrived yet
            if now >= start:
                # Event already started — reminder window missed; mark sent
                # so this event is never re-checked.
                ev.reminder_sent = True
                continue
            owner = ev.resolved_owner()
            recipient_id = owner.id if owner else ev.created_by_id
            if not recipient_id:
                ev.reminder_sent = True
                continue
            # Duplicate guard: never create a second notification for the
            # same event, even if reminder_sent was reset concurrently.
            existing = Notification.query.filter_by(
                event_id=ev.id, type="EVENT_REMINDER"
            ).first()
            if existing:
                ev.reminder_sent = True
                continue
            start_dhaka = start.astimezone(dhaka).strftime("%d %b, %I:%M %p")
            lead_name = None
            if ev.lead is not None and ev.lead.contact is not None:
                lead_name = ev.lead.contact.full_name
            title = f"Reminder: {ev.title}"
            body = f"'{ev.title}' starts at {start_dhaka}."
            if lead_name:
                body += f" Lead: {lead_name}."
            db.session.add(Notification(
                user_id=recipient_id,
                title=title,
                body=body,
                type="EVENT_REMINDER",
                event_id=ev.id,
                lead_id=ev.lead_id,
            ))
            ev.reminder_sent = True
            created += 1
            logger.info(f"Event reminder sent for Event #{ev.id} to user #{recipient_id}")

        db.session.commit()
        if created:
            logger.info(f"check_event_reminders: {created} notification(s) created")


def retry_failed_webhooks(app=None):
    """
    Retry failed webhooks with exponential backoff.
    Runs every 5 minutes via APScheduler.
    """
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import WebhookRetry

        now = datetime.now(timezone.utc)
        retries = WebhookRetry.query.filter(
            WebhookRetry.status.in_(['PENDING', 'RETRYING']),
            WebhookRetry.next_retry_at <= now,
            WebhookRetry.retry_count < WebhookRetry.max_retries
        ).all()

        for r in retries:
            try:
                r.retry_count += 1
                r.status = 'RETRYING'
                process_meta_webhook(r.payload, app=app)
                r.status = 'SUCCESS'
                logger.info(f"Successfully retried webhook #{r.id}")
            except Exception as e:
                logger.error(f"Failed retry #{r.retry_count} for webhook #{r.id}: {e}")
                r.error_message = str(e)
                if r.retry_count >= r.max_retries:
                    r.status = 'FAILED'
                else:
                    backoff_minutes = 2 ** r.retry_count
                    r.next_retry_at = now + timedelta(minutes=backoff_minutes)
        db.session.commit()


def auto_update_scheduled_lead_statuses(app=None):
    """
    Time-based automated lead pipeline and stage updates:
    1. For scheduled appointments where appointment_datetime has passed:
       - If completed or debrief submitted: advances opportunity to VISIT_COMPLETED (if still in APPOINTMENT stage).
       - If passed > 4 hours and still in SCHEDULED/CONFIRMED status: flags as urgent debrief pending.
    2. For opportunities where next_action_deadline has passed:
       - Escalate priority to HIGH or URGENT so it triggers visual overdue badges and alerts.
    3. Runs every 5 minutes in APScheduler or on demand via /api/leads/auto-update-stages.
    """
    app = _get_app(app)
    with app.app_context():
        from app.extensions import db
        from app.models import Appointment, AppointmentStatus, Opportunity, PipelineStage, LeadPriority, PipelineHistory

        now = datetime.now(timezone.utc)
        stats = {
            "appointments_checked": 0,
            "stages_advanced": 0,
            "deadlines_flagged": 0
        }

        # 1. Check passed appointments
        passed_appts = Appointment.query.filter(
            Appointment.appointment_datetime <= now,
            Appointment.is_deleted == False
        ).all()

        stats["appointments_checked"] = len(passed_appts)

        for appt in passed_appts:
            opp = Opportunity.query.get(appt.opportunity_id)
            if not opp or opp.is_deleted:
                continue

            # If appointment was completed or debriefed, auto advance to VISIT_COMPLETED
            if appt.status == AppointmentStatus.COMPLETED or appt.debrief_submitted:
                if opp.pipeline_stage in (PipelineStage.APPOINTMENT_SCHEDULED, PipelineStage.APPOINTMENT_CONFIRMED):
                    old_stage = opp.pipeline_stage.value
                    opp.pipeline_stage = PipelineStage.VISIT_COMPLETED
                    if not opp.visit_date:
                        opp.visit_date = now

                    hist = PipelineHistory(
                        opportunity_id=opp.id,
                        from_stage=PipelineStage[old_stage],
                        to_stage=PipelineStage.VISIT_COMPLETED,
                        changed_by_id=appt.scheduled_by_id or 1,
                        changed_at=now,
                        notes="Auto-advanced to Visit Completed based on completed appointment time"
                    )
                    db.session.add(hist)
                    stats["stages_advanced"] += 1

            # If appointment was scheduled/confirmed and now > 4 hours passed without debrief:
            elif appt.status in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
                appt_dt = appt.appointment_datetime
                if appt_dt.tzinfo is None:
                    appt_dt = appt_dt.replace(tzinfo=timezone.utc)
                time_diff = (now - appt_dt).total_seconds()
                if time_diff > 4 * 3600:
                    if opp.priority != LeadPriority.URGENT:
                        opp.priority = LeadPriority.URGENT
                        stats["deadlines_flagged"] += 1

        # 2. Check next action deadline
        overdue_opps = Opportunity.query.filter(
            Opportunity.next_action_deadline < now,
            Opportunity.final_result.is_(None),
            Opportunity.is_deleted == False
        ).all()

        for opp in overdue_opps:
            if opp.priority in (LeadPriority.LOW, LeadPriority.MEDIUM):
                opp.priority = LeadPriority.HIGH
                stats["deadlines_flagged"] += 1

        db.session.commit()
        logger.info(f"[SCHEDULER] auto_update_scheduled_lead_statuses: {stats}")
        return stats



