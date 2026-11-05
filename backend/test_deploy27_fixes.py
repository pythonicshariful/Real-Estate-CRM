"""Deploy 27 checks — Meta CSV import aliases + poller error surfacing.

Bug context (2026-11-05): 13 genuine Meta leads were imported into the
live CRM through the web import using Meta's own lead-export CSV. They
landed with EMPTY profile phone and profession because the import path
did not recognise Meta's column names:
- the phone lives in a `whatsapp_number` column (value prefixed 'p:')
- the profession lives in a `job_title` column
The numbers/professions survived only inside questionnaire_answers /
raw_payload and had to be repaired by hand (contacts 1515-1527).

Fixes verified here:
- import get_val aliases: whatsapp_number -> phone (with the Meta 'p:'
  prefix stripped), job_title -> profession
- _CORE_IMPORT_KEYS: both columns are core, so they no longer ALSO land
  in questionnaire_answers as raw duplicates
- _suggest_mapping: whatsapp_* suggests 'phone'; job_title already
  suggested 'profession' via the 'job' hint
- poll_facebook_leads: a Graph listing error (e.g. invalidated page
  token) now surfaces in the summary as errors/error instead of an
  all-zeros "clean" result

Run: venv/bin/python test_deploy27_fixes.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import io
import json
import os
import sys
from unittest.mock import patch

import bcrypt

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, Contact, SystemSetting
from app.blueprints.leads.routes import _suggest_mapping
from app.tasks import poll_facebook_leads

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


def mk_token(email, password):
    r = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code}"
    return r.get_json()['access_token']


def setup_data():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='d27_admin@test.com').first():
            db.session.add(User(
                full_name='D27 Admin', email='d27_admin@test.com',
                password_hash=bcrypt.hashpw(b'Admin@123', bcrypt.gensalt()).decode(),
                role=UserRole.ADMIN, is_active=True,
            ))
        db.session.commit()


class FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.ok = False
        self.status_code = 400

    def json(self):
        return self._payload


def main():
    setup_data()
    tok = mk_token('d27_admin@test.com', 'Admin@123')
    hdr = {'Authorization': f'Bearer {tok}'}

    # ── 1. Suggested mapping recognises Meta's column names ────────────
    m = _suggest_mapping(['whatsapp_number', 'job_title', 'full_name'])
    check('suggest: whatsapp_number -> phone', m['whatsapp_number'] == 'phone', str(m))
    check('suggest: job_title -> profession', m['job_title'] == 'profession', str(m))
    check('suggest: full_name -> full_name', m['full_name'] == 'full_name', str(m))

    # ── 2. JSON import path (API-style rows, Meta column names) ────────
    r = client.post('/api/leads/import', headers=hdr, json={'leads': [{
        'full_name': 'D27 Meta CSV',
        'whatsapp_number': 'p:+8801712349876',
        'job_title': 'Banker',
        'company_name': 'Acme Ltd',
        'email': 'd27meta@test.com',
    }]})
    body = r.get_json() or {}
    check('JSON import returns 200/imported=1',
          r.status_code == 200 and body.get('imported') == 1,
          f'{r.status_code} {body}')
    with app.app_context():
        c = Contact.query.filter_by(email='d27meta@test.com').first()
        check('contact created', c is not None)
        if c:
            check("phone_normalized from whatsapp_number, 'p:' stripped",
                  c.phone_normalized == '+8801712349876', str(c.phone_normalized))
            check('phone_raw carries no p: prefix',
                  (c.phone_raw or '') == '+8801712349876', str(c.phone_raw))
            check('profession from job_title', c.profession == 'Banker',
                  str(c.profession))
            opp = (Opportunity.query.filter_by(contact_id=c.id, is_deleted=False)
                   .order_by(Opportunity.id.desc()).first())
            qa = (opp.questionnaire_answers or {}) if opp else {}
            check('extra question column kept in answers',
                  qa.get('company_name') == 'Acme Ltd', str(qa))
            check('whatsapp_number NOT duplicated into answers',
                  'whatsapp_number' not in qa, str(qa))
            check('job_title NOT duplicated into answers',
                  'job_title' not in qa, str(qa))

    # ── 3. CSV file import path (the client's actual route) ────────────
    csv_text = (
        "id,created_time,full_name,whatsapp_number,job_title,company_name\n"
        "l:999,2026-11-04T10:00:00+0000,D27 CSV Lead,p:+8801812349876,Garment Buyer,Textile Co\n"
    )
    buf = io.BytesIO(csv_text.encode('utf-8'))
    r = client.post('/api/leads/import', data={'file': (buf, 'meta_export.csv')},
                    headers=hdr, content_type='multipart/form-data')
    body = r.get_json() or {}
    check('CSV import returns 200/imported=1',
          r.status_code == 200 and body.get('imported') == 1,
          f'{r.status_code} {body}')
    with app.app_context():
        c = Contact.query.filter_by(phone_normalized='+8801812349876').first()
        check('CSV contact found by normalised phone', c is not None)
        if c:
            check('CSV profession from job_title', c.profession == 'Garment Buyer',
                  str(c.profession))

    # ── 4. Poller surfaces a dead-token Graph error ────────────────────
    with app.app_context():
        SystemSetting.set('facebook_page_access_token', 'DEADTOKEN')
        SystemSetting.set('facebook_page_id', 'PAGE27')
        SystemSetting.set('facebook_connection_mode', 'live')
        SystemSetting.set('facebook_lead_forms_json',
                          json.dumps([{'id': 'FORMX', 'name': 'F', 'status': 'ACTIVE'}]))
        SystemSetting.set('facebook_poll_state_json', '')
        db.session.commit()

    def dead_get(url, params=None, timeout=None):
        return FakeResp({'error': {
            'message': 'Error validating access token: The session has been invalidated.',
            'code': 190,
        }})

    with patch('requests.get', side_effect=dead_get):
        s = poll_facebook_leads(app=app)
    check('poll with dead token checks the form', s['forms_checked'] == 1, str(s))
    check('poll with dead token ingests nothing', s['new_leads'] == 0, str(s))
    check('poll surfaces the listing error count', s['errors'] == 1, str(s))
    check('poll surfaces the error message',
          bool(s['error']) and 'validating access token' in s['error'], str(s))

    with app.app_context():
        SystemSetting.set('facebook_page_access_token', '')
        SystemSetting.set('facebook_page_id', '')
        SystemSetting.set('facebook_connection_mode', '')
        SystemSetting.set('facebook_lead_forms_json', '')
        SystemSetting.set('facebook_poll_state_json', '')
        db.session.commit()

    print(f'\n{passed} passed, {failed} failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
