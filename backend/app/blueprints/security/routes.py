from flask import request, jsonify
from app.blueprints.security import security_bp
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.rbac import require_role
from app.models import UserRole, AuditLog

@security_bp.route('/audit-log', methods=['GET'])
@jwt_required()
@require_role(UserRole.ADMIN)
def get_audit_log():
    return jsonify([])

@security_bp.route('/recording-downloads', methods=['GET'])
@jwt_required()
@require_role(UserRole.ADMIN)
def get_recording_downloads():
    return jsonify([])

@security_bp.route('/recordings/<int:call_log_id>/url', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def get_recording_url(call_log_id):
    user_id = get_jwt_identity()
    return jsonify({"download_url": None})

@security_bp.route('/export', methods=['GET'])
@jwt_required()
@require_role(UserRole.ADMIN)
def data_export():
    return jsonify({"msg": "Export started"})
