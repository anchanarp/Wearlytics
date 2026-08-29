"""Wardrobe management blueprint."""

from flask import Blueprint

wardrobe_bp = Blueprint("wardrobe", __name__, url_prefix="/wardrobe")

from app.wardrobe import routes  # noqa: E402, F401
