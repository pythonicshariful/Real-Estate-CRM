"""
Tickets Routes - Module 13: Customer support and issue tracking.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import tickets_bp
from ...extensions import db
from ...models import Ticket, User
from ...utils.rbac import get_current_user_role, require_min_role


@tickets_bp.route("/", methods=["GET"])
@jwt_required()
def list_tickets():
    """List support tickets."""
    user_id = get_jwt_identity()
    user_role = get_current_user_role()
    status = request.args.get("status")
    priority = request.args.get("priority")

    query = Ticket.query

    # Executives see only their own tickets
    if user_role == "EXECUTIVE":
        query = query.filter_by(created_by_id=user_id)

    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    tickets = query.order_by(Ticket.created_at.desc()).limit(200).all()
    return jsonify([t.to_dict() for t in tickets]), 200


@tickets_bp.route("/", methods=["POST"])
@jwt_required()
def create_ticket():
    """Create a new support ticket."""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data.get("subject") or not data.get("description"):
        return jsonify({"error": "'subject' and 'description' are required"}), 400

    ticket = Ticket(
        subject=data["subject"],
        description=data["description"],
        priority=data.get("priority", "MEDIUM"),
        status="OPEN",
        created_by_id=user_id,
        contact_id=data.get("contact_id"),
        opportunity_id=data.get("opportunity_id"),
    )
    db.session.add(ticket)
    db.session.commit()
    return jsonify(ticket.to_dict()), 201


@tickets_bp.route("/<int:ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id):
    """Get ticket details."""
    ticket = Ticket.query.get_or_404(ticket_id)
    return jsonify(ticket.to_dict()), 200


@tickets_bp.route("/<int:ticket_id>", methods=["PUT"])
@jwt_required()
@require_min_role("ADMIN")
def update_ticket(ticket_id):
    """Update ticket status/assignment (Manager+)."""
    ticket = Ticket.query.get_or_404(ticket_id)
    data = request.get_json()

    if "status" in data:
        ticket.status = data["status"]
    if "assigned_to_id" in data:
        ticket.assigned_to_id = data["assigned_to_id"]
    if "resolution_notes" in data:
        ticket.resolution_notes = data["resolution_notes"]

    db.session.commit()
    return jsonify(ticket.to_dict()), 200
