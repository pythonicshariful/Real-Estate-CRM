"""
Expenses Routes - Module 14: Financial outflow tracking.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date

from . import expenses_bp
from ...extensions import db
from ...models import Expense
from ...utils.rbac import get_current_user_role, require_min_role


@expenses_bp.route("/", methods=["GET"])
@jwt_required()
def list_expenses():
    """List expense records."""
    user_id = get_jwt_identity()
    user_role = get_current_user_role()
    category = request.args.get("category")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = Expense.query

    # Executives only see their own expenses
    if user_role == "EXECUTIVE":
        query = query.filter_by(submitted_by_id=user_id)

    if category:
        query = query.filter_by(category=category)
    if date_from:
        query = query.filter(Expense.expense_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.filter(Expense.expense_date <= date.fromisoformat(date_to))

    expenses = query.order_by(Expense.expense_date.desc()).limit(500).all()
    total = sum(e.amount for e in expenses)

    return jsonify({
        "expenses": [e.to_dict() for e in expenses],
        "total": float(total),
        "currency": "BDT"
    }), 200


@expenses_bp.route("/", methods=["POST"])
@jwt_required()
def create_expense():
    """Submit a new expense."""
    user_id = get_jwt_identity()
    data = request.get_json()

    required_fields = ["amount", "category", "description", "expense_date"]
    for field in required_fields:
        if data.get(field) is None:
            return jsonify({"error": f"'{field}' is required"}), 400

    expense = Expense(
        amount=data["amount"],
        currency=data.get("currency", "BDT"),
        category=data["category"],
        description=data["description"],
        expense_date=date.fromisoformat(data["expense_date"]),
        submitted_by_id=user_id,
        opportunity_id=data.get("opportunity_id"),
        receipt_filename=data.get("receipt_filename"),
        status="PENDING",
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201


@expenses_bp.route("/<int:expense_id>/approve", methods=["POST"])
@jwt_required()
@require_min_role("ADMIN")
def approve_expense(expense_id):
    """Approve or reject an expense (Manager+)."""
    expense = Expense.query.get_or_404(expense_id)
    data = request.get_json()
    action = data.get("action")  # "APPROVE" or "REJECT"

    if action not in ["APPROVE", "REJECT"]:
        return jsonify({"error": "'action' must be APPROVE or REJECT"}), 400

    expense.status = "APPROVED" if action == "APPROVE" else "REJECTED"
    expense.approval_notes = data.get("notes")

    db.session.commit()
    return jsonify(expense.to_dict()), 200


@expenses_bp.route("/summary", methods=["GET"])
@jwt_required()
@require_min_role("ADMIN")
def expense_summary():
    """Expense summary by category (Manager+)."""
    from sqlalchemy import func
    results = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label("total"),
        func.count(Expense.id).label("count")
    ).filter_by(status="APPROVED").group_by(Expense.category).all()

    return jsonify([
        {"category": r.category, "total": float(r.total), "count": r.count}
        for r in results
    ]), 200
