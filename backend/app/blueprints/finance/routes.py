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
