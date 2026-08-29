"""AI Outfit generator and recommendation routes."""

import random
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.outfits import outfits_bp


@outfits_bp.route("/")
@login_required
def index():
    """Display saved outfits and AI recommendation engine."""
    outfits = Outfit.query.filter_by(user_id=current_user.id).order_by(Outfit.created_at.desc()).all()
    items_count = ClothingItem.query.filter_by(user_id=current_user.id).count()
    return render_template("outfits/index.html", outfits=outfits, items_count=items_count)


@outfits_bp.post("/generate")
@login_required
def generate():
    """AI algorithm to combine pieces into stylish outfits."""
    occasion = request.form.get("occasion", "Casual")
    season = request.form.get("season", "All Seasons")

    user_items = ClothingItem.query.filter_by(user_id=current_user.id).all()

    # Filter by season if not "All Seasons"
    if season != "All Seasons":
        season_items = [i for i in user_items if i.season in (season, "All Seasons")]
    else:
        season_items = user_items

    tops = [i for i in season_items if i.category in ["Tops", "Dresses"]]
    bottoms = [i for i in season_items if i.category == "Bottoms"]
    shoes = [i for i in season_items if i.category == "Shoes"]
    outerwear = [i for i in season_items if i.category in ["Outerwear", "Accessories"]]

    if not tops or (not bottoms and not any(t.category == "Dresses" for t in tops)):
        flash("You need at least 1 Top/Dress and 1 Bottom in your wardrobe to generate AI outfits!", "error")
        return redirect(url_for("outfits.index"))

    selected_top = random.choice(tops)
    items_in_outfit = [selected_top]

    if selected_top.category != "Dresses" and bottoms:
        items_in_outfit.append(random.choice(bottoms))

    if shoes:
        items_in_outfit.append(random.choice(shoes))

    if outerwear and random.choice([True, False]):
        items_in_outfit.append(random.choice(outerwear))

    # Generate outfit title based on pieces
    piece_names = [item.name for item in items_in_outfit]
    title_styles = [
        f"{occasion} {selected_top.color} Ensemble",
        f"Effortless {selected_top.name.split()[0]} Look",
        f"Curated {season} {occasion} Fit",
        f"Polished {selected_top.color} & Neutral Style",
    ]
    title = random.choice(title_styles)
    desc = f"AI matched: {', '.join(piece_names)}. Perfectly balanced for {occasion.lower()} settings."

    outfit = Outfit(
        user_id=current_user.id,
        title=title,
        description=desc,
        occasion=occasion,
        season=season,
        is_favorite=True,
    )
    outfit.items.extend(items_in_outfit)
    db.session.add(outfit)
    db.session.commit()

    flash(f"✦ AI generated a new outfit: '{title}'!", "success")
    return redirect(url_for("outfits.index"))


@outfits_bp.post("/<int:outfit_id>/favorite")
@login_required
def toggle_favorite(outfit_id):
    """Toggle favorite status of an outfit."""
    outfit = Outfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    outfit.is_favorite = not outfit.is_favorite
    db.session.commit()
    status = "saved to" if outfit.is_favorite else "removed from"
    flash(f"Outfit '{outfit.title}' {status} favorites.", "info")
    return redirect(url_for("outfits.index"))


@outfits_bp.post("/<int:outfit_id>/delete")
@login_required
def delete_outfit(outfit_id):
    """Delete a saved outfit."""
    outfit = Outfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    title = outfit.title
    db.session.delete(outfit)
    db.session.commit()
    flash(f"Outfit '{title}' deleted.", "success")
    return redirect(url_for("outfits.index"))
