from flask import request, jsonify
from app.blueprints.team import team_bp
from app.models import User, UserRole, db, CallLog, Note, Event, Appointment
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime

def _parse_date(val):
    if not val: return None
    try:
        return datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
    except Exception:
        return None

def _parse_time(val):
    if not val: return None
    try:
        return datetime.strptime(str(val).strip(), '%H:%M').time()
    except Exception:
        return None

def _require_admin(claims):
    role = claims.get('role')
    if role != UserRole.ADMIN.value:
        return jsonify({"error": "Admin access required"}), 403
    return None

@team_bp.route('/lead-owners', methods=['GET'])
@jwt_required()
def list_lead_owners():
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    
    users = User.query.filter_by(role=UserRole.LEAD_OWNER).order_by(User.id.asc()).all()
    return jsonify([u.to_dict() for u in users]), 200

@team_bp.route('/lead-owners', methods=['POST'])
@jwt_required()
def create_lead_owner():
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    full_name = data.get('full_name', '').strip()
    password = data.get('password', '')
    phone = data.get('phone', '').strip()
    color = data.get('color', '#6366f1')

    if not email or not password or not full_name:
        return jsonify({'error': 'Email, full name, and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': f"User with email '{email}' already exists"}), 409

    user = User(
        email=email,
        full_name=full_name,
        role=UserRole.LEAD_OWNER,
        phone=phone,
        is_active=True,
        is_mfa_enabled=False,
        calendar_color=color,
        schedule_from_date=_parse_date(data.get('schedule_from_date')),
        schedule_to_date=_parse_date(data.get('schedule_to_date')),
        schedule_start_time=_parse_time(data.get('schedule_start_time')),
        schedule_end_time=_parse_time(data.get('schedule_end_time'))
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Lead Owner created successfully', 'user': user.to_dict()}), 201

@team_bp.route('/lead-owners/<int:id>', methods=['GET'])
@jwt_required()
def get_lead_owner(id):
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    
    user = User.query.get_or_404(id)
    return jsonify(user.to_dict()), 200

@team_bp.route('/lead-owners/<int:id>', methods=['PUT'])
@jwt_required()
def update_lead_owner(id):
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    
    user = User.query.get_or_404(id)
    data = request.get_json() or {}
    
    if 'full_name' in data: user.full_name = data['full_name']
    if 'phone' in data: user.phone = data['phone']
    if 'color' in data: user.calendar_color = data['color']
    if 'schedule_from_date' in data: user.schedule_from_date = _parse_date(data['schedule_from_date'])
    if 'schedule_to_date' in data: user.schedule_to_date = _parse_date(data['schedule_to_date'])
    if 'schedule_start_time' in data: user.schedule_start_time = _parse_time(data['schedule_start_time'])
    if 'schedule_end_time' in data: user.schedule_end_time = _parse_time(data['schedule_end_time'])
    
    db.session.commit()
    return jsonify({'message': 'Updated', 'user': user.to_dict()}), 200

@team_bp.route('/lead-owners/<int:id>/toggle-status', methods=['POST'])
@jwt_required()
def toggle_lead_owner_status(id):
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    if not user.is_active:
        user.deactivated_at = datetime.utcnow()
        user.deactivated_by_id = int(get_jwt_identity())
    else:
        user.deactivated_at = None
        user.deactivated_by_id = None
    db.session.commit()
    return jsonify({'message': f"Status changed to {'Active' if user.is_active else 'Inactive'}", 'user': user.to_dict()}), 200

@team_bp.route('/lead-owners/<int:id>/reset-password', methods=['POST'])
@jwt_required()
def reset_lead_owner_password(id):
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    
    user = User.query.get_or_404(id)
    data = request.get_json() or {}
    new_password = data.get('new_password', '')
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': 'Password reset successfully'}), 200

@team_bp.route('/lead-owners/<int:id>/activities', methods=['GET'])
@jwt_required()
def get_lead_owner_activities(id):
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    
    user = User.query.get_or_404(id)
    timeline = []
    
    calls = CallLog.query.filter_by(logged_by_id=id).all()
    for c in calls:
        timeline.append({
            'type': 'CALL',
            'date': c.created_at.isoformat() if c.created_at else None,
            'connected': c.connected,
            'notes': c.notes,
            'recording_url': c.recording_filename # simplified
        })
        
    notes = Note.query.filter_by(created_by_id=id).all()
    for n in notes:
        timeline.append({
            'type': 'NOTE',
            'date': n.created_at.isoformat() if n.created_at else None,
            'content': n.content
        })
        
    events = Event.query.filter_by(created_by_id=id).all()
    for e in events:
        timeline.append({
            'type': 'EVENT',
            'date': e.start_datetime.isoformat() if e.start_datetime else None,
            'title': e.title,
            'description': e.description
        })

    # Sort descending by date
    timeline.sort(key=lambda x: x.get('date') or '', reverse=True)

    data = user.to_dict()
    data['timeline'] = timeline
    data['last_login'] = user.last_login.isoformat() if user.last_login else None
    
    return jsonify(data), 200

# Keep old routes for backwards compat
@team_bp.route('/users', methods=['GET'])
@jwt_required()
def manage_users_get():
    claims = get_jwt()
    err = _require_admin(claims)
    if err: return err
    users = User.query.order_by(User.id.asc()).all()
    return jsonify([u.to_dict() for u in users]), 200
