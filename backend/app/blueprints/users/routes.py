"""Current-user device endpoints (deploy 34).

POST   /api/users/me/fcm-token — register this device's FCM token so
       the server can push lead/reminder alerts to the signed-in user.
DELETE /api/users/me/fcm-token — unregister (e.g. on logout).

The token is stored on the User row (users.fcm_token) and is never
exposed in any to_dict output.
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import users_bp
from ...extensions import db
from ...models import User


@users_bp.route('/me/fcm-token', methods=['POST'])
@jwt_required()
def save_fcm_token():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"msg": "User not found"}), 404
    data = request.get_json(silent=True) or {}
    token = (data.get('token') or '').strip()
    if not token:
        return jsonify({"msg": "token is required"}), 400
    user.fcm_token = token
    db.session.commit()
    return jsonify({"ok": True}), 200


@users_bp.route('/me/fcm-token', methods=['DELETE'])
@jwt_required()
def clear_fcm_token():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"msg": "User not found"}), 404
    user.fcm_token = None
    db.session.commit()
    return jsonify({"ok": True}), 200
