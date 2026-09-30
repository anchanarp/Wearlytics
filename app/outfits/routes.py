"""AI Outfit generator and recommendation routes."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.outfits import outfits_bp


@outfits_bp.route("/")
@login_required
def index():
    # Redirect legacy GET to unified AI Stylist Quick Outfit tab
    from flask import redirect, url_for
    return redirect(url_for('stylist.index', tab='quick'))


@outfits_bp.post("/generate")
@login_required
def generate():
    """Generate a scored outfit using the recommendation engine and save it."""
    occasion = request.form.get("occasion", "Casual")
    season   = request.form.get("season",   "All Seasons")

    from app.services import recommendation_engine

    # Use the same engine as Smart Recs — top_n=1 gives the best scored combo
    recs = recommendation_engine.get_recommendations(
        user_id=current_user.id,
        occasion=occasion,
        season=season,
        top_n=1,
    )

    if not recs:
        flash(
            "Not enough wardrobe items to generate an outfit. "
            "Add at least one Top/Dress and one Bottom.",
            "error",
        )
        return redirect(url_for("stylist.index", tab="quick"))

    rec   = recs[0]
    combo = rec["clothing_items"]
    score = rec["score"]

    # Build a descriptive title from the items
    piece_names = [item.name for item in combo]
    title = f"{occasion} Look — Score {score}/100"
    desc  = (
        f"AI matched: {', '.join(piece_names)}. "
        f"Compatibility score: {score}/100 for {occasion.lower()} · {season}."
    )

    outfit = Outfit(
        user_id=current_user.id,
        title=title,
        description=desc,
        occasion=occasion,
        season=season,
        is_favorite=False,
        compatibility_score=score,
        recommendation_type="ai_smart",
    )
    outfit.items.extend(combo)
    db.session.add(outfit)
    db.session.commit()

    flash(f"✦ AI generated a new outfit: '{title}'!", "success")
    return redirect(url_for("stylist.index", tab="quick"))



@outfits_bp.post("/<int:outfit_id>/favorite")
@login_required
def toggle_favorite(outfit_id):
    """Toggle favorite status of an outfit."""
    outfit = Outfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    outfit.is_favorite = not outfit.is_favorite
    db.session.commit()
    status = "saved to" if outfit.is_favorite else "removed from"
    flash(f"Outfit '{outfit.title}' {status} favorites.", "info")
    return redirect(url_for("stylist.index", tab="quick"))


@outfits_bp.post("/<int:outfit_id>/delete")
@login_required
def delete_outfit(outfit_id):
    """Delete a saved outfit."""
    outfit = Outfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    title = outfit.title
    db.session.delete(outfit)
    db.session.commit()
    flash(f"Outfit '{title}' deleted.", "success")
    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for("stylist.index", tab="quick"))
