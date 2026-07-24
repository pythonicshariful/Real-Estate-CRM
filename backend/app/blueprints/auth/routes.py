from flask import request, jsonify
from app.blueprints.auth import auth_bp
from app.models import User, UserRole, Opportunity, Task, CallLog
from app.extensions import db
import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
import pyotp
import qrcode
import io
import base64

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Bad email or password"}), 401
        
    if not user.is_active:
        return jsonify({"msg": "Account deactivated. Please contact your Admin."}), 403
    
    # Log login activity
    from app.models import AuditLog
    audit = AuditLog(
        user_id=user.id,
        table_name='users',
        record_id=user.id,
        action='LOGIN',
        new_value=f"User {user.full_name} logged in"
    )
    db.session.add(audit)
    db.session.commit()
    
    redirect_to = 'admin-dashboard.html' if user.role == UserRole.ADMIN else 'dashboard.html'
    
    access_token = create_access_token(identity=str(user.id), additional_claims={
        'role': user.role.value,
        'color': user.calendar_color,
        'full_name': user.full_name,
        'mfa_pending': False
    })
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify(
        access_token=access_token,
        refresh_token=refresh_token,
        mfa_required=False,
        redirect_to=redirect_to,
        role=user.role.value,
        full_name=user.full_name,
        color=user.calendar_color,
        avatar_url=user.avatar_url
    )

@auth_bp.route('/verify-mfa', methods=['POST'])
@jwt_required()
def verify_mfa():
    claims = get_jwt()
    if not claims.get('mfa_pending'):
        return jsonify({"msg": "MFA not pending"}), 400
        
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    token = request.json.get('token')
    
    if not user.verify_totp(token):
        return jsonify({"msg": "Invalid MFA token"}), 401
        
    # Full auth
    access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role.value, 'mfa_pending': False})
    refresh_token = create_refresh_token(identity=str(user.id))
    return jsonify(access_token=access_token, refresh_token=refresh_token)

@auth_bp.route('/setup-mfa', methods=['POST'])
@jwt_required()
def setup_mfa():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    uri = user.get_totp_uri()
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return jsonify({"qr_code": image_base64, "secret": user.mfa_secret})

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In production, implement token blocklisting here
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if user:
        from app.models import AuditLog
        audit = AuditLog(
            user_id=user.id,
            table_name='users',
            record_id=user.id,
            action='LOGOUT',
            new_value=f"User {user.full_name} logged out"
        )
        db.session.add(audit)
        db.session.commit()
    return jsonify({"msg": "Successfully logged out"}), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role.value, 'mfa_pending': False})
    return jsonify(access_token=access_token)

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify(user.to_dict())

@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    if 'full_name' in data: user.full_name = data['full_name']
    if 'phone' in data: user.phone = data['phone']
    
    db.session.commit()
    return jsonify(user.to_dict())

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    if not user.check_password(data.get('current_password')):
        return jsonify({"msg": "Incorrect current password"}), 401
        
    user.set_password(data.get('new_password'))
    db.session.commit()
    return jsonify({"msg": "Password changed successfully"})

@auth_bp.route('/me/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({"msg": "No file part"}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"msg": "No selected file"}), 400
        
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Save the file
    filename = secure_filename(file.filename)
    unique_filename = f"{user.id}_{uuid.uuid4().hex}_{filename}"
    upload_dir = current_app.config.get('AVATARS_FOLDER', 'uploads/avatars')
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_filename)
    file.save(file_path)
    
    user.avatar_url = f"/uploads/avatars/{unique_filename}"
    db.session.commit()
    
    return jsonify({"msg": "Avatar updated", "avatar_url": user.avatar_url})

@auth_bp.route('/me/stats', methods=['GET'])
@jwt_required()
def me_stats():
    user_id = get_jwt_identity()
    
    total_leads = Opportunity.query.filter_by(assigned_to_id=user_id, is_deleted=False).count()
    active_leads = Opportunity.query.filter_by(assigned_to_id=user_id, is_deleted=False).filter(~Opportunity.pipeline_stage.in_(['SOLD', 'CLOSED_LOST', 'INVALID'])).count()
    completed_tasks = Task.query.filter_by(assigned_to_id=user_id, status='COMPLETED').count()
    recent_calls = CallLog.query.filter_by(logged_by_id=user_id).order_by(CallLog.created_at.desc()).limit(10).all()
    
    calls_data = [{
        "id": c.id,
        "type": c.call_type,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in recent_calls]
    
    return jsonify({
        "total_leads": total_leads,
        "active_leads": active_leads,
        "completed_tasks": completed_tasks,
        "recent_activities": calls_data
    })
