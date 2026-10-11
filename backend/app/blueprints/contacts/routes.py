from flask import request, jsonify
from app.blueprints.contacts import contacts_bp
from app.models import Contact, db
from flask_jwt_extended import jwt_required
from datetime import datetime, timezone

def contact_to_dict(contact):
    return {
        "id": contact.id,
        "full_name": contact.full_name,
        "email": contact.email,
        "phone_raw": contact.phone_raw,
        "phone_normalized": contact.phone_normalized,
        "gender": contact.gender,
        "address": contact.address,
        "district": contact.district,
        "city": contact.city,
        "source": contact.source,
        "utm_source": contact.utm_source,
        "is_duplicate": contact.is_duplicate,
        "duplicate_of_id": contact.duplicate_of_id,
        "notes": contact.notes,
        "created_at": contact.created_at.isoformat() if contact.created_at else None
    }

@contacts_bp.route('/', methods=['GET'])
@jwt_required()
def get_contacts():
    query_str = request.args.get('query', '')
    source = request.args.get('source', '')
    
    query = Contact.query.filter(Contact.is_deleted == False)
    
    if query_str:
        query = query.filter(
            Contact.full_name.ilike(f"%{query_str}%") | 
            Contact.email.ilike(f"%{query_str}%") | 
            Contact.phone_raw.ilike(f"%{query_str}%") |
            Contact.phone_normalized.ilike(f"%{query_str}%")
        )
        
    if source:
        query = query.filter(Contact.source == source)
        
    contacts = query.order_by(Contact.created_at.desc()).all()
    return jsonify([contact_to_dict(c) for c in contacts]), 200

@contacts_bp.route('/', methods=['POST'])
@jwt_required()
def create_contact():
    data = request.get_json()
    if not data.get('full_name'):
        return jsonify({"error": "'full_name' is required"}), 400
        
    contact = Contact(
        full_name=data['full_name'],
        email=data.get('email'),
        phone_raw=data.get('phone_raw'),
        phone_normalized=data.get('phone_raw'), # simply reuse raw for normalization here
        gender=data.get('gender'),
        address=data.get('address'),
        district=data.get('district'),
        city=data.get('city'),
        source=data.get('source', 'Manual'),
        notes=data.get('notes'),
        is_deleted=False
    )
    
    db.session.add(contact)
    db.session.commit()
    return jsonify(contact_to_dict(contact)), 201

@contacts_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_contact(id):
    contact = Contact.query.get_or_404(id)
    if contact.is_deleted:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(contact_to_dict(contact)), 200

@contacts_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_contact(id):
    contact = Contact.query.get_or_404(id)
    if contact.is_deleted:
        return jsonify({"error": "Contact not found"}), 404
        
    data = request.get_json()
    
    if 'full_name' in data:
        contact.full_name = data['full_name']
    if 'email' in data:
        contact.email = data['email']
    if 'phone_raw' in data:
        contact.phone_raw = data['phone_raw']
        contact.phone_normalized = data['phone_raw']
    if 'gender' in data:
        contact.gender = data['gender']
    if 'address' in data:
        contact.address = data['address']
    if 'district' in data:
        contact.district = data['district']
    if 'city' in data:
        contact.city = data['city']
    if 'source' in data:
        contact.source = data['source']
    if 'notes' in data:
        contact.notes = data['notes']
        
    db.session.commit()
    return jsonify(contact_to_dict(contact)), 200

@contacts_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    contact.is_deleted = True
    contact.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"message": "Contact deleted successfully"}), 200

@contacts_bp.route('/<int:id>/inquiries', methods=['GET'])
@jwt_required()
def contact_inquiries(id):
    contact = Contact.query.get_or_404(id)
    return jsonify([i.raw_payload for i in contact.inquiries if contact.inquiries]), 200

@contacts_bp.route('/<int:id>/opportunities', methods=['GET'])
@jwt_required()
def contact_opportunities(id):
    contact = Contact.query.get_or_404(id)
    return jsonify([o.to_dict() for o in contact.opportunities if contact.opportunities]), 200


@contacts_bp.route('/import', methods=['POST'])
@jwt_required()
def import_contacts():
    import csv
    import io
    from app.utils.phone import normalize_phone

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded (must provide 'file' field)"}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Only CSV files are supported"}), 400

    stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
    reader = csv.DictReader(stream)

    imported_count = 0
    duplicate_count = 0
    errors = []

    for idx, row in enumerate(reader, start=1):
        full_name = row.get('full_name') or row.get('name') or row.get('Full Name')
        phone = row.get('phone') or row.get('phone_number') or row.get('Phone')
        email = row.get('email') or row.get('Email')

        if not full_name or not phone:
            errors.append(f"Row {idx}: missing full_name or phone")
            continue

        phone_norm = normalize_phone(phone)
        existing = Contact.query.filter_by(phone_normalized=phone_norm).first()
        if existing:
            duplicate_count += 1
            continue

        contact = Contact(
            full_name=full_name.strip(),
            phone_raw=phone.strip(),
            phone_normalized=phone_norm,
            email=email.strip() if email else None,
            job_title=row.get('job_title') or row.get('Job Title'),
            profession=row.get('profession') or row.get('Profession'),
            district=row.get('district') or row.get('District'),
            city=row.get('city') or row.get('City'),
            source=row.get('source') or 'CSV Import',
            consent_given=True,
            consent_date=datetime.now(timezone.utc)
        )
        db.session.add(contact)
        imported_count += 1

    db.session.commit()
    return jsonify({
        "msg": f"Import completed: {imported_count} imported, {duplicate_count} skipped duplicates",
        "imported": imported_count,
        "duplicates": duplicate_count,
        "errors": errors
    }), 200

