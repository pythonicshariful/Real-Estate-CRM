"""Deploy 33 checks — Clients page (contacts) scoped per owner.

Owner instruction (2026-11-05): on contacts.html a Lead Owner must see
only THEIR clients; Admin sees everyone. Before this, GET /api/contacts/
returned every contact to every logged-in user.

Rule implemented in app/blueprints/contacts/routes.py:
- non-admin list + single GET + inquiries/opportunities sub-reads are
  limited to contacts with at least one live lead assigned to them,
  plus contacts with no live lead at all (shared address-book entries,
  e.g. manually added before a lead exists).
- a shared contact's opportunities list shows a non-admin only their own.
- Admin is unfiltered.

Run: venv/bin/python test_deploy33_contacts_scope.py  (from backend/)
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
    return r.get_json()['access_token']


def hdr(tok):
    return {'Authorization': f'Bearer {tok}'}


def mk_contact(name, phone):
    c = Contact(full_name=name, phone_raw=phone, phone_normalized=phone,
                source='Test', is_deleted=False)
    db.session.add(c)
    db.session.commit()
    return c


def mk_opp(contact_id, assigned_to_id):
    o = Opportunity(contact_id=contact_id, assigned_to_id=assigned_to_id)
    db.session.add(o)
    db.session.commit()
    return o


def list_ids(tok):
    r = client.get('/api/contacts/', headers=hdr(tok))
    assert r.status_code == 200, r.status_code
    return {c['id'] for c in r.get_json()}


def main():
    with app.app_context():
        db.create_all()
        admin = mk_user('Admin', 'admin33@test.com', 'Admin@123', UserRole.ADMIN)
        owner_a = mk_user('Owner A', 'a33@test.com', 'Owner@123', UserRole.LEAD_OWNER)
        owner_b = mk_user('Owner B', 'b33@test.com', 'Owner@123', UserRole.LEAD_OWNER)

        c_a = mk_contact('Client A', '01700000001')
        c_b = mk_contact('Client B', '01700000002')
        c_shared = mk_contact('Shared Client', '01700000003')
        c_unassigned = mk_contact('Unassigned Client', '01700000004')
        c_admin = mk_contact('Admin Client', '01700000005')
        c_orphan = mk_contact('Orphan Client', '01700000006')

        mk_opp(c_a.id, owner_a.id)
        mk_opp(c_b.id, owner_b.id)
        opp_shared_a = mk_opp(c_shared.id, owner_a.id)
        opp_shared_b = mk_opp(c_shared.id, owner_b.id)
        mk_opp(c_unassigned.id, None)
        mk_opp(c_admin.id, admin.id)

        tok_admin = mk_token('admin33@test.com', 'Admin@123')
        tok_a = mk_token('a33@test.com', 'Owner@123')
        tok_b = mk_token('b33@test.com', 'Owner@123')

        ids_admin = list_ids(tok_admin)
        check('admin list sees all six contacts',
              ids_admin == {c_a.id, c_b.id, c_shared.id, c_unassigned.id, c_admin.id, c_orphan.id},
              f'{ids_admin}')

        ids_a = list_ids(tok_a)
        check('owner A list: own + shared + orphan only',
              ids_a == {c_a.id, c_shared.id, c_orphan.id}, f'{ids_a}')
        ids_b = list_ids(tok_b)
        check('owner B list: own + shared + orphan only',
              ids_b == {c_b.id, c_shared.id, c_orphan.id}, f'{ids_b}')

        r = client.get(f'/api/contacts/{c_b.id}', headers=hdr(tok_a))
        check('owner A opening owner B contact -> 403', r.status_code == 403,
              f'{r.status_code}')
        r = client.get(f'/api/contacts/{c_a.id}', headers=hdr(tok_a))
        check('owner A opening own contact -> 200', r.status_code == 200)
        r = client.get(f'/api/contacts/{c_unassigned.id}', headers=hdr(tok_a))
        check('owner A opening unassigned-lead contact -> 403', r.status_code == 403,
              f'{r.status_code}')
        r = client.get(f'/api/contacts/{c_orphan.id}', headers=hdr(tok_a))
        check('owner A opening orphan contact -> 200', r.status_code == 200)

        r = client.get(f'/api/contacts/{c_b.id}/opportunities', headers=hdr(tok_a))
        check('owner A reading B contact opportunities -> 403', r.status_code == 403)
        r = client.get(f'/api/contacts/{c_shared.id}/opportunities', headers=hdr(tok_a))
        got = {o['id'] for o in r.get_json()} if r.status_code == 200 else set()
        check('shared contact: owner A sees only own opportunity',
              r.status_code == 200 and got == {opp_shared_a.id}, f'{r.status_code} {got}')
        r = client.get(f'/api/contacts/{c_shared.id}/opportunities', headers=hdr(tok_admin))
        got = {o['id'] for o in r.get_json()} if r.status_code == 200 else set()
        check('shared contact: admin sees both opportunities',
              r.status_code == 200 and got == {opp_shared_a.id, opp_shared_b.id},
              f'{r.status_code} {got}')

        r = client.get(f'/api/contacts/{c_b.id}/inquiries', headers=hdr(tok_a))
        check('owner A reading B contact inquiries -> 403', r.status_code == 403)

    print(f'\n{passed}/{passed + failed} checks passed')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
