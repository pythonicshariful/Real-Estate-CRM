"""
Messages Routes - Module 11: Internal team communication.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from . import messages_bp
from ...extensions import db
from ...models import Message, User


def message_to_dict(m):
    return {
        'id': m.id,
        'sender_id': m.sender_id,
        'sender_name': m.sender.full_name if m.sender else "System",
        'recipient_id': m.recipient_id,
        'recipient_name': m.recipient.full_name if m.recipient else "System",
        'subject': m.subject,
        'body': m.body,
        'is_read': m.is_read,
        'read_at': m.read_at.isoformat() if m.read_at else None,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    }

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

    return jsonify([message_to_dict(m) for m in messages]), 200


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
    return jsonify(message_to_dict(message)), 201


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

@messages_bp.route("/conversation/<int:partner_id>", methods=["GET"])
@jwt_required()
def get_conversation(partner_id):
    """Retrieve chronologically ordered message history between current user and partner_id."""
    user_id = int(get_jwt_identity())
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.recipient_id == partner_id)) |
        ((Message.sender_id == partner_id) & (Message.recipient_id == user_id))
    ).order_by(Message.created_at.asc()).all()
    
    # Auto mark incoming unread messages as read
    from datetime import datetime, timezone
    unread = Message.query.filter_by(sender_id=partner_id, recipient_id=user_id, is_read=False).all()
    if unread:
        for m in unread:
            m.is_read = True
            m.read_at = datetime.now(timezone.utc)
        db.session.commit()
        
    return jsonify([message_to_dict(m) for m in messages]), 200

# Global typing states dictionary
# Maps sender_id to {"partner_id": int, "timestamp": datetime}
_typing_states = {}

@messages_bp.route("/unread-by-sender", methods=["GET"])
@jwt_required()
def unread_by_sender():
    """Retrieve unread message counts grouped by sender_id."""
    user_id = int(get_jwt_identity())
    results = db.session.query(
        Message.sender_id, db.func.count(Message.id)
    ).filter_by(recipient_id=user_id, is_read=False).group_by(Message.sender_id).all()
    
    return jsonify({r[0]: r[1] for r in results}), 200

@messages_bp.route("/typing", methods=["POST"])
@jwt_required()
def set_typing():
    """Set the typing status of the current user for a specific recipient."""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    recipient_id = data.get("recipient_id")
    is_typing = data.get("is_typing", False)
    
    if is_typing and recipient_id:
        _typing_states[user_id] = {
            "partner_id": int(recipient_id),
            "timestamp": datetime.now(timezone.utc)
        }
    else:
        _typing_states.pop(user_id, None)
        
    return jsonify({"success": True}), 200

@messages_bp.route("/typing-state", methods=["GET"])
@jwt_required()
def get_typing_state():
    """Check if the active partner is currently typing to the logged-in user."""
    user_id = int(get_jwt_identity())
    partner_id = request.args.get("partner_id", type=int)
    
    if not partner_id:
        return jsonify({"is_typing": False}), 400
        
    state = _typing_states.get(partner_id)
    if state and state["partner_id"] == user_id:
        # Check if the typing action was within the last 4 seconds
        time_diff = (datetime.now(timezone.utc) - state["timestamp"]).total_seconds()
        if time_diff < 4.0:
            return jsonify({"is_typing": True}), 200
            
    return jsonify({"is_typing": False}), 200
