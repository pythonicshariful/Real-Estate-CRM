"""FCM (Firebase Cloud Messaging) push notifications — HTTP v1 API.

Deploy 34. Sends push notifications to users' Android devices via the
FCM HTTP v1 API using a Google service-account JSON key. No extra
dependencies: the OAuth2 access token is obtained with the standard
service-account JWT flow (PyJWT + requests, both already installed).

Credentials: a service-account JSON file whose path comes from the
FCM_CREDENTIALS_FILE environment variable (falling back to the Flask
config key of the same name). When the variable is unset, the file is
missing/unreadable, or anything else goes wrong, push is DISABLED:
every public function logs and returns False/0 WITHOUT raising — a
push failure must never break lead ingestion, assignment, or reminders.

Public API:
    push_to_user(user, title, body, data=None) -> bool
    push_to_admins(title, body, data=None) -> int   (count sent)
    admin_recipients() -> [User]                    (active ADMINs with a token)
    notify_lead_assignment(recipient, lead_id, title, body)
        — in-app Notification row + push, for lead-assignment triggers.
"""
import json
import logging
import os
import time

import jwt as pyjwt
import requests

logger = logging.getLogger(__name__)

_TOKEN_URL = 'https://oauth2.googleapis.com/token'
_FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
_CHANNEL_ID = 'crm_alerts'
_HTTP_TIMEOUT = 10

# Module-level caches: parsed service account (keyed by file path) and
# the OAuth access token (with its expiry epoch).
_sa_cache = {'path': None, 'data': None}
_token_cache = {'access_token': None, 'expires_at': 0.0}


def _credentials_path():
    path = os.environ.get('FCM_CREDENTIALS_FILE')
    if not path:
        try:
            from flask import current_app, has_app_context
            if has_app_context():
                path = current_app.config.get('FCM_CREDENTIALS_FILE')
        except Exception:
            path = None
    return path or None


def _load_service_account():
    """Return the parsed service-account dict, or None when push is
    disabled (no/invalid credentials). Never raises."""
    path = _credentials_path()
    if not path:
        logger.debug('push disabled: FCM_CREDENTIALS_FILE is not set')
        return None
    if _sa_cache['path'] == path and _sa_cache['data'] is not None:
        return _sa_cache['data']
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        if not data.get('client_email') or not data.get('private_key') \
                or not data.get('project_id'):
            logger.info('push disabled: %s lacks client_email/private_key/project_id', path)
            return None
    except Exception as exc:
        logger.info('push disabled: cannot read FCM credentials %s (%s)', path, exc)
        return None
    _sa_cache['path'] = path
    _sa_cache['data'] = data
    return data


def _get_access_token(sa):
    """Service-account JWT flow → OAuth2 access token, cached until
    ~5 minutes before expiry. Returns None on any failure."""
    now = time.time()
    if _token_cache['access_token'] and now < _token_cache['expires_at'] - 300:
        return _token_cache['access_token']
    try:
        assertion = pyjwt.encode(
            {
                'iss': sa['client_email'],
                'scope': _FCM_SCOPE,
                'aud': _TOKEN_URL,
                'iat': int(now),
                'exp': int(now) + 3600,
            },
            sa['private_key'],
            algorithm='RS256',
        )
        resp = requests.post(
            _TOKEN_URL,
            data={
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': assertion,
            },
            timeout=_HTTP_TIMEOUT,
        )
        payload = resp.json()
        token = payload.get('access_token')
        if not token:
            logger.warning('push: token exchange returned no access_token: %s', payload)
            return None
        _token_cache['access_token'] = token
        _token_cache['expires_at'] = now + int(payload.get('expires_in', 3600))
        return token
    except Exception as exc:
        logger.warning('push: access-token exchange failed (%s)', exc)
        return None


def _is_unregistered(resp):
    """True when FCM says the registration token is gone (UNREGISTERED)."""
    if resp.status_code != 404:
        return False
    try:
        err = (resp.json() or {}).get('error') or {}
    except Exception:
        return False
    if err.get('status') == 'UNREGISTERED':
        return True
    for detail in err.get('details') or []:
        if isinstance(detail, dict) and detail.get('errorCode') == 'UNREGISTERED':
            return True
    return False


def _send(sa, access_token, fcm_token, title, body, data):
    """POST one message to FCM. Returns True, False, or 'unregistered'."""
    message = {
        'token': fcm_token,
        'notification': {'title': title, 'body': body},
        'android': {
            'priority': 'high',
            'notification': {'channel_id': _CHANNEL_ID},
        },
    }
    if data:
        message['data'] = {str(k): str(v) for k, v in data.items()}
    url = f"https://fcm.googleapis.com/v1/projects/{sa['project_id']}/messages:send"
    resp = requests.post(
        url,
        json={'message': message},
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=_HTTP_TIMEOUT,
    )
    if resp.status_code == 200:
        return True
    if _is_unregistered(resp):
        return 'unregistered'
    logger.warning('push: FCM send failed (%s): %s', resp.status_code, resp.text[:300])
    return False


def _clear_token(user):
    """Drop a dead FCM token from the user row (best effort)."""
    try:
        from app.extensions import db
        user.fcm_token = None
        db.session.commit()
        logger.info('push: cleared unregistered FCM token for user #%s', user.id)
    except Exception as exc:
        logger.warning('push: could not clear FCM token for user #%s (%s)',
                       getattr(user, 'id', '?'), exc)
        try:
            from app.extensions import db
            db.session.rollback()
        except Exception:
            pass


def push_to_user(user, title, body, data=None):
    """Send one push to a user's registered device. Returns True only
    when FCM accepted the message. Never raises."""
    try:
        if user is None or not getattr(user, 'fcm_token', None):
            logger.debug('push: user %s has no FCM token — skipped',
                         getattr(user, 'id', None))
            return False
        sa = _load_service_account()
        if sa is None:
            return False
        access_token = _get_access_token(sa)
        if not access_token:
            return False
        result = _send(sa, access_token, user.fcm_token, title, body, data)
        if result == 'unregistered':
            _clear_token(user)
            return False
        return bool(result)
    except Exception as exc:
        logger.warning('push: push_to_user failed (%s)', exc)
        return False


def admin_recipients():
    """Active ADMIN users who have a registered FCM token."""
    try:
        from app.models import User, UserRole
        return (User.query
                .filter(User.role == UserRole.ADMIN,
                        User.is_active == True,  # noqa: E712
                        User.fcm_token.isnot(None),
                        User.fcm_token != '')
                .all())
    except Exception as exc:
        logger.warning('push: admin_recipients query failed (%s)', exc)
        return []


def push_to_admins(title, body, data=None):
    """Send a push to every active ADMIN with a token. Returns the
    number of messages FCM accepted. Never raises."""
    sent = 0
    for admin in admin_recipients():
        if push_to_user(admin, title, body, data=data):
            sent += 1
    return sent


def notify_user(recipient, type_, title, body, data=None, lead_id=None,
                event_id=None):
    """Generic trigger helper: store an in-app Notification row for the
    recipient and fire the matching FCM push. Failure-isolated — never
    raises, so callers (message sending, assignment, ingestion) are
    never affected by a notification/push problem."""
    if recipient is None:
        return
    try:
        from app.extensions import db
        from app.models import Notification
        db.session.add(Notification(
            user_id=recipient.id,
            title=title,
            body=body,
            type=type_,
            lead_id=lead_id,
            event_id=event_id,
        ))
        db.session.commit()
    except Exception as exc:
        logger.warning('push: could not store %s notification (%s)', type_, exc)
        try:
            from app.extensions import db
            db.session.rollback()
        except Exception:
            pass
    push_data = dict(data) if data else {'type': type_}
    push_data.setdefault('type', type_)
    if lead_id is not None:
        push_data.setdefault('lead_id', lead_id)
    if event_id is not None:
        push_data.setdefault('event_id', event_id)
    push_to_user(recipient, title, body, data=push_data)


def notify_lead_assignment(recipient, lead_id, title, body):
    """Lead-assignment trigger helper: store the in-app Notification
    row and fire the matching push. Used by the Meta-ingestion and
    manual-assignment triggers so both behave identically.
    Failure-isolated — never raises."""
    notify_user(recipient, 'LEAD_ASSIGNED', title, body,
                data={'lead_id': lead_id, 'type': 'LEAD_ASSIGNED'},
                lead_id=lead_id)
