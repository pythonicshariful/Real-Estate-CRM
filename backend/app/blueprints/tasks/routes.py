from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from . import tasks_bp
from ...extensions import db
from ...models import Task, TaskPriority, TaskStatus, User, UserRole, Opportunity
from ...utils.rbac import get_current_user_role

def task_to_dict(task):
    assignee = User.query.get(task.assigned_to_id)
    creator = User.query.get(task.created_by_id)
    opportunity = Opportunity.query.get(task.opportunity_id) if task.opportunity_id else None
    
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "assigned_to_id": task.assigned_to_id,
        "assigned_to_name": assignee.full_name if assignee else "Unknown",
        "created_by_id": task.created_by_id,
        "created_by_name": creator.full_name if creator else "Unknown",
        "opportunity_id": task.opportunity_id,
        "opportunity_name": opportunity.project.name if (opportunity and opportunity.project) else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "priority": task.priority.value if task.priority else "MEDIUM",
        "status": task.status.value if task.status else "PENDING",
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }

@tasks_bp.route("/", methods=["GET"])
@jwt_required()
def list_tasks():
    user_id = int(get_jwt_identity())
    user_role = get_current_user_role()
    
    status = request.args.get("status")
    priority = request.args.get("priority")
    assigned_to_id = request.args.get("assigned_to_id", type=int)
    
    query = Task.query
    
    # Filter based on role: non-admins see only tasks assigned to them or created by them
    if user_role != "ADMIN":
        query = query.filter((Task.assigned_to_id == user_id) | (Task.created_by_id == user_id))
        
    if status:
        query = query.filter(Task.status == TaskStatus[status])
    if priority:
        query = query.filter(Task.priority == TaskPriority[priority])
    if assigned_to_id:
        query = query.filter(Task.assigned_to_id == assigned_to_id)
        
    tasks = query.order_by(Task.due_date.asc()).all()
    return jsonify([task_to_dict(t) for t in tasks]), 200

@tasks_bp.route("/", methods=["POST"])
@jwt_required()
def create_task():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data.get("title") or not data.get("due_date"):
        return jsonify({"error": "'title' and 'due_date' are required"}), 400
        
    try:
        due_date = datetime.fromisoformat(data["due_date"].replace('Z', ''))
    except ValueError:
        return jsonify({"error": "Invalid due_date format (ISO 8601 expected)"}), 400
        
    assigned_to_id = data.get("assigned_to_id")
    if assigned_to_id:
        assigned_to_id = int(assigned_to_id)
    else:
        assigned_to_id = user_id
        
    task = Task(
        title=data["title"],
        description=data.get("description"),
        assigned_to_id=assigned_to_id,
        created_by_id=user_id,
        opportunity_id=data.get("opportunity_id"),
        due_date=due_date,
        priority=TaskPriority[data.get("priority", "MEDIUM")],
        status=TaskStatus[data.get("status", "PENDING")]
    )
    
    db.session.add(task)
    db.session.commit()
    return jsonify(task_to_dict(task)), 201

@tasks_bp.route("/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id):
    user_id = int(get_jwt_identity())
    user_role = get_current_user_role()
    task = Task.query.get_or_404(task_id)
    
    # Non-admins can only update tasks assigned to them or created by them
    if user_role != "ADMIN" and task.assigned_to_id != user_id and task.created_by_id != user_id:
        return jsonify({"error": "Access denied"}), 403
        
    data = request.get_json()
    
    if "title" in data:
        task.title = data["title"]
    if "description" in data:
        task.description = data["description"]
    if "due_date" in data:
        try:
            task.due_date = datetime.fromisoformat(data["due_date"].replace('Z', ''))
        except ValueError:
            return jsonify({"error": "Invalid due_date format"}), 400
    if "priority" in data:
        task.priority = TaskPriority[data["priority"]]
    if "status" in data:
        task.status = TaskStatus[data["status"]]
    if "assigned_to_id" in data:
        task.assigned_to_id = int(data["assigned_to_id"]) if data["assigned_to_id"] else user_id
    if "opportunity_id" in data:
        task.opportunity_id = int(data["opportunity_id"]) if data["opportunity_id"] else None
        
    db.session.commit()
    return jsonify(task_to_dict(task)), 200

@tasks_bp.route("/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    user_id = int(get_jwt_identity())
    user_role = get_current_user_role()
    task = Task.query.get_or_404(task_id)
    
    # Only creator or admin can delete tasks
    if user_role != "ADMIN" and task.created_by_id != user_id:
        return jsonify({"error": "Access denied"}), 403
        
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully"}), 200
