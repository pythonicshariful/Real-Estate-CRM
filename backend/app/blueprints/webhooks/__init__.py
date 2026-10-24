from flask import Blueprint
webhooks_bp = Blueprint('webhooks', __name__)
from . import routes       # noqa: E402,F401
from . import facebook     # noqa: E402,F401
