"""Wardrobe analytics and statistics routes."""

from collections import Counter
from flask import render_template
from flask_login import current_user, login_required

from app.analytics import analytics_bp
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit


from app.utils.colors import resolve_color_hex


@analytics_bp.route("/")
@login_required
def index():
    """Calculate and display wardrobe breakdown, wear stats, and color distribution."""
    items = ClothingItem.query.filter_by(user_id=current_user.id).all()
    outfits = Outfit.query.filter_by(user_id=current_user.id).all()

    total_items = len(items)
    total_wears = sum(i.wear_count for i in items)
    avg_wears = round(total_wears / total_items, 1) if total_items > 0 else 0

    # Category Breakdown
    categories_counter = Counter(i.category for i in items)
    categories_data = [
        {"category": cat, "count": count, "percentage": round((count / total_items) * 100) if total_items > 0 else 0}
        for cat, count in categories_counter.most_common()
    ]

    # Season Breakdown
    seasons_counter = Counter(i.season for i in items)
    seasons_data = [
        {"season": s, "count": count, "percentage": round((count / total_items) * 100) if total_items > 0 else 0}
        for s, count in seasons_counter.most_common()
    ]

    # Color Breakdown with resolved CSS hex codes
    colors_counter = Counter(i.color.strip() for i in items if i.color and i.color.strip())
    color_samples = {}
    for i in items:
        if i.color and i.detected_color_hex and i.color.strip() not in color_samples:
            color_samples[i.color.strip()] = i.detected_color_hex

    colors_data = [
        {
            "color": col,
            "hex": resolve_color_hex(col, color_samples.get(col)),
            "count": count,
            "percentage": round((count / total_items) * 100) if total_items > 0 else 0,
        }
        for col, count in colors_counter.most_common(5)
    ]

    # Most Worn vs Underutilized
    sorted_by_wears = sorted(items, key=lambda x: x.wear_count, reverse=True)
    most_worn = sorted_by_wears[:4]
    least_worn = [i for i in reversed(sorted_by_wears) if i.wear_count == 0][:4]

    # Wardrobe Sustainability Index (0-100 score based on avg wears & utilization)
    active_items = sum(1 for i in items if i.wear_count > 0)
    utilization_rate = round((active_items / total_items) * 100) if total_items > 0 else 0
    sustainability_score = min(100, round((utilization_rate * 0.6) + (min(avg_wears, 20) * 2)))

    # Favorite items count
    favorites_count = sum(1 for i in items if i.is_favorite)

    return render_template(
        "analytics/index.html",
        total_items=total_items,
        total_outfits=len(outfits),
        total_wears=total_wears,
        avg_wears=avg_wears,
        categories_data=categories_data,
        seasons_data=seasons_data,
        colors_data=colors_data,
        most_worn=most_worn,
        least_worn=least_worn,
        utilization_rate=utilization_rate,
        sustainability_score=sustainability_score,
        favorites_count=favorites_count,
    )
