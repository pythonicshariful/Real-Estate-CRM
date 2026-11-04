"""Targeted tests for the 2026-11-04 full-QA bug-fix batch (deploy 16).

Covers:
- Exit Lead accepts the UI's 'target_stage' key (was: always "Invalid
  exit stage") as well as 'exit_stage'; invalid values still 400.
- Questionnaire question type alias: to_dict carries question_type
  (uppercase, for the Settings UI) and POST/PUT accept question_type,
  storing lowercase field_type (was: TYPE column "undefined", type
  edits silently dropped).
- Phone '.0': clean_phone_str, contacts API cleans stored values, and
  .xlsx import parses numeric phone cells without a trailing '.0'.
- Datetime serialization: lead created_at is UTC-offset aware, event
  start / task due_date are Dhaka-offset aware.
- Follow-up 'overdue' filter compares in Dhaka wall time.
- Notifications read-all API + reports charts regression (200 + keys).

Run: venv/bin/python test_qa_fixes_2026_11_04.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import io
import os
import sys
from datetime import datetime, timedelta

import bcrypt

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import (User, UserRole, Opportunity, Contact, Notification,
                        LeadQuestionnaireQuestion, clean_phone_str)

app = create_app('testing')
app.config['TESTING'] = True
client = app.test_client()

CHECKS = []
IDS = {}


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
            ('QA Fix Admin', 'qafix_admin@test.com', 'Admin@123', UserRole.ADMIN),
            ('QA Fix Owner', 'qafix_owner@test.com', 'Owner@123', UserRole.LEAD_OWNER),
        ]:
            if not User.query.filter_by(email=email).first():
                db.session.add(User(
                    full_name=name, email=email,
                    password_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
                    role=role, is_active=True,
                ))
        db.session.commit()
        IDS['admin_id'] = User.query.filter_by(email='qafix_admin@test.com').first().id
        IDS['owner_id'] = User.query.filter_by(email='qafix_owner@test.com').first().id


def make_lead(token, name, phone):
    r = client.post('/api/leads/', json={
        'full_name': name, 'phone': phone, 'pipeline_stage': 'NEW',
    }, headers=auth(token))
    assert r.status_code in (200, 201), f"lead create failed: {r.status_code} {r.get_data(as_text=True)}"
    return r.get_json()['id']


def main():
    setup_data()
    admin_tok = mk_token('qafix_admin@test.com', 'Admin@123')
    owner_tok = mk_token('qafix_owner@test.com', 'Owner@123')

    # ── 1. Exit Lead: target_stage (the UI's key) ─────────────────────
    lead_id = make_lead(admin_tok, 'QA Exit Lead', '01999000201')
    r = client.post(f'/api/leads/{lead_id}/exit', json={
        'target_stage': 'CLOSED_LOST', 'reason_code': 'PRICE', 'notes': 'qa test',
    }, headers=auth(admin_tok))
    check('exit with target_stage returns 200', r.status_code == 200,
          f"status={r.status_code} body={r.get_data(as_text=True)[:160]}")
    r = client.get(f'/api/leads/{lead_id}', headers=auth(admin_tok))
    stage = (r.get_json() or {}).get('pipeline_stage')
    check('lead stage became CLOSED_LOST', stage == 'CLOSED_LOST', f"stage={stage}")

    lead2 = make_lead(admin_tok, 'QA Exit Lead 2', '01999000202')
    r = client.post(f'/api/leads/{lead2}/exit', json={'exit_stage': 'INVALID'}, headers=auth(admin_tok))
    check('exit with exit_stage still works', r.status_code == 200, f"status={r.status_code}")
    r = client.post(f'/api/leads/{lead2}/exit', json={'target_stage': 'NOPE'}, headers=auth(admin_tok))
    check('exit with bogus stage still 400', r.status_code == 400, f"status={r.status_code}")

    # ── 2. Questionnaire type alias ───────────────────────────────────
    r = client.post('/api/settings/questionnaire', json={
        'question_text': 'QA Budget Type', 'question_key': 'qa_budget_type',
        'question_type': 'SELECT', 'options': ['Low', 'High'],
    }, headers=auth(admin_tok))
    check('POST questionnaire with question_type 200/201', r.status_code in (200, 201),
          f"status={r.status_code} body={r.get_data(as_text=True)[:160]}")
    body = r.get_json() or {}
    check('stored field_type is lowercase select', body.get('field_type') == 'select',
          f"field_type={body.get('field_type')}")
    check('response carries question_type alias SELECT', body.get('question_type') == 'SELECT',
          f"question_type={body.get('question_type')}")
    qid = body.get('id')
    r = client.put(f'/api/settings/questionnaire/{qid}', json={'question_type': 'NUMBER'}, headers=auth(admin_tok))
    check('PUT with question_type updates type', r.status_code == 200 and (r.get_json() or {}).get('field_type') == 'number',
          f"status={r.status_code} field_type={(r.get_json() or {}).get('field_type')}")
    r = client.get('/api/settings/questionnaire', headers=auth(admin_tok))
    row = next((q for q in r.get_json() if q.get('question_key') == 'qa_budget_type'), {})
    check('GET list exposes question_type (no undefined)', row.get('question_type') == 'NUMBER',
          f"row={row}")

    # ── 3. Phone '.0' ─────────────────────────────────────────────────
    check("clean_phone_str strips '.0'", clean_phone_str('88017000000.0') == '88017000000')
    check('clean_phone_str leaves normal phone', clean_phone_str('01712345678') == '01712345678')
    check('clean_phone_str leaves non-phone text', clean_phone_str('hello.0') == 'hello.0')
    with app.app_context():
        c = Contact(full_name='QA Dot Zero', phone_raw='88017000000.0',
                    phone_normalized='+88017000000')
        db.session.add(c)
        db.session.commit()
    r = client.get('/api/contacts/', headers=auth(admin_tok))
    row = next((x for x in r.get_json() if x.get('full_name') == 'QA Dot Zero'), {})
    check('contacts API returns cleaned phone_raw', row.get('phone_raw') == '88017000000',
          f"phone_raw={row.get('phone_raw')}")

    # xlsx import preview: numeric phone cell must not gain '.0'
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Full Name', 'Phone', 'Email'])
    ws.append(['QA Xlsx Phone', 8801712345678, 'qaxlsx@test.com'])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    r = client.post('/api/leads/import/preview',
                    data={'file': (buf, 'qa.xlsx')},
                    headers=auth(admin_tok), content_type='multipart/form-data')
    ok = r.status_code == 200
    detail = f"status={r.status_code}"
    if ok:
        payload = r.get_json()
        rows = payload.get('preview_rows') or payload.get('rows') or []
        detail += f" payload_keys={list(payload.keys())} rows={str(rows)[:200]}"
        flat = str(rows)
        ok = '8801712345678' in flat and '8801712345678.0' not in flat
    check('xlsx import preview keeps phone integral (no .0)', ok, detail)

    # ── 4. Datetime serialization ─────────────────────────────────────
    r = client.get('/api/leads/', headers=auth(admin_tok))
    item = next((x for x in r.get_json() if x.get('id') == lead_id), {})
    check('lead created_at carries +00:00 offset',
          str(item.get('created_at', '')).endswith('+00:00'),
          f"created_at={item.get('created_at')}")

    # Tasks: storage is naive UTC. The UI sends toISOString() — 10:00 Dhaka
    # is '2026-11-05T04:00:00.000Z' — and must read back the same instant.
    r = client.post('/api/tasks/', json={
        'title': 'QA time task', 'due_date': '2026-11-05T04:00:00.000Z',
        'assigned_to_id': IDS['owner_id'], 'priority': 'MEDIUM', 'status': 'PENDING',
    }, headers=auth(admin_tok))
    check('task create 200/201', r.status_code in (200, 201),
          f"status={r.status_code} body={r.get_data(as_text=True)[:160]}")
    r = client.get('/api/tasks/', headers=auth(admin_tok))
    trow = next((t for t in r.get_json() if t.get('title') == 'QA time task'), {})
    check('task due_date round-trips as the same UTC instant',
          trow.get('due_date') == '2026-11-05T04:00:00+00:00',
          f"due_date={trow.get('due_date')}")
    # A naive value is interpreted as Dhaka wall time (10:00 Dhaka = 04:00 UTC)
    r = client.post('/api/tasks/', json={
        'title': 'QA naive task', 'due_date': '2026-11-06T10:00',
        'assigned_to_id': IDS['owner_id'], 'priority': 'MEDIUM', 'status': 'PENDING',
    }, headers=auth(admin_tok))
    r = client.get('/api/tasks/', headers=auth(admin_tok))
    trow = next((t for t in r.get_json() if t.get('title') == 'QA naive task'), {})
    check('naive due_date interpreted as Dhaka wall (stored 04:00 UTC)',
          trow.get('due_date') == '2026-11-06T04:00:00+00:00',
          f"due_date={trow.get('due_date')}")

    with app.app_context():
        from app.models import Event
        ev = Event(title='QA tz event', event_type='MEETING',
                   start_datetime=datetime(2026, 11, 5, 4, 0),   # 04:00 UTC = 10:00 Dhaka
                   end_datetime=datetime(2026, 11, 5, 5, 0),
                   created_by_id=IDS['admin_id'])
        d = ev.to_dict()
    check('Event.to_dict expresses the UTC instant in +06:00 (10:00 Dhaka)',
          d.get('start') == '2026-11-05T10:00:00+06:00',
          f"start={d.get('start')}")

    # Disposition path: a raw Dhaka-wall follow-up must be stored as UTC
    lead4 = make_lead(admin_tok, 'QA Disposition Lead', '01999000204')
    r = client.post(f'/api/leads/{lead4}/calls', json={
        'notes': 'qa disposition', 'connected': True,
        'next_action_deadline': '2026-11-07T10:00', 'next_action_type': 'CALL',
    }, headers=auth(admin_tok))
    check('log call with follow-up 200/201', r.status_code in (200, 201),
          f"status={r.status_code} body={r.get_data(as_text=True)[:160]}")
    with app.app_context():
        opp = Opportunity.query.get(lead4)
        stored = opp.next_action_deadline
    check('follow-up deadline stored as UTC (10:00 Dhaka -> 04:00 UTC)',
          stored == datetime(2026, 11, 7, 4, 0), f"stored={stored}")

    # ── 5. Follow-up overdue filter (Dhaka wall) ──────────────────────
    lead3 = make_lead(admin_tok, 'QA Overdue Lead', '01999000203')
    with app.app_context():
        opp = Opportunity.query.get(lead3)
        opp.next_action_deadline = datetime.now() - timedelta(days=1)
        db.session.commit()
    r = client.get('/api/leads/?followup=overdue', headers=auth(admin_tok))
    ids = [x.get('id') for x in r.get_json()] if r.status_code == 200 else []
    check('yesterday deadline appears in followup=overdue', lead3 in ids,
          f"status={r.status_code} ids={ids[:8]}")
    r = client.get('/api/leads/?followup=upcoming', headers=auth(admin_tok))
    ids = [x.get('id') for x in r.get_json()] if r.status_code == 200 else []
    check('yesterday deadline NOT in followup=upcoming', lead3 not in ids)

    # ── 6. Notifications read-all + reports charts regression ─────────
    with app.app_context():
        db.session.add(Notification(user_id=IDS['owner_id'], title='QA notif', body='x'))
        db.session.commit()
    r = client.get('/api/notifications/', headers=auth(owner_tok))
    check('notification listed with unread_count 1',
          r.status_code == 200 and (r.get_json() or {}).get('unread_count') == 1,
          f"status={r.status_code} body={r.get_data(as_text=True)[:140]}")
    r = client.post('/api/notifications/read-all', headers=auth(owner_tok))
    check('read-all 200', r.status_code == 200, f"status={r.status_code}")
    r = client.get('/api/notifications/', headers=auth(owner_tok))
    check('unread_count 0 after read-all', (r.get_json() or {}).get('unread_count') == 0)

    r = client.get('/api/reports/charts', headers=auth(admin_tok))
    keys = sorted((r.get_json() or {}).keys()) if r.status_code == 200 else []
    check('reports charts 200 with expected keys',
          r.status_code == 200 and 'weekly_trends' in keys and 'lead_outcome' in keys,
          f"status={r.status_code} keys={keys}")

    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
