from flask import request, jsonify
from app.blueprints.settings import settings_bp
from flask_jwt_extended import jwt_required
from app.utils.rbac import require_role
from app.models import UserRole

@settings_bp.route('/system', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def system_settings():
    return jsonify({"settings": {}})

@settings_bp.route('/sla', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def sla_settings():
    return jsonify({"sla_minutes": 10})

@settings_bp.route('/meta-webhook', methods=['GET'])
@jwt_required()
@require_role(UserRole.ADMIN)
def meta_setup():
    return jsonify({"status": "OK"})

@settings_bp.route('/roles', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def role_matrix():
    return jsonify({"roles": []})
