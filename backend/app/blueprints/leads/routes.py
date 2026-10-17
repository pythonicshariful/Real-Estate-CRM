from flask import request, jsonify, current_app
from app.blueprints.leads import leads_bp
from app.models import Opportunity, Contact, CallLog, Appointment, PipelineStage, AppointmentStatus, Objection, ObjectionCategory, Reservation, Note, PipelineHistory, db, UserRole, LeadTemperature, AuditLog, User, DurationBand, ActivityOutcome, ActivityType, Inquiry, Plot, PlotStatus, Installment, CancellationRequest, PaymentMethod, InstallmentStatus, CancellationStatus, CoachingLog
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
                "profession": contact.profession,
                "service_type": contact.service_type or lead.service_type,
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
    profession = sanitize_input(validated_data.get('profession'))
    service_type = sanitize_input(validated_data.get('service_type'))
    activity_label = sanitize_input(validated_data.get('activity_label'))
    questionnaire_answers = validated_data.get('questionnaire_answers') or {}
    
    contact = Contact.query.filter_by(phone_normalized=phone).first()
    
    if not contact:
        contact = Contact(
            full_name=full_name,
            phone_raw=phone,
            phone_normalized=phone,
            email=email,
            source=source,
            profession=profession,
            service_type=service_type
        )
        db.session.add(contact)
        db.session.flush()
    else:
        if profession and not contact.profession:
            contact.profession = profession
        if service_type and not contact.service_type:
            contact.service_type = service_type
        
    project_id = validated_data.get('project_id')

    inquiry = Inquiry(
        contact_id=contact.id,
        utm_source=source if source else 'MANUAL',
        project_interest=validated_data.get('project_interest'),
        raw_payload=validated_data,
        submitted_at=datetime.now(timezone.utc),
    )
    db.session.add(inquiry)
    db.session.flush()
        
    opp = Opportunity(
        contact_id=contact.id,
        inquiry_id=inquiry.id,
        assigned_to_id=user_id,
        project_id=project_id,
        pipeline_stage=PipelineStage.NEW,
        service_type=service_type,
        activity_label=activity_label,
        questionnaire_answers=questionnaire_answers
    )
    db.session.add(opp)
    db.session.flush() # flush to get opp.id
    
    audit = AuditLog(
        user_id=user_id,
        table_name='opportunities',
        record_id=opp.id,
        action='INSERT',
        field_name='lead',
        activity_label=activity_label,
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
        "profession": contact.profession,
        "service_type": contact.service_type or opp.service_type,
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
    can_access_recordings = role in ('ADMIN', 'MANAGER', 'GM', 'CEO')
    def format_rec_url(fname):
        if not fname or not can_access_recordings: return None
        # If it is a full URL or stored filename in B2
        if fname.startswith('http'):
            # If it's a backblazeb2 URL, refresh with fresh signature if possible
            if 'backblazeb2.com' in fname:
                import urllib.parse
                parsed = urllib.parse.urlparse(fname)
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    raw_filename = path_parts[-1]
                    from app.tasks import generate_b2_presigned_url
                    fresh_url = generate_b2_presigned_url(raw_filename, expires_in=86400)
                    if fresh_url:
                        return fresh_url
            return fname
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
            "profession": contact.profession,
            "service_type": contact.service_type or lead.service_type,
            "job_title": contact.job_title,
            "address": contact.address,
            "city": contact.city,
        }
    profile["call_logs"] = [{
        "id": c.id,
        "connected": c.connected,
        "notes": c.notes,
        "outcome": c.outcome.value if c.outcome else None,
        "activity_label": c.activity_label,
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
    
    # Extract Custom Questionnaire & Dynamic Form Answers
    profile["custom_fields"] = []
    answers = dict(lead.questionnaire_answers or {})

    # Fallback to Inquiry payload if answers is empty
    if not answers and lead.inquiry and lead.inquiry.raw_payload:
        rp = lead.inquiry.raw_payload
        if isinstance(rp, dict):
            if "questionnaire" in rp and isinstance(rp["questionnaire"], dict):
                answers = rp["questionnaire"]
            elif "lead_data" in rp and isinstance(rp["lead_data"], dict):
                field_data = rp["lead_data"].get("field_data", [])
                for f in field_data:
                    n = f.get("name")
                    vals = f.get("values", [])
                    if n not in ["full_name", "name", "email", "phone_number", "phone"] and vals:
                        answers[n] = vals[0]

    from app.models import LeadQuestionnaireQuestion
    questions = LeadQuestionnaireQuestion.query.filter_by(is_active=True).order_by(LeadQuestionnaireQuestion.order_index.asc()).all()
    if not questions:
        LeadQuestionnaireQuestion.seed_defaults()
        questions = LeadQuestionnaireQuestion.query.filter_by(is_active=True).order_by(LeadQuestionnaireQuestion.order_index.asc()).all()

    questionnaire_list = []
    seen_keys = set()
    for q in questions:
        seen_keys.add(q.question_key)
        val = answers.get(q.question_key)
        if val is None or val == "":
            if q.question_key == 'profession' and contact:
                val = contact.profession
            elif q.question_key == 'service_type':
                val = lead.service_type or (contact.service_type if contact else None)
            elif q.question_key == 'project_interest':
                val = lead.project.name if lead.project else (lead.inquiry.project_interest if lead.inquiry else None)

        val_str = str(val) if val is not None else ""
        questionnaire_list.append({
            "key": q.question_key,
            "text": q.question_text,
            "field_type": q.field_type or "text",
            "options": q.options or [],
            "value": val_str,
            "is_required": q.is_required
        })
        profile["custom_fields"].append({
            "name": q.question_text,
            "key": q.question_key,
            "value": val_str
        })

    # Append any remaining keys not in standard questions
    for k, v in answers.items():
        if k not in seen_keys:
            val_str = str(v) if v is not None else ""
            profile["custom_fields"].append({
                "name": k.replace('_', ' ').title(),
                "key": k,
                "value": val_str
            })
            questionnaire_list.append({
                "key": k,
                "text": k.replace('_', ' ').title(),
                "field_type": "text",
                "options": [],
                "value": val_str,
                "is_required": False
            })

    profile["questionnaire"] = questionnaire_list
    profile["questionnaire_answers"] = answers

    profile["timeline"] = timeline_items

    # Strip restricted fields based on role
    from app.utils.rbac import strip_restricted_fields
    if role in ('MANAGER', 'GM', 'CEO', 'ADMIN'):
        profile["manager_assessment"] = lead.manager_assessment
        profile["manager_label"] = lead.manager_label
    profile = strip_restricted_fields(profile, role)

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
            target_stage = PipelineStage[new_stage]

            # Stage Gates: RESERVATION_RECEIVED requires at least 1 valid reservation
            if target_stage in (PipelineStage.RESERVATION_RECEIVED, PipelineStage.DOCUMENTATION_IN_PROCESS, PipelineStage.SOLD):
                existing_res = Reservation.query.filter_by(opportunity_id=lead.id, is_deleted=False).first()
                if not existing_res:
                    return jsonify({"error": f"Cannot advance to {new_stage} without an approved reservation"}), 400

            lead.pipeline_stage = target_stage
            now_dt = datetime.now(timezone.utc)

            # Auto-update stage milestone date tracking
            if target_stage == PipelineStage.CONNECTED and not lead.first_contact_date:
                lead.first_contact_date = now_dt
            if target_stage in (PipelineStage.VISIT_COMPLETED, PipelineStage.APPOINTMENT_CONFIRMED) and not lead.visit_date:
                lead.visit_date = now_dt
            if target_stage == PipelineStage.NEGOTIATION and not lead.negotiation_date:
                lead.negotiation_date = now_dt
            if target_stage == PipelineStage.RESERVATION_RECEIVED and not lead.booking_date:
                lead.booking_date = now_dt
            if target_stage == PipelineStage.SOLD and not lead.sold_date:
                lead.sold_date = now_dt
            if target_stage == PipelineStage.CLOSED_LOST and not lead.closed_lost_date:
                lead.closed_lost_date = now_dt
            
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

            # Record PipelineHistory
            history = PipelineHistory(
                opportunity_id=lead.id,
                from_stage=PipelineStage[old_stage] if old_stage in PipelineStage.__members__ else None,
                to_stage=target_stage,
                changed_by_id=user_id,
                changed_at=now_dt,
                notes=data.get('stage_change_notes', f"Stage changed from {old_stage} to {new_stage}")
            )
            db.session.add(history)
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

    # Update Lead profession and service_type
    if contact:
        if 'profession' in data and data['profession'] is not None:
            contact.profession = str(data['profession']).strip()
        if 'service_type' in data and data['service_type'] is not None:
            contact.service_type = str(data['service_type']).strip()
            lead.service_type = str(data['service_type']).strip()

    if 'service_type' in data and data['service_type'] is not None:
        lead.service_type = str(data['service_type']).strip()
    if 'activity_label' in data and data['activity_label'] is not None:
        lead.activity_label = str(data['activity_label']).strip()
    if 'questionnaire_answers' in data and isinstance(data['questionnaire_answers'], dict):
        cur_q = dict(lead.questionnaire_answers or {})
        cur_q.update(data['questionnaire_answers'])
        lead.questionnaire_answers = cur_q
    
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
    outcome_val = None
    outcome_str = data.get('outcome')
    if outcome_str:
        try:
            outcome_val = ActivityOutcome[outcome_str]
        except KeyError:
            pass

    duration_val = None
    duration_str = data.get('duration_band')
    if duration_str:
        try:
            duration_val = DurationBand[duration_str]
        except KeyError:
            pass

    next_action_type_val = None
    next_action_type_str = data.get('next_action_type')
    if next_action_type_str:
        try:
            next_action_type_val = ActivityType[next_action_type_str]
        except KeyError:
            pass

    # Validation
    if connected:
        if not outcome_val:
            outcome_val = ActivityOutcome.CONNECTED
        if not duration_val:
            duration_val = DurationBand.ONE_TO_3MIN
    if not notes or len(notes.strip()) < 3:
        notes = "Call logged with recording" if request.files.get('recording_file') else "Call logged"

    activity_label = data.get('activity_label')
    if activity_label:
        activity_label = sanitize_input(activity_label)

    log = CallLog(
        opportunity_id=id,
        logged_by_id=user_id,
        connected=connected,
        notes=notes,
        call_type=data.get('call_type', 'OUTBOUND'),
        outcome=outcome_val,
        duration_band=duration_val,
        next_action_type=next_action_type_val,
        activity_label=activity_label,
    )
    
    now_dt = datetime.now(timezone.utc)
    lead.last_activity_type = ActivityType.CALL
    if activity_label:
        lead.activity_label = activity_label
    if outcome_val:
        lead.last_activity_outcome = outcome_val
    if next_action_type_val:
        lead.next_action_type = next_action_type_val

    # Auto-update first_contact_date and last_contact_date
    if not lead.first_contact_date:
        lead.first_contact_date = now_dt
    lead.last_contact_date = now_dt
    
    if next_deadline:
        try:
            lead.next_action_deadline = datetime.fromisoformat(next_deadline)
        except ValueError:
            pass
    
    lead.last_activity_at = now_dt
    
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

        ext = os.path.splitext(secure_filename(recording_file.filename))[1]
        if not ext:
            ext = '.mp3'
        
        # Support audio and video formats
        allowed_recording_ext = {
            # Audio
            '.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma', '.amr', '.weba',
            # Video
            '.mp4', '.webm', '.mkv', '.mov', '.avi', '.wmv', '.m4v', '.3gp'
        }
        if ext.lower() not in allowed_recording_ext:
            return jsonify({"error": "Invalid recording file type. Allowed formats: MP3, WAV, OGG, M4A, AAC, FLAC, AMR, MP4, WEBM, MKV, MOV, AVI."}), 400
            
        safe_name = f"call_{log.id}_{uuid.uuid4().hex[:8]}{ext}"
        recordings_dir = current_app.config.get('RECORDINGS_FOLDER', 'uploads/recordings')
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

@leads_bp.route('/<int:id>/appointments', methods=['GET'])
@jwt_required()
def get_lead_appointments(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), int(get_jwt_identity())):
        return jsonify({"error": "Access denied"}), 403
    appointments = Appointment.query.filter_by(opportunity_id=id, is_deleted=False).order_by(Appointment.appointment_datetime.asc()).all()
    return jsonify([a.to_dict() for a in appointments]), 200

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
    # Record PipelineHistory
    old_stage = lead.pipeline_stage.value if lead.pipeline_stage else 'NEW'
    history = PipelineHistory(
        opportunity_id=lead.id,
        from_stage=PipelineStage[old_stage] if old_stage in PipelineStage.__members__ else None,
        to_stage=PipelineStage.APPOINTMENT_SCHEDULED,
        changed_by_id=user_id,
        changed_at=datetime.now(timezone.utc),
        notes=f"Appointment booked for {appt.appointment_datetime.isoformat()}"
    )
    db.session.add(history)

    db.session.commit()
    return jsonify({"id": appt.id, "msg": "Appointment booked"}), 201


@leads_bp.route('/appointments/<int:appt_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    lead = Opportunity.query.get_or_404(appt.opportunity_id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), user_id):
        return jsonify({"error": "Access denied"}), 403

    appt.status = AppointmentStatus.CONFIRMED
    appt.confirmed_at = datetime.now(timezone.utc)
    lead.appointment_status = AppointmentStatus.CONFIRMED
    lead.pipeline_stage = PipelineStage.APPOINTMENT_CONFIRMED

    history = PipelineHistory(
        opportunity_id=lead.id,
        from_stage=PipelineStage.APPOINTMENT_SCHEDULED,
        to_stage=PipelineStage.APPOINTMENT_CONFIRMED,
        changed_by_id=user_id,
        changed_at=datetime.now(timezone.utc),
        notes=f"Appointment #{appt.id} confirmed"
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({"msg": "Appointment confirmed", "status": appt.status.value}), 200


@leads_bp.route('/appointments/<int:appt_id>/complete', methods=['POST'])
@jwt_required()
def complete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    lead = Opportunity.query.get_or_404(appt.opportunity_id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    appt.status = AppointmentStatus.COMPLETED
    appt.completed_at = datetime.now(timezone.utc)
    lead.appointment_status = AppointmentStatus.COMPLETED
    lead.pipeline_stage = PipelineStage.VISIT_COMPLETED
    if not lead.visit_date:
        lead.visit_date = datetime.now(timezone.utc)

    if data.get('debrief_notes'):
        appt.debrief_submitted = True
        appt.debrief_notes = data['debrief_notes']

    history = PipelineHistory(
        opportunity_id=lead.id,
        from_stage=PipelineStage.APPOINTMENT_CONFIRMED,
        to_stage=PipelineStage.VISIT_COMPLETED,
        changed_by_id=user_id,
        changed_at=datetime.now(timezone.utc),
        notes=f"Visit completed for appointment #{appt.id}"
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({"msg": "Appointment completed", "status": appt.status.value}), 200


@leads_bp.route('/appointments/<int:appt_id>/no-show', methods=['POST'])
@jwt_required()
def noshow_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    lead = Opportunity.query.get_or_404(appt.opportunity_id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    appt.status = AppointmentStatus.NO_SHOW
    appt.no_show_reason = data.get('reason', 'Client did not attend')
    lead.appointment_status = AppointmentStatus.NO_SHOW

    db.session.commit()
    return jsonify({"msg": "Appointment marked as no-show", "status": appt.status.value}), 200


@leads_bp.route('/appointments/<int:appt_id>/reschedule', methods=['POST'])
@jwt_required()
def reschedule_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    lead = Opportunity.query.get_or_404(appt.opportunity_id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    new_dt_str = data.get('appointment_datetime')
    if not new_dt_str:
        return jsonify({"error": "new appointment_datetime is required"}), 400

    try:
        new_dt = datetime.fromisoformat(new_dt_str)
    except ValueError:
        return jsonify({"error": "Invalid datetime format"}), 400

    appt.status = AppointmentStatus.RESCHEDULED

    # Create new appointment linked via rescheduled_from_id
    new_appt = Appointment(
        opportunity_id=lead.id,
        contact_id=lead.contact_id,
        scheduled_by_id=user_id,
        appointment_datetime=new_dt,
        location=data.get('location', appt.location),
        status=AppointmentStatus.SCHEDULED,
        rescheduled_from_id=appt.id
    )
    db.session.add(new_appt)
    lead.pipeline_stage = PipelineStage.APPOINTMENT_SCHEDULED
    lead.appointment_status = AppointmentStatus.SCHEDULED

    history = PipelineHistory(
        opportunity_id=lead.id,
        from_stage=PipelineStage.APPOINTMENT_SCHEDULED,
        to_stage=PipelineStage.APPOINTMENT_SCHEDULED,
        changed_by_id=user_id,
        changed_at=datetime.now(timezone.utc),
        notes=f"Appointment rescheduled from #{appt.id} to {new_dt.isoformat()}"
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({"id": new_appt.id, "msg": "Appointment rescheduled successfully"}), 201


@leads_bp.route('/appointments/<int:appt_id>/debrief', methods=['POST'])
@jwt_required()
def debrief_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    lead = Opportunity.query.get_or_404(appt.opportunity_id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    notes = data.get('notes')
    if not notes:
        return jsonify({"error": "Debrief notes are required"}), 400

    appt.debrief_submitted = True
    appt.debrief_notes = notes

    db.session.commit()
    return jsonify({"msg": "Debrief submitted successfully"}), 200

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
    return jsonify({"id": note.id, "msg": "Note added"}), 201

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


# ── Reservations ───────────────────────────────────────────────────────────────
@leads_bp.route('/<int:id>/reservations', methods=['GET'])
@jwt_required()
def get_lead_reservations(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), int(get_jwt_identity())):
        return jsonify({"error": "Access denied"}), 403
    reservations = Reservation.query.filter_by(opportunity_id=id, is_deleted=False).all()
    return jsonify([r.to_dict() for r in reservations]), 200

@leads_bp.route('/<int:id>/reservations', methods=['POST'])
@jwt_required()
def create_reservation(id):
    lead = Opportunity.query.get_or_404(id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get('role')
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    unit_reference = data.get('unit_reference')
    booking_amount = data.get('booking_amount')
    receipt_number = data.get('receipt_number')
    payment_method_str = data.get('payment_method', 'BANK_TRANSFER')
    plot_id = data.get('plot_id')

    if not unit_reference or not booking_amount or not receipt_number:
        return jsonify({"error": "unit_reference, booking_amount, and receipt_number are required"}), 400

    existing_receipt = Reservation.query.filter_by(receipt_number=receipt_number).first()
    if existing_receipt:
        return jsonify({"error": "Receipt number must be unique"}), 400

    # If plot_id provided, verify and mark plot as RESERVED
    if plot_id:
        plot = Plot.query.filter_by(id=plot_id, is_deleted=False).first()
        if plot:
            if plot.status in (PlotStatus.RESERVED, PlotStatus.BOOKED, PlotStatus.SOLD):
                return jsonify({"error": f"Plot is already {plot.status.value}"}), 400
            plot.status = PlotStatus.RESERVED

    try:
        payment_method = PaymentMethod[payment_method_str]
    except KeyError:
        payment_method = PaymentMethod.BANK_TRANSFER

    reservation = Reservation(
        opportunity_id=lead.id,
        contact_id=lead.contact_id,
        project_id=data.get('project_id', lead.project_id),
        plot_id=plot_id,
        unit_reference=unit_reference,
        booking_amount=booking_amount,
        currency=data.get('currency', 'BDT'),
        receipt_number=receipt_number,
        payment_method=payment_method,
        approving_officer_id=user_id,
        approved_at=datetime.now(timezone.utc),
        notes=data.get('notes')
    )
    db.session.add(reservation)

    # Automatically advance opportunity stage to RESERVATION_RECEIVED
    old_stage = lead.pipeline_stage.value if lead.pipeline_stage else 'NEW'
    lead.pipeline_stage = PipelineStage.RESERVATION_RECEIVED
    if not lead.booking_date:
        lead.booking_date = datetime.now(timezone.utc)

    # Record PipelineHistory
    history = PipelineHistory(
        opportunity_id=lead.id,
        from_stage=PipelineStage[old_stage] if old_stage in PipelineStage.__members__ else None,
        to_stage=PipelineStage.RESERVATION_RECEIVED,
        changed_by_id=user_id,
        changed_at=datetime.now(timezone.utc),
        notes=f"Reservation created (Receipt: {receipt_number})"
    )
    db.session.add(history)

    db.session.commit()
    return jsonify(reservation.to_dict()), 201


# ── Installments ───────────────────────────────────────────────────────────────
@leads_bp.route('/reservations/<int:res_id>/installments', methods=['GET'])
@jwt_required()
def get_installments(res_id):
    reservation = Reservation.query.get_or_404(res_id)
    installments = Installment.query.filter_by(reservation_id=res_id, is_deleted=False).order_by(Installment.installment_number.asc()).all()
    return jsonify([i.to_dict() for i in installments]), 200

@leads_bp.route('/reservations/<int:res_id>/installments', methods=['POST'])
@jwt_required()
def create_installment(res_id):
    reservation = Reservation.query.get_or_404(res_id)
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    if not data.get('installment_number') or not data.get('amount') or not data.get('due_date'):
        return jsonify({"error": "installment_number, amount, and due_date are required"}), 400

    installment = Installment(
        reservation_id=res_id,
        opportunity_id=reservation.opportunity_id,
        installment_number=data['installment_number'],
        title=data.get('title', f"Installment #{data['installment_number']}"),
        amount=data['amount'],
        due_date=datetime.fromisoformat(data['due_date']).date(),
        status=InstallmentStatus.PENDING,
        notes=data.get('notes')
    )
    db.session.add(installment)
    db.session.commit()
    return jsonify(installment.to_dict()), 201

@leads_bp.route('/installments/<int:inst_id>/pay', methods=['POST'])
@jwt_required()
def pay_installment(inst_id):
    installment = Installment.query.get_or_404(inst_id)
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    paid_amount = data.get('paid_amount', installment.amount)
    payment_method_str = data.get('payment_method', 'BANK_TRANSFER')
    try:
        pm = PaymentMethod[payment_method_str]
    except KeyError:
        pm = PaymentMethod.BANK_TRANSFER

    installment.paid_amount = paid_amount
    installment.paid_at = datetime.now(timezone.utc)
    installment.payment_method = pm
    installment.receipt_number = data.get('receipt_number')
    installment.status = InstallmentStatus.PAID
    installment.recorded_by_id = user_id
    if data.get('notes'):
        installment.notes = data['notes']

    db.session.commit()
    return jsonify(installment.to_dict()), 200


# ── Cancellation Requests ──────────────────────────────────────────────────────
@leads_bp.route('/reservations/<int:res_id>/cancellations', methods=['POST'])
@jwt_required()
def request_cancellation(res_id):
    reservation = Reservation.query.get_or_404(res_id)
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    if not data.get('reason'):
        return jsonify({"error": "Cancellation reason is required"}), 400

    cancellation = CancellationRequest(
        reservation_id=res_id,
        opportunity_id=reservation.opportunity_id,
        reason=data['reason'],
        refund_amount_requested=data.get('refund_amount_requested'),
        requested_by_id=user_id,
        status=CancellationStatus.PENDING
    )
    db.session.add(cancellation)
    db.session.commit()
    return jsonify(cancellation.to_dict()), 201

@leads_bp.route('/cancellations/<int:cancel_id>/review', methods=['POST'])
@jwt_required()
def review_cancellation(cancel_id):
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({"error": "Admin/Manager access required to review cancellation"}), 403

    cancellation = CancellationRequest.query.get_or_404(cancel_id)
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    decision = data.get('decision') # APPROVED or REJECTED

    if decision not in ('APPROVED', 'REJECTED'):
        return jsonify({"error": "decision must be APPROVED or REJECTED"}), 400

    cancellation.status = CancellationStatus[decision]
    cancellation.reviewed_by_id = user_id
    cancellation.reviewed_at = datetime.now(timezone.utc)
    cancellation.review_notes = data.get('review_notes')

    if decision == 'APPROVED':
        cancellation.refund_amount_approved = data.get('refund_amount_approved', cancellation.refund_amount_requested)
        # Release plot if attached
        reservation = cancellation.reservation
        if reservation and reservation.plot_id:
            plot = Plot.query.get(reservation.plot_id)
            if plot:
                plot.status = PlotStatus.AVAILABLE

    db.session.commit()
    return jsonify(cancellation.to_dict()), 200


# ── Objections ────────────────────────────────────────────────────────────────
@leads_bp.route('/<int:id>/objections', methods=['GET'])
@jwt_required()
def get_objections(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), int(get_jwt_identity())):
        return jsonify({"error": "Access denied"}), 403
    objections = Objection.query.filter_by(opportunity_id=id).order_by(Objection.created_at.desc()).all()
    return jsonify([{
        "id": o.id,
        "opportunity_id": o.opportunity_id,
        "category": o.category.value if o.category else None,
        "specific_objection": o.specific_objection,
        "competitor_name": o.competitor_name,
        "intensity": o.intensity,
        "is_principal": o.is_principal,
        "reactivation_eligible": o.reactivation_eligible,
        "handling_notes": o.handling_notes,
        "executive_response": o.executive_response,
        "resolved": o.resolved,
        "created_at": o.created_at.isoformat() if o.created_at else None
    } for o in objections]), 200

@leads_bp.route('/<int:id>/objections', methods=['POST'])
@jwt_required()
def add_objection(id):
    lead = Opportunity.query.get_or_404(id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    category_str = data.get('category')
    specific_objection = data.get('specific_objection')

    if not category_str or not specific_objection:
        return jsonify({"error": "category and specific_objection are required"}), 400

    try:
        cat = ObjectionCategory[category_str]
    except KeyError:
        return jsonify({"error": "Invalid objection category"}), 400

    objection = Objection(
        opportunity_id=lead.id,
        logged_by_id=user_id,
        category=cat,
        specific_objection=specific_objection,
        competitor_name=data.get('competitor_name'),
        intensity=data.get('intensity', 3),
        is_principal=data.get('is_principal', True),
        reactivation_eligible=data.get('reactivation_eligible', False),
        handling_notes=data.get('handling_notes'),
        executive_response=data.get('executive_response'),
        resolved=data.get('resolved', False)
    )
    db.session.add(objection)
    db.session.commit()
    return jsonify({"id": objection.id, "msg": "Objection logged successfully"}), 201

@leads_bp.route('/objections/<int:obj_id>', methods=['PUT'])
@jwt_required()
def update_objection(obj_id):
    objection = Objection.query.get_or_404(obj_id)
    lead = Opportunity.query.get_or_404(objection.opportunity_id)
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    if not _check_lead_access(lead, claims.get('role'), user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    if 'resolved' in data:
        objection.resolved = bool(data['resolved'])
    if 'handling_notes' in data:
        objection.handling_notes = data['handling_notes']
    if 'executive_response' in data:
        objection.executive_response = data['executive_response']
    if 'intensity' in data:
        objection.intensity = data['intensity']
    if 'reactivation_eligible' in data:
        objection.reactivation_eligible = bool(data['reactivation_eligible'])

    db.session.commit()
    return jsonify({"msg": "Objection updated successfully"}), 200


# ── Single-Lead Reassignment (Manager / Admin) ─────────────────────────────────
@leads_bp.route('/<int:id>/reassign', methods=['PUT'])
@jwt_required()
def reassign_lead(id):
    claims = get_jwt()
    role = claims.get('role')
    current_user_id = int(get_jwt_identity())
    if role not in ('MANAGER', 'GM', 'CEO', 'ADMIN'):
        return jsonify({"error": "Manager or higher role required"}), 403

    lead = Opportunity.query.get_or_404(id)
    data = request.get_json() or {}
    new_owner_id = data.get('assigned_to_id')
    reason = data.get('reason', 'Manager reassignment')

    new_owner = User.query.get(new_owner_id) if new_owner_id else None
    if new_owner_id and not new_owner:
        return jsonify({"error": "Target user not found"}), 404

    old_owner_id = lead.assigned_to_id
    lead.assigned_to_id = new_owner_id
    lead.assigned_by_id = current_user_id
    lead.assigned_date = datetime.now(timezone.utc)

    audit = AuditLog(
        user_id=current_user_id,
        table_name='opportunities',
        record_id=lead.id,
        action='UPDATE',
        field_name='assigned_to_id',
        old_value=str(old_owner_id) if old_owner_id else "None",
        new_value=str(new_owner_id) if new_owner_id else "None"
    )
    db.session.add(audit)
    db.session.commit()
    return jsonify({"msg": f"Lead reassigned to {new_owner.full_name if new_owner else 'Unassigned'}"}), 200


# ── Coaching Logs (Manager+ only) ─────────────────────────────────────────────
@leads_bp.route('/coaching', methods=['GET'])
@jwt_required()
def get_coaching_logs():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    if role in ('MANAGER', 'GM', 'CEO', 'ADMIN'):
        logs = CoachingLog.query.order_by(CoachingLog.created_at.desc()).all()
    else:
        logs = CoachingLog.query.filter_by(executive_id=user_id).order_by(CoachingLog.created_at.desc()).all()
    return jsonify([l.to_dict() for l in logs]), 200

@leads_bp.route('/coaching', methods=['POST'])
@jwt_required()
def create_coaching_log():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    if role not in ('MANAGER', 'GM', 'CEO', 'ADMIN'):
        return jsonify({"error": "Manager or higher role required"}), 403

    data = request.get_json() or {}
    executive_id = data.get('executive_id')
    if not executive_id:
        return jsonify({"error": "executive_id is required"}), 400

    coaching = CoachingLog(
        manager_id=user_id,
        executive_id=executive_id,
        call_log_id=data.get('call_log_id'),
        opportunity_id=data.get('opportunity_id'),
        score=data.get('score'),
        strengths=data.get('strengths'),
        areas_for_improvement=data.get('areas_for_improvement'),
        action_items=data.get('action_items'),
        session_date=datetime.fromisoformat(data['session_date']) if data.get('session_date') else datetime.now(timezone.utc)
    )
    db.session.add(coaching)
    db.session.commit()
    return jsonify(coaching.to_dict()), 201


# ---------------------------------------------------------------------------
# Real-Time Lead Duplicate Detection API
# ---------------------------------------------------------------------------

@leads_bp.route('/check-duplicate', methods=['GET', 'POST'])
@jwt_required()
def check_lead_duplicate():
    """
    Check if a contact or active opportunity already exists with the given phone or email.
    Used for real-time frontend duplicate alerts and prevention.
    """
    from app.utils.phone import normalize_phone
    body = request.get_json(silent=True) or {}
    phone = request.args.get('phone') or body.get('phone')
    email = request.args.get('email') or body.get('email')

    if not phone and not email:
        return jsonify({"is_duplicate": False, "match": None})

    phone = phone.strip() if phone else None
    if phone:
        if phone.startswith('880'):
            phone = '+' + phone
        elif phone.startswith('01') and len(phone) == 11:
            phone = '+88' + phone
    email = email.strip().lower() if email else None
    phone_norm = normalize_phone(phone) if phone else None
    
    contact = None
    if phone_norm:
        contact = Contact.query.filter((Contact.phone_normalized == phone_norm) | (Contact.phone_raw == phone_norm)).first()
    if not contact and phone:
        contact = Contact.query.filter((Contact.phone_raw == phone) | (Contact.phone_normalized == phone)).first()
    if not contact and email:
        contact = Contact.query.filter_by(email=email).first()

    if not contact:
        return jsonify({"is_duplicate": False, "match": None})

    terminal_stages = ['SOLD', 'CLOSED_LOST', 'INVALID', 'BOUGHT_ELSEWHERE', 'UNREACHABLE']
    active_opp = Opportunity.query.filter_by(
        contact_id=contact.id,
        is_deleted=False
    ).filter(~Opportunity.pipeline_stage.in_(terminal_stages)).order_by(Opportunity.created_at.desc()).first()

    assigned_owner_name = "Unassigned"
    if active_opp and active_opp.assigned_to:
        assigned_owner_name = active_opp.assigned_to.full_name or active_opp.assigned_to.email

    stage_val = None
    if active_opp:
        raw_stage = active_opp.pipeline_stage
        stage_val = raw_stage.value if hasattr(raw_stage, 'value') else str(raw_stage)

    return jsonify({
        "is_duplicate": True,
        "contact_id": contact.id,
        "contact_name": contact.full_name,
        "phone": contact.phone_raw,
        "email": contact.email,
        "has_active_lead": bool(active_opp),
        "opportunity_id": active_opp.id if active_opp else None,
        "assigned_to": assigned_owner_name,
        "stage": stage_val,
        "message": (
            f"Lead already exists: {contact.full_name} (Assigned: {assigned_owner_name} | Stage: {stage_val})"
            if active_opp else
            f"Existing contact found: {contact.full_name}"
        )
    })


# ---------------------------------------------------------------------------
# Lead Questionnaire (Dynamic Meta / Custom Lead Questions)
# ---------------------------------------------------------------------------

@leads_bp.route('/<int:id>/questionnaire', methods=['GET'])
@jwt_required()
def get_lead_questionnaire(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403

    from app.models import LeadQuestionnaireQuestion
    questions = LeadQuestionnaireQuestion.query.filter_by(is_active=True).order_by(LeadQuestionnaireQuestion.order_index.asc()).all()
    if not questions:
        LeadQuestionnaireQuestion.seed_defaults()
        questions = LeadQuestionnaireQuestion.query.filter_by(is_active=True).order_by(LeadQuestionnaireQuestion.order_index.asc()).all()

    answers = dict(lead.questionnaire_answers or {})
    contact = lead.contact
    if contact:
        if not answers.get('profession') and contact.profession:
            answers['profession'] = contact.profession
        if not answers.get('service_type') and (contact.service_type or lead.service_type):
            answers['service_type'] = contact.service_type or lead.service_type

    items = []
    seen = set()
    for q in questions:
        seen.add(q.question_key)
        val = answers.get(q.question_key, "")
        items.append({
            "key": q.question_key,
            "question_key": q.question_key,
            "text": q.question_text,
            "question_text": q.question_text,
            "field_type": q.field_type or "text",
            "question_type": (q.field_type or "text").upper(),
            "options": q.options or [],
            "value": str(val) if val is not None else "",
            "is_required": q.is_required
        })

    for k, v in answers.items():
        if k not in seen:
            items.append({
                "key": k,
                "question_key": k,
                "text": k.replace('_', ' ').title(),
                "question_text": k.replace('_', ' ').title(),
                "field_type": "text",
                "question_type": "TEXT",
                "options": [],
                "value": str(v) if v is not None else "",
                "is_required": False
            })

    return jsonify({
        "lead_id": lead.id,
        "answers": answers,
        "questions": items
    })


@leads_bp.route('/<int:id>/questionnaire', methods=['PUT'])
@jwt_required()
def update_lead_questionnaire(id):
    lead = Opportunity.query.get_or_404(id)
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    if not _check_lead_access(lead, role, user_id):
        return jsonify({"error": "Access denied"}), 403

    data = request.json or {}
    new_answers = data.get('answers', data)

    if not isinstance(new_answers, dict):
        return jsonify({"error": "Answers must be a JSON object"}), 400

    cur_answers = dict(lead.questionnaire_answers or {})
    cur_answers.update(new_answers)
    lead.questionnaire_answers = cur_answers

    # Synchronize top-level contact/opportunity fields
    if 'profession' in new_answers and lead.contact:
        lead.contact.profession = str(new_answers['profession']).strip()
    if 'service_type' in new_answers:
        lead.service_type = str(new_answers['service_type']).strip()
        if lead.contact:
            lead.contact.service_type = str(new_answers['service_type']).strip()

    audit = AuditLog(
        user_id=user_id,
        table_name='opportunities',
        record_id=lead.id,
        action='UPDATE',
        field_name='questionnaire_answers',
        new_value=f"Updated questionnaire answers ({len(new_answers)} fields)"
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        "status": "success",
        "lead_id": lead.id,
        "answers": lead.questionnaire_answers
    }), 200


# ---------------------------------------------------------------------------
# Automated Status Update Trigger (Scheduled / Time-Based)
# ---------------------------------------------------------------------------

@leads_bp.route('/auto-update-stages', methods=['POST'])
@jwt_required()
def trigger_stage_auto_updates():
    from app.tasks import auto_update_scheduled_lead_statuses
    stats = auto_update_scheduled_lead_statuses(current_app)
    return jsonify({
        "status": "success",
        "message": "Scheduled lead pipeline stages & deadlines successfully refreshed",
        "stats": stats
    }), 200


# ---------------------------------------------------------------------------
# Lead Import & Automatic Duplicate Detection
# ---------------------------------------------------------------------------

@leads_bp.route('/import/template', methods=['GET'])
def download_import_template():
    import io
    import csv
    from flask import Response

    headers = [
        "Full Name", "Phone Number", "Email", "Profession",
        "Service Type", "Project Name", "Budget Range", "Source", "Notes"
    ]
    sample_rows = [
        ["Shahadat Hossain", "01711223344", "shahadat@example.com", "Business Owner", "Residential Plot", "Green Valley City", "50-70 Lakhs", "Facebook Ad", "Interested in 5 Katha south facing plot"],
        ["Dr. Nasrin Akter", "01819556677", "nasrin@example.com", "Doctor", "Villa / Duplex Plot", "Lake View City", "1.2 - 2 Crore", "Referral", "Looking for lakeside facing corner plot"]
    ]

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    cw.writerows(sample_rows)

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=leads_import_template.csv"}
    )


@leads_bp.route('/import', methods=['POST'])
@jwt_required()
def import_leads():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    from app.utils.phone import normalize_phone
    from app.utils.security import sanitize_input
    from app.tasks import assign_lead_owner_auto
    import csv
    import io

    duplicate_action = (
        request.form.get('duplicate_strategy') or
        request.form.get('duplicate_action') or
        request.args.get('duplicate_action') or
        'merge'
    )
    default_assigned_to = request.form.get('assigned_to_id')
    default_owner_id = int(default_assigned_to) if default_assigned_to and default_assigned_to.isdigit() else None

    rows = []

    # Check for file upload
    if 'file' in request.files:
        f = request.files['file']
        if not f.filename:
            return jsonify({"error": "No file selected"}), 400

        content = f.read().decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(content))
        for r in csv_reader:
            rows.append(r)
    elif request.is_json:
        data = request.json or {}
        rows = data.get('leads', [])
        duplicate_action = data.get('duplicate_strategy', data.get('duplicate_action', duplicate_action))
        if data.get('assigned_to_id'):
            default_owner_id = int(data['assigned_to_id'])
    else:
        return jsonify({"error": "Please provide a CSV file or JSON body with leads"}), 400

    if not rows:
        return jsonify({"error": "No lead records found in the import payload"}), 400

    def get_val(row, *aliases):
        for a in aliases:
            for k in row.keys():
                if k.strip().lower() == a.lower():
                    v = row[k]
                    return str(v).strip() if v is not None else ""
        return ""

    total = len(rows)
    imported = 0
    duplicates_merged = 0
    duplicates_skipped = 0
    errors = []

    terminal_stages = [
        'SOLD', 'CLOSED_LOST', 'INVALID', 'BOUGHT_ELSEWHERE', 'UNREACHABLE'
    ]

    for idx, row in enumerate(rows, 1):
        try:
            full_name = get_val(row, 'Full Name', 'Name', 'Customer Name', 'full_name')
            phone_raw = get_val(row, 'Phone Number', 'Phone', 'Mobile', 'Contact Number', 'phone', 'phone_raw')
            email = get_val(row, 'Email', 'Email Address', 'email')
            profession = get_val(row, 'Profession', 'Occupation', 'Job', 'profession')
            service_type = get_val(row, 'Service Type', 'Service', 'Property Type', 'service_type')
            project_name = get_val(row, 'Project Name', 'Project', 'project', 'project_name')
            source = get_val(row, 'Source', 'Lead Source', 'source') or 'Imported'
            notes = get_val(row, 'Notes', 'Remarks', 'Comment', 'notes')
            budget_str = get_val(row, 'Budget Range', 'Budget', 'budget')

            if not phone_raw and not full_name:
                continue

            if not full_name:
                full_name = "Valued Customer"

            phone_norm = normalize_phone(phone_raw) if phone_raw else None
            
            # Find duplicate contact
            existing_contact = None
            if phone_norm:
                existing_contact = Contact.query.filter_by(phone_normalized=phone_norm).first()
            if not existing_contact and phone_raw:
                existing_contact = Contact.query.filter_by(phone_raw=phone_raw).first()
            if not existing_contact and email:
                existing_contact = Contact.query.filter_by(email=email).first()

            if existing_contact:
                if duplicate_action == 'skip':
                    duplicates_skipped += 1
                    continue
                else:
                    # Auto-merge / update existing contact
                    if profession and not existing_contact.profession:
                        existing_contact.profession = profession
                    if service_type and not existing_contact.service_type:
                        existing_contact.service_type = service_type
                    if email and not existing_contact.email:
                        existing_contact.email = email
                    
                    # Check if there is an active opportunity
                    active_opp = Opportunity.query.filter_by(
                        contact_id=existing_contact.id,
                        is_deleted=False
                    ).filter(~Opportunity.pipeline_stage.in_(terminal_stages)).first()

                    if active_opp:
                        if service_type and not active_opp.service_type:
                            active_opp.service_type = service_type
                        if notes:
                            n = Note(
                                opportunity_id=active_opp.id,
                                contact_id=existing_contact.id,
                                created_by_id=user_id,
                                content=f"[Import Update] {notes}"
                            )
                            db.session.add(n)
                        duplicates_merged += 1
                        continue
                    else:
                        # Existing contact has no active open leads -> create a new Opportunity
                        inquiry = Inquiry(
                            contact_id=existing_contact.id,
                            utm_source=source,
                            project_interest=project_name,
                            raw_payload=row,
                            submitted_at=datetime.now(timezone.utc)
                        )
                        db.session.add(inquiry)
                        db.session.flush()

                        assigned_id = default_owner_id
                        if not assigned_id:
                            auto_owner = assign_lead_owner_auto(app=current_app)
                            assigned_id = auto_owner.id if auto_owner else user_id

                        new_opp = Opportunity(
                            contact_id=existing_contact.id,
                            inquiry_id=inquiry.id,
                            assigned_to_id=assigned_id,
                            pipeline_stage=PipelineStage.NEW,
                            service_type=service_type,
                            questionnaire_answers={"profession": profession, "service_type": service_type, "budget": budget_str}
                        )
                        db.session.add(new_opp)
                        if notes:
                            db.session.flush()
                            n = Note(opportunity_id=new_opp.id, contact_id=existing_contact.id, created_by_id=user_id, content=notes)
                            db.session.add(n)
                        imported += 1
            else:
                # Brand new contact
                contact = Contact(
                    full_name=sanitize_input(full_name),
                    phone_raw=sanitize_input(phone_raw),
                    phone_normalized=phone_norm,
                    email=sanitize_input(email) if email else None,
                    profession=sanitize_input(profession) if profession else None,
                    service_type=sanitize_input(service_type) if service_type else None,
                    source=sanitize_input(source)
                )
                db.session.add(contact)
                db.session.flush()

                inquiry = Inquiry(
                    contact_id=contact.id,
                    utm_source=source,
                    project_interest=project_name,
                    raw_payload=row,
                    submitted_at=datetime.now(timezone.utc)
                )
                db.session.add(inquiry)
                db.session.flush()

                assigned_id = default_owner_id
                if not assigned_id:
                    auto_owner = assign_lead_owner_auto(app=current_app)
                    assigned_id = auto_owner.id if auto_owner else user_id

                opp = Opportunity(
                    contact_id=contact.id,
                    inquiry_id=inquiry.id,
                    assigned_to_id=assigned_id,
                    pipeline_stage=PipelineStage.NEW,
                    service_type=service_type,
                    questionnaire_answers={"profession": profession, "service_type": service_type, "budget": budget_str}
                )
                db.session.add(opp)
                if notes:
                    db.session.flush()
                    n = Note(opportunity_id=opp.id, contact_id=contact.id, created_by_id=user_id, content=notes)
                    db.session.add(n)
                imported += 1

        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")

    db.session.commit()

    return jsonify({
        "status": "success",
        "total_rows": total,
        "total_processed": total,
        "imported": imported,
        "created_count": imported,
        "duplicates_merged": duplicates_merged,
        "merged_count": duplicates_merged,
        "duplicates_skipped": duplicates_skipped,
        "skipped_count": duplicates_skipped,
        "errors": errors[:10]
    }), 200



