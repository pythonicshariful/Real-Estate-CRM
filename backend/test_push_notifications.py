"""Deploy 34 checks — FCM push notifications (backend).

Covers:
- POST/DELETE /api/users/me/fcm-token (save, clear, 401 unauthenticated,
  400 empty token; token never exposed in /api/auth/me)
- push disabled when FCM_CREDENTIALS_FILE is unset (returns False/0,
  no network call, no exception)
- with requests mocked at the app.push level: a send produces the
  correct FCM HTTP v1 payload (notification + stringified data +
  android channel_id crm_alerts), and an UNREGISTERED response clears
  the stored token
- Meta ingestion of a NEW lead with an auto-assigned owner creates
  exactly one LEAD_ASSIGNED Notification and one push; re-ingesting
  the same lead (dedupe/merge path) creates none
- manual reassign to a different owner fires one notification + push
  (reassign to the same owner, or an admin assigning to themself, none)
- sending an internal message creates exactly one MESSAGE Notification
  for the recipient (title = sender name, body = 120-char preview) and
  one push; the sender gets none

Run: venv/bin/python test_push_notifications.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import json
import os
import sys
import tempfile

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

import bcrypt
from unittest.mock import patch, MagicMock

from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Contact, Opportunity, Notification
from app.tasks import process_meta_webhook
import app.push as push

app = create_app('testing')
app.config['TESTING'] = True
client = app.test_client()

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f'  PASS {name}')
    else:
        failed += 1
        print(f'  FAIL {name}' + (f' — {detail}' if detail else ''))


def mk_user(name, email, role, fcm_token=None):
    u = User(full_name=name, email=email,
             password_hash=bcrypt.hashpw(b'Pass@123', bcrypt.gensalt()).decode(),
             role=role, is_active=True, fcm_token=fcm_token)
    db.session.add(u)
    db.session.commit()
    return u


def mk_jwt(u):
    return create_access_token(identity=str(u.id),
                               additional_claims={'role': u.role.value})


def hdr(tok):
    return {'Authorization': f'Bearer {tok}'}


# ---------------------------------------------------------------------------
# Fake HTTP layer for app.push (token exchange + FCM send)
# ---------------------------------------------------------------------------
class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


FCM_CALLS = []          # recorded sends: list of (url, json, headers)
TOKEN_CALLS = []        # recorded OAuth exchanges: list of data dicts
FCM_MODE = {'mode': 'ok'}


def fake_post(url, data=None, json=None, headers=None, timeout=None):
    if url == 'https://oauth2.googleapis.com/token':
        TOKEN_CALLS.append(data or {})
        return FakeResp(200, {'access_token': 'ya29.fake', 'expires_in': 3600})
    if 'fcm.googleapis.com' in url:
        FCM_CALLS.append((url, json, headers or {}))
        if FCM_MODE['mode'] == 'unregistered':
            return FakeResp(404, {'error': {
                'code': 404, 'status': 'NOT_FOUND',
                'details': [{'@type': 'type.googleapis.com/google.firebase.fcm.v1.FcmError',
                             'errorCode': 'UNREGISTERED'}]}})
        return FakeResp(200, {'name': 'projects/test-project/messages/1'})
    raise AssertionError(f'unexpected POST {url}')


def make_sa_file():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    sa = {'type': 'service_account', 'project_id': 'test-project',
          'client_email': 'push@test-project.iam.gserviceaccount.com',
          'private_key': pem}
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as fh:
        json.dump(sa, fh)
    return path


def reset_push_caches():
    push._sa_cache.update({'path': None, 'data': None})
    push._token_cache.update({'access_token': None, 'expires_at': 0.0})


def use_fcm(path):
    os.environ['FCM_CREDENTIALS_FILE'] = path
    reset_push_caches()


def disable_fcm():
    os.environ.pop('FCM_CREDENTIALS_FILE', None)
    app.config['FCM_CREDENTIALS_FILE'] = None
    reset_push_caches()


def notif_count(user_id, type_):
    return Notification.query.filter_by(user_id=user_id, type=type_).count()


def main():
    sa_path = make_sa_file()
    with app.app_context():
        db.create_all()
        disable_fcm()

        # ================= A. token endpoints =================
        u1 = mk_user('Token User', 'token34@test.com', UserRole.ADMIN)
        tok1 = mk_jwt(u1)

        r = client.post('/api/users/me/fcm-token', json={'token': 'x'})
        check('POST fcm-token without auth → 401', r.status_code == 401,
              f'status={r.status_code}')

        r = client.post('/api/users/me/fcm-token', json={'token': 'dev-token-1'},
                        headers=hdr(tok1))
        check('POST fcm-token → 200 {ok: true}',
              r.status_code == 200 and r.get_json() == {'ok': True},
              f'status={r.status_code} body={r.get_json()}')
        db.session.expire_all()
        check('token stored on the user row',
              User.query.get(u1.id).fcm_token == 'dev-token-1')

        r = client.get('/api/auth/me', headers=hdr(tok1))
        check('fcm_token NOT exposed in /api/auth/me',
              r.status_code == 200 and 'fcm_token' not in r.get_json())

        r = client.post('/api/users/me/fcm-token', json={}, headers=hdr(tok1))
        check('POST fcm-token with missing token → 400', r.status_code == 400)
        r = client.post('/api/users/me/fcm-token', json={'token': '  '},
                        headers=hdr(tok1))
        check('POST fcm-token with blank token → 400', r.status_code == 400)
        db.session.expire_all()
        check('rejected saves did not clobber the stored token',
              User.query.get(u1.id).fcm_token == 'dev-token-1')

        r = client.delete('/api/users/me/fcm-token', headers=hdr(tok1))
        check('DELETE fcm-token → 200 {ok: true}',
              r.status_code == 200 and r.get_json() == {'ok': True})
        db.session.expire_all()
        check('token cleared after DELETE',
              User.query.get(u1.id).fcm_token is None)

        # ================= B. push disabled =================
        db.session.expire_all()
        u1 = User.query.get(u1.id)
        u1.fcm_token = 'dev-token-1'
        db.session.commit()
        spy = MagicMock(side_effect=AssertionError('network must not be called'))
        with patch('app.push.requests.post', spy):
            res = push.push_to_user(u1, 'T', 'B')
            admins_res = push.push_to_admins('T', 'B')
        check('push_to_user returns False when credentials unset', res is False)
        check('push_to_admins returns 0 when credentials unset', admins_res == 0)
        check('no HTTP attempted while push disabled', spy.call_count == 0)

        # ================= C. payload shape =================
        use_fcm(sa_path)
        FCM_CALLS.clear(); TOKEN_CALLS.clear(); FCM_MODE['mode'] = 'ok'
        with patch('app.push.requests.post', side_effect=fake_post):
            res = push.push_to_user(u1, 'Hello', 'World',
                                    data={'lead_id': 42, 'type': 'LEAD_ASSIGNED'})
        check('push_to_user returns True on FCM 200', res is True)
        check('exactly one FCM send attempted', len(FCM_CALLS) == 1)
        if FCM_CALLS:
            url, payload, headers = FCM_CALLS[0]
            check('send URL is the v1 project endpoint',
                  url == 'https://fcm.googleapis.com/v1/projects/test-project/messages:send',
                  url)
            check('Authorization header carries the access token',
                  headers.get('Authorization') == 'Bearer ya29.fake')
            msg = (payload or {}).get('message') or {}
            check('message.token is the user device token',
                  msg.get('token') == 'dev-token-1')
            check('message.notification carries title/body',
                  msg.get('notification') == {'title': 'Hello', 'body': 'World'})
            check('message.data values are stringified',
                  msg.get('data') == {'lead_id': '42', 'type': 'LEAD_ASSIGNED'},
                  str(msg.get('data')))
            check('android block sets high priority + crm_alerts channel',
                  msg.get('android') == {'priority': 'high',
                                         'notification': {'channel_id': 'crm_alerts'}})
        check('exactly one OAuth token exchange happened', len(TOKEN_CALLS) == 1)
        if TOKEN_CALLS:
            import jwt as pyjwt
            data = TOKEN_CALLS[0]
            check('token exchange uses the jwt-bearer grant',
                  data.get('grant_type') == 'urn:ietf:params:oauth:grant-type:jwt-bearer')
            claims = pyjwt.decode(data.get('assertion', ''),
                                  options={'verify_signature': False})
            check('assertion iss/scope/aud are the FCM service-account claims',
                  claims.get('iss') == 'push@test-project.iam.gserviceaccount.com'
                  and claims.get('scope') == 'https://www.googleapis.com/auth/firebase.messaging'
                  and claims.get('aud') == 'https://oauth2.googleapis.com/token',
                  str(claims))

        # ================= D. UNREGISTERED clears token =================
        FCM_MODE['mode'] = 'unregistered'
        with patch('app.push.requests.post', side_effect=fake_post):
            res = push.push_to_user(u1, 'T', 'B')
        check('push_to_user returns False on UNREGISTERED', res is False)
        db.session.expire_all()
        check('UNREGISTERED cleared the stored token',
              User.query.get(u1.id).fcm_token is None)
        FCM_MODE['mode'] = 'ok'

        # ================= E. meta ingestion trigger =================
        owner = mk_user('Push Owner', 'owner34@test.com', UserRole.LEAD_OWNER,
                        fcm_token='owner-device-token')
        payload = {'entry': [{'changes': [{'field': 'leadgen', 'value': {
            'leadgen_id': 'PUSHLEAD1', 'form_id': 'FORMX',
            'field_data': [
                {'name': 'full_name', 'values': ['Push Test Lead']},
                {'name': 'phone_number', 'values': ['+8801777000111']},
            ]}}]}]}
        FCM_CALLS.clear()
        with patch('app.push.requests.post', side_effect=fake_post):
            processed = process_meta_webhook(payload, app=app)
        check('meta webhook processed the new lead', processed == 1,
              f'processed={processed}')
        contact = Contact.query.filter_by(facebook_lead_id='PUSHLEAD1').first()
        opp = Opportunity.query.filter_by(contact_id=contact.id).first() if contact else None
        check('opportunity auto-assigned to the only owner',
              bool(opp) and opp.assigned_to_id == owner.id)
        rows = Notification.query.filter_by(user_id=owner.id, type='LEAD_ASSIGNED').all()
        check('exactly one LEAD_ASSIGNED notification for the owner',
              len(rows) == 1, f'count={len(rows)}')
        if rows and opp:
            check('notification points at the new lead',
                  rows[0].lead_id == opp.id and rows[0].title == 'New lead assigned'
                  and 'Push Test Lead' in (rows[0].body or ''))
        owner_sends = [c for c in FCM_CALLS
                       if (c[1] or {}).get('message', {}).get('token') == 'owner-device-token']
        check('exactly one push sent to the owner device', len(owner_sends) == 1,
              f'sends={len(owner_sends)}')
        if owner_sends:
            d = owner_sends[0][1]['message'].get('data') or {}
            check('owner push data carries lead_id + type',
                  d.get('type') == 'LEAD_ASSIGNED' and d.get('lead_id') == str(opp.id),
                  str(d))

        with patch('app.push.requests.post', side_effect=fake_post):
            process_meta_webhook(payload, app=app)
        check('re-ingesting the same lead creates no new notification',
              notif_count(owner.id, 'LEAD_ASSIGNED') == 1)
        check('re-ingesting the same lead sends no new push',
              len([c for c in FCM_CALLS
                   if (c[1] or {}).get('message', {}).get('token') == 'owner-device-token']) == 1)

        # ================= F. manual reassign trigger =================
        admin = mk_user('Assign Admin', 'admin34@test.com', UserRole.ADMIN)
        owner_b = mk_user('Owner B', 'ownerb34@test.com', UserRole.LEAD_OWNER,
                          fcm_token='ownerb-device-token')
        c2 = Contact(full_name='Reassign Client', phone_raw='01700000901',
                     phone_normalized='01700000901', source='Test', is_deleted=False)
        db.session.add(c2)
        db.session.commit()
        opp2 = Opportunity(contact_id=c2.id, assigned_to_id=owner.id)
        db.session.add(opp2)
        db.session.commit()

        FCM_CALLS.clear()
        tok_admin = mk_jwt(admin)
        with patch('app.push.requests.post', side_effect=fake_post):
            r = client.put(f'/api/leads/{opp2.id}/reassign',
                           json={'assigned_to_id': owner_b.id}, headers=hdr(tok_admin))
        check('reassign request succeeds', r.status_code == 200,
              f'status={r.status_code}')
        rows_b = Notification.query.filter_by(user_id=owner_b.id, type='LEAD_ASSIGNED').all()
        check('reassign created one LEAD_ASSIGNED notification for the new owner',
              len(rows_b) == 1 and rows_b[0].lead_id == opp2.id
              and rows_b[0].title == 'Lead assigned to you'
              and 'Reassign Client' in (rows_b[0].body or ''),
              f'count={len(rows_b)}')
        b_sends = [c for c in FCM_CALLS
                   if (c[1] or {}).get('message', {}).get('token') == 'ownerb-device-token']
        check('reassign sent exactly one push to the new owner', len(b_sends) == 1)

        with patch('app.push.requests.post', side_effect=fake_post):
            r = client.put(f'/api/leads/{opp2.id}/reassign',
                           json={'assigned_to_id': owner_b.id}, headers=hdr(tok_admin))
        check('reassign to the SAME owner fires nothing new',
              r.status_code == 200 and notif_count(owner_b.id, 'LEAD_ASSIGNED') == 1
              and len([c for c in FCM_CALLS
                       if (c[1] or {}).get('message', {}).get('token') == 'ownerb-device-token']) == 1)

        with patch('app.push.requests.post', side_effect=fake_post):
            r = client.put(f'/api/leads/{opp2.id}/reassign',
                           json={'assigned_to_id': admin.id}, headers=hdr(tok_admin))
        check('admin assigning to themself gets no notification',
              r.status_code == 200 and notif_count(admin.id, 'LEAD_ASSIGNED') == 0)

        # ================= G. internal message trigger =================
        sender = mk_user('Sender Person', 'sender34@test.com', UserRole.LEAD_OWNER)
        recip = mk_user('Recip Person', 'recip34@test.com', UserRole.LEAD_OWNER,
                        fcm_token='recip-device-token')
        tok_sender = mk_jwt(sender)
        long_body = 'M' * 200
        FCM_CALLS.clear()
        with patch('app.push.requests.post', side_effect=fake_post):
            r = client.post('/api/messages/',
                            json={'recipient_id': recip.id, 'body': long_body},
                            headers=hdr(tok_sender))
        check('message send succeeds', r.status_code == 201,
              f'status={r.status_code}')
        rows_m = Notification.query.filter_by(user_id=recip.id, type='MESSAGE').all()
        check('recipient got exactly one MESSAGE notification', len(rows_m) == 1,
              f'count={len(rows_m)}')
        if rows_m:
            check('MESSAGE title is the sender name',
                  rows_m[0].title == 'Sender Person', rows_m[0].title)
            check('MESSAGE body is the 120-char preview',
                  rows_m[0].body == 'M' * 120,
                  f'len={len(rows_m[0].body or "")}')
        check('sender got no MESSAGE notification',
              notif_count(sender.id, 'MESSAGE') == 0)
        m_sends = [c for c in FCM_CALLS
                   if (c[1] or {}).get('message', {}).get('token') == 'recip-device-token']
        check('exactly one push sent to the recipient device', len(m_sends) == 1)
        if m_sends:
            d = m_sends[0][1]['message'].get('data') or {}
            n = m_sends[0][1]['message'].get('notification') or {}
            check('message push data carries type + sender_id',
                  d.get('type') == 'MESSAGE' and d.get('sender_id') == str(sender.id),
                  str(d))
            check('message push notification mirrors title/preview',
                  n.get('title') == 'Sender Person' and n.get('body') == 'M' * 120)

    disable_fcm()
    try:
        os.unlink(sa_path)
    except OSError:
        pass
    print(f'\n{passed} passed, {failed} failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
