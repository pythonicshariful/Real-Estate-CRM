"""Tests for the client Sales & Lead Management requirements (branch
feature/client-lead-requirements):
1. Manager-only response-time analytics + KPI gating
2. Label -> disposition popup submit -> CallLog + persistent Event
3. Excel import with manual column mapping (preview -> map -> import)
4. Manager assignment: schedule/capacity, bulk-assign, EXECUTIVE pool,
   persisted assignment rule (lowest_count / round_robin)

Run: ../.venv/bin/python test_client_requirements.py  (from backend/)
Uses the in-memory testing config; writes nothing to the live dev DB.
"""
import io
import json
import os
import sys
from datetime import datetime, timezone, timedelta

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, SLAEvent, SLAStatus, Event

app = create_app('testing')
client = app.test_client()


def login(email, password):
    res = client.post('/api/auth/login', json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.data}"
    return {"Authorization": f"Bearer {res.json['access_token']}"}


def test_suite():
    print("\nRunning Client Requirements Test Suite...")
    with app.app_context():
        users = {}
        for role, email, name, pw in [
            (UserRole.ADMIN, "req_admin@southeast.com", "Req Admin", "AdminPass123!"),
            (UserRole.MANAGER, "req_mgr@southeast.com", "Req Manager", "ManagerPass123!"),
            (UserRole.EXECUTIVE, "req_exec@southeast.com", "Req Executive", "ExecPass123!"),
            (UserRole.LEAD_OWNER, "req_owner@southeast.com", "Req Owner", "OwnerPass123!"),
        ]:
            u = User(email=email, full_name=name, role=role)
            u.set_password(pw)
            db.session.add(u)
            db.session.flush()
            users[role] = u
        db.session.commit()

        admin_h = login("req_admin@southeast.com", "AdminPass123!")
        mgr_h = login("req_mgr@southeast.com", "ManagerPass123!")
        exec_h = login("req_exec@southeast.com", "ExecPass123!")
        owner_h = login("req_owner@southeast.com", "OwnerPass123!")

        # Create a lead, then assign it to the executive via the manager
        # reassign route (sets assigned_date).
        res = client.post('/api/leads/', headers=admin_h, json={
            "full_name": "Req Test Lead", "phone": "01711112222",
            "email": "reqlead@test.com", "source": "Facebook Ad",
            "profession": "Engineer", "service_type": "Residential Plot",
        })
        assert res.status_code == 201, f"Lead create failed: {res.data}"
        lead_id = res.json['id']
        print(f"   lead #{lead_id} created")
        res = client.put(f'/api/leads/{lead_id}/reassign', headers=mgr_h,
                         json={"assigned_to_id": users[UserRole.EXECUTIVE].id})
        assert res.status_code == 200, f"Reassign failed: {res.data}"

        # 1a. Response-times gating
        print("1. Manager-only response-time gating...")
        res = client.get('/api/reports/response-times', headers=exec_h)
        assert res.status_code == 403, f"Executive must get 403, got {res.status_code}"
        res = client.get('/api/reports/response-times', headers=mgr_h)
        assert res.status_code == 200, f"Manager must get 200: {res.data}"
        assert "per_lead" in res.json and "per_executive" in res.json
        print("   [PASS] executive 403 / manager 200 on /api/reports/response-times")

        res = client.get('/api/reports/kpis', headers=exec_h)
        assert res.status_code == 200
        assert "speed_to_lead" not in res.json, "Executive must not see speed_to_lead in KPIs"
        assert "sla_compliance" not in res.json, "Executive must not see sla_compliance in KPIs"
        res = client.get('/api/reports/kpis', headers=mgr_h)
        assert "speed_to_lead" in res.json and "sla_compliance" in res.json
        print("   [PASS] KPIs omit response-time fields for executive, include them for manager")

        # 1b/2. First call resolves SLA + disposition creates an Event
        print("2. Disposition submit -> CallLog + Event + SLA resolution...")
        lead = Opportunity.query.get(lead_id)
        sla = SLAEvent(opportunity_id=lead_id, assigned_at=lead.assigned_date,
                       status=SLAStatus.PENDING)
        db.session.add(sla)
        db.session.commit()
        followup = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0).isoformat()
        res = client.post(f'/api/leads/{lead_id}/calls', headers=exec_h, json={
            "notes": "Customer wants a site visit next week",
            "activity_label": "Hot Lead",
            "next_action_deadline": followup,
            "next_action_type": "Follow-up",
            "disposition_activity_type": "Follow-up",
            "connected": True,
        })
        assert res.status_code == 201, f"Disposition call failed: {res.data}"
        event_id = res.json.get('event_id')
        assert event_id, f"Disposition must create an Event, got: {res.json}"
        print(f"   call logged, event #{event_id} created")
        ev = Event.query.get(event_id)
        assert ev is not None and ev.lead_id == lead_id
        assert ev.event_type == "Follow-up"
        sla_after = SLAEvent.query.filter_by(opportunity_id=lead_id).first()
        assert sla_after.status == SLAStatus.RESOLVED, f"SLA must resolve on first call, got {sla_after.status}"
        print("   [PASS] first call resolved SLA to RESOLVED")

        # Virtual reminder suppressed for this lead+deadline, real event present
        res = client.get('/api/events/', headers=exec_h)
        assert res.status_code == 200
        ids = [e.get('id') for e in res.json]
        assert event_id in ids, "Real disposition Event must appear in GET /api/events/"
        assert f"opp_{lead_id}" not in ids, "Virtual opp_ reminder must be suppressed once a real Event exists"
        print("   [PASS] virtual reminder suppressed, real Event listed")

        # Manual event edit via existing PUT endpoint
        res = client.put(f'/api/events/{event_id}', headers=exec_h,
                         json={"title": "Follow-up: Req Test Lead (edited)"})
        assert res.status_code == 200 and res.json['title'].endswith("(edited)")
        res = client.get(f'/api/events/lead/{lead_id}', headers=exec_h)
        assert res.status_code == 200 and any(e['id'] == event_id for e in res.json)
        print("   [PASS] disposition Event editable via PUT /api/events/<id>")

        # Response-time data now shows this lead as contacted (manager only)
        res = client.get('/api/reports/response-times', headers=mgr_h)
        row = next(r for r in res.json['per_lead'] if r['lead_id'] == lead_id)
        assert row['status'] == 'contacted' and row['response_minutes'] is not None and row['response_minutes'] >= 0
        assert row['assigned_date'] and row['first_contact_date']
        exec_rows = [e for e in res.json['per_executive'] if e['assigned_to_id'] == users[UserRole.EXECUTIVE].id]
        assert exec_rows and exec_rows[0]['avg_response_minutes'] is not None
        print(f"   [PASS] response-time row: {row['response_minutes']} min, assigned_date/first_contact_date present")

        # 3. Excel import with manual mapping
        print("3. Excel import with mapping (preview -> map -> import)...")
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Customer", "Mobile No", "Extra Junk"])
        ws.append(["Excel Mapping Lead", "01822334455", "ignore-me"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        res = client.post('/api/leads/import/preview', headers=admin_h,
                          data={'file': (io.BytesIO(buf.getvalue()), 'leads.xlsx')},
                          content_type='multipart/form-data')
        assert res.status_code == 200, f"Preview failed: {res.data}"
        assert res.json['headers'] == ["Customer", "Mobile No", "Extra Junk"]
        assert res.json['suggested_mapping']["Customer"] == "full_name"
        assert res.json['suggested_mapping']["Mobile No"] == "phone"
        assert res.json['total_rows'] == 1
        mapping = {"Customer": "full_name", "Mobile No": "phone", "Extra Junk": ""}
        res = client.post('/api/leads/import', headers=admin_h,
                          data={'file': (io.BytesIO(buf.getvalue()), 'leads.xlsx'),
                                'mapping': json.dumps(mapping),
                                'duplicate_strategy': 'merge'},
                          content_type='multipart/form-data')
        assert res.status_code == 200, f"Excel import failed: {res.data}"
        assert res.json['created_count'] == 1, res.json
        from app.models import Contact
        from app.utils.phone import normalize_phone
        contact = Contact.query.filter_by(phone_normalized=normalize_phone("01822334455")).first()
        assert contact is not None and contact.full_name == "Excel Mapping Lead"
        print("   [PASS] .xlsx preview + mapping import created the lead, junk column skipped")

        # 4. Manager assignment
        print("4. Manager assignment rights + EXECUTIVE pool + rule setting...")
        res = client.put(f"/api/team/lead-owners/{users[UserRole.EXECUTIVE].id}",
                         headers=exec_h, json={"max_lead_capacity": 5})
        assert res.status_code == 403, "Executive must not set schedules/capacity"
        res = client.put(f"/api/team/lead-owners/{users[UserRole.EXECUTIVE].id}",
                         headers=mgr_h, json={"max_lead_capacity": 5,
                                              "schedule_start_time": "09:00",
                                              "schedule_end_time": "18:00"})
        assert res.status_code == 200, f"Manager schedule/capacity update failed: {res.data}"
        assert res.json['user']['max_lead_capacity'] == 5
        res = client.get(f"/api/team/lead-owners", headers=mgr_h)
        assert res.status_code == 200
        print("   [PASS] manager can set schedule/capacity, executive cannot")

        res = client.post('/api/leads/bulk-assign', headers=mgr_h,
                          json={"lead_ids": [lead_id], "owner_id": users[UserRole.EXECUTIVE].id})
        assert res.status_code == 200, f"Manager bulk-assign failed: {res.data}"
        res = client.post('/api/leads/bulk-assign', headers=exec_h,
                          json={"lead_ids": [lead_id], "owner_id": users[UserRole.EXECUTIVE].id})
        assert res.status_code == 403, "Executive must not bulk-assign"
        print("   [PASS] manager bulk-assign works, executive gets 403")

        res = client.put('/api/leads/assignment-rule', headers=mgr_h,
                         json={"auto_assign_mode": "round_robin"})
        assert res.status_code == 200, f"Assignment rule set failed: {res.data}"
        res = client.get('/api/leads/assignment-rule', headers=mgr_h)
        assert res.json['auto_assign_mode'] == 'round_robin'
        from app.tasks import assign_lead_owner_auto
        picked = assign_lead_owner_auto(app=app)
        assert picked is not None and picked.role in (UserRole.EXECUTIVE, UserRole.LEAD_OWNER), \
            f"Auto-assign must pick an EXECUTIVE/LEAD_OWNER, got {picked}"
        print(f"   [PASS] round_robin rule persisted; auto-assign picked {picked.full_name} ({picked.role.value})")
        client.put('/api/leads/assignment-rule', headers=mgr_h, json={"auto_assign_mode": "lowest_count"})
        db.session.commit()

        print("\nALL CLIENT REQUIREMENTS TESTS PASSED SUCCESSFULLY! (4/4 groups)\n")


if __name__ == '__main__':
    test_suite()
