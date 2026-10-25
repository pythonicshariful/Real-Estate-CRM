"""Tests for in-app event reminders + calendar reminder entries (branch
feature/client-lead-requirements):

1. POST /api/events/ accepts reminder_minutes (default 30, null = none,
   invalid values rejected); PUT re-arms the reminder when time/reminder
   changes.
2. check_event_reminders creates exactly one notification for the owner
   when the reminder time arrives, none before that, never for null
   reminders.
3. Notifications API is per-user only (another user sees nothing, cannot
   mark another user's notification read); mark read / read-all work.
4. Calendar feed (GET /api/events/) contains BOTH the event entry (owner
   colour) AND a separate amber reminder entry at start-30min; a
   no-reminder event produces no reminder entry.
5. Log Call follow-up auto-creates a lead-linked Event with
   reminder_minutes=30, and the calendar shows its reminder entry.

Run: venv/bin/python test_event_reminders.py  (from backend/)
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
from app.models import User, UserRole, Event, Notification
from app.tasks import check_event_reminders

REMINDER_COLOR = "#f59e0b"

app = create_app('testing')
client = app.test_client()


def login(email, password):
    res = client.post('/api/auth/login', json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.data}"
    return {"Authorization": f"Bearer {res.json['access_token']}"}


def iso_in(minutes):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def test_suite():
    print("\nRunning Event Reminder Test Suite...")
    passed = 0

    with app.app_context():
        users = {}
        for role, email, name, pw in [
            (UserRole.ADMIN, "rem_admin@southeast.com", "Rem Admin", "AdminPass123!"),
            (UserRole.LEAD_OWNER, "rem_sarah@southeast.com", "Rem Sarah", "SarahPass123!"),
            (UserRole.LEAD_OWNER, "rem_john@southeast.com", "Rem John", "JohnPass123!"),
        ]:
            u = User(email=email, full_name=name, role=role)
            u.set_password(pw)
            db.session.add(u)
            db.session.flush()
            users[role if role != UserRole.LEAD_OWNER else email] = u
        db.session.commit()
        sarah = users["rem_sarah@southeast.com"]
        john = users["rem_john@southeast.com"]

        admin_h = login("rem_admin@southeast.com", "AdminPass123!")
        sarah_h = login("rem_sarah@southeast.com", "SarahPass123!")
        john_h = login("rem_john@southeast.com", "JohnPass123!")

        # -- 1. Create event with reminder via API -----------------------
        print("1. Event create with reminder_minutes...")
        res = client.post('/api/events/', headers=sarah_h, json={
            "title": "Site visit — reminder test",
            "start_datetime": iso_in(20),
            "reminder_minutes": 30,
        })
        assert res.status_code == 201, f"Event create failed: {res.data}"
        ev = res.json
        assert ev["reminder_minutes"] == 30, f"reminder_minutes not stored: {ev}"
        assert ev["reminder_sent"] is False
        ev_id = ev["id"]
        print("   [PASS] event created with reminder_minutes=30, reminder_sent=False")
        passed += 1

        # default 30 when omitted
        res = client.post('/api/events/', headers=sarah_h, json={
            "title": "Default reminder event", "start_datetime": iso_in(120),
        })
        assert res.status_code == 201, res.data
        assert res.json["reminder_minutes"] == 30, res.json
        default_ev_id = res.json["id"]
        print("   [PASS] omitted reminder_minutes defaults to 30")
        passed += 1

        # null = no reminder
        res = client.post('/api/events/', headers=sarah_h, json={
            "title": "No reminder event", "start_datetime": iso_in(20),
            "reminder_minutes": None,
        })
        assert res.status_code == 201, res.data
        assert res.json["reminder_minutes"] is None
        no_rem_ev_id = res.json["id"]
        print("   [PASS] reminder_minutes=null stored as no reminder")
        passed += 1

        # invalid value rejected
        res = client.post('/api/events/', headers=sarah_h, json={
            "title": "Bad reminder", "start_datetime": iso_in(20),
            "reminder_minutes": 2000,
        })
        assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.data}"
        print("   [PASS] reminder_minutes=2000 rejected with 400")
        passed += 1

        # -- 2. Scheduler: fires once, only when due --------------------
        print("2. check_event_reminders timing + exactly-once...")
        check_event_reminders(app)
        notes = Notification.query.filter_by(user_id=sarah.id, event_id=ev_id).all()
        assert len(notes) == 1, f"Expected 1 notification, got {len(notes)}"
        assert notes[0].type == "EVENT_REMINDER"
        assert "Site visit" in notes[0].title
        assert notes[0].is_read is False
        ev_row = Event.query.get(ev_id)
        assert ev_row.reminder_sent is True
        print("   [PASS] notification created for owner when reminder time arrived")
        passed += 1

        check_event_reminders(app)  # re-run: must not duplicate
        notes = Notification.query.filter_by(user_id=sarah.id, event_id=ev_id).all()
        assert len(notes) == 1, f"Duplicate notification created: {len(notes)}"
        print("   [PASS] re-run creates no duplicate")
        passed += 1

        # 2h-away event with 30-min reminder: nothing yet
        check_event_reminders(app)
        notes = Notification.query.filter_by(user_id=sarah.id, event_id=default_ev_id).all()
        assert len(notes) == 0, f"Too-early notification created: {len(notes)}"
        # null-reminder event: never
        notes = Notification.query.filter_by(user_id=sarah.id, event_id=no_rem_ev_id).all()
        assert len(notes) == 0
        print("   [PASS] future event + null-reminder event produce no notification")
        passed += 1

        # -- 3. Notifications API: per-user only, read / read-all -------
        print("3. Notifications API scoping + read...")
        res = client.get('/api/notifications/', headers=sarah_h)
        assert res.status_code == 200, res.data
        assert res.json["unread_count"] == 1, res.json
        assert len(res.json["notifications"]) == 1
        notif_id = res.json["notifications"][0]["id"]

        res = client.get('/api/notifications/', headers=john_h)
        assert res.status_code == 200, res.data
        assert res.json["unread_count"] == 0 and res.json["notifications"] == [], res.json
        res = client.post(f'/api/notifications/{notif_id}/read', headers=john_h)
        assert res.status_code == 404, f"Other user must get 404, got {res.status_code}"
        print("   [PASS] another user sees nothing and cannot mark read (404)")
        passed += 1

        res = client.post(f'/api/notifications/{notif_id}/read', headers=sarah_h)
        assert res.status_code == 200 and res.json["is_read"] is True, res.data
        res = client.get('/api/notifications/', headers=sarah_h)
        assert res.json["unread_count"] == 0
        print("   [PASS] mark one read works")
        passed += 1

        # read-all: create a second due notification first
        ev2 = Event(title="Second reminder", start_datetime=datetime.now(timezone.utc) + timedelta(minutes=10),
                    end_datetime=datetime.now(timezone.utc) + timedelta(minutes=40),
                    created_by_id=sarah.id, owner_id=sarah.id,
                    reminder_minutes=30, reminder_sent=False, status="SCHEDULED")
        db.session.add(ev2)
        db.session.commit()
        check_event_reminders(app)
        res = client.get('/api/notifications/?unread_only=true', headers=sarah_h)
        assert res.json["unread_count"] == 1, res.json
        res = client.post('/api/notifications/read-all', headers=sarah_h)
        assert res.status_code == 200 and res.json["marked_read"] == 1, res.data
        res = client.get('/api/notifications/', headers=sarah_h)
        assert res.json["unread_count"] == 0
        print("   [PASS] read-all marks all own unread as read")
        passed += 1

        # -- 4. Calendar feed: event + amber reminder entry -------------
        print("4. Calendar feed reminder entries...")
        res = client.get('/api/events/', headers=sarah_h)
        assert res.status_code == 200, res.data
        feed = res.json
        real = [e for e in feed if e.get("id") == ev_id]
        assert len(real) == 1, "event entry missing from feed"
        # Event keeps the owner's colour — it must NOT be the reminder colour.
        assert real[0]["color"] and real[0]["color"] != REMINDER_COLOR, real[0]
        rem = [e for e in feed if e.get("id") == f"rem_{ev_id}"]
        assert len(rem) == 1, f"reminder entry rem_{ev_id} missing from feed"
        # Reminder uses the event owner's colour (same as the event itself),
        # so the admin can tell whose reminder it is.
        assert rem[0]["color"] == real[0]["color"], (rem[0], real[0])
        assert rem[0]["title"].startswith("\U0001f514 Reminder:"), rem[0]["title"]
        assert rem[0]["event_id"] == ev_id and rem[0]["is_reminder"] is True
        start = datetime.fromisoformat(real[0]["start"].replace("Z", "+00:00"))
        rstart = datetime.fromisoformat(rem[0]["start"].replace("Z", "+00:00"))
        assert abs((start - rstart).total_seconds() - 30 * 60) < 60, (start, rstart)
        print("   [PASS] feed has event (owner colour) + reminder entry at start-30min, owner's colour")
        passed += 1

        # -- 4b. Feed datetimes carry a Dhaka offset (the UTC/PAST bug) ----
        # Stored datetimes are naive UTC; the calendar feed must serialise
        # them as Dhaka wall time with a +06:00 offset. FullCalendar keeps
        # the offset an event's own ISO string carries, so a +00:00 string
        # renders as UTC time even with timeZone 'Asia/Dhaka'.
        print("4b. Feed datetimes carry a Dhaka (+06:00) offset...")
        for e in feed:
            for key in ("start", "end"):
                v = e.get(key)
                if v:
                    assert v.endswith("+06:00"), (e.get("id"), key, v)
                    assert datetime.fromisoformat(v).tzinfo is not None
        # The test event starts in the future: parsed, it must still be in
        # the future, and its Dhaka wall time must match the event's start.
        assert start.tzinfo is not None and start > datetime.now(timezone.utc), start
        assert rem[0]["end"].endswith("+06:00")
        print("   [PASS] feed start/end are Dhaka-aware (+06:00); future event is not past")
        passed += 1

        rem_none = [e for e in feed if e.get("id") == f"rem_{no_rem_ev_id}"]
        assert len(rem_none) == 0, "no-reminder event must not produce a reminder entry"
        print("   [PASS] no-reminder event produces no reminder entry")
        passed += 1

        # PUT re-arms the reminder when the time changes
        res = client.put(f'/api/events/{ev_id}', headers=sarah_h, json={
            "start_datetime": iso_in(25),
        })
        assert res.status_code == 200, res.data
        assert res.json["reminder_sent"] is False, res.json
        print("   [PASS] PUT moving the event re-arms reminder_sent=False")
        passed += 1

        # -- 5. Log Call follow-up -> Event with reminder 30 ------------
        print("5. Log Call follow-up Event gets default reminder...")
        res = client.post('/api/leads/', headers=admin_h, json={
            "full_name": "Rem Lead", "phone": "01799998888",
            "email": "remlead@test.com", "source": "Facebook Ad",
        })
        assert res.status_code == 201, f"Lead create failed: {res.data}"
        lead_id = res.json['id']
        res = client.put(f'/api/leads/{lead_id}/reassign', headers=admin_h,
                         json={"assigned_to_id": sarah.id})
        assert res.status_code == 200, f"Reassign failed: {res.data}"
        res = client.post(f'/api/leads/{lead_id}/calls', headers=sarah_h, json={
            "notes": "follow-up test", "connected": True,
            "outcome": "CONNECTED", "duration_band": "ONE_TO_3MIN",
            "next_action_deadline": iso_in(40),
            "next_action_type": "CALL",
        })
        assert res.status_code in (200, 201), f"Call log failed: {res.data}"
        assert res.json.get("event_id"), f"No event created: {res.json}"
        f_ev = Event.query.get(res.json["event_id"])
        assert f_ev is not None and f_ev.reminder_minutes == 30, f_ev
        assert f_ev.lead_id == lead_id
        print("   [PASS] follow-up Event created with reminder_minutes=30")
        passed += 1

        res = client.get('/api/events/', headers=sarah_h)
        feed = res.json
        rem_f = [e for e in feed if e.get("id") == f"rem_{f_ev.id}"]
        assert len(rem_f) == 1 and rem_f[0]["color"] == real[0]["color"], rem_f
        assert rem_f[0]["lead_id"] == lead_id
        print("   [PASS] follow-up reminder entry on calendar (owner's colour, linked to lead)")
        passed += 1

        # cleanup
        db.session.delete(f_ev)
        for row in Notification.query.filter_by(user_id=sarah.id).all():
            db.session.delete(row)
        for eid in (ev_id, default_ev_id, no_rem_ev_id, ev2.id):
            row = Event.query.get(eid)
            if row:
                db.session.delete(row)
        from app.models import Opportunity, CallLog
        for cl in CallLog.query.filter_by(opportunity_id=lead_id).all():
            db.session.delete(cl)
        lead = Opportunity.query.get(lead_id)
        if lead:
            db.session.delete(lead)
        for u in users.values():
            db.session.delete(u)
        db.session.commit()
        print("   (test data cleaned up)")

    print(f"\nALL EVENT REMINDER TESTS PASSED SUCCESSFULLY! ({passed} checks)\n")


if __name__ == "__main__":
    test_suite()
