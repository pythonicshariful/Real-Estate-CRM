"""
Prospects Routes (Estimates and Proposals)
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
import json

from . import prospects_bp
from ...extensions import db
from ...models import Proposal, Estimate, Contact, ProposalStatus
from ...utils.rbac import get_current_user_role

@prospects_bp.route("/proposals", methods=["GET"])
@jwt_required()
def get_proposals():
    user_id = get_jwt_identity()
    user_role = get_current_user_role()
    
    query = Proposal.query
    if user_role != "ADMIN":
        query = query.filter(Proposal.created_by_id == user_id)
        
    proposals = query.order_by(Proposal.created_at.desc()).all()
    
    result = []
    for p in proposals:
        d = p.to_dict()
        contact = Contact.query.get(p.contact_id)
        d['contact_name'] = contact.full_name if contact else 'Unknown'
        result.append(d)
        
    return jsonify(result), 200

@prospects_bp.route("/proposals", methods=["POST"])
@jwt_required()
def create_proposal():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get("title") or not data.get("contact_id"):
        return jsonify({"error": "Title and contact_id are required"}), 400
        
    proposal = Proposal(
        title=data["title"],
        contact_id=data["contact_id"],
        opportunity_id=data.get("opportunity_id"),
        created_by_id=user_id,
        content=data.get("content", ""),
        total_value=data.get("total_value", 0.0),
        status=ProposalStatus.DRAFT
    )
    db.session.add(proposal)
    db.session.commit()
    return jsonify(proposal.to_dict()), 201

@prospects_bp.route("/estimates", methods=["GET"])
@jwt_required()
def get_estimates():
    user_id = get_jwt_identity()
    user_role = get_current_user_role()
    
    query = Estimate.query
    if user_role != "ADMIN":
        query = query.filter(Estimate.created_by_id == user_id)
        
    estimates = query.order_by(Estimate.created_at.desc()).all()
    
    result = []
    for e in estimates:
        d = e.to_dict()
        contact = Contact.query.get(e.contact_id)
        d['contact_name'] = contact.full_name if contact else 'Unknown'
        result.append(d)
        
    return jsonify(result), 200

@prospects_bp.route("/estimates", methods=["POST"])
@jwt_required()
def create_estimate():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get("contact_id"):
        return jsonify({"error": "contact_id is required"}), 400
        
    estimate = Estimate(
        contact_id=data["contact_id"],
        created_by_id=user_id,
        project_id=data.get("project_id"),
        estimated_amount=data.get("estimated_amount", 0.0),
        details=data.get("details", "")
    )
    db.session.add(estimate)
    db.session.commit()
    return jsonify(estimate.to_dict()), 201
