from flask import request, jsonify
from app.blueprints.auth import auth_bp
from app.models import User, UserRole
from app.extensions import db
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
