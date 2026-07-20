"""
Notes Routes - Module 10: Private/Shared note-taking.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import notes_bp
from ...extensions import db
from ...models import Note
from ...utils.rbac import get_current_user_role


@notes_bp.route("/", methods=["GET"])
@jwt_required()
def list_notes():
    """List notes visible to the current user."""
    user_id = int(get_jwt_identity())
    user_role = get_current_user_role()
    opportunity_id = request.args.get("opportunity_id", type=int)
    contact_id = request.args.get("contact_id", type=int)

    query = Note.query

    # Executives only see their own notes + shared notes
    if user_role == "EXECUTIVE":
        query = query.filter(
            (Note.created_by_id == user_id) | (Note.is_private == False)  # noqa: E712
        )

    if opportunity_id:
        query = query.filter(Note.opportunity_id == opportunity_id)
    if contact_id:
        query = query.filter(Note.contact_id == contact_id)

    notes = query.order_by(Note.created_at.desc()).limit(100).all()
    return jsonify([n.to_dict() for n in notes]), 200


@notes_bp.route("/", methods=["POST"])
@jwt_required()
def create_note():
    """Create a new note."""
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data.get("content"):
        return jsonify({"error": "'content' is required"}), 400

    note = Note(
        content=data["content"],
        is_private=data.get("is_private", False),
        created_by_id=user_id,
        opportunity_id=data.get("opportunity_id"),
        contact_id=data.get("contact_id"),
    )
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@notes_bp.route("/<int:note_id>", methods=["PUT"])
@jwt_required()
def update_note(note_id):
    """Update a note (owner only)."""
    user_id = int(get_jwt_identity())
    note = Note.query.get_or_404(note_id)

    if note.created_by_id != user_id:
        return jsonify({"error": "Access denied: you can only edit your own notes"}), 403

    data = request.get_json()
    if "content" in data:
        note.content = data["content"]
    if "is_private" in data:
        note.is_private = data["is_private"]

    db.session.commit()
    return jsonify(note.to_dict()), 200


@notes_bp.route("/<int:note_id>", methods=["DELETE"])
@jwt_required()
def delete_note(note_id):
    """Delete a note (owner only)."""
    user_id = int(get_jwt_identity())
    note = Note.query.get_or_404(note_id)
    user_role = get_current_user_role()

    if note.created_by_id != user_id and user_role != "ADMIN":
        return jsonify({"error": "Access denied"}), 403

    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Note deleted"}), 200
