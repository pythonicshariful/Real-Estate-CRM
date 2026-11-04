"""Targeted tests for the deploy-20 client bug batch (2026-11-04).

Covers:
- FIX 1 (Excel/CSV import questions invisible in the lead profile):
  import_leads now stores every non-core, non-empty row column into
  questionnaire_answers (keyed by column name), on BOTH the brand-new
  contact path and the existing-contact/no-active-opportunity path —
  the same convention as the Meta webhook path.
- FIX 3 (calendar reminder description 6h early): the rem_<id> feed
  entry formats the event start in Asia/Dhaka, not naive UTC.
- FIX 2/4 (static): the event/appointment create forms send the raw
  datetime-local value (no browser-tz toISOString conversion), leads.js
  is cache-busted to ?v=29, and lead-owners.html carries the live
  in-window badge logic without the stale round-robin promise copy.

Run: venv/bin/python test_deploy20_fixes.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import io
import os
import sys

import bcrypt

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, Contact

app = create_app('testing')
app.config['TESTING'] = True
client = app.test_client()

CHECKS = []
IDS = {}
STATIC = os.path.join(os.path.dirname(__file__), 'app', 'static')


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def mk_token(email, password):
    r = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.get_data(as_text=True)}"
    return r.get_json()['access_token']


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def setup_data():
    with app.app_context():
        db.create_all()
        for name, email, pw, role in [
            ('D20 Admin', 'd20_admin@test.com', 'Admin@123', UserRole.ADMIN),
            ('D20 Owner', 'd20_owner@test.com', 'Owner@123', UserRole.LEAD_OWNER),
        ]:
            if not User.query.filter_by(email=email).first():
                db.session.add(User(
                    full_name=name, email=email,
                    password_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
                    role=role, is_active=True,
                ))
        db.session.commit()
        IDS['admin_id'] = User.query.filter_by(email='d20_admin@test.com').first().id


def post_import(token, csv_text, filename='d20.csv'):
    buf = io.BytesIO(csv_text.encode('utf-8'))
    return client.post('/api/leads/import',
                       data={'file': (buf, filename)},
                       headers=auth(token), content_type='multipart/form-data')


def opp_id_for_phone(phone_raw):
    with app.app_context():
        c = Contact.query.filter_by(phone_raw=phone_raw).first()
        assert c, f"contact not found for {phone_raw}"
        opp = (Opportunity.query.filter_by(contact_id=c.id, is_deleted=False)
               .order_by(Opportunity.id.desc()).first())
        assert opp, f"opportunity not found for {phone_raw}"
        return opp.id


def main():
    setup_data()
    admin_tok = mk_token('d20_admin@test.com', 'Admin@123')

    # ── 1a. Import (new-contact path): question columns land in the profile ──
    csv1 = (
        "Full Name,Phone,Email,Profession,Service Type,Budget,Preferred Location,Monthly Income\n"
        "D20 Import Lead,01999000311,d20lead@test.com,Engineer,Apartment,1 Crore,Dhanmondi,85000\n"
    )
    r = post_import(admin_tok, csv1)
    body = r.get_json() or {}
    check('import returns 200 with 1 imported',
          r.status_code == 200 and body.get('imported') == 1,
          f"status={r.status_code} body={str(body)[:200]}")

    lead_id = opp_id_for_phone('01999000311')
    r = client.get(f'/api/leads/{lead_id}/profile', headers=auth(admin_tok))
    prof = r.get_json() or {}
    qa = prof.get('questionnaire_answers') or {}
    check('profile questionnaire_answers has Preferred Location',
          qa.get('Preferred Location') == 'Dhanmondi', f"qa={qa}")
    check('profile questionnaire_answers has Monthly Income',
          qa.get('Monthly Income') == '85000')
    check('profession/service_type/budget still present',
          qa.get('profession') == 'Engineer' and qa.get('service_type') == 'Apartment'
          and qa.get('budget') == '1 Crore', f"qa={qa}")
    check('core name/phone/email NOT duplicated into answers',
          'Full Name' not in qa and 'Phone' not in qa and 'Email' not in qa,
          f"keys={sorted(qa.keys())}")
    check('raw profession/service/budget headers not duplicated either',
          'Profession' not in qa and 'Service Type' not in qa and 'Budget' not in qa,
          f"keys={sorted(qa.keys())}")
    cf = {f.get('key'): f.get('value') for f in (prof.get('custom_fields') or [])}
    check('custom_fields renders Preferred Location for the profile UI',
          cf.get('Preferred Location') == 'Dhanmondi', f"custom_fields={cf}")

    # ── 1b. Import (existing-contact, no active opp path) ─────────────
    r = client.post(f'/api/leads/{lead_id}/exit',
                    json={'target_stage': 'CLOSED_LOST', 'reason_code': 'PRICE'},
                    headers=auth(admin_tok))
    check('exit first imported lead 200', r.status_code == 200,
          f"status={r.status_code}")
    csv2 = (
        "Full Name,Phone,Email,Profession,Preferred Area,Budget Flexibility\n"
        "D20 Import Lead,01999000311,d20lead@test.com,Engineer,Mirpur,Negotiable\n"
    )
    r = post_import(admin_tok, csv2)
    body = r.get_json() or {}
    check('re-import creates a fresh opportunity (imported=1)',
          r.status_code == 200 and body.get('imported') == 1,
          f"status={r.status_code} body={str(body)[:200]}")
    lead2_id = opp_id_for_phone('01999000311')
    check('re-import produced a NEW opportunity', lead2_id != lead_id,
          f"first={lead_id} second={lead2_id}")
    r = client.get(f'/api/leads/{lead2_id}/profile', headers=auth(admin_tok))
    qa2 = (r.get_json() or {}).get('questionnaire_answers') or {}
    check('existing-contact path also stores question columns',
          qa2.get('Preferred Area') == 'Mirpur' and qa2.get('Budget Flexibility') == 'Negotiable',
          f"qa={qa2}")

    # ── 2. Reminder description is Dhaka time; event start is +06:00 ──
    r = client.post('/api/events/', json={
        'title': 'D20 tz event', 'start_datetime': '2026-11-10T15:30',
        'reminder_minutes': 30,
    }, headers=auth(admin_tok))
    check('event create 201', r.status_code in (200, 201),
          f"status={r.status_code} body={r.get_data(as_text=True)[:160]}")
    ev_id = (r.get_json() or {}).get('id')
    r = client.get('/api/events/', headers=auth(admin_tok))
    feed = r.get_json() or []
    ev = next((e for e in feed if e.get('id') == ev_id), {})
    check('event start serializes as 15:30 +06:00',
          str(ev.get('start', '')).startswith('2026-11-10T15:30') and '+06:00' in str(ev.get('start')),
          f"start={ev.get('start')}")
    rem = next((e for e in feed if e.get('id') == f'rem_{ev_id}'), {})
    desc = rem.get('description') or ''
    check('reminder description shows Dhaka time 03:30 PM', '03:30 PM' in desc,
          f"description={desc}")
    check('reminder description does NOT show UTC time 09:30 AM', '09:30 AM' not in desc)

    # ── 3. Static checks (FIX 2 + FIX 4) ──────────────────────────────
    def read_static(rel):
        with open(os.path.join(STATIC, rel), encoding='utf-8') as f:
            return f.read()

    events_html = read_static('events.html')
    check('events.html sends raw start (no toISOString conversion)',
          'new Date(start).toISOString()' not in events_html
          and 'start_datetime: start,' in events_html)
    details_html = read_static('lead-details.html')
    check('lead-details.html sends raw start_datetime',
          'new Date(start).toISOString()' not in details_html
          and 'start_datetime: start' in details_html)
    leads_js = read_static(os.path.join('assets', 'js', 'leads.js'))
    check('leads.js drawer Set Event sends raw dt',
          'new Date(dt).toISOString()' not in leads_js and 'start_datetime: dt,' in leads_js)
    check('leads.js appointment sends raw dt',
          'appointment_datetime: dt' in leads_js)
    leads_html = read_static('leads.html')
    check('leads.html cache-busts leads.js to ?v=29', 'leads.js?v=29' in leads_html)
    owners_html = read_static('lead-owners.html')
    check('lead-owners.html has in-window badge logic',
          'scheduleWindowStatus' in owners_html and 'In window now' in owners_html
          and 'Schedule expired' in owners_html and 'No schedule' in owners_html)
    check('lead-owners.html dropped the round-robin promise copy',
          'divide equally (round-robin)' not in owners_html
          and 'Equal Round-Robin' not in owners_html)

    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
