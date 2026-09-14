from flask import Blueprint

stylist_bp = Blueprint('stylist', __name__, url_prefix='/stylist')
from app.stylist import routes  # noqa: F401, E402