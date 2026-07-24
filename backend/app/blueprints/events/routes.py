"""
Events / Corporate Calendar Routes.
Module 02: Corporate calendar and event management.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from . import events_bp
from ...extensions import db
from ...models import Event, User, Appointment, Task, Contact, Opportunity
from ...utils.rbac import get_current_user_role, require_min_role

@events_bp.route("/", methods=["GET"])
@jwt_required()
def list_events():
    """List all events, optionally filtered by date range."""
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    event_type = request.args.get("type")

    user_id = get_jwt_identity()
    user_role = get_current_user_role()

    # 1. Base query for Events
    query_evt = Event.query
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
        query_evt = query_evt.filter(Event.created_by_id == user_id)

    events = query_evt.order_by(Event.start_datetime.asc()).all()
    out_list = [e.to_dict() for e in events]

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
                "start": apt.appointment_datetime.isoformat(),
                "end": (apt.appointment_datetime + timedelta(hours=1)).isoformat(),
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
                "start": tsk.due_date.isoformat(),
                "end": (tsk.due_date + timedelta(minutes=30)).isoformat(),
                "created_by_id": tsk.created_by_id,
                "opportunity_id": tsk.opportunity_id,
                "is_all_day": False,
                "color": user.calendar_color if user else "#f59e0b"
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
        for opp in opps:
            contact = Contact.query.get(opp.contact_id)
            contact_name = contact.full_name if contact else "Unknown Contact"
            action_type_name = opp.next_action_type.value if opp.next_action_type else "Follow-up"
            user = User.query.get(opp.assigned_to_id)
            out_list.append({
                "id": f"opp_{opp.id}",
                "title": f"Lead Reminder: {action_type_name} ({contact_name})",
                "description": f"Lead: {contact_name} | Next Action: {action_type_name}",
                "event_type": "REMINDER",
                "start": opp.next_action_deadline.isoformat(),
                "end": (opp.next_action_deadline + timedelta(minutes=30)).isoformat(),
                "created_by_id": opp.assigned_to_id,
                "opportunity_id": opp.id,
                "contact_id": opp.contact_id,
                "is_all_day": False,
                "color": user.calendar_color if user else "#e11d48"
            })

    return jsonify(out_list), 200


@events_bp.route("/", methods=["POST"])
@jwt_required()
def create_event():
    """Create a new corporate event."""
    user_id = get_jwt_identity()
    data = request.get_json()

    required_fields = ["title", "start_datetime"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

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

    event = Event(
        title=data["title"],
        description=data.get("description"),
        event_type=data.get("event_type", "GENERAL"),
        start_datetime=start_dt,
        end_datetime=end_dt,
        is_all_day=data.get("is_all_day", False),
        created_by_id=user_id,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify(event.to_dict()), 201


@events_bp.route("/<int:event_id>", methods=["GET"])
@jwt_required()
def get_event(event_id):
    """Get a single event by ID."""
    event = Event.query.get_or_404(event_id)
    return jsonify(event.to_dict()), 200


@events_bp.route("/<int:event_id>", methods=["PUT"])
@jwt_required()
def update_event(event_id):
    """Update an existing event."""
    user_id = get_jwt_identity()
    event = Event.query.get_or_404(event_id)
    user_role = get_current_user_role()

    # Only creator or admin can edit
    if event.created_by_id != user_id and user_role != "ADMIN":
        return jsonify({"error": "Access denied: only the creator or an Admin can edit this event"}), 403

    data = request.get_json()

    if "title" in data:
        event.title = data["title"]
    if "description" in data:
        event.description = data["description"]
    if "event_type" in data:
        event.event_type = data["event_type"]
    if "is_all_day" in data:
        event.is_all_day = data["is_all_day"]
    if "start_datetime" in data:
        event.start_datetime = datetime.fromisoformat(data["start_datetime"])
    if "end_datetime" in data:
        event.end_datetime = datetime.fromisoformat(data["end_datetime"]) if data["end_datetime"] else (event.start_datetime + timedelta(hours=1))

    db.session.commit()
    return jsonify(event.to_dict()), 200


@events_bp.route("/<int:event_id>", methods=["DELETE"])
@jwt_required()
def delete_event(event_id):
    """Delete an event (creator or Admin only)."""
    user_id = get_jwt_identity()
    user_role = get_current_user_role()
    event = Event.query.get_or_404(event_id)
    
    if event.created_by_id != user_id and user_role != "ADMIN":
        return jsonify({"error": "Access denied"}), 403
    
    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": "Event deleted"}), 200
