"""Recommendations blueprint — AI-powered outfit suggestions."""

from flask import Blueprint

recommendations_bp = Blueprint("recommendations", __name__, url_prefix="/recommendations")

from app.recommendations import routes  # noqa: F401, E402
