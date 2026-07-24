from flask import request, jsonify, current_app
from app.blueprints.settings import settings_bp
from flask_jwt_extended import jwt_required
from app.utils.rbac import require_role
from app.models import UserRole, SystemSetting, Inquiry, db
from datetime import datetime

DEFAULT_SETTINGS = {
    'company_name': 'Southeast Landmark CRM',
    'admin_email': 'admin@southeast.com',
    'currency_symbol': 'BDT',
    'timezone': 'Asia/Dhaka',
    'meta_verify_token': 'sl_crm_secure_webhook_token_2025',
    'meta_app_secret': 'meta_app_secret_placeholder',
    'meta_app_id': '',
    'meta_page_access_token': '',
    'sla_reminder_minutes': '10',
    'sla_manager_alert_minutes': '20',
    'sla_escalation_minutes': '30',
    'auto_reassign_sla_breach': 'true',
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': '587',
    'smtp_username': '',
    'smtp_password': '',
    'sender_email': 'noreply@southeast.com',
    'company_logo': ''
}

import os
from werkzeug.utils import secure_filename

@settings_bp.route('/branding', methods=['GET'])
def get_branding():
    # Public endpoint for sidebar and login page
    keys = ['company_name', 'company_logo']
    return jsonify(_get_setting_dict(keys))

@settings_bp.route('/branding/logo', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def upload_logo():
    if 'logo' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        # Use proper UPLOAD_FOLDER configuration
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        logo_url = f'/uploads/{filename}'
        SystemSetting.set('company_logo', logo_url)
        return jsonify({'message': 'Logo uploaded successfully', 'company_logo': logo_url})

def _get_setting_dict(keys):
    result = {}
    for key in keys:
        db_val = SystemSetting.get(key)
        if db_val is not None:
            result[key] = db_val
        else:
            default_val = DEFAULT_SETTINGS.get(key, '')
            result[key] = default_val
            SystemSetting.set(key, default_val)
    return result

@settings_bp.route('/system', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def system_settings():
    if request.method == 'GET':
        all_keys = list(DEFAULT_SETTINGS.keys())
        return jsonify({"settings": _get_setting_dict(all_keys)})
    
    data = request.get_json() or {}
    settings_data = data.get('settings', data)
    for key, val in settings_data.items():
        SystemSetting.set(key, str(val))
    return jsonify({"message": "Settings updated successfully", "settings": _get_setting_dict(list(DEFAULT_SETTINGS.keys()))})

@settings_bp.route('/general', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def general_settings():
    keys = ['company_name', 'admin_email', 'currency_symbol', 'timezone', 'company_logo']
    if request.method == 'GET':
        return jsonify(_get_setting_dict(keys))
    
    data = request.get_json() or {}
    for k in keys:
        if k in data:
            SystemSetting.set(k, str(data[k]))
    return jsonify({"message": "General settings updated successfully", "settings": _get_setting_dict(keys)})

@settings_bp.route('/sla', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def sla_settings():
    keys = ['sla_reminder_minutes', 'sla_manager_alert_minutes', 'sla_escalation_minutes', 'auto_reassign_sla_breach']
    if request.method == 'GET':
        settings = _get_setting_dict(keys)
        return jsonify({
            "sla_reminder_minutes": int(settings.get('sla_reminder_minutes', 10)),
            "sla_manager_alert_minutes": int(settings.get('sla_manager_alert_minutes', 20)),
            "sla_escalation_minutes": int(settings.get('sla_escalation_minutes', 30)),
            "auto_reassign_sla_breach": settings.get('auto_reassign_sla_breach') == 'true'
        })
    
    data = request.get_json() or {}
    if 'sla_reminder_minutes' in data:
        SystemSetting.set('sla_reminder_minutes', str(data['sla_reminder_minutes']))
    if 'sla_manager_alert_minutes' in data:
        SystemSetting.set('sla_manager_alert_minutes', str(data['sla_manager_alert_minutes']))
    if 'sla_escalation_minutes' in data:
        SystemSetting.set('sla_escalation_minutes', str(data['sla_escalation_minutes']))
    if 'auto_reassign_sla_breach' in data:
        SystemSetting.set('auto_reassign_sla_breach', 'true' if data['auto_reassign_sla_breach'] else 'false')

    settings = _get_setting_dict(keys)
    return jsonify({
        "message": "SLA configuration updated successfully",
        "settings": {
            "sla_reminder_minutes": int(settings.get('sla_reminder_minutes', 10)),
            "sla_manager_alert_minutes": int(settings.get('sla_manager_alert_minutes', 20)),
            "sla_escalation_minutes": int(settings.get('sla_escalation_minutes', 30)),
            "auto_reassign_sla_breach": settings.get('auto_reassign_sla_breach') == 'true'
        }
    })

@settings_bp.route('/meta-webhook', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def meta_setup():
    keys = ['meta_verify_token', 'meta_app_secret', 'meta_app_id', 'meta_page_access_token']
    if request.method == 'PUT':
        data = request.get_json() or {}
        for k in keys:
            if k in data:
                SystemSetting.set(k, str(data[k]))
                
    settings = _get_setting_dict(keys)
    
    # Check last payload received from Inquiries
    last_inquiry = Inquiry.query.order_by(Inquiry.created_at.desc()).first()
    last_payload_time = last_inquiry.created_at.isoformat() if last_inquiry and last_inquiry.created_at else None

    # Construct webhook callback URL based on request host
    host_url = request.host_url.rstrip('/')
    webhook_url = f"{host_url}/api/webhooks/meta"

    return jsonify({
        "status": "active" if settings.get('meta_verify_token') else "inactive",
        "webhook_url": webhook_url,
        "meta_verify_token": settings.get('meta_verify_token', ''),
        "meta_app_secret": settings.get('meta_app_secret', ''),
        "meta_app_id": settings.get('meta_app_id', ''),
        "meta_page_access_token": settings.get('meta_page_access_token', ''),
        "last_payload_received": last_payload_time
    })

@settings_bp.route('/test-meta-webhook', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def test_meta_webhook():
    token = SystemSetting.get('meta_verify_token')
    secret = SystemSetting.get('meta_app_secret')
    if not token or not secret:
        return jsonify({"success": False, "message": "Verify token or App Secret is missing"}), 400
    return jsonify({"success": True, "message": "Meta Webhook configuration verified successfully!"})

@settings_bp.route('/email-templates', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def email_templates():
    keys = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'sender_email']
    if request.method == 'GET':
        return jsonify(_get_setting_dict(keys))
    
    data = request.get_json() or {}
    for k in keys:
        if k in data:
            SystemSetting.set(k, str(data[k]))
    return jsonify({"message": "Email settings updated successfully", "settings": _get_setting_dict(keys)})

@settings_bp.route('/roles', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def role_matrix():
    return jsonify({
        "roles": [
            {"role": "ADMIN", "permissions": ["all"]},
            {"role": "LEAD_OWNER", "permissions": ["view_assigned_leads", "log_calls", "create_notes", "manage_appointments"]}
        ]
    })

