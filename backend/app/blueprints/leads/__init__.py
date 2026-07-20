from flask import Blueprint
leads_bp = Blueprint('leads', __name__)
from . import routes
