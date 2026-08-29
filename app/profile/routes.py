"""Profile management routes."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.profile import profile_bp


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display user profile and update user info."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name:
            flash("Name cannot be empty.", "error")
            return redirect(url_for("profile.index"))

        current_user.name = name

        if new_password:
            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "error")
                return redirect(url_for("profile.index"))
            if new_password != confirm_password:
                flash("Passwords do not match.", "error")
                return redirect(url_for("profile.index"))
            current_user.set_password(new_password)
            flash("Password updated successfully!", "success")

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile.index"))

    items_count = ClothingItem.query.filter_by(user_id=current_user.id).count()
    outfits_count = Outfit.query.filter_by(user_id=current_user.id).count()
    favorites_count = ClothingItem.query.filter_by(user_id=current_user.id, is_favorite=True).count()

    return render_template(
        "profile/index.html",
        items_count=items_count,
        outfits_count=outfits_count,
        favorites_count=favorites_count,
    )
