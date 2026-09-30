"""Public application routes."""

from datetime import datetime
from flask import render_template
from flask_login import current_user, login_required

from app.main import main_bp
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.models.planner import WeeklyPlan
from app.utils.seeder import seed_user_wardrobe


@main_bp.get("/")
@login_required
def home():
    """Render the dashboard with dynamic user wardrobe stats."""
    # Ensure wardrobe has starter items if empty and only for demo users
    if getattr(current_user, "is_demo", False):
        seed_user_wardrobe(current_user)

    items = ClothingItem.query.filter_by(user_id=current_user.id).order_by(ClothingItem.created_at.desc()).all()
    outfits = Outfit.query.filter_by(user_id=current_user.id).all()
    weekly_plans = WeeklyPlan.query.filter_by(user_id=current_user.id).all()
    favorites = [i for i in items if i.is_favorite]

    recent_items = items[:4]
    today_str = datetime.now().strftime("%A, %B %d")

    return render_template(
        "index.html",
        total_items=len(items),
        total_outfits=len(outfits),
        total_plans=len([p for p in weekly_plans if p.outfit_id is not None]),
        total_favorites=len(favorites),
        recent_items=recent_items,
        today_str=today_str,
    )
