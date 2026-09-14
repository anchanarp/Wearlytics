"""Unified AI Stylist — single recommendation workflow.

Flow:
  GET  /stylist/          → render form (occasion, season, wardrobe picker)
  POST /stylist/generate  → run engine, store results in session, redirect
  GET  /stylist/?done=1   → render form + results popped from session
"""

import json

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.feedback import OutfitFeedback
from app.models.outfit import Outfit
from app.models.user_preferences import UserPreferences
from app.services import clothing_classifier, recommendation_engine
from app.stylist import stylist_bp


# ---------------------------------------------------------------------------
# Occasion label → internal engine key mapping
# ---------------------------------------------------------------------------
OCCASION_DISPLAY_LIST = [
    "Casual",
    "Work / Business",
    "College / Campus",
    "Formal",
    "Party",
    "Date Night",
    "Wedding / Ceremony",
    "Festive / Traditional",
    "Sporty / Workout",
    "Travel / Vacation",
    "Beach / Resort",
    "Brunch / Cafe",
    "Outdoor / Adventure",
    "Home / Relaxed",
    "Any Occasion",
]

_OCCASION_TO_ENGINE = {
    "Casual":               "Casual",
    "Work / Business":      "Office",
    "College / Campus":     "College",
    "Formal":               "Interview",
    "Party":                "Party",
    "Date Night":           "Date",
    "Wedding / Ceremony":   "Wedding",
    "Festive / Traditional":"Party",
    "Sporty / Workout":     "Gym",
    "Travel / Vacation":    "Casual",
    "Beach / Resort":       "Casual",
    "Brunch / Cafe":        "Casual",
    "Outdoor / Adventure":  "Casual",
    "Home / Relaxed":       "Casual",
    "Any Occasion":         None,
}

SEASONS = clothing_classifier.ALL_SEASONS  # ["All Seasons", "Summer", "Rainy", "Winter"]

SESSION_KEY = "stylist_results"


# ---------------------------------------------------------------------------
# GET /stylist/
# ---------------------------------------------------------------------------

@stylist_bp.route("/")
@login_required
def index():
    """Render the AI Stylist form. If ?done=1, also pop results from session."""
    from app.models.clothing import ClothingItem

    prefs = UserPreferences.get_or_create(current_user.id)
    db.session.commit()

    wardrobe = (
        ClothingItem.query
        .filter_by(user_id=current_user.id)
        .filter_by(is_in_laundry=False)
        .order_by(ClothingItem.category, ClothingItem.name)
        .all()
    )

    # Pop result payload from session (set by POST /stylist/generate)
    result_data = None
    pinned_error = False
    if request.args.get("done") == "1":
        raw = session.pop(SESSION_KEY, None)
        if raw:
            result_data = json.loads(raw)
        pinned_error = session.pop("stylist_pinned_error", False)

    # Feedback counts for the learning banner
    liked_count    = OutfitFeedback.query.filter_by(user_id=current_user.id, reaction="liked").count()
    disliked_count = OutfitFeedback.query.filter_by(user_id=current_user.id, reaction="disliked").count()

    return render_template(
        "stylist/index.html",
        prefs=prefs,
        wardrobe=wardrobe,
        result_data=result_data,
        pinned_error=pinned_error,
        occasions=OCCASION_DISPLAY_LIST,
        seasons=SEASONS,
        liked_count=liked_count,
        disliked_count=disliked_count,
        wardrobe_gaps=recommendation_engine.detect_wardrobe_gaps(wardrobe),
        # Restore form state from session so the form stays filled after redirect
        selected_occasion=session.pop("stylist_occasion", ""),
        selected_season=session.pop("stylist_season", "All Seasons"),
        selected_item_ids=session.pop("stylist_item_ids", []),
    )


# ---------------------------------------------------------------------------
# POST /stylist/generate
# ---------------------------------------------------------------------------

@stylist_bp.post("/generate")
@login_required
def generate():
    """Run the recommendation engine and store results in session, then redirect."""
    from app.models.clothing import ClothingItem

    occasion_label = request.form.get("occasion", "").strip()
    season         = request.form.get("season", "All Seasons").strip()
    item_ids       = [int(x) for x in request.form.getlist("item_ids") if x.isdigit()]

    # Map display label → engine key
    engine_occasion = _OCCASION_TO_ENGINE.get(occasion_label)  # None = Any

    # Persist form state so it survives the redirect
    session["stylist_occasion"]  = occasion_label
    session["stylist_season"]    = season
    session["stylist_item_ids"]  = item_ids

    # Run the engine
    recs = recommendation_engine.get_recommendations(
        user_id=current_user.id,
        occasion=engine_occasion,
        season=season if season != "All Seasons" else None,
        top_n=3,
        pinned_item_ids=item_ids if item_ids else None,
    )

    if item_ids and not recs:
        # Strict pinned constraint could not be satisfied
        session["stylist_pinned_error"] = True
        return redirect(url_for("stylist.index", done="1"))

    if not recs:
        flash("Not enough wardrobe items to generate an outfit. Add at least a Top and a Bottom.", "error")
        return redirect(url_for("stylist.index"))

    # Serialize results (ORM objects → plain dicts) for session storage
    serialized = []
    for rec in recs:
        serialized.append({
            "score":            rec["score"],
            "occasion":         rec["occasion"],
            "season":           rec["season"],
            "color_breakdown":  rec["color_breakdown"],
            "category_summary": rec["category_summary"],
            "breakdown":        rec["breakdown"],
            "item_ids":         [i.id for i in rec["clothing_items"]],
            "items": [
                {
                    "id":                 i.id,
                    "name":               i.name,
                    "category":           i.category,
                    "color":              i.color,
                    "clothing_type":      i.clothing_type or "",
                    "image_url":          i.image_url,
                    "detected_color_hex": i.detected_color_hex or "",
                    "is_favorite":        i.is_favorite,
                    "wear_count":         i.wear_count,
                    "style":              i.style or "Casual",
                }
                for i in rec["clothing_items"]
            ],
        })

    session[SESSION_KEY] = json.dumps(serialized)
    return redirect(url_for("stylist.index", done="1"))
