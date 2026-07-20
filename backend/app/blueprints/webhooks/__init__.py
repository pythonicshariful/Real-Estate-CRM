from flask import Blueprint
webhooks_bp = Blueprint('webhooks', __name__)
from . import routes
