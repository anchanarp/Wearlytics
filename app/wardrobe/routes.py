"""Wardrobe routes for managing clothing items."""

import os
import uuid
from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.clothing import ClothingItem
from app.wardrobe import wardrobe_bp
from app.services import clothing_classifier, color_detector

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


PRESET_IMAGES = [
    {"label": "Classic White Shirt", "url": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=600&auto=format&fit=crop&q=80"},
    {"label": "Denim Jacket", "url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=600&auto=format&fit=crop&q=80"},
    {"label": "Tailored Trousers", "url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&auto=format&fit=crop&q=80"},
    {"label": "White Sneakers", "url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&auto=format&fit=crop&q=80"},
    {"label": "Cashmere Sweater", "url": "https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=600&auto=format&fit=crop&q=80"},
    {"label": "Leather Boots", "url": "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=600&auto=format&fit=crop&q=80"},
    {"label": "Trench Coat", "url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=600&auto=format&fit=crop&q=80"},
    {"label": "Summer Dress", "url": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=600&auto=format&fit=crop&q=80"},
]


def _save_uploaded_image(file):
    """Save an uploaded image file and return its static URL AND absolute disk path."""
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    upload_dir = os.path.join(current_app.static_folder, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    abs_path = os.path.join(upload_dir, unique_filename)
    file.save(abs_path)
    static_url = url_for("static", filename=f"uploads/{unique_filename}")
    return static_url, abs_path


@wardrobe_bp.post("/analyze")
# Authentication handled manually to return JSON 401.
def analyze_image():
    """
    AJAX endpoint — receive an uploaded image, run AI analysis, return JSON.
    Used by the upload form to show live AI suggestions before saving.

    Returns JSON:
        {success, category, clothing_type, confidence, source, color_hex, color_name}
    """
    if not current_user.is_authenticated:
        return jsonify({"success": False, "error": "Session expired"}), 401
    file = request.files.get("image_file")
    if not file or not file.filename or not allowed_file(file.filename):
        return jsonify({"success": False, "error": "No valid image provided."})

    try:
        # Save temporarily to run AI analysis
        _, abs_path = _save_uploaded_image(file)

        result = {"success": True, "category": "Tops", "clothing_type": "",
                  "confidence": 0.0, "source": "fallback",
                  "color_hex": "", "color_name": ""}

        # --- Clothing classification ---
        try:
            clf = clothing_classifier.classify(abs_path)
            result["category"]      = clf.get("category", "Tops")
            result["clothing_type"] = clf.get("clothing_type", "")
            result["confidence"]    = round(clf.get("confidence", 0.0) * 100, 1)
            result["source"]        = clf.get("source", "fallback")
        except Exception:
            pass

        # --- Color detection ---
        try:
            col = color_detector.extract_color(abs_path)
            if col:
                result["color_hex"]  = col.get("hex", "")
                result["color_name"] = col.get("name", "")
        except Exception:
            pass

        return jsonify(result)

    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)})


@wardrobe_bp.route("/")
@login_required
def index():
    """Display user's wardrobe with search and filtering options."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    season = request.args.get("season", "").strip()
    favorite_only = request.args.get("favorite") == "1"

    items_query = ClothingItem.query.filter_by(user_id=current_user.id)

    if query:
        items_query = items_query.filter(
            db.or_(
                ClothingItem.name.ilike(f"%{query}%"),
                ClothingItem.brand.ilike(f"%{query}%"),
                ClothingItem.color.ilike(f"%{query}%"),
            )
        )
    if category:
        items_query = items_query.filter(ClothingItem.category == category)
    if season:
        items_query = items_query.filter(ClothingItem.season == season)
    if favorite_only:
        items_query = items_query.filter(ClothingItem.is_favorite == True)

    items = items_query.order_by(ClothingItem.created_at.desc()).all()

    categories = ["All", "Tops", "Bottoms", "Shoes", "Outerwear", "Accessories", "Dresses"]
    seasons = ["All", "All Seasons", "Summer", "Winter", "Spring/Fall"]

    return render_template(
        "wardrobe/index.html",
        items=items,
        categories=categories,
        seasons=seasons,
        selected_category=category or "All",
        selected_season=season or "All",
        search_query=query,
        favorite_only=favorite_only,
    )


@wardrobe_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Form to add a new clothing item to the user's wardrobe."""
    # AI prediction to pre-fill the form (GET only)
    ai_prediction = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "Tops")
        color = request.form.get("color", "Black").strip() or "Black"
        season = request.form.get("season", "All Seasons")
        brand = request.form.get("brand", "").strip()
        style = request.form.get("style", "Casual").strip() or "Casual"
        clothing_type = request.form.get("clothing_type", "").strip()
        is_favorite = request.form.get("is_favorite") == "on"
        preset_url = request.form.get("preset_url", "").strip()

        if not name:
            flash("Please enter a name for the clothing item.", "error")
            return redirect(url_for("wardrobe.upload"))

        image_url = ""
        abs_path = None
        file = request.files.get("image_file")
        if file and file.filename and allowed_file(file.filename):
            image_url, abs_path = _save_uploaded_image(file)
        elif preset_url:
            image_url = preset_url
        else:
            image_url = "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=600&auto=format&fit=crop&q=80"

        # --- AI Analysis (non-blocking) ---
        detected_hex = None
        ai_confidence = None
        detected_color_name = None
        if abs_path:
            try:
                color_result = color_detector.extract_color(abs_path)
                if color_result:
                    detected_hex = color_result["hex"]
                    detected_color_name = color_result["name"]
                    # Auto-fill color if user left it as default
                    if color in ("Black", "") and detected_color_name:
                        color = detected_color_name
            except Exception:
                pass

            try:
                clf_result = clothing_classifier.classify(abs_path)
                ai_confidence = clf_result.get("confidence", 0.0)
                # Auto-fill category if AI is confident enough and user left default
                if ai_confidence >= 0.6 and clf_result.get("category") and not clothing_type:
                    clothing_type = clf_result.get("clothing_type", "")
            except Exception:
                pass

        item = ClothingItem(
            user_id=current_user.id,
            name=name,
            category=category,
            color=color,
            season=season,
            brand=brand,
            image_url=image_url,
            is_favorite=is_favorite,
            style=style,
            clothing_type=clothing_type or None,
            detected_color_hex=detected_hex,
            ai_confidence=ai_confidence,
        )
        db.session.add(item)
        db.session.commit()

        if detected_color_name and detected_hex:
            flash(
                f"✦ AI detected dominant color: {detected_color_name} ({detected_hex}). "
                f"'{name}' added to your wardrobe!",
                "success",
            )
        else:
            flash(f"'{name}' added to your wardrobe!", "success")
        return redirect(url_for("wardrobe.index"))

    return render_template(
        "wardrobe/upload.html",
        preset_images=PRESET_IMAGES,
        all_styles=clothing_classifier.ALL_STYLES,
        all_occasions=clothing_classifier.ALL_OCCASIONS,
        all_seasons=clothing_classifier.ALL_SEASONS,
        ai_prediction=ai_prediction,
    )


@wardrobe_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    """Edit an existing clothing item."""
    item = ClothingItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Item name cannot be empty.", "error")
            return redirect(url_for("wardrobe.edit_item", item_id=item_id))

        item.name = name
        item.category = request.form.get("category", item.category)
        item.color = request.form.get("color", item.color).strip() or item.color
        item.season = request.form.get("season", item.season)
        item.brand = request.form.get("brand", "").strip() or None
        item.is_favorite = request.form.get("is_favorite") == "on"
        item.style = request.form.get("style", item.style or "Casual")
        item.clothing_type = request.form.get("clothing_type", "").strip() or item.clothing_type

        # Only replace image if a new file was uploaded
        file = request.files.get("image_file")
        if file and file.filename and allowed_file(file.filename):
            item.image_url, _ = _save_uploaded_image(file)

        db.session.commit()
        flash(f"'{item.name}' updated successfully!", "success")
        return redirect(url_for("wardrobe.index"))

    return render_template(
        "wardrobe/edit.html",
        item=item,
        all_styles=clothing_classifier.ALL_STYLES,
        all_types=clothing_classifier.get_types_for_category(item.category),
        all_seasons=clothing_classifier.ALL_SEASONS,
    )


@wardrobe_bp.post("/<int:item_id>/wear")
@login_required
def wear_item(item_id):
    """Increment the wear count and record the date for a clothing item. Returns JSON for AJAX requests."""
    from datetime import datetime, timezone as tz
    item = ClothingItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item.wear_count += 1
    item.last_worn_at = datetime.now(tz.utc)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "wear_count": item.wear_count,
            "last_worn_at": item.last_worn_at.strftime("%d %b %Y") if item.last_worn_at else None,
        })

    flash(f"Logged wear for '{item.name}'. (Total: {item.wear_count})", "success")
    return redirect(request.referrer or url_for("wardrobe.index"))


@wardrobe_bp.post("/<int:item_id>/favorite")
@login_required
def toggle_favorite(item_id):
    """Toggle favorite status of a clothing item. Returns JSON for AJAX requests."""
    item = ClothingItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item.is_favorite = not item.is_favorite
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "is_favorite": item.is_favorite})

    status = "added to" if item.is_favorite else "removed from"
    flash(f"'{item.name}' {status} favorites.", "info")
    return redirect(request.referrer or url_for("wardrobe.index"))


@wardrobe_bp.post("/<int:item_id>/laundry")
@login_required
def toggle_laundry(item_id):
    """Toggle the laundry/availability status of a clothing item."""
    item = ClothingItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item.is_in_laundry = not item.is_in_laundry
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "is_in_laundry": item.is_in_laundry})

    status = "moved to laundry 🧺" if item.is_in_laundry else "marked as available ✅"
    flash(f"'{item.name}' {status}.", "info")
    return redirect(request.referrer or url_for("wardrobe.index"))


@wardrobe_bp.post("/<int:item_id>/delete")
@login_required
def delete_item(item_id):
    """Delete a clothing item from user's wardrobe."""
    item = ClothingItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item_name = item.name
    db.session.delete(item)
    db.session.commit()
    flash(f"'{item_name}' removed from your wardrobe.", "success")
    return redirect(url_for("wardrobe.index"))

