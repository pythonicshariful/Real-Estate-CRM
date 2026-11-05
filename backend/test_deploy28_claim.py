"""Deploy 28 checks — Lead Owner self-claim on unclaimed leads.

Bug (2026-11-05): a Lead Owner got "Access denied" when logging a call
or adding an event, whenever the lead was not formally assigned to them.
Live audit at the time: 1,452 opportunities unassigned, 12 parked on the
ADMIN account (the client's own CSV import, auto-assign pool exhausted)
— and the Clients page lists every contact to everyone, so owners kept
walking into leads they could see but not work.

Fix: claim_lead_if_unclaimed (app/models.py) + _ensure_lead_access on
lead-scoped endpoints (leads blueprint) and the events blueprint lead
checks. A non-admin reaching an unassigned or admin-held lead claims it
(assigned_to/by/date set, committed) and proceeds; a lead owned by
another non-admin still denies. DELETE stays on the strict check.

Run: venv/bin/python test_deploy28_claim.py  (from backend/)
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
from app.models import User, UserRole, Opportunity, Contact

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


def mk_user(name, email, pw, role):
    u = User(full_name=name, email=email,
             password_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
             role=role, is_active=True)
    db.session.add(u)
    db.session.commit()
    return u


def mk_token(email, pw):
    r = client.post('/api/auth/login', json={'email': email, 'password': pw})
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()['access_token']


def mk_lead(name, phone, assigned_to_id):
    c = Contact(full_name=name, phone_raw=phone, source='Manual Entry',
                consent_given=True)
    db.session.add(c)
    db.session.commit()
    o = Opportunity(contact_id=c.id, assigned_to_id=assigned_to_id)
    db.session.add(o)
    db.session.commit()
    return o


def assignee(lead_id):
    with app.app_context():
        db.session.expire_all()
        o = Opportunity.query.get(lead_id)
        return o.assigned_to_id, o.assigned_date


def main():
    with app.app_context():
        db.create_all()
        admin = mk_user('D28 Admin', 'd28_admin@t.com', 'Admin@123', UserRole.ADMIN)
        o1 = mk_user('D28 Owner1', 'd28_o1@t.com', 'Owner@123', UserRole.LEAD_OWNER)
        o2 = mk_user('D28 Owner2', 'd28_o2@t.com', 'Owner@123', UserRole.LEAD_OWNER)
        admin_id, o1_id, o2_id = admin.id, o1.id, o2.id
        lead_free = mk_lead('Free Lead', '+8801744444444', None)
        lead_admin = mk_lead('Admin Held', '+8801755555555', admin_id)
        lead_o2 = mk_lead('Peer Lead', '+8801766666666', o2_id)
        lead_free2 = mk_lead('Free Lead 2', '+8801777777777', None)
        lead_free3 = mk_lead('Free Lead 3', '+8801788888888', None)
        ids = (lead_free.id, lead_admin.id, lead_o2.id, lead_free2.id, lead_free3.id)

    free_id, adminheld_id, peer_id, free2_id, free3_id = ids
    t1 = mk_token('d28_o1@t.com', 'Owner@123')
    h1 = {'Authorization': f'Bearer {t1}'}
    tadm = mk_token('d28_admin@t.com', 'Admin@123')
    hadm = {'Authorization': f'Bearer {tadm}'}

    # 1. Opening an unassigned lead's profile claims it
    r = client.get(f'/api/leads/{free_id}/profile', headers=h1)
    check('owner opens unassigned profile -> 200', r.status_code == 200,
          f'{r.status_code} {r.get_json()}')
    a, d = assignee(free_id)
    check('unassigned lead claimed by opener', a == o1_id, f'assigned_to={a}')
    check('claim sets assigned_date', d is not None)

    # 2. Log Call on an ADMIN-held lead claims it and succeeds
    r = client.post(f'/api/leads/{adminheld_id}/calls', headers=h1,
                    json={'notes': 'd28 call', 'connected': True})
    check('owner logs call on admin-held lead -> 201', r.status_code == 201,
          f'{r.status_code} {r.get_json()}')
    a, _ = assignee(adminheld_id)
    check('admin-held lead claimed by caller', a == o1_id, f'assigned_to={a}')

    # 3. Add Event on another unassigned lead claims it and succeeds
    r = client.post(f'/api/events/lead/{free2_id}', headers=h1, json={
        'title': 'D28 Visit', 'start_datetime': '2026-11-06T10:00'})
    check('owner adds event on unassigned lead -> 201', r.status_code == 201,
          f'{r.status_code} {r.get_json()}')
    a, _ = assignee(free2_id)
    check('event lead claimed by creator', a == o1_id, f'assigned_to={a}')

    # 4. A peer's lead still denies everything
    r = client.get(f'/api/leads/{peer_id}/profile', headers=h1)
    check("owner opens peer's profile -> 403", r.status_code == 403,
          f'{r.status_code}')
    r = client.post(f'/api/leads/{peer_id}/calls', headers=h1,
                    json={'notes': 'x', 'connected': True})
    check("owner logs call on peer's lead -> 403", r.status_code == 403,
          f'{r.status_code}')
    r = client.post(f'/api/events/lead/{peer_id}', headers=h1, json={
        'title': 'X', 'start_datetime': '2026-11-06T10:00'})
    check("owner adds event on peer's lead -> 403", r.status_code == 403,
          f'{r.status_code}')
    a, _ = assignee(peer_id)
    check("peer's lead untouched", a == o2_id, f'assigned_to={a}')

    # 5. DELETE stays strict even on an unassigned lead
    r = client.delete(f'/api/leads/{free3_id}', headers=h1)
    check('owner deletes unassigned lead -> 403 (strict)', r.status_code == 403,
          f'{r.status_code}')
    a, _ = assignee(free3_id)
    check('unassigned lead still unassigned after delete attempt', a is None,
          f'assigned_to={a}')

    # 6. Admin unaffected: can open a peer-owned lead
    r = client.get(f'/api/leads/{peer_id}/profile', headers=hadm)
    check("admin opens peer's profile -> 200", r.status_code == 200,
          f'{r.status_code}')
    a, _ = assignee(peer_id)
    check("admin view does not steal the lead", a == o2_id, f'assigned_to={a}')

    print(f'\n{passed} passed, {failed} failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
