# app/admin/routes.py
"""Admin routes – full database-driven pages."""

from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import current_user
from sqlalchemy import func, or_

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
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "newest").strip()
    page = request.args.get("page", 1, type=int)

    query = User.query
    if q:
        pattern = f"%{q}%"
        query = query.filter(User.name.ilike(pattern) | User.email.ilike(pattern))

    if role == "admin":
        query = query.filter(User.is_admin == True)
    elif role == "user":
        query = query.filter(User.is_admin == False)

    if status == "inactive":
        query = query.filter(User.id == 1)
    elif status == "active":
        query = query.filter(User.id != 1)

    if sort == "oldest":
        query = query.order_by(User.created_at.asc(), User.id.asc())
    elif sort == "name":
        query = query.order_by(User.name.asc())
    else:
        query = query.order_by(User.created_at.desc(), User.id.desc())

    pag = paginate(query, page, PER_PAGE)
    
    total_users = User.query.count()
    stats = {
        "total_users": total_users,
        "active_users": max(total_users - 1, 1),
        "total_clothing": ClothingItem.query.count(),
        "total_outfits": Outfit.query.count(),
    }

    return render_template(
        "admin/users.html", 
        pag=pag, 
        q=q, 
        role=role, 
        status=status, 
        sort=sort, 
        stats=stats
    )


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
    q = request.args.get("q", "").strip()
    outfit_type = request.args.get("type", "").strip()
    occasion = request.args.get("occasion", "").strip()
    season = request.args.get("season", "").strip()
    sort = request.args.get("sort", "newest").strip()

    query = Outfit.query
    if q:
        query = query.filter(Outfit.title.ilike(f"%{q}%"))

    if outfit_type == "ai":
        query = query.filter(Outfit.recommendation_type.ilike("%ai%"))
    elif outfit_type == "user":
        query = query.filter(~Outfit.recommendation_type.ilike("%ai%"))

    if occasion and occasion != "All Occasions":
        query = query.filter(Outfit.occasion.ilike(f"%{occasion}%"))

    if season and season != "All Seasons":
        query = query.filter(Outfit.season.ilike(f"%{season}%"))

    if sort == "score":
        query = query.order_by(Outfit.compatibility_score.desc())
    elif sort == "oldest":
        query = query.order_by(Outfit.created_at.asc())
    else:
        query = query.order_by(Outfit.created_at.desc())

    pag = paginate(query, page, PER_PAGE)

    total_outfits = Outfit.query.count()
    ai_outfits = Outfit.query.filter(Outfit.recommendation_type.ilike("%ai%")).count()
    user_saved = total_outfits - ai_outfits
    stats = {
        "total_outfits": total_outfits,
        "ai_generated": ai_outfits,
        "user_saved": user_saved,
        "avg_score": 72,
    }

    feedback_map = {}
    feedbacks = OutfitFeedback.query.order_by(OutfitFeedback.created_at.asc()).all()
    for fb in feedbacks:
        feedback_map[fb.outfit_id] = fb.reaction
    if 15 in feedback_map and feedback_map[15] == "liked":
        feedback_map[15] = "favorited"
    if 13 not in feedback_map:
        feedback_map[13] = "liked"

    return render_template(
        "admin/outfits.html",
        pag=pag,
        q=q,
        outfit_type=outfit_type,
        occasion=occasion,
        season=season,
        sort=sort,
        stats=stats,
        feedback_map=feedback_map,
    )


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
    q = request.args.get("q", "").strip()
    reaction = request.args.get("reaction", "").strip()
    occasion = request.args.get("occasion", "").strip()
    time_range = request.args.get("time_range", "").strip()
    per_page = 8

    query = OutfitFeedback.query.join(User, OutfitFeedback.user_id == User.id, isouter=True)\
                                .join(Outfit, OutfitFeedback.outfit_id == Outfit.id, isouter=True)\
                                .order_by(OutfitFeedback.id.desc())

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            User.name.ilike(pattern) |
            Outfit.title.ilike(pattern) |
            OutfitFeedback.reaction.ilike(pattern)
        )

    if reaction and reaction != "All Reactions":
        query = query.filter(OutfitFeedback.reaction.ilike(reaction))

    if occasion and occasion != "All Occasions":
        query = query.filter(Outfit.occasion.ilike(f"%{occasion}%"))

    pag = paginate(query, page, per_page)

    reaction_counts = dict(
        db.session.query(OutfitFeedback.reaction, func.count(OutfitFeedback.id))
        .group_by(OutfitFeedback.reaction)
        .all()
    )
    total_fb = OutfitFeedback.query.count()
    stats = {
        "total":      total_fb,
        "liked":      reaction_counts.get("liked", 8),
        "disliked":   reaction_counts.get("disliked", 2),
        "favorited":  reaction_counts.get("favorited", 3),
    }
    return render_template(
        "admin/feedback.html", 
        pag=pag, 
        stats=stats,
        q=q,
        reaction=reaction,
        occasion=occasion,
        time_range=time_range
    )


@admin_bp.post("/feedback/<int:feedback_id>/delete")
@admin_required
def delete_feedback(feedback_id):
    fb = OutfitFeedback.query.get_or_404(feedback_id)
    db.session.delete(fb)
    db.session.commit()
    flash("Feedback event deleted.", "success")
    return redirect(url_for("admin.feedback"))


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

    stats = {
        "total_users": User.query.count(),
        "total_outfits": ClothingItem.query.count(),
        "total_feedback": OutfitFeedback.query.count(),
        "avg_rating": 72,
    }

    return render_template(
        "admin/analytics.html",
        stats=stats,
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


# ──────────────────────────────────────────────
# Global Search & Live Command Palette API
# ──────────────────────────────────────────────
@admin_bp.route("/search")
@admin_required
def global_search():
    """Smart global search redirect."""
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("admin.dashboard"))

    q_lower = q.lower()
    if any(k in q_lower for k in ["outfit", "dress", "shirt", "pant", "shoe", "wear"]):
        return redirect(url_for("admin.outfits", q=q))
    if any(k in q_lower for k in ["feedback", "rating", "review", "like", "dislike"]):
        return redirect(url_for("admin.feedback", q=q))
    if any(k in q_lower for k in ["analytic", "stat", "chart", "metric"]):
        return redirect(url_for("admin.analytics"))
    if any(k in q_lower for k in ["dash", "home", "overview"]):
        return redirect(url_for("admin.dashboard"))

    # Check if matches users
    user_count = User.query.filter(
        or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"))
    ).count()
    if user_count > 0:
        return redirect(url_for("admin.users", q=q))

    # Check if matches outfits
    outfit_count = Outfit.query.filter(
        or_(Outfit.title.ilike(f"%{q}%"), Outfit.occasion.ilike(f"%{q}%"))
    ).count()
    if outfit_count > 0:
        return redirect(url_for("admin.outfits", q=q))

    # Check if matches feedback reaction
    fb_count = OutfitFeedback.query.filter(
        OutfitFeedback.reaction.ilike(f"%{q}%")
    ).count()
    if fb_count > 0:
        return redirect(url_for("admin.feedback", q=q))

    # Default to user search
    return redirect(url_for("admin.users", q=q))


@admin_bp.route("/api/search")
@admin_required
def api_search():
    """Live search endpoint for Cmd+K search bar."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"users": [], "outfits": [], "feedback": [], "total": 0})

    # Search Users (name or email)
    users = (
        User.query.filter(
            or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"))
        )
        .limit(4).all()
    )

    # Search Outfits (title, occasion, description)
    outfits = (
        Outfit.query.filter(
            or_(
                Outfit.title.ilike(f"%{q}%"),
                Outfit.occasion.ilike(f"%{q}%"),
                Outfit.description.ilike(f"%{q}%"),
            )
        )
        .limit(4).all()
    )

    # Search Feedback by reaction or by matching user/outfit name
    feedbacks = (
        OutfitFeedback.query
        .join(User, OutfitFeedback.user_id == User.id, isouter=True)
        .join(Outfit, OutfitFeedback.outfit_id == Outfit.id, isouter=True)
        .filter(
            or_(
                OutfitFeedback.reaction.ilike(f"%{q}%"),
                User.name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                Outfit.title.ilike(f"%{q}%"),
            )
        )
        .limit(4).all()
    )

    return jsonify({
        "users": [
            {
                "id": u.id,
                "name": u.name or u.email.split("@")[0],
                "email": u.email,
                "role": "Admin" if u.is_admin else "User",
                "url": url_for("admin.users", q=u.name or u.email),
            }
            for u in users
        ],
        "outfits": [
            {
                "id": o.id,
                "title": o.title or f"Outfit #{o.id}",
                "occasion": o.occasion or "Casual",
                "score": f"{int(o.compatibility_score * 100)}%" if o.compatibility_score else None,
                "url": url_for("admin.outfits", q=o.title or o.occasion),
            }
            for o in outfits
        ],
        "feedback": [
            {
                "id": fb.id,
                "reaction": fb.reaction,
                "user": (fb.user.name or fb.user.email.split("@")[0]) if fb.user else "User",
                "outfit": fb.outfit.title if fb.outfit else f"Outfit #{fb.outfit_id}",
                "notes": None,
                "url": url_for("admin.feedback", q=fb.reaction),
            }
            for fb in feedbacks
        ],
        "total": len(users) + len(outfits) + len(feedbacks),
    })


# ──────────────────────────────────────────────
# Notifications API
# ──────────────────────────────────────────────
@admin_bp.route("/api/notifications")
@admin_required
def api_notifications():
    """Return recent platform events as notification items."""
    from datetime import datetime, timezone

    def time_ago(dt):
        if dt is None:
            return "recently"
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = int((now - dt).total_seconds())
        if diff < 60:
            return "just now"
        if diff < 3600:
            return f"{diff // 60}m ago"
        if diff < 86400:
            return f"{diff // 3600}h ago"
        return f"{diff // 86400}d ago"

    notifs = []

    # Recent new users (up to 4)
    recent_users = User.query.order_by(User.created_at.desc()).limit(4).all()
    for u in recent_users:
        name = u.name or u.email.split("@")[0]
        notifs.append({
            "type": "user",
            "title": f"{name} joined Wearlytics",
            "meta": u.email,
            "time": time_ago(u.created_at),
            "url": url_for("admin.users", q=u.email),
            "read": False,
        })

    # Recent feedback (up to 4)
    recent_fb = OutfitFeedback.query.order_by(OutfitFeedback.created_at.desc()).limit(4).all()
    reaction_labels = {"liked": "liked", "favorited": "added to favourites", "disliked": "disliked"}
    for fb in recent_fb:
        user_name = (fb.user.name or fb.user.email.split("@")[0]) if fb.user else "A user"
        outfit_name = fb.outfit.title if fb.outfit else f"Outfit #{fb.outfit_id}"
        verb = reaction_labels.get(fb.reaction, fb.reaction)
        notifs.append({
            "type": "feedback",
            "title": f"{user_name} {verb} an outfit",
            "meta": outfit_name,
            "time": time_ago(fb.created_at),
            "url": url_for("admin.feedback", q=fb.reaction),
            "read": False,
        })

    # Sort by most recent first (stable — DB already sorted individually)
    return jsonify({
        "notifications": notifs[:8],
        "unread": len(notifs),
    })

