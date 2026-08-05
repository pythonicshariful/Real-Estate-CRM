from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from . import finance_bp
from ...extensions import db
from ...models import Invoice, InvoiceStatus, Contact, User

def invoice_to_dict(inv):
    client = Contact.query.get(inv.contact_id)
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "contact_id": inv.contact_id,
        "contact_name": client.full_name if client else "Unknown",
        "opportunity_id": inv.opportunity_id,
        "amount": float(inv.amount),
        "currency": inv.currency,
        "status": inv.status.value if inv.status else "DRAFT",
        "issued_date": inv.issued_date.isoformat() if inv.issued_date else None,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "paid_date": inv.paid_date.isoformat() if inv.paid_date else None,
        "notes": inv.notes
    }

@finance_bp.route("/invoices/", methods=["GET"])
@jwt_required()
def list_invoices():
    status = request.args.get("status")
    query = Invoice.query
    
    if status:
        query = query.filter(Invoice.status == InvoiceStatus[status])
        
    invoices = query.order_by(Invoice.issued_date.desc()).all()
    return jsonify([invoice_to_dict(i) for i in invoices]), 200

@finance_bp.route("/invoices/", methods=["POST"])
@jwt_required()
def create_invoice():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    required = ["invoice_number", "contact_id", "amount", "issued_date", "due_date"]
    for f in required:
        if data.get(f) is None:
            return jsonify({"error": f"'{f}' is required"}), 400
            
    invoice = Invoice(
        invoice_number=data["invoice_number"],
        contact_id=int(data["contact_id"]),
        opportunity_id=data.get("opportunity_id"),
        amount=float(data["amount"]),
        currency=data.get("currency", "BDT"),
        status=InvoiceStatus[data.get("status", "DRAFT")],
        issued_date=date.fromisoformat(data["issued_date"]),
        due_date=date.fromisoformat(data["due_date"]),
        created_by_id=user_id
    )
    
    db.session.add(invoice)
    db.session.commit()
    return jsonify(invoice_to_dict(invoice)), 201

@finance_bp.route("/invoices/<int:inv_id>", methods=["PUT"])
@jwt_required()
def update_invoice(inv_id):
    invoice = Invoice.query.get_or_404(inv_id)
    data = request.get_json()
    
    if "status" in data:
        invoice.status = InvoiceStatus[data["status"]]
        if data["status"] == "PAID":
            invoice.paid_date = date.today()
    if "amount" in data:
        invoice.amount = float(data["amount"])
    if "due_date" in data:
        invoice.due_date = date.fromisoformat(data["due_date"])
    if "notes" in data:
        invoice.notes = data["notes"]
        
    db.session.commit()
    return jsonify(invoice_to_dict(invoice)), 200

@finance_bp.route("/invoices/<int:inv_id>", methods=["DELETE"])
@jwt_required()
def delete_invoice(inv_id):
    invoice = Invoice.query.get_or_404(inv_id)
    db.session.delete(invoice)
    db.session.commit()
    return jsonify({"message": "Invoice deleted successfully"}), 200

# ---------------------------------------------------------------------------
# Sales Hub Extensions (Orders, Items, Contracts)
# ---------------------------------------------------------------------------

from ...models import Order, OrderStatus, ProductItem, Contract

@finance_bp.route("/orders/", methods=["GET"])
@jwt_required()
def list_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        d = o.to_dict()
        contact = Contact.query.get(o.contact_id)
        d['contact_name'] = contact.full_name if contact else 'Unknown'
        result.append(d)
    return jsonify(result), 200

@finance_bp.route("/orders/", methods=["POST"])
@jwt_required()
def create_order():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data.get("contact_id") or not data.get("total_amount"):
        return jsonify({"error": "contact_id and total_amount are required"}), 400
    
    order = Order(
        contact_id=int(data["contact_id"]),
        total_amount=float(data["total_amount"]),
        status=OrderStatus[data.get("status", "PENDING")],
        created_by_id=user_id
    )
    db.session.add(order)
    db.session.commit()
    return jsonify(order.to_dict()), 201

@finance_bp.route("/items/", methods=["GET"])
@jwt_required()
def list_items():
    items = ProductItem.query.order_by(ProductItem.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items]), 200

@finance_bp.route("/items/", methods=["POST"])
@jwt_required()
def create_item():
    data = request.get_json()
    if not data.get("name") or not data.get("price"):
        return jsonify({"error": "name and price are required"}), 400
        
    item = ProductItem(
        name=data["name"],
        description=data.get("description", ""),
        price=float(data["price"]),
        is_active=data.get("is_active", True)
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201

@finance_bp.route("/contracts/", methods=["GET"])
@jwt_required()
def list_contracts():
    contracts = Contract.query.order_by(Contract.created_at.desc()).all()
    result = []
    for c in contracts:
        d = c.to_dict()
        contact = Contact.query.get(c.contact_id)
        d['contact_name'] = contact.full_name if contact else 'Unknown'
        result.append(d)
    return jsonify(result), 200

@finance_bp.route("/contracts/", methods=["POST"])
@jwt_required()
def create_contract():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data.get("contact_id") or not data.get("title"):
        return jsonify({"error": "contact_id and title are required"}), 400
        
    contract = Contract(
        contact_id=int(data["contact_id"]),
        title=data["title"],
        content=data.get("content", ""),
        signed=data.get("signed", False),
        created_by_id=user_id
    )
    if contract.signed:
        contract.signed_at = datetime.now(timezone.utc)
        
    db.session.add(contract)
    db.session.commit()
    return jsonify(contract.to_dict()), 201
