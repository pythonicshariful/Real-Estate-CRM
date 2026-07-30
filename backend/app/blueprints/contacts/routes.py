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
