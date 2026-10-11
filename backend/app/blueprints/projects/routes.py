from flask import request, jsonify
from app.blueprints.projects import projects_bp
from app.models import Project, ProjectStatus, Phase, Block, Road, Plot, PlotStatus, db, UserRole
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
    if not is_admin(claims.get('role')):
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
    if not is_admin(claims.get('role')):
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
    if not is_admin(claims.get('role')):
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    project = Project.query.get_or_404(project_id)
    
    # Check if there are opportunities associated with this project before deleting
    if getattr(project, 'opportunities', None):
        # Depending on models, we might not allow deletion. Assuming simple case for now.
        pass

    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'}), 200


# ── Inventory: Phases ──────────────────────────────────────────────────────────
@projects_bp.route('/<int:project_id>/phases', methods=['GET'])
@jwt_required()
def get_phases(project_id):
    phases = Phase.query.filter_by(project_id=project_id).all()
    return jsonify([p.to_dict() for p in phases]), 200

@projects_bp.route('/<int:project_id>/phases', methods=['POST'])
@jwt_required()
def create_phase(project_id):
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({'error': 'Admin access required'}), 403
    Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'Phase name is required'}), 400
    phase = Phase(
        project_id=project_id,
        name=data['name'],
        description=data.get('description')
    )
    db.session.add(phase)
    db.session.commit()
    return jsonify(phase.to_dict()), 201


# ── Inventory: Blocks ──────────────────────────────────────────────────────────
@projects_bp.route('/phases/<int:phase_id>/blocks', methods=['GET'])
@jwt_required()
def get_blocks(phase_id):
    blocks = Block.query.filter_by(phase_id=phase_id).all()
    return jsonify([b.to_dict() for b in blocks]), 200

@projects_bp.route('/phases/<int:phase_id>/blocks', methods=['POST'])
@jwt_required()
def create_block(phase_id):
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({'error': 'Admin access required'}), 403
    Phase.query.get_or_404(phase_id)
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'Block name is required'}), 400
    block = Block(
        phase_id=phase_id,
        name=data['name']
    )
    db.session.add(block)
    db.session.commit()
    return jsonify(block.to_dict()), 201


# ── Inventory: Roads ───────────────────────────────────────────────────────────
@projects_bp.route('/blocks/<int:block_id>/roads', methods=['GET'])
@jwt_required()
def get_roads(block_id):
    roads = Road.query.filter_by(block_id=block_id).all()
    return jsonify([r.to_dict() for r in roads]), 200

@projects_bp.route('/blocks/<int:block_id>/roads', methods=['POST'])
@jwt_required()
def create_road(block_id):
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({'error': 'Admin access required'}), 403
    Block.query.get_or_404(block_id)
    data = request.get_json() or {}
    if not data.get('road_number'):
        return jsonify({'error': 'Road number is required'}), 400
    road = Road(
        block_id=block_id,
        road_number=data['road_number']
    )
    db.session.add(road)
    db.session.commit()
    return jsonify(road.to_dict()), 201


# ── Inventory: Plots ───────────────────────────────────────────────────────────
@projects_bp.route('/<int:project_id>/plots', methods=['GET'])
@jwt_required()
def get_plots(project_id):
    query = Plot.query.filter_by(project_id=project_id, is_deleted=False)
    status_filter = request.args.get('status')
    if status_filter:
        try:
            query = query.filter(Plot.status == PlotStatus[status_filter.upper()])
        except KeyError:
            pass
    block_id = request.args.get('block_id')
    if block_id:
        query = query.filter_by(block_id=int(block_id))
    plots = query.order_by(Plot.plot_number.asc()).all()
    return jsonify([p.to_dict() for p in plots]), 200

@projects_bp.route('/<int:project_id>/plots', methods=['POST'])
@jwt_required()
def create_plot(project_id):
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({'error': 'Admin access required'}), 403
    Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('plot_number') or not data.get('size_katha'):
        return jsonify({'error': 'Plot number and size in Katha are required'}), 400

    plot = Plot(
        project_id=project_id,
        phase_id=data.get('phase_id'),
        block_id=data.get('block_id'),
        road_id=data.get('road_id'),
        plot_number=data['plot_number'],
        size_katha=data['size_katha'],
        facing=data.get('facing'),
        rate_per_katha=data.get('rate_per_katha'),
        total_price=data.get('total_price'),
        status=PlotStatus[data.get('status', 'AVAILABLE').upper()] if data.get('status') in PlotStatus.__members__ else PlotStatus.AVAILABLE,
        notes=data.get('notes')
    )
    db.session.add(plot)
    db.session.commit()
    return jsonify(plot.to_dict()), 201

@projects_bp.route('/plots/<int:plot_id>', methods=['GET'])
@jwt_required()
def get_plot(plot_id):
    plot = Plot.query.filter_by(id=plot_id, is_deleted=False).first_or_404()
    return jsonify(plot.to_dict()), 200

@projects_bp.route('/plots/<int:plot_id>', methods=['PUT'])
@jwt_required()
def update_plot(plot_id):
    claims = get_jwt()
    if not is_admin(claims.get('role')):
        return jsonify({'error': 'Admin access required'}), 403
    plot = Plot.query.filter_by(id=plot_id, is_deleted=False).first_or_404()
    data = request.get_json() or {}

    if 'plot_number' in data:
        plot.plot_number = data['plot_number']
    if 'size_katha' in data:
        plot.size_katha = data['size_katha']
    if 'facing' in data:
        plot.facing = data['facing']
    if 'rate_per_katha' in data:
        plot.rate_per_katha = data['rate_per_katha']
    if 'total_price' in data:
        plot.total_price = data['total_price']
    if 'status' in data and data['status'] in PlotStatus.__members__:
        plot.status = PlotStatus[data['status']]
    if 'notes' in data:
        plot.notes = data['notes']

    db.session.commit()
    return jsonify(plot.to_dict()), 200

