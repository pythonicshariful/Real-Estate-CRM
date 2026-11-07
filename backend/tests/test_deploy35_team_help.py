"""Deploy 35 checks — Team user management + Help article edit/delete.

Fills two backend gaps the web UI already called:

- team.js / TeamAPI (api.js): POST /team/users (Create Account form),
  POST /team/users/<id>/toggle-status, POST /team/users/<id>/deactivate
  — none of these routes existed (create 405'd in web AND app).
  POST mirrors create_lead_owner (admin-only, password policy, 409 on
  duplicate email) but honours the form's role values
  (ADMIN/CEO/GM/MANAGER/EXECUTIVE from team.html; missing role ->
  LEAD_OWNER; unknown role -> 400). Toggle/deactivate mirror the
  lead-owner toggle semantics, plus a self-guard the owner toggle
  lacks: an admin cannot switch off their own account (400).

- help admin: POST /help/articles existed but PUT/DELETE did not.
  PUT updates only the fields present; DELETE removes the article.
  Both are ADMIN-only (require_min_role), 404 on a missing id.

Run: venv/bin/python tests/test_deploy35_team_help.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import os
import sys

import bcrypt

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Article

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


def main():
    with app.app_context():
        db.create_all()
        admin = mk_user('Admin', 'admin35@test.com', 'Admin@123', UserRole.ADMIN)
        owner = mk_user('Owner', 'owner35@test.com', 'Owner@123', UserRole.LEAD_OWNER)
        tok_admin = mk_token('admin35@test.com', 'Admin@123')
        tok_owner = mk_token('owner35@test.com', 'Owner@123')

        # ---- POST /team/users -------------------------------------------
        payload = {'email': 'newmgr35@test.com', 'full_name': 'New Manager',
                   'password': 'Strong@123', 'role': 'MANAGER',
                   'phone': '+8801700000099', 'max_lead_capacity': 45}
        r = client.post('/api/team/users', json=payload, headers=hdr(tok_admin))
        body = r.get_json() or {}
        created = body.get('user') or {}
        check('admin creates user -> 201', r.status_code == 201,
              f'{r.status_code} {body}')
        check('create honours role MANAGER', created.get('role') == 'MANAGER',
              f"{created.get('role')}")
        check('create returns message for team.js toast',
              body.get('message') == 'User account created successfully',
              f"{body.get('message')}")
        check('returned user carries no password material',
              'password' not in created and 'password_hash' not in created,
              f'{sorted(created)}')
        check('phone + capacity stored',
              created.get('phone') == '+8801700000099'
              and created.get('max_lead_capacity') == 45, f'{created}')

        r = client.post('/api/team/users',
                        json={'email': 'lower35@test.com', 'full_name': 'Lower',
                              'password': 'Strong@123', 'role': 'executive'},
                        headers=hdr(tok_admin))
        check('role value is case-insensitive (executive -> EXECUTIVE)',
              r.status_code == 201
              and (r.get_json() or {}).get('user', {}).get('role') == 'EXECUTIVE',
              f'{r.status_code}')

        r = client.post('/api/team/users',
                        json={'email': 'norole35@test.com', 'full_name': 'No Role',
                              'password': 'Strong@123'},
                        headers=hdr(tok_admin))
        check('missing role defaults to LEAD_OWNER',
              r.status_code == 201
              and (r.get_json() or {}).get('user', {}).get('role') == 'LEAD_OWNER',
              f'{r.status_code}')

        r = client.post('/api/team/users',
                        json={'email': 'badrole35@test.com', 'full_name': 'Bad',
                              'password': 'Strong@123', 'role': 'SUPERUSER'},
                        headers=hdr(tok_admin))
        check('unrecognised role -> 400', r.status_code == 400, f'{r.status_code}')

        r = client.post('/api/team/users', json=payload, headers=hdr(tok_admin))
        check('duplicate email -> 409', r.status_code == 409, f'{r.status_code}')

        r = client.post('/api/team/users',
                        json={'email': 'weak35@test.com', 'full_name': 'Weak',
                              'password': 'weak', 'role': 'EXECUTIVE'},
                        headers=hdr(tok_admin))
        check('weak password -> 400 with policy message',
              r.status_code == 400 and 'error' in (r.get_json() or {}),
              f'{r.status_code}')

        r = client.post('/api/team/users',
                        json={'email': 'nofield35@test.com', 'role': 'EXECUTIVE'},
                        headers=hdr(tok_admin))
        check('missing required field -> 400', r.status_code == 400,
              f'{r.status_code}')

        r = client.post('/api/team/users', json=payload, headers=hdr(tok_owner))
        check('non-admin create -> 403', r.status_code == 403, f'{r.status_code}')

        new_id = created['id']

        # ---- toggle-status / deactivate ----------------------------------
        r = client.post(f'/api/team/users/{new_id}/toggle-status',
                        headers=hdr(tok_owner))
        check('non-admin toggle -> 403', r.status_code == 403, f'{r.status_code}')

        r = client.post(f'/api/team/users/{new_id}/toggle-status',
                        headers=hdr(tok_admin))
        check('toggle #1 -> inactive',
              r.status_code == 200
              and (r.get_json() or {}).get('user', {}).get('is_active') is False,
              f'{r.status_code} {r.get_json()}')
        r = client.post(f'/api/team/users/{new_id}/toggle-status',
                        headers=hdr(tok_admin))
        check('toggle #2 -> active again',
              r.status_code == 200
              and (r.get_json() or {}).get('user', {}).get('is_active') is True,
              f'{r.status_code} {r.get_json()}')

        r = client.post(f'/api/team/users/{new_id}/deactivate',
                        headers=hdr(tok_admin))
        check('deactivate -> inactive',
              r.status_code == 200
              and (r.get_json() or {}).get('user', {}).get('is_active') is False,
              f'{r.status_code} {r.get_json()}')
        r = client.post(f'/api/team/users/{new_id}/deactivate',
                        headers=hdr(tok_admin))
        check('deactivate is idempotent',
              r.status_code == 200
              and (r.get_json() or {}).get('user', {}).get('is_active') is False,
              f'{r.status_code}')

        r = client.post('/api/team/users/999999/toggle-status',
                        headers=hdr(tok_admin))
        check('toggle missing user -> 404', r.status_code == 404,
              f'{r.status_code}')
        r = client.post('/api/team/users/999999/deactivate',
                        headers=hdr(tok_admin))
        check('deactivate missing user -> 404', r.status_code == 404,
              f'{r.status_code}')

        r = client.post(f'/api/team/users/{admin.id}/toggle-status',
                        headers=hdr(tok_admin))
        check('self toggle -> 400 (own-account guard)',
              r.status_code == 400, f'{r.status_code}')
        r = client.post(f'/api/team/users/{admin.id}/deactivate',
                        headers=hdr(tok_admin))
        check('self deactivate -> 400 (own-account guard)',
              r.status_code == 400, f'{r.status_code}')
        db.session.expire_all()
        check('admin still active after self-guard',
              User.query.get(admin.id).is_active is True)

        # ---- Help articles PUT / DELETE ----------------------------------
        r = client.post('/api/help/articles',
                        json={'title': 'Old Title', 'content': 'Body',
                              'category': 'GUIDE', 'is_published': True},
                        headers=hdr(tok_admin))
        check('setup: admin creates article -> 201', r.status_code == 201,
              f'{r.status_code}')
        art_id = (r.get_json() or {})['id']

        r = client.put(f'/api/help/articles/{art_id}',
                       json={'title': 'New Title', 'is_published': False},
                       headers=hdr(tok_admin))
        body = r.get_json() or {}
        check('admin PUT -> 200', r.status_code == 200, f'{r.status_code}')
        check('PUT updates title + is_published',
              body.get('title') == 'New Title'
              and body.get('is_published') is False, f'{body}')
        db.session.expire_all()
        art = Article.query.get(art_id)
        check('PUT persisted (title, is_published, untouched content kept)',
              art.title == 'New Title' and art.is_published is False
              and art.content == 'Body')

        r = client.put(f'/api/help/articles/{art_id}',
                       json={'title': 'Nope'}, headers=hdr(tok_owner))
        check('non-admin PUT -> 403', r.status_code == 403, f'{r.status_code}')

        r = client.put('/api/help/articles/999999',
                       json={'title': 'Nope'}, headers=hdr(tok_admin))
        check('PUT missing article -> 404', r.status_code == 404,
              f'{r.status_code}')

        r = client.delete(f'/api/help/articles/{art_id}',
                          headers=hdr(tok_owner))
        check('non-admin DELETE -> 403', r.status_code == 403,
              f'{r.status_code}')

        r = client.delete(f'/api/help/articles/{art_id}',
                          headers=hdr(tok_admin))
        check('admin DELETE -> 200', r.status_code == 200, f'{r.status_code}')
        r = client.get('/api/help/articles', headers=hdr(tok_admin))
        ids = {a['id'] for a in r.get_json()}
        check('deleted article gone from GET /help/articles',
              art_id not in ids, f'{ids}')

        r = client.delete('/api/help/articles/999999', headers=hdr(tok_admin))
        check('DELETE missing article -> 404', r.status_code == 404,
              f'{r.status_code}')

    print(f'\n{passed}/{passed + failed} checks passed')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
