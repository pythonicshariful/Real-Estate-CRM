from flask import jsonify, request
from app.blueprints.dashboard import dashboard_bp
from app.models import Opportunity, Contact, PipelineStage, User, UserRole, db
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, date
from sqlalchemy import func

def _is_admin(role):
    return role == UserRole.ADMIN.value

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    today = date.today()
    
    base_query = Opportunity.query.filter_by(is_deleted=False)
    
    if _is_admin(role):
        # Admin sees all stats + per-owner breakdown
        total_leads = base_query.count()
        overdue = base_query.filter(
            Opportunity.next_action_deadline < datetime.utcnow(),
            Opportunity.next_action_deadline.isnot(None)
        ).count()
        
        new_today = base_query.filter(
            db.func.date(Opportunity.created_at) == today
        ).count()
        
        closed_won = base_query.filter(
            Opportunity.pipeline_stage == PipelineStage.SOLD
        ).count()
        
        # Per-owner breakdown
        lead_owners = User.query.filter_by(role=UserRole.LEAD_OWNER, is_active=True).all()
        owners_data = []
        for owner in lead_owners:
            owner_leads = base_query.filter_by(assigned_to_id=owner.id)
            owners_data.append({
                "id": owner.id,
                "name": owner.full_name,
                "color": owner.calendar_color,
                "total_leads": owner_leads.count(),
                "overdue": owner_leads.filter(
                    Opportunity.next_action_deadline < datetime.utcnow(),
                    Opportunity.next_action_deadline.isnot(None)
                ).count(),
                "new_today": owner_leads.filter(
                    db.func.date(Opportunity.created_at) == today
                ).count(),
                "closed_won": owner_leads.filter(
                    Opportunity.pipeline_stage == PipelineStage.SOLD
                ).count(),
                "is_active": owner.is_active,
            })
        
        return jsonify({
            "role": "ADMIN",
            "total_leads": total_leads,
            "overdue": overdue,
            "new_today": new_today,
            "closed_won": closed_won,
            "lead_owners": owners_data,
            "lead_owner_count": len(lead_owners),
        })
    else:
        # Lead Owner sees only their own stats
        my_q = base_query.filter_by(assigned_to_id=user_id)
        total_leads = my_q.count()
        overdue = my_q.filter(
            Opportunity.next_action_deadline < datetime.utcnow(),
            Opportunity.next_action_deadline.isnot(None)
        ).count()
        new_today = my_q.filter(
            db.func.date(Opportunity.created_at) == today
        ).count()
        closed_won = my_q.filter(
            Opportunity.pipeline_stage == PipelineStage.SOLD
        ).count()
        
        me = User.query.get(user_id)
        
        return jsonify({
            "role": "LEAD_OWNER",
            "total_leads": total_leads,
            "overdue": overdue,
            "new_today": new_today,
            "closed_won": closed_won,
            "my_color": me.calendar_color if me else "#6366f1",
        })

@dashboard_bp.route('/funnel', methods=['GET'])
@jwt_required()
def dashboard_funnel():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    base_query = Opportunity.query.filter_by(is_deleted=False)
    if not _is_admin(role):
        base_query = base_query.filter_by(assigned_to_id=user_id)
    
    stages = [s.value for s in PipelineStage]
    funnel = []
    for stage in stages:
        count = base_query.filter_by(pipeline_stage=PipelineStage[stage]).count()
        funnel.append({"stage": stage, "count": count})
    
    return jsonify({"funnel": funnel})

@dashboard_bp.route('/recent-activity', methods=['GET'])
@jwt_required()
def recent_activity():
    from app.models import CallLog
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())
    
    limit = int(request.args.get('limit', 20))
    
    query = CallLog.query
    if not _is_admin(role):
        query = query.filter_by(logged_by_id=user_id)
    
    logs = query.order_by(CallLog.created_at.desc()).limit(limit).all()
    
    result = []
    for log in logs:
        opp = Opportunity.query.get(log.opportunity_id)
        contact = Contact.query.get(opp.contact_id) if opp else None
        owner = User.query.get(log.logged_by_id)
        result.append({
            "id": log.id,
            "lead_name": contact.full_name if contact else "Unknown",
            "lead_id": log.opportunity_id,
            "notes": log.notes,
            "connected": log.connected,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "logged_by": owner.full_name if owner else "Unknown",
            "owner_color": owner.calendar_color if owner else "#6366f1",
        })
    
    return jsonify(result)

@dashboard_bp.route('/heatmap', methods=['GET'])
@jwt_required()
def dashboard_heatmap():
    return jsonify({"heatmap": []})

@dashboard_bp.route('/attendance', methods=['GET'])
@jwt_required()
def dashboard_attendance():
    return jsonify({"attendance": []})

@dashboard_bp.route('/team-performance', methods=['GET'])
@jwt_required()
def team_performance():
    return jsonify({"team": []})
