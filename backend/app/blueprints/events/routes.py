"""
Events / Corporate Calendar Routes.
Module 02: Corporate calendar and event management.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from . import events_bp
from ...extensions import db
from ...models import Event, User, Appointment, Task, Contact, Opportunity, dhaka_iso
from ...utils.rbac import get_current_user_role, require_min_role

# Fallback colour for a reminder entry when its owner has no calendar
# colour set. Reminder entries normally use the EVENT OWNER's colour
# (admin-set per owner), so the admin can tell whose reminder it is;
# the "Reminder:" title is what distinguishes them from real events.
REMINDER_COLOR = "#f59e0b"  # amber (fallback only)


def _parse_reminder_minutes(value):
    """Validate a reminder_minutes value.

    Returns (minutes_or_None, error_or_None). None means "no reminder".
    Accepts an int 0..1440 (0 = remind at the event start time).
    """
    if value is None or value == "":
        return None, None
    if isinstance(value, bool):
        return None, "reminder_minutes must be an integer number of minutes"
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return None, "reminder_minutes must be an integer number of minutes"
    if minutes < 0 or minutes > 1440:
        return None, "reminder_minutes must be between 0 and 1440"
    return minutes, None


def _can_view_event(event, user_id, user_role):
    """
    Visibility rules for a single calendar event.

    • ADMIN sees everything (colour-coded per owner in the UI)
    • Everyone else sees events they created, events owned by them, and
      events linked to a lead assigned to them.
    """
    if user_role == "ADMIN":
        return True
    if event.created_by_id == user_id:
        return True
    if event.owner_id == user_id:
        return True
    if event.lead is not None and event.lead.assigned_to_id == user_id:
        return True
    return False


@events_bp.route("/", methods=["GET"])
@jwt_required()
def list_events():
    """
    List calendar items, optionally filtered by date range.

    Events carry an `color` (the owning Lead Owner's calendar colour) plus
    lead linkage info so the UI can colour-code and deep-link them.
    Pass `?lead_id=N` to fetch the events of a single lead.
    """
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    event_type = request.args.get("type")
    lead_filter = request.args.get("lead_id")

    user_id = int(get_jwt_identity())
    user_role = get_current_user_role()

    # 1. Base query for Events
    query_evt = Event.query

    if lead_filter:
        try:
            query_evt = query_evt.filter(Event.lead_id == int(lead_filter))
        except ValueError:
            return jsonify({"error": "Invalid lead_id"}), 400
    if start_str:
        try:
            start_dt = datetime.fromisoformat(start_str)
            query_evt = query_evt.filter(Event.start_datetime >= start_dt)
        except ValueError:
            return jsonify({"error": "Invalid start date format (ISO 8601 required)"}), 400
    if end_str:
        try:
            end_dt = datetime.fromisoformat(end_str)
            query_evt = query_evt.filter(Event.end_datetime <= end_dt)
        except ValueError:
            return jsonify({"error": "Invalid end date format (ISO 8601 required)"}), 400

    if event_type:
        query_evt = query_evt.filter(Event.event_type == event_type)

    if user_role != "ADMIN":
        # Own events + events on leads assigned to me
        query_evt = query_evt.filter(
            db.or_(
                Event.created_by_id == user_id,
                Event.owner_id == user_id,
                Event.lead_id.in_(
                    db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
                ),
            )
        )

    events = query_evt.order_by(Event.start_datetime.asc()).all()
    out_list = [e.to_dict() for e in events]
    # The calendar feed must carry Dhaka (+06:00) offsets, not UTC ones:
    # FullCalendar displays an event in the offset its own ISO string
    # carries, so +00:00 strings render as UTC times despite the calendar's
    # timeZone 'Asia/Dhaka'. (to_dict() itself stays UTC — other callers
    # parse the instant with new Date(...).)
    for _ev, _d in zip(events, out_list):
        _d["start"] = dhaka_iso(_ev.start_datetime)
        _d["end"] = dhaka_iso(_ev.end_datetime) if _ev.end_datetime else None

    # 1b. Reminder entries for real Events — one calendar entry per event
    # with a reminder, placed at (start - reminder_minutes) in the EVENT
    # OWNER's colour (admin-set per owner, same as the event itself).
    # A reminder is a schedule entry, not a one-time popup:
    # it stays on the calendar even after it has fired / been read.
    # When the feed is filtered to a reminder type, the section-1 query
    # above yields nothing, so fetch the visible events with reminders
    # separately in that case.
    if not event_type or event_type in ("REMINDER", "EVENT_REMINDER"):
        reminder_events = events
        if event_type in ("REMINDER", "EVENT_REMINDER"):
            rq = Event.query.filter(Event.reminder_minutes.isnot(None))
            if user_role != "ADMIN":
                rq = rq.filter(
                    db.or_(
                        Event.created_by_id == user_id,
                        Event.owner_id == user_id,
                        Event.lead_id.in_(
                            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
                        ),
                    )
                )
            reminder_events = rq.order_by(Event.start_datetime.asc()).all()
        for ev in reminder_events:
            if ev.reminder_minutes is None:
                continue
            if (ev.status or "SCHEDULED") != "SCHEDULED":
                continue
            d = ev.to_dict()
            remind_start = ev.start_datetime - timedelta(minutes=ev.reminder_minutes)
            if start_str and remind_start < start_dt:
                continue
            if end_str and remind_start > end_dt:
                continue
            out_list.append({
                "id": f"rem_{ev.id}",
                "title": f"\U0001f514 Reminder: {ev.title}",
                "description": (
                    f"Reminder for event '{ev.title}' — starts "
                    f"{ev.start_datetime.strftime('%d %b %Y, %I:%M %p')}."
                    + (f" Lead: {d.get('lead_name')}." if d.get("lead_name") else "")
                ),
                "event_type": "EVENT_REMINDER",
                "start": dhaka_iso(remind_start),
                "end": dhaka_iso(remind_start + timedelta(minutes=30)),
                "created_by_id": ev.created_by_id,
                "is_all_day": False,
                "color": d.get("color") or REMINDER_COLOR,
                "owner_id": d.get("owner_id"),
                "owner_name": d.get("owner_name"),
                "lead_id": ev.lead_id,
                "lead_name": d.get("lead_name"),
                "lead_phone": d.get("lead_phone"),
                "lead_stage": d.get("lead_stage"),
                "event_id": ev.id,
                "is_reminder": True,
                "reminder_minutes": ev.reminder_minutes,
                "reminder_sent": bool(ev.reminder_sent),
            })

    # 2. Add Appointments (if no specific event_type filter or if type is APPOINTMENT)
    if not event_type or event_type == "APPOINTMENT":
        query_apt = Appointment.query
        if start_str:
            query_apt = query_apt.filter(Appointment.appointment_datetime >= start_dt)
        if end_str:
            query_apt = query_apt.filter(Appointment.appointment_datetime <= end_dt)
        if user_role != "ADMIN":
            # Scheduled by user OR linked lead is assigned to user
            query_apt = query_apt.join(Opportunity, Appointment.opportunity_id == Opportunity.id).filter(
                db.or_(Appointment.scheduled_by_id == user_id, Opportunity.assigned_to_id == user_id)
            )
            
        appointments = query_apt.all()
        for apt in appointments:
            contact = Contact.query.get(apt.contact_id)
            contact_name = contact.full_name if contact else "Unknown Contact"
            opp = Opportunity.query.get(apt.opportunity_id)
            owner_id = opp.assigned_to_id if opp else apt.scheduled_by_id
            user = User.query.get(owner_id) if owner_id else None
            out_list.append({
                "id": f"apt_{apt.id}",
                "title": f"Appointment with {contact_name}",
                "description": f"Location: {apt.location or 'TBD'} | Status: {apt.status.value}",
                "event_type": "APPOINTMENT",
                "start": dhaka_iso(apt.appointment_datetime),
                "end": dhaka_iso(apt.appointment_datetime + timedelta(hours=1)),
                "created_by_id": apt.scheduled_by_id,
                "opportunity_id": apt.opportunity_id,
                "contact_id": apt.contact_id,
                "is_all_day": False,
                "color": user.calendar_color if user else "#10b981"
            })

    # 3. Add Tasks / Reminders (if no specific event_type filter or if type is REMINDER)
    if not event_type or event_type == "REMINDER":
        query_tsk = Task.query
        if start_str:
            query_tsk = query_tsk.filter(Task.due_date >= start_dt)
        if end_str:
            query_tsk = query_tsk.filter(Task.due_date <= end_dt)
        if user_role != "ADMIN":
            query_tsk = query_tsk.filter((Task.assigned_to_id == user_id) | (Task.created_by_id == user_id))
            
        tasks = query_tsk.all()
        for tsk in tasks:
            user = User.query.get(tsk.assigned_to_id)
            out_list.append({
                "id": f"tsk_{tsk.id}",
                "title": f"Task/Reminder: {tsk.title}",
                "description": f"Priority: {tsk.priority.value} | Status: {tsk.status.value} | Details: {tsk.description or 'None'}",
                "event_type": "REMINDER",
                "start": dhaka_iso(tsk.due_date),
                "end": dhaka_iso(tsk.due_date + timedelta(minutes=30)),
                "created_by_id": tsk.created_by_id,
                "opportunity_id": tsk.opportunity_id,
                "is_all_day": False,
                # Tasks are reminders: the assignee's colour, so the admin
                # can tell whose task it is.
                "color": user.calendar_color if user and user.calendar_color else REMINDER_COLOR,
                "is_reminder": True,
            })

    # 4. Add Lead Next Action Deadlines (if no specific event_type filter or if type is REMINDER)
    if not event_type or event_type == "REMINDER":
        query_opp = Opportunity.query.filter(Opportunity.next_action_deadline.isnot(None), Opportunity.is_deleted == False)
        if start_str:
            query_opp = query_opp.filter(Opportunity.next_action_deadline >= start_dt)
        if end_str:
            query_opp = query_opp.filter(Opportunity.next_action_deadline <= end_dt)
        if user_role != "ADMIN":
            query_opp = query_opp.filter(Opportunity.assigned_to_id == user_id)
            
        opps = query_opp.all()
        # Suppress the virtual opp_ reminder when a real, persistent Event
        # already exists for this lead at exactly this deadline (created by
        # a disposition submit). Otherwise the calendar shows the same
        # follow-up twice. Queried independently of any type filter above.
        real_event_keys = {
            (ev.lead_id, ev.start_datetime)
            for ev in Event.query.filter(Event.lead_id.isnot(None)).all()
        }
        for opp in opps:
            if (opp.id, opp.next_action_deadline) in real_event_keys:
                continue
            contact = Contact.query.get(opp.contact_id)
            contact_name = contact.full_name if contact else "Unknown Contact"
            action_type_name = opp.next_action_type.value if opp.next_action_type else "Follow-up"
            user = User.query.get(opp.assigned_to_id)
            out_list.append({
                "id": f"opp_{opp.id}",
                "title": f"Lead Reminder: {action_type_name} ({contact_name})",
                "description": f"Lead: {contact_name} | Next Action: {action_type_name}",
                "event_type": "REMINDER",
                "start": dhaka_iso(opp.next_action_deadline),
                "end": dhaka_iso(opp.next_action_deadline + timedelta(minutes=30)),
                "created_by_id": opp.assigned_to_id,
                "opportunity_id": opp.id,
                "contact_id": opp.contact_id,
                "is_all_day": False,
                # Virtual follow-up reminders use the lead owner's colour.
                "color": user.calendar_color if user and user.calendar_color else REMINDER_COLOR,
                "is_reminder": True,
            })

    return jsonify(out_list), 200


@events_bp.route("/", methods=["POST"])
@jwt_required()
def create_event():
    """
    Create a corporate event.

    Optionally pass `lead_id` to link the event to a lead. Linked events:
      • borrow the lead owner's calendar colour
      • become visible to that lead owner even if someone else created them
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    if not data.get("title"):
        return jsonify({"error": "'title' is required"}), 400
    if not data.get("start_datetime"):
        return jsonify({"error": "'start_datetime' is required"}), 400

    try:
        start_dt = datetime.fromisoformat(data["start_datetime"])
    except ValueError:
        return jsonify({"error": "Invalid start_datetime (ISO 8601 required)"}), 400

    end_dt = None
    if data.get("end_datetime"):
        try:
            end_dt = datetime.fromisoformat(data["end_datetime"])
        except ValueError:
            return jsonify({"error": "Invalid end_datetime (ISO 8601 required)"}), 400
    if not end_dt:
        end_dt = start_dt + timedelta(hours=1)

    # ── Optional lead linkage ────────────────────────────────────────────
    lead_id = data.get("lead_id") or data.get("opportunity_id")
    lead = None
    if lead_id:
        lead = Opportunity.query.filter_by(id=int(lead_id), is_deleted=False).first()
        if not lead:
            return jsonify({"error": f"Lead {lead_id} not found"}), 404

        user_role = get_current_user_role()
        if user_role != "ADMIN" and lead.assigned_to_id != user_id:
            return jsonify({"error": "Access denied: you can only add events to your own leads"}), 403

    owner_id = (lead.assigned_to_id if lead and lead.assigned_to_id else user_id)

    status = data.get("status") or "SCHEDULED"
    if status not in ("SCHEDULED", "COMPLETED", "CANCELLED"):
        return jsonify({"error": "Invalid status (SCHEDULED/COMPLETED/CANCELLED)"}), 400
    priority = data.get("priority") or "NORMAL"
    if priority not in ("LOW", "NORMAL", "HIGH"):
        return jsonify({"error": "Invalid priority (LOW/NORMAL/HIGH)"}), 400

    # Reminder: explicit null = no reminder; omitted = default 30 min before.
    if "reminder_minutes" in data:
        reminder_minutes, rem_err = _parse_reminder_minutes(data.get("reminder_minutes"))
        if rem_err:
            return jsonify({"error": rem_err}), 400
    else:
        reminder_minutes = 30

    event = Event(
        title=data["title"],
        description=data.get("description"),
        event_type=data.get("event_type") or ("LEAD_EVENT" if lead else "GENERAL"),
        start_datetime=start_dt,
        end_datetime=end_dt,
        is_all_day=data.get("is_all_day", False),
        location=data.get("location"),
        status=status,
        priority=priority,
        reminder_minutes=reminder_minutes,
        reminder_sent=False,
        created_by_id=user_id,
        lead_id=lead.id if lead else None,
        owner_id=owner_id,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify(event.to_dict()), 201


@events_bp.route("/<int:event_id>", methods=["GET"])
@jwt_required()
def get_event(event_id):
    """Get a single event by ID."""
    event = Event.query.get_or_404(event_id)
    if not _can_view_event(event, int(get_jwt_identity()), get_current_user_role()):
        return jsonify({"error": "Access denied"}), 403
    return jsonify(event.to_dict()), 200


@events_bp.route("/<int:event_id>", methods=["PUT"])
@jwt_required()
def update_event(event_id):
    """Update an existing event."""
    user_id = int(get_jwt_identity())
    event = Event.query.get_or_404(event_id)
    user_role = get_current_user_role()

    # Only creator, the linked lead's owner, or an Admin can edit
    allowed = event.created_by_id == user_id or user_role == "ADMIN"
    if not allowed and event.lead is not None and event.lead.assigned_to_id == user_id:
        allowed = True
    if not allowed:
        return jsonify({"error": "Access denied: only the creator or an Admin can edit this event"}), 403

    data = request.get_json() or {}

    if "title" in data:
        event.title = data["title"]
    if "description" in data:
        event.description = data["description"]
    if "event_type" in data:
        event.event_type = data["event_type"]
    if "location" in data:
        event.location = data["location"]
    if "status" in data:
        if data["status"] not in ("SCHEDULED", "COMPLETED", "CANCELLED"):
            return jsonify({"error": "Invalid status (SCHEDULED/COMPLETED/CANCELLED)"}), 400
        event.status = data["status"]
    if "priority" in data:
        if data["priority"] not in ("LOW", "NORMAL", "HIGH"):
            return jsonify({"error": "Invalid priority (LOW/NORMAL/HIGH)"}), 400
        event.priority = data["priority"]
    if "is_all_day" in data:
        event.is_all_day = data["is_all_day"]
    if "start_datetime" in data:
        new_start = datetime.fromisoformat(data["start_datetime"])
        if new_start != event.start_datetime:
            # Time moved — the reminder must fire again at the new time.
            event.reminder_sent = False
        event.start_datetime = new_start
    if "end_datetime" in data:
        event.end_datetime = datetime.fromisoformat(data["end_datetime"]) if data["end_datetime"] else (event.start_datetime + timedelta(hours=1))
    if "reminder_minutes" in data:
        reminder_minutes, rem_err = _parse_reminder_minutes(data.get("reminder_minutes"))
        if rem_err:
            return jsonify({"error": rem_err}), 400
        if reminder_minutes != event.reminder_minutes:
            # Reminder setting changed — re-arm it.
            event.reminder_sent = False
        event.reminder_minutes = reminder_minutes

    # Re-link / un-link the event
    if "lead_id" in data:
        new_lead_id = data["lead_id"]
        if new_lead_id:
            new_lead = Opportunity.query.filter_by(id=int(new_lead_id), is_deleted=False).first()
            if not new_lead:
                return jsonify({"error": f"Lead {new_lead_id} not found"}), 404
            if user_role != "ADMIN" and new_lead.assigned_to_id != user_id:
                return jsonify({"error": "Access denied: you can only link events to your own leads"}), 403
            event.lead_id = new_lead.id
            event.owner_id = new_lead.assigned_to_id or user_id
        else:
            event.lead_id = None

    db.session.commit()
    return jsonify(event.to_dict()), 200


@events_bp.route("/<int:event_id>", methods=["DELETE"])
@jwt_required()
def delete_event(event_id):
    """Delete an event (creator, linked lead owner, or Admin only)."""
    user_id = int(get_jwt_identity())
    user_role = get_current_user_role()
    event = Event.query.get_or_404(event_id)

    allowed = event.created_by_id == user_id or user_role == "ADMIN"
    if not allowed and event.lead is not None and event.lead.assigned_to_id == user_id:
        allowed = True
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": "Event deleted"}), 200


# ---------------------------------------------------------------------------
# Lead-scoped convenience endpoints
# ---------------------------------------------------------------------------

@events_bp.route("/lead/<int:lead_id>", methods=["GET"])
@jwt_required()
def list_lead_events(lead_id):
    """All events linked to one lead (used by the Lead Details page)."""
    user_id = int(get_jwt_identity())
    user_role = get_current_user_role()

    lead = Opportunity.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
    if user_role != "ADMIN" and lead.assigned_to_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    events = (Event.query
              .filter(Event.lead_id == lead_id)
              .order_by(Event.start_datetime.asc())
              .all())
    return jsonify([e.to_dict() for e in events]), 200


@events_bp.route("/lead/<int:lead_id>", methods=["POST"])
@jwt_required()
def create_lead_event(lead_id):
    """Shortcut to create an event straight from a lead."""
    body = request.get_json() or {}
    body["lead_id"] = lead_id
    # delegate to create_event() so validation lives in one place
    return create_event()
