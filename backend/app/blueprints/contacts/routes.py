from flask import request, jsonify
from app.blueprints.contacts import contacts_bp
from app.models import Contact, db
from flask_jwt_extended import jwt_required

@contacts_bp.route('/', methods=['GET'])
@jwt_required()
def get_contacts():
    return jsonify([])

@contacts_bp.route('/', methods=['POST'])
@jwt_required()
def create_contact():
    return jsonify({"msg": "Created"}), 201

@contacts_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_contact(id):
    contact = Contact.query.get_or_404(id)
    return jsonify({"id": contact.id, "full_name": contact.full_name})

@contacts_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_contact(id):
    return jsonify({"msg": "Updated"})

@contacts_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    contact.is_deleted = True
    db.session.commit()
    return jsonify({"msg": "Deleted"})

@contacts_bp.route('/<int:id>/inquiries', methods=['GET'])
@jwt_required()
def contact_inquiries(id):
    return jsonify([])

@contacts_bp.route('/<int:id>/opportunities', methods=['GET'])
@jwt_required()
def contact_opportunities(id):
    return jsonify([])
