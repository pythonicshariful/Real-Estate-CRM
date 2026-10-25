"""
In-app notifications API.

A user sees ONLY their own notifications — every query is scoped to the
JWT identity, and single-item actions return 404 for other users' rows
so no existence is leaked. Delivery is pull-based: the header bell polls
GET /api/notifications/ (the unread count is refreshed every 60s).
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import notifications_bp
from ...extensions import db
from ...models import Notification


@notifications_bp.route("/", methods=["GET"])
@jwt_required()
def list_notifications():
    """Current user's notifications, newest first.

    Query params: limit (default 20, max 50), unread_only=true.
    Response: {notifications: [...], unread_count, total}
    """
    user_id = int(get_jwt_identity())
    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 50))
    unread_only = request.args.get("unread_only", "").lower() in ("1", "true", "yes")

    query = Notification.query.filter_by(user_id=user_id)
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    total = query.count()
    if unread_only:
        query = query.filter_by(is_read=False)
    rows = query.order_by(Notification.created_at.desc()).limit(limit).all()

    return jsonify({
        "notifications": [r.to_dict() for r in rows],
        "unread_count": unread_count,
        "total": total,
    }), 200


@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@jwt_required()
def mark_read(notif_id):
    """Mark one notification as read. Only the owner can do this."""
    user_id = int(get_jwt_identity())
    row = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not row:
        return jsonify({"error": "Notification not found"}), 404
    row.is_read = True
    db.session.commit()
    return jsonify(row.to_dict()), 200


@notifications_bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_read():
    """Mark all of the current user's unread notifications as read."""
    user_id = int(get_jwt_identity())
    updated = (
        Notification.query.filter_by(user_id=user_id, is_read=False)
        .update({"is_read": True}, synchronize_session=False)
    )
    db.session.commit()
    return jsonify({"marked_read": updated}), 200
