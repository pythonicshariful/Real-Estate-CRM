from flask import request, jsonify
from app.blueprints.leads import leads_bp
from app.models import Opportunity, Contact, CallLog, Appointment, PipelineStage, AppointmentStatus, Objection, Reservation, db, UserRole, LeadTemperature
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime

def _is_admin(role):
    return role == UserRole.ADMIN.value

def _check_lead_access(lead, role, user_id):
    """Returns True if user can access this lead."""
    if _is_admin(role):
        return True
    return lead.assigned_to_id == user_id

@leads_bp.route('/', methods=['GET'])
@jwt_required()
def get_leads():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    query = Opportunity.query.filter_by(is_deleted=False)
    
    # Lead Owners only see their own leads
    if not _is_admin(role):
        query = query.filter_by(assigned_to_id=user_id)
    
    # Optional filters
    stage = request.args.get('stage')
    if stage:
        try:
            query = query.filter_by(pipeline_stage=PipelineStage[stage])
        except KeyError:
            pass

    owner_id = request.args.get('owner_id')
    if owner_id and _is_admin(role):
        query = query.filter_by(assigned_to_id=int(owner_id))
        
    leads = query.order_by(Opportunity.created_at.desc()).all()
    
    result = []
    for lead in leads:
        data = lead.to_dict()
        contact = Contact.query.get(lead.contact_id)
        if contact:
            data["contact"] = {
                "full_name": contact.full_name,
                "email": contact.email,
                "phone": contact.phone_raw,
                "source": contact.source,
            }
        result.append(data)
        
    return jsonify(result)

@leads_bp.route('/', methods=['POST'])
@jwt_required()
def create_lead():
    data = request.json
    if not data or not data.get('full_name') or not data.get('phone'):
        return jsonify({"error": "Full name and phone are required"}), 400
        
    user_id = int(get_jwt_identity())
    
    phone = data.get('phone')
    contact = Contact.query.filter_by(phone_normalized=phone).first()
    
    if not contact:
        contact = Contact(
            full_name=data.get('full_name'),
            phone_raw=phone,
            phone_normalized=phone,
            email=data.get('email'),
            source=data.get('source', 'Manual Entry')
        )
        db.session.add(contact)
        db.session.flush()
        
    project_id = data.get('project_id') or None
        
    opp = Opportunity(
        contact_id=contact.id,
        assigned_to_id=user_id,
        project_id=project_id,
        pipeline_stage=PipelineStage.NEW
    )
    db.session.add(opp)
    db.session.commit()
    
    result = opp.to_dict()
    result["contact"] = {
        "full_name": contact.full_name,
        "email": contact.email,
        "phone": contact.phone_raw,
        "source": contact.source,
    }
    return jsonify(result), 201

@leads_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_lead(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify(lead.to_dict())

@leads_bp.route('/<int:id>/profile', methods=['GET'])
@jwt_required()
def get_lead_profile(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403

    contact = Contact.query.get(lead.contact_id)
    call_logs = CallLog.query.filter_by(opportunity_id=id).order_by(CallLog.created_at.desc()).all()
    appointments = Appointment.query.filter_by(opportunity_id=id).order_by(Appointment.appointment_datetime.asc()).all()
    objections = Objection.query.filter_by(opportunity_id=id).all()
    reservations = Reservation.query.filter_by(opportunity_id=id).first()

    profile = lead.to_dict()
    if contact:
        profile["contact"] = {
            "full_name": contact.full_name,
            "email": contact.email,
            "phone": contact.phone_raw,
            "source": contact.source,
            "address": contact.address,
            "city": contact.city,
        }
    profile["call_logs"] = [{
        "id": c.id,
        "connected": c.connected,
        "notes": c.notes,
        "outcome": c.outcome.value if c.outcome else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "recording_url": c.recording_filename,
    } for c in call_logs]
    profile["appointments"] = [{
        "id": a.id,
        "appointment_datetime": a.appointment_datetime.isoformat() if a.appointment_datetime else None,
        "location": a.location,
        "status": a.status.value if a.status else None,
    } for a in appointments]
    profile["objections"] = [{
        "id": o.id,
        "category": o.category.value if o.category else None,
        "specific_objection": o.specific_objection,
        "resolved": o.resolved,
    } for o in objections]
    profile["reservation"] = {
        "unit_reference": reservations.unit_reference,
        "booking_amount": str(reservations.booking_amount),
    } if reservations else None

    return jsonify(profile)

@leads_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_lead(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json
    if 'pipeline_stage' in data:
        try:
            lead.pipeline_stage = PipelineStage[data['pipeline_stage']]
        except KeyError:
            return jsonify({"error": "Invalid stage"}), 400
    if 'next_action_deadline' in data and data['next_action_deadline']:
        try:
            lead.next_action_deadline = datetime.fromisoformat(data['next_action_deadline'])
        except ValueError:
            pass
    if 'manager_assessment' in data and _is_admin(role):
        lead.manager_assessment = data['manager_assessment']
    
    db.session.commit()
    return jsonify(lead.to_dict())

@leads_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_lead(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    lead.is_deleted = True
    lead.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"msg": "Lead deleted"})

@leads_bp.route('/<int:id>/star', methods=['PUT'])
@jwt_required()
def toggle_star(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json
    lead.is_starred = data.get('is_starred', not lead.is_starred)
    db.session.commit()
    return jsonify(lead.to_dict())

@leads_bp.route('/<int:id>/temperature', methods=['PUT'])
@jwt_required()
def update_temperature(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json
    new_temp = data.get('temperature', 'COLD').upper()
    try:
        lead.lead_temperature = LeadTemperature[new_temp]
    except KeyError:
        return jsonify({"error": "Invalid temperature"}), 400
    
    db.session.commit()
    return jsonify(lead.to_dict())

@leads_bp.route('/<int:id>/calls', methods=['POST'])
@jwt_required()
def log_call(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json or {}
    log = CallLog(
        opportunity_id=id,
        logged_by_id=user_id,
        connected=data.get('connected', False),
        notes=data.get('notes', ''),
        call_type='OUTBOUND',
    )
    
    if data.get('next_action_deadline'):
        try:
            lead.next_action_deadline = datetime.fromisoformat(data['next_action_deadline'])
        except ValueError:
            pass
    
    lead.last_activity_at = datetime.utcnow()
    
    db.session.add(log)
    db.session.commit()
    return jsonify({"id": log.id, "msg": "Call logged"}), 201

@leads_bp.route('/<int:id>/appointments', methods=['POST'])
@jwt_required()
def book_appointment(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json or {}
    appt_dt_str = data.get('appointment_datetime')
    if not appt_dt_str:
        return jsonify({"error": "appointment_datetime is required"}), 400
    
    try:
        appt_dt = datetime.fromisoformat(appt_dt_str)
    except ValueError:
        return jsonify({"error": "Invalid datetime format"}), 400
    
    appt = Appointment(
        opportunity_id=id,
        contact_id=lead.contact_id,
        scheduled_by_id=user_id,
        appointment_datetime=appt_dt,
        location=data.get('location', ''),
        status=AppointmentStatus.SCHEDULED
    )
    lead.pipeline_stage = PipelineStage.APPOINTMENT_SCHEDULED
    lead.appointment_status = AppointmentStatus.SCHEDULED
    
    db.session.add(appt)
    db.session.commit()
    return jsonify({"id": appt.id, "msg": "Appointment booked"}), 201

@leads_bp.route('/<int:id>/notes', methods=['POST'])
@jwt_required()
def add_note(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    data = request.json or {}
    if not data.get('text'):
        return jsonify({"error": "Note text is required"}), 400
    
    log = CallLog(
        opportunity_id=id,
        logged_by_id=user_id,
        connected=False,
        notes=data.get('text'),
        call_type='NOTE',
    )
    lead.last_activity_at = datetime.utcnow()
    db.session.add(log)
    db.session.commit()
    return jsonify({"id": log.id, "msg": "Note added"}), 201
