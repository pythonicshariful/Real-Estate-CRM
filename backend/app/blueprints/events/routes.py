"""
Events / Corporate Calendar Routes.
Module 02: Corporate calendar and event management.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from . import events_bp
from ...extensions import db
from ...models import Event, User
from ...utils.rbac import get_current_user_role, require_min_role


@events_bp.route("/", methods=["GET"])
@jwt_required()
def list_events():
    """List all events, optionally filtered by date range."""
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    event_type = request.args.get("type")

    query = Event.query

    if start_str:
        try:
            start_dt = datetime.fromisoformat(start_str)
            query = query.filter(Event.start_datetime >= start_dt)
        except ValueError:
            return jsonify({"error": "Invalid start date format (ISO 8601 required)"}), 400

    if end_str:
        try:
            end_dt = datetime.fromisoformat(end_str)
            query = query.filter(Event.end_datetime <= end_dt)
        except ValueError:
            return jsonify({"error": "Invalid end date format (ISO 8601 required)"}), 400

    if event_type:
        query = query.filter(Event.event_type == event_type)

    user_id = get_jwt_identity()
    user_role = get_current_user_role()

    # Role-based filtering: Admin sees all, Lead Owners see their own
    if user_role != "ADMIN":
        query = query.filter(Event.created_by_id == user_id)

    events = query.order_by(Event.start_datetime.asc()).all()
    return jsonify([e.to_dict() for e in events]), 200


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
