"""AI Outfits blueprint."""

from flask import Blueprint

outfits_bp = Blueprint("outfits", __name__, url_prefix="/outfits")

from app.outfits import routes  # noqa: E402, F401
