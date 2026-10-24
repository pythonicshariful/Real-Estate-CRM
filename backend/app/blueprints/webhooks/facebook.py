"""
Facebook / Meta integration — OAuth connect + Lead Form field import.

Flow
----
1.  Admin clicks "Connect with Facebook" on Settings → Meta tab.
2.  Frontend calls  GET /api/webhooks/facebook/oauth/start
    → returns the Facebook OAuth dialog URL (server builds it from the
      App ID / App Secret stored in SystemSetting or the environment).
3.  Facebook redirects back to  GET /api/webhooks/facebook/oauth/callback?code=...
    → we exchange the code for a user token, list the Pages, pick the first
      one (or the configured one), exchange for a long-lived Page Access Token
      and store it. Then we pull the Page's Lead Forms.
4.  Admin reviews the form questions and imports them into the CRM's lead
    questionnaire so the same questions appear on every lead that arrives.

Demo mode
---------
Without real App credentials nothing can be exchanged with Facebook, so
POST /api/webhooks/facebook/demo-connect seeds a realistic demo connection
(1 page, 2 lead forms with real-looking questions) so the whole UI can be
exercised offline. It is clearly flagged as demo everywhere.
"""

import os
import secrets
import urllib.parse

import requests
from flask import request, jsonify, current_app, redirect

from . import webhooks_bp
from ...extensions import db
from ...models import SystemSetting, UserRole, LeadQuestionnaireQuestion
from ...utils.rbac import require_role
from flask_jwt_extended import jwt_required

GRAPH = "https://graph.facebook.com/v19.0"
OAUTH_DIALOG = "https://www.facebook.com/v19.0/dialog/oauth"
TOKEN_URL = f"{GRAPH}/oauth/access_token"

KEYS = {
    'app_id': 'facebook_app_id',
    'app_secret': 'facebook_app_secret',
    'redirect_uri': 'facebook_redirect_uri',
    'page_id': 'facebook_page_id',
    'page_name': 'facebook_page_name',
    'page_token': 'facebook_page_access_token',
    'connected_at': 'facebook_connected_at',
    'mode': 'facebook_connection_mode',        # 'live' | 'demo'
    'forms': 'facebook_lead_forms_json',
    'last_sync': 'facebook_last_sync',
}


def _get(key, default=''):
    return SystemSetting.get(KEYS.get(key, key), default) or ''


def _set(key, value):
    SystemSetting.set(KEYS.get(key, key), '' if value is None else str(value))


def _app_credentials():
    app_id = _get('app_id') or current_app.config.get('META_APP_ID', '')
    app_secret = _get('app_secret') or current_app.config.get('META_APP_SECRET', '')
    return app_id, app_secret


def _default_redirect_uri():
    configured = _get('redirect_uri')
    if configured:
        return configured
    base = request.host_url.rstrip('/')
    return f"{base}/api/webhooks/facebook/oauth/callback"


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@webhooks_bp.route('/facebook/status', methods=['GET'])
@jwt_required()
def facebook_status():
    """Everything the Settings UI needs to render the connection card."""
    import json
    app_id, app_secret = _app_credentials()
    forms = []
    raw_forms = _get('forms')
    if raw_forms:
        try:
            forms = json.loads(raw_forms)
        except Exception:
            forms = []

    return jsonify({
        'connected': bool(_get('page_token')),
        'mode': _get('mode') or ('live' if _get('page_token') else ''),
        'app_id': app_id,
        'has_app_secret': bool(app_secret),
        'has_credentials': bool(app_id and app_secret),
        'page_id': _get('page_id'),
        'page_name': _get('page_name'),
        'connected_at': _get('connected_at'),
        'last_sync': _get('last_sync'),
        'redirect_uri': _default_redirect_uri(),
        'forms': forms,
        'form_count': len(forms),
    }), 200


@webhooks_bp.route('/facebook/credentials', methods=['PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def facebook_credentials():
    """Store the Facebook App ID / Secret / redirect URI."""
    data = request.get_json() or {}
    if 'app_id' in data:
        _set('app_id', (data.get('app_id') or '').strip())
    if 'app_secret' in data and data.get('app_secret') not in (None, ''):
        _set('app_secret', data['app_secret'].strip())
    if 'redirect_uri' in data:
        _set('redirect_uri', (data.get('redirect_uri') or '').strip())
    return jsonify({'success': True, 'message': 'Facebook credentials saved.'}), 200


# ---------------------------------------------------------------------------
# Real OAuth
# ---------------------------------------------------------------------------

@webhooks_bp.route('/facebook/oauth/start', methods=['GET'])
@jwt_required()
@require_role(UserRole.ADMIN)
def facebook_oauth_start():
    """Return the Facebook OAuth dialog URL the browser should visit."""
    app_id, app_secret = _app_credentials()
    if not (app_id and app_secret):
        return jsonify({
            'success': False,
            'needs_credentials': True,
            'message': 'Add your Facebook App ID and App Secret first '
                       '(developers.facebook.com → your app → Settings → Basic).',
        }), 400

    state = secrets.token_urlsafe(24)
    _set('oauth_state', state)

    params = {
        'client_id': app_id,
        'redirect_uri': _default_redirect_uri(),
        'state': state,
        'response_type': 'code',
        # Page management + lead retrieval + form definitions
        'scope': 'pages_show_list,pages_read_engagement,pages_manage_metadata,'
                 'leads_retrieval,pages_manage_ads,business_management',
    }
    return jsonify({
        'success': True,
        'auth_url': f"{OAUTH_DIALOG}?{urllib.parse.urlencode(params)}",
        'redirect_uri': _default_redirect_uri(),
    }), 200


@webhooks_bp.route('/facebook/oauth/callback', methods=['GET'])
def facebook_oauth_callback():
    """
    Facebook redirects here with ?code=... . We exchange it, store the Page
    token and return an HTML page that closes itself / bounces back to Settings.
    """
    error = request.args.get('error_description') or request.args.get('error')
    if error:
        return _callback_html(False, f"Facebook returned an error: {error}")

    code = request.args.get('code')
    state = request.args.get('state')
    expected_state = _get('oauth_state')
    if not code:
        return _callback_html(False, 'Missing authorization code.')
    if expected_state and state != expected_state:
        return _callback_html(False, 'Invalid OAuth state — please retry the connection.')

    app_id, app_secret = _app_credentials()
    if not (app_id and app_secret):
        return _callback_html(False, 'Facebook App credentials are not configured.')

    try:
        # 1. code → short-lived user token
        r = requests.get(TOKEN_URL, params={
            'client_id': app_id,
            'client_secret': app_secret,
            'redirect_uri': _default_redirect_uri(),
            'code': code,
        }, timeout=20)
        payload = r.json()
        if 'access_token' not in payload:
            return _callback_html(False, f"Token exchange failed: {payload}")

        user_token = payload['access_token']

        # 2. list pages the admin manages
        pr = requests.get(f"{GRAPH}/me/accounts", params={
            'access_token': user_token,
            'fields': 'id,name,access_token',
        }, timeout=20).json()

        pages = pr.get('data', [])
        if not pages:
            return _callback_html(
                False,
                'No Facebook Page found for this account. '
                'You need to be an admin of at least one Page.'
            )

        configured_page = _get('page_id')
        page = next((p for p in pages if p['id'] == configured_page), pages[0])

        _set('page_id', page['id'])
        _set('page_name', page.get('name', ''))
        _set('page_token', page.get('access_token', ''))
        _set('connected_at', _now())
        _set('mode', 'live')
        _set('oauth_state', '')

        # 3. pull lead forms for that page
        sync_info = _sync_lead_forms(page['id'], page.get('access_token', ''))

        return _callback_html(
            True,
            f"Connected to Page “{page.get('name','')}”. {sync_info}",
        )
    except requests.RequestException as exc:
        return _callback_html(False, f"Network error talking to Facebook: {exc}")
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error(f'FB OAuth error: {exc}')
        return _callback_html(False, f"Unexpected error: {exc}")


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _sync_lead_forms(page_id, page_token):
    """Fetch the Page's lead forms + their questions and cache them."""
    import json
    try:
        resp = requests.get(f"{GRAPH}/{page_id}/leadgen_forms", params={
            'access_token': page_token,
            'fields': 'id,name,status,questions,locale,created_time',
            'limit': 50,
        }, timeout=20).json()

        if 'error' in resp:
            return f"Could not read lead forms: {resp['error'].get('message','unknown error')}"

        forms = []
        for f in resp.get('data', []):
            forms.append({
                'id': f.get('id'),
                'name': f.get('name') or 'Untitled form',
                'status': f.get('status'),
                'locale': f.get('locale'),
                'created_time': f.get('created_time'),
                'questions': [
                    {
                        'key': q.get('key'),
                        'label': q.get('label'),
                        'type': q.get('type'),
                        'options': [o.get('value') for o in (q.get('options') or [])],
                    }
                    for q in (f.get('questions') or [])
                ],
            })

        _set('forms', json.dumps(forms))
        _set('last_sync', _now())
        return f"Found {len(forms)} lead form(s)."
    except Exception as exc:  # noqa: BLE001
        return f"Form sync failed: {exc}"


@webhooks_bp.route('/facebook/sync-forms', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def facebook_sync_forms():
    """Re-pull lead forms from the connected Page."""
    page_id = _get('page_id')
    page_token = _get('page_token')
    if not (page_id and page_token):
        return jsonify({'success': False, 'message': 'Facebook Page is not connected yet.'}), 400

    if _get('mode') == 'demo':
        return jsonify({'success': True, 'message': 'Demo connection — forms are fixed.',
                        'forms': _demo_forms()}), 200

    msg = _sync_lead_forms(page_id, page_token)
    import json
    return jsonify({'success': True, 'message': msg,
                    'forms': json.loads(_get('forms') or '[]')}), 200


@webhooks_bp.route('/facebook/disconnect', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def facebook_disconnect():
    for k in ('page_token', 'page_id', 'page_name', 'connected_at', 'mode', 'forms', 'last_sync'):
        _set(k, '')
    return jsonify({'success': True, 'message': 'Facebook disconnected.'}), 200


# ---------------------------------------------------------------------------
# Demo connect (no real credentials required)
# ---------------------------------------------------------------------------

def _demo_forms():
    return [
        {
            'id': 'demo_form_residential',
            'name': 'Residential Plot — Dream Home Campaign',
            'status': 'ACTIVE',
            'locale': 'en_US',
            'created_time': _now(),
            'demo': True,
            'questions': [
                {'key': 'full_name', 'label': 'Full Name', 'type': 'FULL_NAME', 'options': []},
                {'key': 'phone_number', 'label': 'Phone Number', 'type': 'PHONE', 'options': []},
                {'key': 'email', 'label': 'Email', 'type': 'EMAIL', 'options': []},
                {'key': 'profession', 'label': 'Your Profession', 'type': 'CUSTOM',
                 'options': ['Businessman', 'Service Holder', 'Doctor', 'Engineer', 'Teacher', 'Other']},
                {'key': 'budget_range', 'label': 'Budget Range', 'type': 'CUSTOM',
                 'options': ['25-50 Lakhs', '50-80 Lakhs', '80 Lakhs - 1 Crore', '1 Crore+']},
                {'key': 'plot_size', 'label': 'Preferred Plot Size', 'type': 'CUSTOM',
                 'options': ['3 Katha', '5 Katha', '7 Katha', '10 Katha']},
                {'key': 'preferred_location', 'label': 'Preferred Location', 'type': 'CUSTOM',
                 'options': ['Bashundhara R/A', 'Purbachal', 'Uttara', 'Mirpur', 'Savar']},
                {'key': 'purchasing_timeline', 'label': 'When do you plan to buy?', 'type': 'CUSTOM',
                 'options': ['Immediately', 'Within 3 months', 'Within 6 months', 'Just exploring']},
                {'key': 'contact_time', 'label': 'Best time to call you', 'type': 'CUSTOM',
                 'options': ['Morning (9am-12pm)', 'Afternoon (12pm-4pm)', 'Evening (4pm-8pm)']},
                {'key': 'service_type', 'label': 'Service Interest', 'type': 'CUSTOM',
                 'options': ['Residential Plot', 'Apartment', 'Commercial Space']},
            ],
        },
        {
            'id': 'demo_form_apartment',
            'name': 'Apartment Launch — Elite Society',
            'status': 'ACTIVE',
            'locale': 'en_US',
            'created_time': _now(),
            'demo': True,
            'questions': [
                {'key': 'full_name', 'label': 'Full Name', 'type': 'FULL_NAME', 'options': []},
                {'key': 'phone_number', 'label': 'Phone Number', 'type': 'PHONE', 'options': []},
                {'key': 'email', 'label': 'Email', 'type': 'EMAIL', 'options': []},
                {'key': 'unit_type', 'label': 'Unit Type', 'type': 'CUSTOM',
                 'options': ['2 BHK', '3 BHK', '4 BHK', 'Duplex']},
                {'key': 'floor_preference', 'label': 'Floor Preference', 'type': 'CUSTOM',
                 'options': ['Ground', '1-5', '6-10', '10+']},
                {'key': 'budget_range', 'label': 'Budget Range', 'type': 'CUSTOM',
                 'options': ['50-80 Lakhs', '80 Lakhs - 1.5 Crore', '1.5 Crore+']},
                {'key': 'contact_time', 'label': 'Best time to call you', 'type': 'CUSTOM',
                 'options': ['Morning (9am-12pm)', 'Afternoon (12pm-4pm)', 'Evening (4pm-8pm)']},
            ],
        },
    ]


@webhooks_bp.route('/facebook/demo-connect', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def facebook_demo_connect():
    """
    Simulate a successful Facebook connection without any App credentials.
    Lets you exercise the full UI + field-import flow offline.
    """
    import json
    _set('page_id', 'demo_page_100000000000001')
    _set('page_name', 'Southeast Landmark Properties (Demo Page)')
    _set('page_token', 'DEMO_TOKEN_NOT_A_REAL_TOKEN')
    _set('connected_at', _now())
    _set('mode', 'demo')
    _set('last_sync', _now())
    forms = _demo_forms()
    _set('forms', json.dumps(forms))
    return jsonify({
        'success': True,
        'message': f"Demo connection established with {len(forms)} lead form(s).",
        'forms': forms,
    }), 200


# ---------------------------------------------------------------------------
# Import form questions into the CRM questionnaire
# ---------------------------------------------------------------------------

@webhooks_bp.route('/facebook/forms', methods=['GET'])
@jwt_required()
def facebook_forms():
    import json
    raw = _get('forms')
    forms = []
    if raw:
        try:
            forms = json.loads(raw)
        except Exception:
            forms = []
    return jsonify({'connected': bool(_get('page_token')), 'mode': _get('mode'),
                    'forms': forms}), 200


@webhooks_bp.route('/facebook/import-form/<form_id>', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def facebook_import_form(form_id):
    """
    Turn a Facebook lead form's questions into CRM questionnaire questions so
    the exact same questions are fetched/asked on the lead inside the CRM.
    """
    import json
    raw = _get('forms')
    try:
        forms = json.loads(raw) if raw else []
    except Exception:
        forms = []

    form = next((f for f in forms if f.get('id') == form_id), None)
    if not form:
        return jsonify({'success': False, 'message': f'Form {form_id} not found. Sync first.'}), 404

    import re

    skip_types = {'FULL_NAME', 'PHONE', 'EMAIL', 'FIRST_NAME', 'LAST_NAME'}
    created, updated, skipped = [], [], []

    max_order = db.session.query(db.func.max(LeadQuestionnaireQuestion.order_index)).scalar() or 0

    for q in form.get('questions', []):
        label = (q.get('label') or '').strip()
        if not label:
            continue
        if (q.get('type') or '').upper() in skip_types:
            skipped.append(label)          # already native lead fields
            continue

        existing = LeadQuestionnaireQuestion.query.filter(
            db.func.lower(LeadQuestionnaireQuestion.question_text) == label.lower()
        ).first()

        options = q.get('options') or []
        field_type = 'select' if options else 'text'

        if existing:
            existing.field_type = field_type
            existing.options = options or []
            existing.is_active = True
            updated.append(label)
        else:
            key = q.get('key') or re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
            # question_key must be unique
            base_key, n = key, 1
            while LeadQuestionnaireQuestion.query.filter_by(question_key=key).first():
                n += 1
                key = f"{base_key}_{n}"
            max_order += 1
            db.session.add(LeadQuestionnaireQuestion(
                question_key=key,
                question_text=label,
                field_type=field_type,
                options=options or [],
                order_index=max_order,
                is_active=True,
                is_required=False,
            ))
            created.append(label)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Imported “{form.get('name')}”: {len(created)} new, {len(updated)} updated, "
                   f"{len(skipped)} skipped (native fields).",
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'form': form,
    }), 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _callback_html(success, message):
    """Small landing page for the OAuth popup/redirect."""
    colour = '#10b981' if success else '#ef4444'
    icon = '✓' if success else '✕'
    title = 'Facebook connected' if success else 'Connection failed'
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
  body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
       font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;}}
  .card{{max-width:520px;padding:40px;border-radius:20px;background:rgba(255,255,255,.05);
        border:1px solid rgba(255,255,255,.1);text-align:center;}}
  .badge{{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;
         margin:0 auto 20px;font-size:30px;background:{colour}22;color:{colour};border:1px solid {colour}55;}}
  h1{{font-size:20px;margin:0 0 10px;}}
  p{{font-size:14px;line-height:1.6;color:#94a3b8;margin:0 0 24px;}}
  a{{display:inline-block;padding:12px 24px;border-radius:12px;background:#0F766E;color:#fff;
    text-decoration:none;font-weight:600;font-size:14px;}}
</style></head>
<body><div class="card">
  <div class="badge">{icon}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <a href="/settings.html#meta">Back to Settings</a>
</div>
<script>
  try {{ if (window.opener) {{ window.opener.postMessage({{type:'facebook-connected'}}, '*'); }} }}
  catch (e) {{}}
  setTimeout(function () {{ location.href = '/settings.html#meta'; }}, 2600);
</script>
</body></html>"""
    return html, (200 if success else 400), {'Content-Type': 'text/html; charset=utf-8'}
