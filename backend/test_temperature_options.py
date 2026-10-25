"""Tests for admin-configurable lead temperature options.

- GET /api/settings/temperature-options returns the defaults (COLD/WARM/HOT)
  for any logged-in user.
- PUT /api/settings/temperature-options is ADMIN-only, validates the list,
  and replaces it.
- PUT /api/leads/<id>/temperature validates against the CONFIGURED options
  (not a hardcoded enum); a lead already set to a removed value keeps it.

Run: venv/bin/python test_temperature_options.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import os
import sys
import bcrypt

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, Contact, Inquiry, SystemSetting

app = create_app('testing')
app.config['TESTING'] = True
client = app.test_client()

CHECKS = []
LEAD_ID = None


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
        if not User.query.filter_by(email='tempu_admin@test.com').first():
            admin = User(
                full_name='TempU Admin', email='tempu_admin@test.com',
                password_hash=bcrypt.hashpw(b'Admin@123', bcrypt.gensalt()).decode(),
                role=UserRole.ADMIN, is_active=True,
            )
            db.session.add(admin)
        if not User.query.filter_by(email='tempu_owner@test.com').first():
            owner = User(
                full_name='TempU Owner', email='tempu_owner@test.com',
                password_hash=bcrypt.hashpw(b'Owner@123', bcrypt.gensalt()).decode(),
                role=UserRole.LEAD_OWNER, is_active=True,
            )
            db.session.add(owner)
        db.session.commit()


def cleanup():
    with app.app_context():
        contact_ids = [c.id for c in Contact.query.filter(Contact.phone_normalized == '01999000111').all()]
        Opportunity.query.filter(Opportunity.id == LEAD_ID).delete(synchronize_session=False)
        if contact_ids:
            Inquiry.query.filter(Inquiry.contact_id.in_(contact_ids)).delete(synchronize_session=False)
            Contact.query.filter(Contact.id.in_(contact_ids)).delete(synchronize_session=False)
        SystemSetting.query.filter_by(key='temperature_options').delete(synchronize_session=False)
        User.query.filter(User.email.in_(['tempu_admin@test.com', 'tempu_owner@test.com'])).delete(synchronize_session=False)
        db.session.commit()


def main():
    global LEAD_ID
    setup_data()
    admin_tok = mk_token('tempu_admin@test.com', 'Admin@123')
    owner_tok = mk_token('tempu_owner@test.com', 'Owner@123')

    # 1. Defaults load for any logged-in user (lead owner here)
    r = client.get('/api/settings/temperature-options', headers=auth(owner_tok))
    data = r.get_json() if r.status_code == 200 else None
    check('GET temperature-options 200 for lead owner', r.status_code == 200, f"status={r.status_code}")
    check('defaults are COLD/WARM/HOT', isinstance(data, list) and [o['value'] for o in data] == ['COLD', 'WARM', 'HOT'],
          f"got={[o['value'] for o in data] if isinstance(data, list) else data}")
    check('defaults carry colours', isinstance(data, list) and all(o.get('color', '').startswith('#') for o in data))

    # 2. Admin adds a custom option "BOILING"
    new_list = [
        {"value": "COLD", "label": "Cold", "color": "#3b82f6"},
        {"value": "WARM", "label": "Warm", "color": "#f59e0b"},
        {"value": "HOT", "label": "Hot", "color": "#f43f5e"},
        {"value": "BOILING", "label": "Boiling", "color": "#8b5cf6"},
    ]
    r = client.put('/api/settings/temperature-options', json=new_list, headers=auth(admin_tok))
    check('admin PUT adds BOILING (200)', r.status_code == 200, f"status={r.status_code}")
    r = client.get('/api/settings/temperature-options', headers=auth(owner_tok))
    check('GET shows 4 options incl. BOILING', r.status_code == 200 and len(r.get_json()) == 4
          and 'BOILING' in [o['value'] for o in r.get_json()])

    # Create a test lead (admin) to set its temperature on
    r = client.post('/api/leads/', json={
        'full_name': 'Temp Options Lead', 'phone': '01999000111',
        'email': 'tempopts@test.com', 'pipeline_stage': 'NEW',
    }, headers=auth(admin_tok))
    assert r.status_code in (200, 201), f"lead create failed: {r.status_code} {r.get_data(as_text=True)}"
    LEAD_ID = r.get_json()['id']

    # 3. PUT temperature accepts the new custom option and stores it
    r = client.put(f'/api/leads/{LEAD_ID}/temperature', json={'temperature': 'BOILING'}, headers=auth(admin_tok))
    check('PUT temperature BOILING accepted (200)', r.status_code == 200, f"status={r.status_code}")
    r = client.get('/api/leads/', headers=auth(admin_tok))
    lead = next((x for x in r.get_json() if x['id'] == LEAD_ID), None)
    check('lead stores BOILING via to_dict', lead is not None and lead.get('lead_temperature') == 'BOILING',
          f"got={lead.get('lead_temperature') if lead else 'lead not in list'}")

    # 4. Admin removes BOILING again; PUT temperature then rejects it (400)
    reduced = [o for o in new_list if o['value'] != 'BOILING']
    r = client.put('/api/settings/temperature-options', json=reduced, headers=auth(admin_tok))
    check('admin PUT removes BOILING (200)', r.status_code == 200, f"status={r.status_code}")
    r = client.put(f'/api/leads/{LEAD_ID}/temperature', json={'temperature': 'BOILING'}, headers=auth(admin_tok))
    check('PUT temperature BOILING rejected after removal (400)', r.status_code == 400, f"status={r.status_code}")
    # ...but the lead already set to BOILING keeps its value in to_dict
    r = client.get('/api/leads/', headers=auth(admin_tok))
    lead = next((x for x in r.get_json() if x['id'] == LEAD_ID), None)
    check('lead with removed value still renders BOILING', lead is not None and lead.get('lead_temperature') == 'BOILING',
          f"got={lead.get('lead_temperature') if lead else 'lead not in list'}")

    # 5. Non-admin PUT -> 403
    r = client.put('/api/settings/temperature-options', json=reduced, headers=auth(owner_tok))
    check('non-admin PUT temperature-options -> 403', r.status_code == 403, f"status={r.status_code}")

    # 6. Empty list rejected (400)
    r = client.put('/api/settings/temperature-options', json=[], headers=auth(admin_tok))
    check('empty list rejected (400)', r.status_code == 400, f"status={r.status_code}")

    # 7. Duplicate values rejected (400)
    dup = reduced + [{"value": "cold", "label": "Cold again", "color": "#10b981"}]
    r = client.put('/api/settings/temperature-options', json=dup, headers=auth(admin_tok))
    check('duplicate value rejected (400)', r.status_code == 400, f"status={r.status_code}")

    # 8. Invalid value characters rejected (400)
    bad = reduced + [{"value": "SUPER-HOT!", "label": "Super Hot", "color": "#10b981"}]
    r = client.put('/api/settings/temperature-options', json=bad, headers=auth(admin_tok))
    check('invalid value chars rejected (400)', r.status_code == 400, f"status={r.status_code}")

    # 9. Unknown temperature rejected (400)
    r = client.put(f'/api/leads/{LEAD_ID}/temperature', json={'temperature': 'LUKewarm'}, headers=auth(admin_tok))
    check('PUT temperature unknown value -> 400', r.status_code == 400, f"status={r.status_code}")

    cleanup()
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n{passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == '__main__':
    sys.exit(main())
