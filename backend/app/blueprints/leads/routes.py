from flask import request, jsonify, current_app
from app.blueprints.leads import leads_bp
from app.models import Opportunity, Contact, CallLog, Appointment, PipelineStage, AppointmentStatus, Objection, Reservation, Note, PipelineHistory, db, UserRole, LeadTemperature, AuditLog, User
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timezone
import os
from app.utils.rbac import is_admin


def _check_lead_access(lead, role, user_id):
    """Returns True if user can access this lead."""
    if is_admin(role):
        return True
    return lead.assigned_to_id == user_id

@leads_bp.route('/', methods=['GET'])
@jwt_required()
def get_leads():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    query = db.session.query(Opportunity, Contact).outerjoin(
        Contact, Opportunity.contact_id == Contact.id
    ).filter(Opportunity.is_deleted == False)
    
    # Lead Owners only see their own leads
    if not is_admin(role):
        query = query.filter(Opportunity.assigned_to_id == user_id)
    
    # Optional filters
    stage = request.args.get('stage')
    if stage:
        try:
            query = query.filter(Opportunity.pipeline_stage == PipelineStage[stage])
        except KeyError:
            pass

    owner_id = request.args.get('owner_id')
    if owner_id and is_admin(role):
        query = query.filter(Opportunity.assigned_to_id == int(owner_id))
        
    leads_and_contacts = query.order_by(Opportunity.created_at.desc()).all()
    
    result = []
    for lead, contact in leads_and_contacts:
        data = lead.to_dict()
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
    from app.schemas import LeadCreateSchema
    from marshmallow import ValidationError
    from app.utils.security import sanitize_input
    
    schema = LeadCreateSchema()
    try:
        validated_data = schema.load(request.json or {})
    except ValidationError as err:
        return jsonify({"status": "error", "code": 400, "message": "Validation Error", "details": err.messages}), 400
        
    user_id = int(get_jwt_identity())
    
    phone = sanitize_input(validated_data['phone'])
    full_name = sanitize_input(validated_data['full_name'])
    email = sanitize_input(validated_data.get('email'))
    source = sanitize_input(validated_data.get('source'))
    
    contact = Contact.query.filter_by(phone_normalized=phone).first()
    
    if not contact:
        contact = Contact(
            full_name=full_name,
            phone_raw=phone,
            phone_normalized=phone,
            email=email,
            source=source
        )
        db.session.add(contact)
        db.session.flush()
        
    project_id = validated_data.get('project_id')
        
    opp = Opportunity(
        contact_id=contact.id,
        assigned_to_id=user_id,
        project_id=project_id,
        pipeline_stage=PipelineStage.NEW
    )
    db.session.add(opp)
    db.session.flush() # flush to get opp.id
    
    audit = AuditLog(
        user_id=user_id,
        table_name='opportunities',
        record_id=opp.id,
        action='INSERT',
        field_name='lead',
        new_value=f"Created Lead: {contact.full_name}"
    )
    db.session.add(audit)
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
    notes = Note.query.filter_by(opportunity_id=id).order_by(Note.created_at.desc()).all()
    history = PipelineHistory.query.filter_by(opportunity_id=id).order_by(PipelineHistory.changed_at.desc()).all()

    # Consolidate Timeline
    timeline_items = []
    
    # Calls
    def format_rec_url(fname):
        if not fname: return None
        if fname.startswith('http'): return fname
        import urllib.parse
        return f"/uploads/recordings/{urllib.parse.quote(fname)}"
        
    for c in call_logs:
        timeline_items.append({
            "type": "CALL",
            "date": c.created_at.isoformat() if c.created_at else None,
            "connected": c.connected,
            "notes": c.notes,
            "recording_url": format_rec_url(c.recording_filename),
        })
        
    # Notes
    for n in notes:
        timeline_items.append({
            "type": "NOTE",
            "date": n.created_at.isoformat() if n.created_at else None,
            "content": n.content,
        })
        
    # History
    for h in history:
        timeline_items.append({
            "type": "STAGE_CHANGE",
            "date": h.changed_at.isoformat() if h.changed_at else None,
            "from_stage": h.from_stage.value if h.from_stage else None,
            "to_stage": h.to_stage.value if h.to_stage else None,
            "notes": h.notes,
        })
        
    # Appointments
    for a in appointments:
        timeline_items.append({
            "type": "APPOINTMENT",
            "date": a.created_at.isoformat() if a.created_at else None,
            "appointment_datetime": a.appointment_datetime.isoformat() if a.appointment_datetime else None,
            "status": a.status.value if a.status else None,
            "location": a.location,
        })

    # Sort timeline by date descending
    timeline_items.sort(key=lambda x: x["date"] or "", reverse=True)

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
        "recording_url": format_rec_url(c.recording_filename),
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
    
    # Extract Custom Meta Questions
    profile["custom_fields"] = []
    if lead.inquiry and lead.inquiry.raw_payload:
        rp = lead.inquiry.raw_payload
        lead_data = rp.get("lead_data", {})
        field_data = lead_data.get("field_data", [])
        for f in field_data:
            name = f.get("name")
            vals = f.get("values", [])
            if name not in ["full_name", "name", "email", "phone_number", "phone"] and vals:
                profile["custom_fields"].append({
                    "name": name,
                    "value": vals[0]
                })

    profile["timeline"] = timeline_items

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
    contact = lead.contact
    if contact and is_admin(role):
        new_name = data.get('full_name', contact.full_name)
        new_email = data.get('email', contact.email)
        new_phone = data.get('phone', contact.phone_raw)
        
        if new_name != contact.full_name or new_email != contact.email or new_phone != contact.phone_raw:
            from app.utils.phone import normalize_phone
            new_phone_norm = normalize_phone(new_phone) if new_phone else None
            
            # Check how many active opportunities share this contact
            shared_count = Opportunity.query.filter_by(contact_id=contact.id).count()
            
            if shared_count > 1:
                # Need to detach to avoid changing other leads
                existing_contact = None
                if new_phone_norm:
                    existing_contact = Contact.query.filter_by(phone_normalized=new_phone_norm).first()
                if not existing_contact and new_email:
                    existing_contact = Contact.query.filter_by(email=new_email).first()
                    
                if existing_contact:
                    lead.contact_id = existing_contact.id
                    existing_contact.full_name = new_name
                else:
                    new_contact = Contact(
                        full_name=new_name,
                        email=new_email,
                        phone_raw=new_phone,
                        phone_normalized=new_phone_norm,
                        source=contact.source,
                        gender=contact.gender,
                        address=contact.address,
                        consent_given=contact.consent_given,
                        consent_date=contact.consent_date
                    )
                    db.session.add(new_contact)
                    db.session.flush()
                    lead.contact_id = new_contact.id
            else:
                # Safe to update in-place
                contact.full_name = new_name
                contact.email = new_email
                contact.phone_raw = new_phone
                contact.phone_normalized = new_phone_norm
    if 'pipeline_stage' in data:
        try:
            old_stage = lead.pipeline_stage.value if lead.pipeline_stage else 'NEW'
            new_stage = data['pipeline_stage']
            lead.pipeline_stage = PipelineStage[new_stage]
            
            audit = AuditLog(
                user_id=user_id,
                table_name='opportunities',
                record_id=lead.id,
                action='UPDATE',
                field_name='pipeline_stage',
                old_value=old_stage,
                new_value=new_stage
            )
            db.session.add(audit)
        except KeyError:
            return jsonify({"error": "Invalid stage"}), 400
    if 'next_action_deadline' in data and data['next_action_deadline']:
        try:
            old_deadline = lead.next_action_deadline.isoformat() if lead.next_action_deadline else None
            new_deadline = data['next_action_deadline']
            lead.next_action_deadline = datetime.fromisoformat(new_deadline)
            
            audit = AuditLog(
                user_id=user_id,
                table_name='opportunities',
                record_id=lead.id,
                action='UPDATE',
                field_name='next_action_deadline',
                old_value=old_deadline,
                new_value=new_deadline
            )
            db.session.add(audit)
        except ValueError:
            pass
    if 'manager_assessment' in data and is_admin(role):
        from app.utils.security import sanitize_input
        lead.manager_assessment = sanitize_input(data['manager_assessment'])
    
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
    lead.deleted_at = datetime.now(timezone.utc)
    
    # Audit log lead deletion
    contact_name = lead.contact.full_name if lead.contact else "Unknown"
    audit = AuditLog(
        user_id=user_id,
        table_name='opportunities',
        record_id=lead.id,
        action='DELETE',
        field_name='is_deleted',
        old_value='False',
        new_value=f"Deleted Lead: {contact_name}"
    )
    db.session.add(audit)
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

@leads_bp.route('/<int:id>/calls/bulk-delete', methods=['POST'])
@jwt_required()
def bulk_delete_calls(id):
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    call_ids = data.get('call_ids', [])
    
    if not call_ids:
        return jsonify({"error": "No call IDs provided"}), 400

    calls_to_delete = CallLog.query.filter(CallLog.id.in_(call_ids), CallLog.opportunity_id == id).all()
    
    for call in calls_to_delete:
        # Delete local file if it exists
        if call.recording_filename and not call.recording_filename.startswith('http'):
            try:
                recordings_dir = current_app.config.get('RECORDINGS_FOLDER', 'uploads/call record')
                # Try new local path
                local_path = os.path.join(recordings_dir, call.recording_filename)
                if os.path.exists(local_path):
                    os.remove(local_path)
                else:
                    # Try old local path
                    old_local_path = os.path.join(current_app.config.get('RECORDINGS_FOLDER', 'uploads/recordings'), call.recording_filename)
                    if os.path.exists(old_local_path):
                        os.remove(old_local_path)
            except Exception as e:
                current_app.logger.error(f"Failed to delete local recording: {e}")
                
        db.session.delete(call)

    db.session.commit()
    return jsonify({"message": f"{len(calls_to_delete)} call records deleted successfully"}), 200

@leads_bp.route('/<int:id>/calls', methods=['POST'])
@jwt_required()
def log_call(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403
    
    from app.utils.security import sanitize_input
    # Accept both JSON and multipart/form-data (form includes a file input)
    if request.content_type and 'application/json' in request.content_type:
        data = request.json or {}
        connected = data.get('connected', False)
        notes = sanitize_input(data.get('notes', ''))
        next_deadline = data.get('next_action_deadline')
    else:
        data = request.form
        connected = data.get('connected') == 'on'  # checkbox sends 'on' when checked
        notes = sanitize_input(data.get('notes', ''))
        next_deadline = data.get('next_action_deadline')
    log = CallLog(
        opportunity_id=id,
        logged_by_id=user_id,
        connected=connected,
        notes=notes,
        call_type='OUTBOUND',
    )
    
    if next_deadline:
        try:
            lead.next_action_deadline = datetime.fromisoformat(next_deadline)
        except ValueError:
            pass
    
    lead.last_activity_at = datetime.now(timezone.utc)
    
    db.session.add(log)
    db.session.flush()
    
    contact_name = lead.contact.full_name if lead.contact else "Unknown"
    audit = AuditLog(
        user_id=user_id,
        table_name='call_logs',
        record_id=log.id,
        action='INSERT',
        field_name='call',
        new_value=f"Logged Call (Connected: {connected}) for Lead: {contact_name}"
    )
    db.session.add(audit)
    db.session.commit()  # commit first so we have log.id for the filename

    # ── Handle optional recording file upload ──────────────────────────────
    recording_url = None
    recording_file = request.files.get('recording_file')
    if recording_file and recording_file.filename:
        import uuid
        from werkzeug.utils import secure_filename
        from app.tasks import upload_recording_to_b2

        ext = os.path.splitext(secure_filename(recording_file.filename))[1] or '.mp3'
        
        allowed_audio_ext = {'.mp3', '.wav', '.ogg', '.m4a', '.mp4'}
        if ext.lower() not in allowed_audio_ext:
            return jsonify({"error": "Invalid recording file type"}), 400
            
        safe_name = f"call_{log.id}_{uuid.uuid4().hex[:8]}{ext}"
        recordings_dir = current_app.config.get('RECORDINGS_FOLDER', 'uploads/call record')
        os.makedirs(recordings_dir, exist_ok=True)
        local_path = os.path.join(recordings_dir, safe_name)

        recording_file.save(local_path)
        log.recording_filename = safe_name
        db.session.commit()

        import urllib.parse
        recording_url = f"/uploads/recordings/{urllib.parse.quote(safe_name)}"
        upload_error = None

        from app.models import SystemSetting
        storage_strategy = SystemSetting.get('recording_storage_strategy', 'b2')

        if storage_strategy == 'b2':
            # Synchronous B2 upload
            from app.tasks import upload_recording_to_b2
            
            try:
                link = upload_recording_to_b2(local_path, safe_name)
                if link:
                    log.recording_filename = link
                    recording_url = link
                    db.session.commit()
            except Exception as e:
                upload_error = str(e)

        resp_data = {
            "id": log.id,
            "msg": "Call logged",
            "recording_url": recording_url
        }
        if upload_error:
            resp_data["upload_error"] = upload_error
            
        return jsonify(resp_data), 201

@leads_bp.route('/calls/<int:log_id>/status', methods=['GET'])
@jwt_required()
def get_call_log_status(log_id):
    from app.models import CallLog
    log = CallLog.query.get_or_404(log_id)
    return jsonify({"id": log.id, "recording_url": log.recording_filename})

@leads_bp.route('/<int:id>/appointments', methods=['POST'])
@leads_bp.route('/<int:id>/appointment', methods=['POST'])
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
    
    from app.utils.security import sanitize_input
    location = sanitize_input(data.get('location', ''))
    
    appt = Appointment(
        opportunity_id=id,
        contact_id=lead.contact_id,
        scheduled_by_id=user_id,
        appointment_datetime=appt_dt,
        location=location,
        status=AppointmentStatus.SCHEDULED
    )
    lead.pipeline_stage = PipelineStage.APPOINTMENT_SCHEDULED
    lead.appointment_status = AppointmentStatus.SCHEDULED
    
    db.session.add(appt)
    db.session.flush()
    
    contact_name = lead.contact.full_name if lead.contact else "Unknown"
    audit = AuditLog(
        user_id=user_id,
        table_name='appointments',
        record_id=appt.id,
        action='INSERT',
        field_name='appointment',
        new_value=f"Booked Appointment for Lead: {contact_name} at {appt.appointment_datetime.isoformat()}"
    )
    db.session.add(audit)
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
    
    from app.utils.security import sanitize_input
    text = sanitize_input(data.get('text'))
    
    note = Note(
        opportunity_id=id,
        created_by_id=user_id,
        content=text,
        is_private=False
    )
    from app.models import ActivityType
    lead.last_activity_type = ActivityType.NOTE
    lead.last_activity_at = datetime.now(timezone.utc)
    db.session.add(note)
    db.session.flush()
    
    contact_name = lead.contact.full_name if lead.contact else "Unknown"
    audit = AuditLog(
        user_id=user_id,
        table_name='notes',
        record_id=note.id,
        action='INSERT',
        field_name='content',
        new_value=f"Added Activity Note: '{note.content[:40]}...' for Lead: {contact_name}"
    )
    db.session.add(audit)
    db.session.commit()
    return jsonify({"id": log.id, "msg": "Note added"}), 201

@leads_bp.route('/bulk-assign', methods=['POST'])
@jwt_required()
def bulk_assign_leads():
    current_user_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role != 'ADMIN':
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json()
    lead_ids = data.get('lead_ids', [])
    owner_id = data.get('owner_id')
    
    if not lead_ids:
        return jsonify({"error": "lead_ids is required"}), 400

    leads = Opportunity.query.filter(Opportunity.id.in_(lead_ids)).all()
    if not leads:
        return jsonify({"error": "No valid leads found"}), 404
        
    owner = db.session.query(User).get(owner_id) if owner_id else None
    owner_name = owner.full_name if owner else "Unassigned"

    for lead in leads:
        old_owner = lead.assigned_to_id
        lead.assigned_to_id = owner_id if owner_id else None
        
        # Add Audit log
        contact_name = lead.contact.full_name if lead.contact else "Unknown"
        audit = AuditLog(
            user_id=current_user_id,
            table_name='opportunities',
            record_id=lead.id,
            action='UPDATE',
            field_name='assigned_to_id',
            old_value=str(old_owner) if old_owner else "None",
            new_value=str(owner_id) if owner_id else "None"
        )
        db.session.add(audit)
        
    db.session.commit()
    return jsonify({"msg": f"Successfully assigned {len(leads)} leads to {owner_name}."}), 200
