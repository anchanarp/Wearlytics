"""Profile management routes."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.models.user_preferences import UserPreferences
from app.profile import profile_bp
from app.services import clothing_classifier


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display user profile and update user info."""
    prefs = UserPreferences.get_or_create(current_user.id)

    if request.method == "POST":
        action = request.form.get("action", "profile")

        if action == "profile":
            name = request.form.get("name", "").strip()
            bio = request.form.get("bio", "").strip()
            avatar_color = request.form.get("avatar_color", "").strip()

            if not name:
                flash("Name cannot be empty.", "error")
                return redirect(url_for("profile.index"))

            current_user.name = name
            current_user.bio = bio or None
            if avatar_color:
                current_user.avatar_color = avatar_color

            db.session.commit()
            flash("Profile updated successfully!", "success")

        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not current_user.check_password(current_password):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("profile.index"))
            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "error")
                return redirect(url_for("profile.index"))
            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return redirect(url_for("profile.index"))
            current_user.set_password(new_password)
            db.session.commit()
            flash("Password changed successfully!", "success")

        elif action == "preferences":
            prefs.preferred_styles_list = request.form.getlist("styles")
            prefs.preferred_occasions_list = request.form.getlist("occasions")
            prefs.preferred_seasons_list = request.form.getlist("seasons")
            db.session.commit()
            flash("Style preferences updated!", "success")

        return redirect(url_for("profile.index"))

    items_count = ClothingItem.query.filter_by(user_id=current_user.id).count()
    outfits_count = Outfit.query.filter_by(user_id=current_user.id).count()
    favorites_count = ClothingItem.query.filter_by(user_id=current_user.id, is_favorite=True).count()
    laundry_count = ClothingItem.query.filter_by(user_id=current_user.id, is_in_laundry=True).count()

    db.session.commit()

    return render_template(
        "profile/index.html",
        items_count=items_count,
        outfits_count=outfits_count,
        favorites_count=favorites_count,
        laundry_count=laundry_count,
        prefs=prefs,
        all_styles=clothing_classifier.ALL_STYLES,
        all_occasions=clothing_classifier.ALL_OCCASIONS,
        all_seasons=clothing_classifier.ALL_SEASONS,
    )
