"""Targeted tests for deploy 30 (2026-11-05): schedule wins over capacity.

Client report: a duty schedule was configured so leads arriving in that
window go to a specific Lead Owner. Manual adds routed fine (inside the
test window), imports did not — live audit showed both owners at/over
their 30-lead capacity AND schedule windows that were 1-2 minute test
windows. Fix: in assign_lead_owner_auto, when the candidate pool was
restricted to in-window (scheduled) owners, capacity no longer blocks
the pick; the fallback (nobody scheduled) pool still respects capacity.

Run: venv/bin/python test_deploy30_schedule.py  (from backend/)
"""
import io
import os
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import bcrypt

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, Contact, PipelineStage, SystemSetting
from app.tasks import assign_lead_owner_auto

app = create_app('testing')
app.config['TESTING'] = True
client = app.test_client()

CHECKS = []
IDS = {}
_counter = [0]


def check(name, ok, detail=""):
    CHECKS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def mk_user(name, email, pw, role, cap=None):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(full_name=name, email=email,
                 password_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),
                 role=role, is_active=True, max_lead_capacity=cap)
        db.session.add(u)
        db.session.commit()
    return u


def give_leads(user, n):
    for _ in range(n):
        _counter[0] += 1
        phone = f"0177777{_counter[0]:04d}"
        c = Contact(full_name=f"D30 Lead {_counter[0]}", phone_raw=phone,
                    phone_normalized=phone, source='Manual Entry')
        db.session.add(c)
        db.session.flush()
        db.session.add(Opportunity(contact_id=c.id, assigned_to_id=user.id,
                                   pipeline_stage=PipelineStage.NEW))
    db.session.commit()


def set_schedule(user, on):
    if on:
        today = datetime.now(ZoneInfo('Asia/Dhaka')).date()
        user.schedule_from_date = today - timedelta(days=1)
        user.schedule_to_date = today + timedelta(days=1)
        user.schedule_start_time = time(0, 0, 0)
        user.schedule_end_time = time(23, 59, 59)
    else:
        user.schedule_from_date = None
        user.schedule_to_date = None
        user.schedule_start_time = None
        user.schedule_end_time = None
    db.session.commit()


def pick_id():
    u = assign_lead_owner_auto()
    db.session.rollback()
    return u.id if u else None


def main():
    with app.app_context():
        db.create_all()
        SystemSetting.set('auto_assign_mode', 'lowest_count')
        db.session.commit()
        # Isolate the pool: deactivate every other owner/executive left in
        # the shared testing DB by earlier suites.
        for u in User.query.filter(User.role.in_([UserRole.LEAD_OWNER, UserRole.EXECUTIVE])).all():
            u.is_active = False
        db.session.commit()

        admin = mk_user('D30 Admin', 'd30_admin@test.com', 'Admin@123', UserRole.ADMIN)
        a = mk_user('D30 Owner A', 'd30_a@test.com', 'Owner@123', UserRole.LEAD_OWNER, cap=2)
        b = mk_user('D30 Owner B', 'd30_b@test.com', 'Owner@123', UserRole.LEAD_OWNER, cap=2)
        a.is_active = True
        b.is_active = True
        db.session.commit()
        IDS['a'], IDS['b'] = a.id, b.id
        give_leads(a, 2)   # A exactly AT capacity (2/2)
        give_leads(b, 3)   # B OVER capacity (3/2)

        # 1) Both scheduled, both full → lowest-count scheduled owner wins (A)
        set_schedule(a, True)
        set_schedule(b, True)
        check('scheduled pool ignores capacity, lowest count picked',
              pick_id() == a.id, f"pick={pick_id()} A={a.id} B={b.id}")

        # 2) Only B scheduled (and over capacity) → B
        set_schedule(a, False)
        check('only scheduled owner picked despite being over capacity',
              pick_id() == b.id, f"pick={pick_id()}")

        # 3) Nobody scheduled, both full → None (fallback still respects cap)
        set_schedule(b, False)
        check('fallback pool still respects capacity (None when all full)',
              pick_id() is None, f"pick={pick_id()}")

        # 4) Nobody scheduled, B gets headroom → B (A still full, skipped)
        b.max_lead_capacity = 99
        db.session.commit()
        check('fallback picks the owner with room', pick_id() == b.id,
              f"pick={pick_id()}")

    # 5) End-to-end: the client's scenario — CSV import while B is the
    #    scheduled owner and over the old capacity lands on B.
    with app.app_context():
        b = User.query.get(IDS['b'])
        b.max_lead_capacity = 2  # back to over-capacity (3 active)
        db.session.commit()
        set_schedule(b, True)
        a = User.query.get(IDS['a'])
        set_schedule(a, False)
    r = client.post('/api/auth/login', json={'email': 'd30_admin@test.com', 'password': 'Admin@123'})
    assert r.status_code == 200, r.get_data(as_text=True)
    token = r.get_json()['access_token']
    csv_text = "Full Name,Phone\nD30 Imported Lead,01777779999\n"
    r = client.post('/api/leads/import',
                    data={'file': (io.BytesIO(csv_text.encode()), 'd30.csv')},
                    headers={'Authorization': f'Bearer {token}'},
                    content_type='multipart/form-data')
    body = r.get_json() or {}
    with app.app_context():
        c = Contact.query.filter_by(phone_raw='01777779999').first()
        opp = (Opportunity.query.filter_by(contact_id=c.id, is_deleted=False)
               .order_by(Opportunity.id.desc()).first()) if c else None
        check('import during B schedule window lands on B (over capacity)',
              r.status_code == 200 and body.get('imported') == 1
              and opp is not None and opp.assigned_to_id == IDS['b'],
              f"status={r.status_code} imported={body.get('imported')} "
              f"assigned_to={opp.assigned_to_id if opp else None} B={IDS['b']}")

    passed = sum(1 for _, ok in CHECKS if ok)
    print(f"\n{passed}/{len(CHECKS)} checks passed")
    sys.exit(0 if passed == len(CHECKS) else 1)


if __name__ == '__main__':
    main()
