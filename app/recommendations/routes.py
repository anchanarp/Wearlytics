"""Recommendation routes — AI-powered outfit suggestions with feedback learning."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.feedback import OutfitFeedback
from app.models.outfit import Outfit
from app.models.user_preferences import UserPreferences
from app.recommendations import recommendations_bp
from app.services import clothing_classifier, recommendation_engine


OCCASIONS = clothing_classifier.ALL_OCCASIONS
SEASONS = clothing_classifier.ALL_SEASONS


@recommendations_bp.route("/")
@login_required
def index():
    """Smart Recommendations — also accessible via /stylist/?tab=smart."""
    from app.models.clothing import ClothingItem

    selected_occasion = request.args.get("occasion", "").strip()
    selected_season   = request.args.get("season",   "").strip()

    recs = recommendation_engine.get_recommendations(
        user_id=current_user.id,
        occasion=selected_occasion or None,
        season=selected_season or None,
        top_n=3,
    )

    liked_count    = OutfitFeedback.query.filter_by(user_id=current_user.id, reaction="liked").count()
    disliked_count = OutfitFeedback.query.filter_by(user_id=current_user.id, reaction="disliked").count()

    UserPreferences.get_or_create(current_user.id)
    wardrobe_gaps = []

    return render_template(
        "recommendations/index.html",
        recommendations=recs,
        occasions=OCCASIONS,
        seasons=SEASONS,
        selected_occasion=selected_occasion,
        selected_season=selected_season,
        liked_count=liked_count,
        disliked_count=disliked_count,
        wardrobe_gaps=wardrobe_gaps,
        tab="smart",
    )



@recommendations_bp.post("/save")
@login_required
def save_outfit():
    """Save a recommended outfit to the user's outfit collection."""
    occasion = request.form.get("occasion", "Casual")
    season = request.form.get("season", "All Seasons")
    score = request.form.get("score", type=float)
    item_ids = request.form.getlist("item_ids", type=int)
    title = request.form.get("title", "").strip() or "AI Recommended Outfit"

    from app.models.clothing import ClothingItem

    items = ClothingItem.query.filter(
        ClothingItem.id.in_(item_ids),
        ClothingItem.user_id == current_user.id,
    ).all()

    if not items:
        flash("No items found to save.", "error")
        return redirect(url_for("recommendations.index"))

    outfit = Outfit(
        user_id=current_user.id,
        title=title,
        description=f"AI Smart Recommendation. Compatibility score: {score}/100",
        occasion=occasion,
        season=season,
        is_favorite=False,
        compatibility_score=score,
        recommendation_type="ai_smart",
    )
    outfit.items.extend(items)
    db.session.add(outfit)
    db.session.commit()

    flash(f"✦ Outfit saved to your collection! (Score: {score}/100)", "success")
    return redirect(url_for("recommendations.index", occasion=occasion, season=season))


@recommendations_bp.post("/feedback")
@login_required
def submit_feedback():
    """
    Record like / dislike / favorite feedback for a recommendation.
    Since recommended outfits are transient, this saves the outfit first
    then records feedback on the saved outfit.
    """
    reaction = request.form.get("reaction", "").strip()
    occasion = request.form.get("occasion", "Casual")
    season = request.form.get("season", "All Seasons")
    score = request.form.get("score", type=float)
    item_ids = request.form.getlist("item_ids", type=int)
    title = request.form.get("title", "AI Recommendation")

    if reaction not in OutfitFeedback.VALID_REACTIONS:
        flash("Invalid feedback.", "error")
        return redirect(url_for("recommendations.index"))

    from app.models.clothing import ClothingItem

    items = ClothingItem.query.filter(
        ClothingItem.id.in_(item_ids),
        ClothingItem.user_id == current_user.id,
    ).all()

    # Save the outfit so we can attach feedback to it.
    # IMPORTANT: add + flush BEFORE extending items so outfit.id is assigned
    # before the outfit_items join-table rows are written.
    outfit = Outfit(
        user_id=current_user.id,
        title=title,
        description=f"AI Recommendation (Feedback: {reaction})",
        occasion=occasion,
        season=season,
        is_favorite=(reaction == "favorited"),
        compatibility_score=score,
        recommendation_type="ai_smart",
    )
    db.session.add(outfit)
    db.session.flush()  # assigns outfit.id before any relationship writes

    outfit.items.extend(items)  # outfit.id is set; FK in outfit_items is valid

    if outfit.id is None:
        db.session.rollback()
        flash("Could not save outfit — please try again.", "error")
        return redirect(url_for("recommendations.index"))

    feedback = OutfitFeedback(
        user_id=current_user.id,
        outfit_id=outfit.id,
        reaction=reaction,
    )
    db.session.add(feedback)

    # --- Update UserPreferences based on feedback ---
    prefs = UserPreferences.get_or_create(current_user.id)

    if reaction in ("liked", "favorited"):
        # Boost preferred colors and styles from liked items
        colors = prefs.preferred_colors_list
        styles = prefs.preferred_styles_list
        for item in items:
            if item.color and item.color not in colors:
                colors.append(item.color)
            if item.style and item.style not in styles:
                styles.append(item.style)
        prefs.preferred_colors_list = colors[-10:]   # keep last 10
        prefs.preferred_styles_list = styles[-6:]

    elif reaction == "disliked":
        # Track disliked colors
        disliked = prefs.disliked_colors_list
        for item in items:
            if item.color and item.color not in disliked:
                disliked.append(item.color)
        prefs.disliked_colors_list = disliked[-10:]

    db.session.commit()

    emoji = {"liked": "👍", "disliked": "👎", "favorited": "⭐"}.get(reaction, "")
    flash(f"{emoji} Feedback saved! Future recommendations will improve.", "success")
    return redirect(url_for("recommendations.index", occasion=occasion, season=season))


@recommendations_bp.route("/preferences")
@login_required
def preferences():
    """Display and edit user's learned style preferences."""
    prefs = UserPreferences.get_or_create(current_user.id)
    db.session.commit()

    feedback_count = OutfitFeedback.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "recommendations/preferences.html",
        prefs=prefs,
        all_styles=clothing_classifier.ALL_STYLES,
        all_occasions=OCCASIONS,
        all_seasons=SEASONS,
        feedback_count=feedback_count,
    )


@recommendations_bp.post("/preferences/update")
@login_required
def update_preferences():
    """Save manually edited user preferences."""
    prefs = UserPreferences.get_or_create(current_user.id)

    prefs.preferred_styles_list = request.form.getlist("styles")
    prefs.preferred_occasions_list = request.form.getlist("occasions")
    prefs.preferred_seasons_list = request.form.getlist("seasons")

    db.session.commit()
    flash("Your style preferences have been updated!", "success")
    return redirect(url_for("recommendations.preferences"))
