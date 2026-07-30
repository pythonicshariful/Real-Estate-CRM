from flask import request, jsonify
from app.blueprints.projects import projects_bp
from app.models import Project, ProjectStatus, db, UserRole
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
from app.utils.rbac import is_admin

@projects_bp.route('/', methods=['GET'])
@jwt_required()
def get_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        # Calculate some basic KPIs for the project if needed, for now just basic properties
        result.append({
            'id': p.id,
            'name': p.name,
            'code': p.code,
            'description': p.description,
            'location': p.location,
            'total_units': p.total_units,
            'available_units': p.available_units,
            'price_per_sqft': float(p.price_per_sqft) if p.price_per_sqft else None,
            'status': p.status.value if p.status else None,
            'created_at': p.created_at.isoformat() if p.created_at else None
        })
    return jsonify(result), 200

@projects_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    claims = get_jwt()
    if not _is_admin(claims.get('role')):
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    data = request.get_json()
    if not data or not data.get('name') or not data.get('code'):
        return jsonify({'error': 'Name and code are required'}), 400

    existing_project = Project.query.filter_by(code=data['code']).first()
    if existing_project:
        return jsonify({'error': 'Project with this code already exists'}), 400

    new_project = Project(
        name=data['name'],
        code=data['code'],
        description=data.get('description'),
        location=data.get('location'),
        total_units=data.get('total_units'),
        available_units=data.get('available_units', data.get('total_units')),
        price_per_sqft=data.get('price_per_sqft'),
        status=ProjectStatus[data.get('status', 'ACTIVE').upper()]
    )
    db.session.add(new_project)
    db.session.commit()

    return jsonify({'message': 'Project created successfully', 'id': new_project.id}), 201

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    claims = get_jwt()
    if not _is_admin(claims.get('role')):
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    project = Project.query.get_or_404(project_id)
    data = request.get_json()

    if 'name' in data:
        project.name = data['name']
    if 'code' in data and data['code'] != project.code:
        existing = Project.query.filter_by(code=data['code']).first()
        if existing:
            return jsonify({'error': 'Project code must be unique'}), 400
        project.code = data['code']
    if 'description' in data:
        project.description = data['description']
    if 'location' in data:
        project.location = data['location']
    if 'total_units' in data:
        project.total_units = data['total_units']
    if 'available_units' in data:
        project.available_units = data['available_units']
    if 'price_per_sqft' in data:
        project.price_per_sqft = data['price_per_sqft']
    if 'status' in data:
        try:
            project.status = ProjectStatus[data['status'].upper()]
        except KeyError:
            pass

    db.session.commit()
    return jsonify({'message': 'Project updated successfully'}), 200

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    claims = get_jwt()
    if not _is_admin(claims.get('role')):
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    project = Project.query.get_or_404(project_id)
    
    # Check if there are opportunities associated with this project before deleting
    if getattr(project, 'opportunities', None):
        # Depending on models, we might not allow deletion. Assuming simple case for now.
        pass

    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'}), 200
