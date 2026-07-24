from flask import Blueprint
messages_bp = Blueprint('messages', __name__)
from . import routes
