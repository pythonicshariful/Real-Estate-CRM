"""Tests for the Leads list filters (GET /api/leads/ query params):
source, created_from/created_to (Dhaka dates), followup (overdue/today/upcoming).

Run: venv/bin/python test_lead_filters.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import os
import sys
from datetime import datetime, timezone, timedelta

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, Contact, PipelineStage

app = create_app('testing')
client = app.test_client()

DHAKA = timezone(timedelta(hours=6))


def login(email, password):
    res = client.post('/api/auth/login', json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.data}"
    return {"Authorization": f"Bearer {res.json['access_token']}"}


def mk_lead(admin_h, name, phone, source, created_at=None, deadline=None):
    res = client.post('/api/leads/', headers=admin_h, json={
        "full_name": name, "phone": phone, "email": f"{phone}@test.com",
        "source": source, "profession": "Engineer",
        "service_type": "Residential Plot",
    })
    assert res.status_code == 201, f"Lead create failed: {res.data}"
    lead_id = res.json['id']
    with app.app_context():
        opp = Opportunity.query.get(lead_id)
        if created_at is not None:
            opp.created_at = created_at
        if deadline is not None:
            opp.next_action_deadline = deadline
        db.session.commit()
    return lead_id


def ids(res):
    assert res.status_code == 200, res.data
    return {l["id"] for l in res.json}


def test_suite():
    print("\nRunning Lead Filters Test Suite...")
    passed = 0
    with app.app_context():
        admin = User(email="flt_admin@southeast.com", full_name="Flt Admin", role=UserRole.ADMIN)
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        admin_h = login("flt_admin@southeast.com", "AdminPass123!")

        now_utc = datetime.now(timezone.utc)
        today_dhaka = now_utc.astimezone(DHAKA).date()
        # A lead created yesterday (Dhaka) at 20:00 Dhaka = 14:00 UTC same day;
        # a lead created today (Dhaka) at 02:00 Dhaka = 20:00 UTC yesterday.
        yday_20_dhaka = datetime(today_dhaka.year, today_dhaka.month, today_dhaka.day, 20, 0, tzinfo=DHAKA) - timedelta(days=1)
        today_02_dhaka = datetime(today_dhaka.year, today_dhaka.month, today_dhaka.day, 2, 0, tzinfo=DHAKA)
        old = now_utc - timedelta(days=10)

        a = mk_lead(admin_h, "Filter Meta", "01790000001", "Meta Lead Ads",
                    created_at=yday_20_dhaka.astimezone(timezone.utc).replace(tzinfo=None),
                    deadline=(now_utc - timedelta(hours=2)).replace(tzinfo=None))  # overdue
        b = mk_lead(admin_h, "Filter Manual", "01790000002", "Manual",
                    created_at=today_02_dhaka.astimezone(timezone.utc).replace(tzinfo=None),
                    deadline=(now_utc + timedelta(hours=2)).replace(tzinfo=None))  # due today
        c = mk_lead(admin_h, "Filter Import", "01790000003", "CSV Import",
                    created_at=old.replace(tzinfo=None),
                    deadline=(now_utc + timedelta(days=3)).replace(tzinfo=None))  # upcoming
        d = mk_lead(admin_h, "Filter NoDeadline", "01790000004", "Meta Lead Ads",
                    created_at=old.replace(tzinfo=None), deadline=None)

        # -- 1. source filter -------------------------------------------------
        got = ids(client.get('/api/leads/?source=Meta%20Lead%20Ads', headers=admin_h))
        assert {a, d} <= got and b not in got and c not in got, got
        print("   [PASS] source=Meta Lead Ads returns only Meta leads")
        passed += 1

        # -- 2. created date range (Dhaka dates) ------------------------------
        # Yesterday (Dhaka): only A (created 20:00 Dhaka yesterday).
        got = ids(client.get(f'/api/leads/?created_from={today_dhaka - timedelta(days=1)}&created_to={today_dhaka - timedelta(days=1)}', headers=admin_h))
        assert got == {a}, got
        # Today (Dhaka): only B (created 02:00 Dhaka today, though 20:00 UTC yesterday).
        got = ids(client.get(f'/api/leads/?created_from={today_dhaka}&created_to={today_dhaka}', headers=admin_h))
        assert got == {b}, got
        print("   [PASS] created_from/to use Dhaka dates (02:00 Dhaka counts as today)")
        passed += 1

        # Bad date -> 400
        res = client.get('/api/leads/?created_from=not-a-date', headers=admin_h)
        assert res.status_code == 400, res.status_code
        print("   [PASS] invalid created_from returns 400")
        passed += 1

        # -- 3. follow-up due --------------------------------------------------
        got = ids(client.get('/api/leads/?followup=overdue', headers=admin_h))
        assert got == {a}, got
        # "Due today" includes today's already-passed deadline (A): it is
        # still due today. Overdue is the past-due subset of today+earlier.
        got = ids(client.get('/api/leads/?followup=today', headers=admin_h))
        assert got == {a, b}, got
        got = ids(client.get('/api/leads/?followup=upcoming', headers=admin_h))
        assert got == {c}, got
        print("   [PASS] followup overdue/today/upcoming split correctly (no-deadline lead in none)")
        passed += 1

        # -- 4. filters combine (AND) -----------------------------------------
        got = ids(client.get('/api/leads/?source=Meta%20Lead%20Ads&followup=overdue', headers=admin_h))
        assert got == {a}, got
        got = ids(client.get('/api/leads/?source=Manual&followup=overdue', headers=admin_h))
        assert got == set(), got
        print("   [PASS] source + followup combine with AND logic")
        passed += 1

        # cleanup
        for lid in (a, b, c, d):
            opp = Opportunity.query.get(lid)
            Contact.query.filter_by(id=opp.contact_id).delete()
            db.session.delete(opp)
        db.session.delete(admin)
        db.session.commit()
        print(f"\nALL LEAD FILTER TESTS PASSED SUCCESSFULLY! ({passed} checks)\n")


if __name__ == "__main__":
    test_suite()
