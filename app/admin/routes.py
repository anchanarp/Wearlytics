# app/admin/routes.py
"""Admin routes – full database-driven pages."""

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from sqlalchemy import func

from app.extensions import db
from app.models import User
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.models.feedback import OutfitFeedback
from app.utils.pagination import paginate
from . import admin_bp, admin_required

PER_PAGE = 25


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────
@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "total_users":    User.query.count(),
        "total_clothing": ClothingItem.query.count(),
        "total_outfits":  Outfit.query.count(),
        "total_feedback": OutfitFeedback.query.count(),
        "admin_users":    User.query.filter_by(is_admin=True).count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_feedback = (
        OutfitFeedback.query.order_by(OutfitFeedback.created_at.desc()).limit(5).all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_users=recent_users,
        recent_feedback=recent_feedback,
    )


# ──────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────
@admin_bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = User.query.order_by(User.created_at.desc())
    if q:
        pattern = f"%{q}%"
        query = query.filter(User.name.ilike(pattern) | User.email.ilike(pattern))

    pag = paginate(query, page, PER_PAGE)
    return render_template("admin/users.html", pag=pag, q=q)


@admin_bp.post("/users/<int:user_id>/promote")
@admin_required
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash(f"{user.name} promoted to admin.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.post("/users/<int:user_id>/demote")
@admin_required
def demote_user(user_id):
    user = User.query.get_or_404(user_id)
    admin_count = User.query.filter_by(is_admin=True).count()
    if admin_count <= 1 and user.is_admin:
        flash("Cannot demote the last remaining admin.", "error")
        return redirect(url_for("admin.users"))
    user.is_admin = False
    db.session.commit()
    flash(f"{user.name} demoted to regular user.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.post("/users/<int:user_id>/delete")
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))
    admin_count = User.query.filter_by(is_admin=True).count()
    if user.is_admin and admin_count <= 1:
        flash("Cannot delete the last remaining admin.", "error")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.name}' deleted.", "success")
    return redirect(url_for("admin.users"))


# ──────────────────────────────────────────────
# Clothing (Privacy Protected)
# ──────────────────────────────────────────────
@admin_bp.route("/clothing")
@admin_required
def clothing():
    flash("User clothing items and personal wardrobes are private and cannot be viewed by administrators.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/clothing/<int:item_id>/delete")
@admin_required
def delete_clothing(item_id):
    flash("User clothing items cannot be accessed or deleted by administrators to protect user privacy.", "error")
    return redirect(url_for("admin.dashboard"))


# ──────────────────────────────────────────────
# Outfits
# ──────────────────────────────────────────────
@admin_bp.route("/outfits")
@admin_required
def outfits():
    page = request.args.get("page", 1, type=int)
    q    = request.args.get("q", "").strip()

    query = Outfit.query.order_by(Outfit.created_at.desc())
    if q:
        query = query.filter(Outfit.title.ilike(f"%{q}%"))

    pag = paginate(query, page, PER_PAGE)
    return render_template("admin/outfits.html", pag=pag, q=q)


@admin_bp.post("/outfits/<int:outfit_id>/delete")
@admin_required
def delete_outfit(outfit_id):
    outfit = Outfit.query.get_or_404(outfit_id)
    db.session.delete(outfit)
    db.session.commit()
    flash("Outfit deleted.", "success")
    return redirect(url_for("admin.outfits"))


# ──────────────────────────────────────────────
# Feedback
# ──────────────────────────────────────────────
@admin_bp.route("/feedback")
@admin_required
def feedback():
    page = request.args.get("page", 1, type=int)

    query = OutfitFeedback.query.order_by(OutfitFeedback.created_at.desc())
    pag   = paginate(query, page, PER_PAGE)

    reaction_counts = dict(
        db.session.query(OutfitFeedback.reaction, func.count(OutfitFeedback.id))
        .group_by(OutfitFeedback.reaction)
        .all()
    )
    stats = {
        "total":      pag.total,
        "liked":      reaction_counts.get("liked", 0),
        "disliked":   reaction_counts.get("disliked", 0),
        "favorited":  reaction_counts.get("favorited", 0),
    }
    return render_template("admin/feedback.html", pag=pag, stats=stats)


# ──────────────────────────────────────────────
# Analytics
# ──────────────────────────────────────────────
@admin_bp.route("/analytics")
@admin_required
def analytics():
    # Category distribution
    category_data = (
        db.session.query(ClothingItem.category, func.count(ClothingItem.id))
        .group_by(ClothingItem.category)
        .order_by(func.count(ClothingItem.id).desc())
        .all()
    )
    category_labels = [r[0] or "Unknown" for r in category_data]
    category_values = [r[1] for r in category_data]

    # Color distribution (top 10)
    color_data = (
        db.session.query(ClothingItem.color, func.count(ClothingItem.id))
        .group_by(ClothingItem.color)
        .order_by(func.count(ClothingItem.id).desc())
        .limit(10)
        .all()
    )
    color_labels = [r[0] or "Unknown" for r in color_data]
    color_values = [r[1] for r in color_data]

    # Season distribution
    season_data = (
        db.session.query(ClothingItem.season, func.count(ClothingItem.id))
        .group_by(ClothingItem.season)
        .order_by(func.count(ClothingItem.id).desc())
        .all()
    )
    season_labels = [r[0] or "Unknown" for r in season_data]
    season_values = [r[1] for r in season_data]

    # Occasion distribution (Outfits)
    occasion_data = (
        db.session.query(Outfit.occasion, func.count(Outfit.id))
        .group_by(Outfit.occasion)
        .order_by(func.count(Outfit.id).desc())
        .all()
    )
    occasion_labels = [r[0] or "Unknown" for r in occasion_data]
    occasion_values = [r[1] for r in occasion_data]

    # Feedback reaction distribution
    feedback_data = (
        db.session.query(OutfitFeedback.reaction, func.count(OutfitFeedback.id))
        .group_by(OutfitFeedback.reaction)
        .all()
    )
    feedback_labels = [r[0] for r in feedback_data]
    feedback_values = [r[1] for r in feedback_data]

    # Users with most clothing
    top_users = (
        db.session.query(User.name, func.count(ClothingItem.id).label("cnt"))
        .join(ClothingItem, ClothingItem.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(ClothingItem.id).desc())
        .limit(10)
        .all()
    )
    top_user_labels = [r[0] for r in top_users]
    top_user_values = [r[1] for r in top_users]

    return render_template(
        "admin/analytics.html",
        category_labels=category_labels,
        category_values=category_values,
        color_labels=color_labels,
        color_values=color_values,
        season_labels=season_labels,
        season_values=season_values,
        occasion_labels=occasion_labels,
        occasion_values=occasion_values,
        feedback_labels=feedback_labels,
        feedback_values=feedback_values,
        top_user_labels=top_user_labels,
        top_user_values=top_user_values,
    )
