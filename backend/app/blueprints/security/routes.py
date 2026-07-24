from flask import request, jsonify
from app.blueprints.security import security_bp
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.utils.rbac import require_role
from app.models import UserRole, AuditLog

from datetime import datetime

@security_bp.route('/audit-log', methods=['GET'])
@jwt_required()
def get_audit_log():
    claims = get_jwt()
    role = claims.get('role')
    current_user_id = int(get_jwt_identity())
    
    query = AuditLog.query
    
    # Executive can only see their own activity logs
    if role != UserRole.ADMIN.value:
        query = query.filter_by(user_id=current_user_id)
    else:
        # Admin can filter by user_id
        filter_user_id = request.args.get('user_id', type=int)
        if filter_user_id:
            query = query.filter_by(user_id=filter_user_id)
            
    # Filter by date range (start_date, end_date)
    start_date_str = request.args.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace(' ', 'T'))
            query = query.filter(AuditLog.created_at >= start_date)
        except ValueError:
            pass
            
    end_date_str = request.args.get('end_date')
    if end_date_str:
        try:
            if len(end_date_str) == 10:
                end_date_str += "T23:59:59"
            end_date = datetime.fromisoformat(end_date_str.replace(' ', 'T'))
            query = query.filter(AuditLog.created_at <= end_date)
        except ValueError:
            pass
            
    logs = query.order_by(AuditLog.created_at.desc()).all()
    return jsonify([l.to_dict() for l in logs]), 200

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
