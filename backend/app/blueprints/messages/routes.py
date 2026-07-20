"""
Messages Routes - Module 11: Internal team communication.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from . import messages_bp
from ...extensions import db
from ...models import Message, User


@messages_bp.route("/", methods=["GET"])
@jwt_required()
def list_messages():
    """List messages for the current user (inbox + sent)."""
    user_id = get_jwt_identity()
    box = request.args.get("box", "inbox")  # 'inbox' or 'sent'

    if box == "sent":
        messages = Message.query.filter_by(sender_id=user_id).order_by(
            Message.created_at.desc()
        ).limit(100).all()
    else:
        messages = Message.query.filter_by(recipient_id=user_id).order_by(
            Message.created_at.desc()
        ).limit(100).all()

    return jsonify([m.to_dict() for m in messages]), 200


@messages_bp.route("/", methods=["POST"])
@jwt_required()
def send_message():
    """Send an internal message."""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data.get("recipient_id") or not data.get("body"):
        return jsonify({"error": "'recipient_id' and 'body' are required"}), 400

    recipient = User.query.get(data["recipient_id"])
    if not recipient or not recipient.is_active:
        return jsonify({"error": "Recipient not found or inactive"}), 404

    message = Message(
        sender_id=user_id,
        recipient_id=data["recipient_id"],
        subject=data.get("subject", ""),
        body=data["body"],
        is_read=False,
    )
    db.session.add(message)
    db.session.commit()
    return jsonify(message.to_dict()), 201


@messages_bp.route("/<int:msg_id>/read", methods=["POST"])
@jwt_required()
def mark_read(msg_id):
    """Mark a message as read."""
    user_id = get_jwt_identity()
    msg = Message.query.get_or_404(msg_id)

    if msg.recipient_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    msg.is_read = True
    msg.read_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


@messages_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def unread_count():
    """Get the count of unread messages for current user."""
    user_id = get_jwt_identity()
    count = Message.query.filter_by(recipient_id=user_id, is_read=False).count()
    return jsonify({"unread_count": count}), 200
