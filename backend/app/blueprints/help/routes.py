"""
Help & Support Routes
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

from . import help_bp
from ...extensions import db
from ...models import Article, ArticleCategory
from ...utils.rbac import get_current_user_role, require_min_role

@help_bp.route("/articles", methods=["GET"])
@jwt_required()
def get_articles():
    # Only return published articles unless ADMIN
    user_role = get_current_user_role()
    query = Article.query
    
    if user_role != "ADMIN":
        query = query.filter(Article.is_published == True)
        
    articles = query.order_by(Article.created_at.desc()).all()
    return jsonify([a.to_dict() for a in articles]), 200

@help_bp.route("/articles", methods=["POST"])
@jwt_required()
@require_min_role("ADMIN")
def create_article():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get("title") or not data.get("content"):
        return jsonify({"error": "Title and content are required"}), 400
        
    article = Article(
        title=data["title"],
        content=data["content"],
        category=data.get("category", ArticleCategory.FAQ.value),
        created_by_id=user_id,
        is_published=data.get("is_published", True)
    )
    db.session.add(article)
    db.session.commit()
    return jsonify(article.to_dict()), 201
