from flask import Blueprint

help_bp = Blueprint('help', __name__)

from . import routes
