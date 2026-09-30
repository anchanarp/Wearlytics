"""Recommendation routes — AI-powered outfit suggestions with feedback learning."""

import json
from flask import flash, redirect, render_template, request, session, url_for
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
    title = request.form.get("title", "").strip()

    from app.models.clothing import ClothingItem

    items = ClothingItem.query.filter(
        ClothingItem.id.in_(item_ids),
        ClothingItem.user_id == current_user.id,
    ).all()

    if not items:
        flash("No items found to save.", "error")
        return redirect(url_for("recommendations.index"))

    # Generate a friendly title based on items if title is generic
    if not title or title.startswith("AI Stylist") or title.startswith("AI Recommended"):
        names = [it.name for it in items]
        if len(names) == 1:
            title = names[0]
        elif len(names) == 2:
            title = f"{names[0]} & {names[1]}"
        elif len(names) > 2:
            title = f"{names[0]}, {names[1]} & {len(names)-2} more"
        else:
            title = f"{occasion} Outfit"

    # Deduplication: Check if an outfit with the exact same items already exists
    target_ids = {it.id for it in items}
    existing_outfit = None
    for o in current_user.outfits.all():
        if {it.id for it in o.items} == target_ids:
            existing_outfit = o
            break

    if existing_outfit:
        existing_outfit.title = title
        existing_outfit.occasion = occasion
        existing_outfit.season = season
        existing_outfit.compatibility_score = score
        existing_outfit.recommendation_type = "user_saved"
        OutfitFeedback.query.filter_by(user_id=current_user.id, outfit_id=existing_outfit.id, reaction="disliked").delete()
        db.session.commit()
        flash(f"✦ Outfit saved to your collection! (Score: {score}/100)", "success")
        if request.referrer:
            return redirect(request.referrer)
        return redirect(url_for("recommendations.index", occasion=occasion, season=season))

    outfit = Outfit(
        user_id=current_user.id,
        title=title,
        description=f"AI Smart Recommendation. Compatibility score: {score}/100",
        occasion=occasion,
        season=season,
        is_favorite=False,
        compatibility_score=score,
        recommendation_type="user_saved",
    )
    outfit.items.extend(items)
    db.session.add(outfit)
    db.session.commit()

    flash(f"✦ Outfit saved to your collection! (Score: {score}/100)", "success")
    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for("recommendations.index", occasion=occasion, season=season))


@recommendations_bp.post("/feedback")
@login_required
def submit_feedback():
    """
    Record like / dislike / favorite feedback for a recommendation.
    Since recommended outfits are transient, this attaches to existing outfit
    or creates an internal feedback record without polluting the user's saved outfits.
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

    # Reuse existing outfit if one already exists for this combination
    target_ids = {it.id for it in items}
    outfit = None
    for o in current_user.outfits.all():
        if {it.id for it in o.items} == target_ids:
            outfit = o
            break

    if not outfit:
        outfit = Outfit(
            user_id=current_user.id,
            title=title,
            description=f"AI Recommendation (Feedback: {reaction})",
            occasion=occasion,
            season=season,
            is_favorite=(reaction == "favorited"),
            compatibility_score=score,
            recommendation_type="ai_feedback",
        )
        db.session.add(outfit)
        db.session.flush()
        outfit.items.extend(items)

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
        # Boost preferred colors and styles, and add liked clothes to favorites
        colors = prefs.preferred_colors_list
        styles = prefs.preferred_styles_list
        for item in items:
            item.is_favorite = True  # Automatically available in "Favorites Only" tab
            if item.color and item.color not in colors:
                colors.append(item.color)
            if item.style and item.style not in styles:
                styles.append(item.style)
        prefs.preferred_colors_list = colors[-10:]   # keep last 10
        prefs.preferred_styles_list = styles[-6:]

        # Update stylist session results if present so UI updates seamlessly
        raw_sess = session.get("stylist_results")
        if raw_sess:
            try:
                stored = json.loads(raw_sess)
                target_ids = {it.id for it in items}
                for rec_dict in stored:
                    for it in rec_dict.get("items", []):
                        if it.get("id") in target_ids:
                            it["is_favorite"] = True
                session["stylist_results"] = json.dumps(stored)
            except Exception:
                pass

    elif reaction == "disliked":
        # Track disliked colors and remove disliked clothes from favorites
        disliked = prefs.disliked_colors_list
        for item in items:
            item.is_favorite = False  # Remove from "Favorites Only" tab
            if item.color and item.color not in disliked:
                disliked.append(item.color)
        prefs.disliked_colors_list = disliked[-10:]

        # Update stylist session results if present so UI updates seamlessly
        raw_sess = session.get("stylist_results")
        if raw_sess:
            try:
                stored = json.loads(raw_sess)
                target_ids = {it.id for it in items}
                for rec_dict in stored:
                    for it in rec_dict.get("items", []):
                        if it.get("id") in target_ids:
                            it["is_favorite"] = False
                session["stylist_results"] = json.dumps(stored)
            except Exception:
                pass

    db.session.commit()

    emoji = {"liked": "👍", "disliked": "👎", "favorited": "⭐"}.get(reaction, "")
    if reaction in ("liked", "favorited"):
        flash(f"{emoji} Outfit liked! Its items are now available in your Favorites tab.", "success")
    elif reaction == "disliked":
        flash(f"{emoji} Outfit disliked. Its items have been removed from your Favorites.", "info")
    else:
        flash(f"{emoji} Feedback saved! Future recommendations will improve.", "success")

    if request.referrer:
        return redirect(request.referrer)
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
