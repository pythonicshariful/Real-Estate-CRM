from flask import request, jsonify, current_app
from app.blueprints.settings import settings_bp
from flask_jwt_extended import jwt_required
from app.utils.rbac import require_role
from app.models import UserRole, SystemSetting, Inquiry, db, ActivityLabel, LeadQuestionnaireQuestion
from datetime import datetime
from sqlalchemy import func

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
    'company_logo': '',
    'b2_key_id': '',
    'b2_application_key': '',
    'b2_bucket_name': 'crm-recordings',
    'b2_endpoint': 'https://s3.us-east-005.backblazeb2.com',
    'recording_storage_strategy': 'local',
    'quick_notes': 'Left Voicemail,Meeting Scheduled,Call Back Later,Send More Info,Not Interested,Wrong Number'
}

import os
from werkzeug.utils import secure_filename

@settings_bp.route('/branding', methods=['GET'])
def get_branding():
    # Public endpoint for sidebar and login page
    keys = ['company_name', 'company_logo']
    return jsonify(_get_setting_dict(keys))

@settings_bp.route('/quick_notes', methods=['GET'])
@jwt_required()
def get_quick_notes():
    # Public endpoint for all authenticated users to read quick notes
    keys = ['quick_notes']
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
        
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Only PNG, JPG, JPEG, and WEBP are allowed."}), 400
        
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
    keys = ['meta_verify_token', 'meta_app_secret', 'meta_app_id', 'meta_page_access_token', 'meta_webhook_last_error']
    if request.method == 'PUT':
        data = request.get_json() or {}
        for k in keys:
            if k in data:
                val = str(data[k]).strip()
                SystemSetting.set(k, val)
                
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
        "last_payload_received": last_payload_time,
        "meta_webhook_last_error": settings.get('meta_webhook_last_error', '')
    })

@settings_bp.route('/test-meta-webhook', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def test_meta_webhook():
    """Legacy config check — kept for backward compat."""
    token = SystemSetting.get('meta_verify_token')
    secret = SystemSetting.get('meta_app_secret')
    if not token or not secret:
        return jsonify({"success": False, "message": "Verify token or App Secret is missing"}), 400
    return jsonify({"success": True, "message": "Meta Webhook configuration verified successfully!"})


@settings_bp.route('/simulate-meta-lead', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def simulate_meta_lead():
    """
    Simulate a Meta Lead Ads webhook payload to test the full pipeline
    WITHOUT needing a real Facebook ad or live webhook call.
    Creates a fake lead via process_meta_webhook() in the app context.
    """
    import uuid
    from datetime import datetime, timezone
    from flask import current_app
    from app.tasks import process_meta_webhook

    data = request.get_json() or {}

    import random
    from app.models import Contact
    from app.utils.phone import normalize_phone

    def _random_bd_mobile():
        """A fresh, valid-looking BD mobile number (01[3-9] + 8 digits)."""
        return random.choice(['017', '018', '019', '016', '015']) + ''.join(
            random.choice('0123456789') for _ in range(8)
        )

    def _phone_taken(num):
        norm = normalize_phone(num)
        return Contact.query.filter(
            db.or_(Contact.phone_normalized == norm, Contact.phone_raw == num)
        ).first() is not None

    full_name = data.get('full_name', 'Test Lead (Simulated)')
    phone = str(data.get('phone') or '').strip()
    email = str(data.get('email') or '').strip()

    if not phone:
        phone = _random_bd_mobile()

    # If the number already exists, process_meta_webhook() MERGES the new
    # inquiry into the existing lead instead of creating a new one. Clicking
    # "Simulate Lead Now" repeatedly with the prefilled number therefore looked
    # like nothing happened. Roll a fresh number unless a duplicate is
    # explicitly requested (pass allow_duplicate: true).
    if not data.get('allow_duplicate'):
        attempts = 0
        while _phone_taken(phone) and attempts < 25:
            phone = _random_bd_mobile()
            attempts += 1

    if not email:
        email = f"sim+{uuid.uuid4().hex[:8]}@example.com"
    profession = data.get('profession', 'Businessman')
    service_type = data.get('service_type', 'Residential Plot')
    budget = data.get('budget', '50-80 Lakhs')
    plot_size = data.get('plot_size', '5 Katha')
    location = data.get('location', 'Dhaka')
    campaign_name = data.get('campaign_name', 'TEST_CAMPAIGN_SIMULATED')
    form_name = data.get('form_name', 'Test Lead Form')

    # Construct a Facebook-style Lead Ads webhook payload
    fake_payload = {
        "object": "page",
        "entry": [
            {
                "id": "111111111111111",
                "time": int(datetime.now(timezone.utc).timestamp()),
                "changes": [
                    {
                        "value": {
                            "leadgen_id": f"sim_{uuid.uuid4().hex[:12]}",
                            "page_id": "111111111111111",
                            "form_id": f"form_{uuid.uuid4().hex[:10]}",
                            "campaign_id": f"camp_{uuid.uuid4().hex[:8]}",
                            "campaign_name": campaign_name,
                            "adset_id": f"adset_{uuid.uuid4().hex[:8]}",
                            "ad_id": f"ad_{uuid.uuid4().hex[:8]}",
                            "form_name": form_name,
                            "field_data": [
                                {"name": "full_name", "values": [full_name]},
                                {"name": "phone_number", "values": [phone]},
                                {"name": "email", "values": [email]},
                                {"name": "profession", "values": [profession]},
                                {"name": "service_type", "values": [service_type]},
                                {"name": "budget_range", "values": [budget]},
                                {"name": "plot_size", "values": [plot_size]},
                                {"name": "preferred_location", "values": [location]},
                                {"name": "purchasing_timeline", "values": ["Within 3 months"]},
                                {"name": "contact_time", "values": ["Morning (9am-12pm)"]},
                            ]
                        },
                        "field": "leadgen"
                    }
                ]
            }
        ]
    }

    try:
        app_obj = current_app._get_current_object()
        process_meta_webhook(fake_payload, app=app_obj)
        return jsonify({
            "success": True,
            "message": f"✅ Simulated lead '{full_name}' successfully created via Meta webhook pipeline!",
            "simulated_data": {
                "name": full_name,
                "phone": phone,
                "email": email,
                "profession": profession,
                "service_type": service_type,
                "budget": budget,
                "campaign": campaign_name
            }
        })
    except Exception as e:
        import traceback
        current_app.logger.error(f'Simulate lead error: {traceback.format_exc()}')
        return jsonify({
            "success": False,
            "message": f"Error simulating lead: {str(e)}"
        }), 500

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

@settings_bp.route('/b2-storage', methods=['GET', 'PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def b2_storage_settings():
    keys = ['b2_key_id', 'b2_application_key', 'b2_bucket_name', 'b2_endpoint', 'recording_storage_strategy']
    if request.method == 'GET':
        return jsonify(_get_setting_dict(keys))
    
    data = request.get_json() or {}
    for k in keys:
        if k in data:
            SystemSetting.set(k, str(data[k]))
    return jsonify({"message": "B2 storage settings updated successfully", "settings": _get_setting_dict(keys)})

@settings_bp.route('/b2-storage/test', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def test_b2_storage():
    """Test connection, bucket access, and upload capabilities to Backblaze B2."""
    data = request.get_json() or {}
    key_id = data.get('b2_key_id') or SystemSetting.get('b2_key_id', '').strip()
    app_key = data.get('b2_application_key') or SystemSetting.get('b2_application_key', '').strip()
    bucket = data.get('b2_bucket_name') or SystemSetting.get('b2_bucket_name', '').strip()
    endpoint = data.get('b2_endpoint') or SystemSetting.get('b2_endpoint', '').strip()

    if not all([key_id, app_key, bucket, endpoint]):
        return jsonify({"success": False, "message": "Missing credentials. Please fill Key ID, Application Key, Bucket Name, and Endpoint."}), 400

    try:
        import boto3
        from botocore.config import Config
        import io
        import uuid
        
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            config=Config(signature_version='s3v4')
        )
        
        test_filename = f"b2_test_{uuid.uuid4().hex[:6]}.txt"
        test_content = b"Southeast Landmark CRM - Backblaze B2 connection test successful!"
        
        s3.put_object(
            Bucket=bucket,
            Key=test_filename,
            Body=test_content,
            ContentType='text/plain'
        )
        
        # Verify and clean up test file
        try:
            s3.delete_object(Bucket=bucket, Key=test_filename)
        except Exception:
            pass
            
        return jsonify({
            "success": True,
            "message": f"Successfully connected to Backblaze B2! Bucket '{bucket}' is accessible and write test passed."
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }), 400

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


# ---------------------------------------------------------------------------
# Activity Labels Management
# ---------------------------------------------------------------------------

@settings_bp.route('/activity-labels', methods=['GET'])
@jwt_required()
def get_activity_labels():
    labels = ActivityLabel.query.filter_by(is_active=True).order_by(ActivityLabel.name.asc()).all()
    if not labels:
        ActivityLabel.seed_defaults()
        labels = ActivityLabel.query.filter_by(is_active=True).order_by(ActivityLabel.name.asc()).all()
    return jsonify([l.to_dict() for l in labels])


@settings_bp.route('/activity-labels', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def create_activity_label():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    color = (data.get('color') or '#6366f1').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'error': 'Label name is required'}), 400

    existing = ActivityLabel.query.filter(func.lower(ActivityLabel.name) == func.lower(name)).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.color = color
            existing.description = description
            db.session.commit()
            return jsonify(existing.to_dict()), 200
        return jsonify({'error': f"Label '{name}' already exists"}), 400

    label = ActivityLabel(name=name, color=color, description=description)
    db.session.add(label)
    db.session.commit()
    return jsonify(label.to_dict()), 201


@settings_bp.route('/activity-labels/<int:id>', methods=['PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def update_activity_label(id):
    label = ActivityLabel.query.get_or_404(id)
    data = request.json or {}
    if 'name' in data and data['name'].strip():
        label.name = data['name'].strip()
    if 'color' in data and data['color'].strip():
        label.color = data['color'].strip()
    if 'description' in data:
        label.description = data['description'].strip()
    if 'is_active' in data:
        label.is_active = bool(data['is_active'])
    db.session.commit()
    return jsonify(label.to_dict())


@settings_bp.route('/activity-labels/<int:id>', methods=['DELETE'])
@jwt_required()
@require_role(UserRole.ADMIN)
def delete_activity_label(id):
    label = ActivityLabel.query.get_or_404(id)
    label.is_active = False
    db.session.commit()
    return jsonify({'message': f"Label '{label.name}' removed successfully"}), 200


# ---------------------------------------------------------------------------
# Lead Questionnaire Configuration
# ---------------------------------------------------------------------------

@settings_bp.route('/questionnaire', methods=['GET'])
@jwt_required()
def get_questionnaire_template():
    questions = LeadQuestionnaireQuestion.query.filter_by(is_active=True).order_by(LeadQuestionnaireQuestion.order_index.asc()).all()
    if not questions:
        LeadQuestionnaireQuestion.seed_defaults()
        questions = LeadQuestionnaireQuestion.query.filter_by(is_active=True).order_by(LeadQuestionnaireQuestion.order_index.asc()).all()
    return jsonify([q.to_dict() for q in questions])


@settings_bp.route('/questionnaire', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def create_questionnaire_question():
    data = request.json or {}
    text = (data.get('question_text') or '').strip()
    key = (data.get('question_key') or '').strip()
    if not key:
        import re
        key = re.sub(r'[^a-zA-Z0-9_]', '_', text.lower()).strip('_')
    
    if not text or not key:
        return jsonify({'error': 'Question text and key are required'}), 400

    existing = LeadQuestionnaireQuestion.query.filter_by(question_key=key).first()
    if existing:
        existing.question_text = text
        existing.field_type = data.get('field_type', existing.field_type)
        existing.options = data.get('options', existing.options)
        existing.is_required = bool(data.get('is_required', existing.is_required))
        existing.is_active = True
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    max_order = db.session.query(func.max(LeadQuestionnaireQuestion.order_index)).scalar() or 0
    q = LeadQuestionnaireQuestion(
        question_key=key,
        question_text=text,
        field_type=data.get('field_type', 'text'),
        options=data.get('options', []),
        order_index=data.get('order_index', max_order + 1),
        is_required=bool(data.get('is_required', False)),
        is_active=True
    )
    db.session.add(q)
    db.session.commit()
    return jsonify(q.to_dict()), 201


@settings_bp.route('/questionnaire/<int:id>', methods=['PUT'])
@jwt_required()
@require_role(UserRole.ADMIN)
def update_questionnaire_question(id):
    q = LeadQuestionnaireQuestion.query.get_or_404(id)
    data = request.json or {}
    if 'question_text' in data and data['question_text'].strip():
        q.question_text = data['question_text'].strip()
    if 'field_type' in data:
        q.field_type = data['field_type']
    if 'options' in data:
        q.options = data['options']
    if 'order_index' in data:
        q.order_index = int(data['order_index'])
    if 'is_required' in data:
        q.is_required = bool(data['is_required'])
    if 'is_active' in data:
        q.is_active = bool(data['is_active'])
    db.session.commit()
    return jsonify(q.to_dict())


@settings_bp.route('/questionnaire/<int:id>', methods=['DELETE'])
@jwt_required()
@require_role(UserRole.ADMIN)
def delete_questionnaire_question(id):
    q = LeadQuestionnaireQuestion.query.get_or_404(id)
    q.is_active = False
    db.session.commit()
    return jsonify({'message': f"Question '{q.question_text}' deactivated successfully"}), 200


@settings_bp.route('/questionnaire/reset', methods=['POST'])
@jwt_required()
@require_role(UserRole.ADMIN)
def reset_questionnaire_defaults():
    LeadQuestionnaireQuestion.seed_defaults()
    questions = LeadQuestionnaireQuestion.query.filter_by(is_active=True).order_by(LeadQuestionnaireQuestion.order_index.asc()).all()
    return jsonify([q.to_dict() for q in questions])


