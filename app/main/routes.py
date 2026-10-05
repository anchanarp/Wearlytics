"""Public application routes."""

from datetime import datetime, timezone as tz
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.main import main_bp
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.models.planner import WeeklyPlan
from app.services.outfit_collage import get_outfit_collage_url
from app.utils.seeder import seed_user_wardrobe


def _resolve_todays_look(user_id):
    """Resolve the active outfit items, title, desc, occasion, and collage URL for today's look."""
    today_dt = datetime.now()
    today_str = today_dt.strftime("%A, %B %d")
    today_full_str = today_dt.strftime("%A, %B %d, %Y")
    today_day_name = today_dt.strftime("%A")

    # 1. Check if user has an outfit planned for today in WeeklyPlan
    plan = WeeklyPlan.query.filter_by(user_id=user_id, day_of_week=today_day_name).first()
    todays_items = []
    todays_title = "Everyday Comfort"
    todays_desc = "A simple look for a beautiful day."
    todays_occasion = "Everyday / Casual"
    is_planned_today = False

    if plan:
        if plan.custom_outfit and len(plan.custom_outfit.items) > 0:
            todays_items = list(plan.custom_outfit.items)
            todays_title = plan.custom_outfit.name or "My Custom Look"
            if plan.custom_outfit.note:
                todays_desc = plan.custom_outfit.note
            is_planned_today = True
        elif plan.outfit and len(plan.outfit.items) > 0:
            todays_items = list(plan.outfit.items)
            todays_title = plan.outfit.display_name
            if plan.outfit.occasion:
                todays_occasion = plan.outfit.occasion
            if plan.notes:
                todays_desc = plan.notes
            is_planned_today = True

    # 2. If no planned outfit for today, check any planned day from WeeklyPlan
    if not todays_items:
        any_plan = WeeklyPlan.query.filter(
            WeeklyPlan.user_id == user_id,
            (WeeklyPlan.custom_outfit_id.isnot(None)) | (WeeklyPlan.outfit_id.isnot(None))
        ).first()
        if any_plan:
            if any_plan.custom_outfit and len(any_plan.custom_outfit.items) > 0:
                todays_items = list(any_plan.custom_outfit.items)
                todays_title = any_plan.custom_outfit.name or "Everyday Comfort"
                if any_plan.custom_outfit.note:
                    todays_desc = any_plan.custom_outfit.note
            elif any_plan.outfit and len(any_plan.outfit.items) > 0:
                todays_items = list(any_plan.outfit.items)
                todays_title = any_plan.outfit.display_name
                if any_plan.outfit.occasion:
                    todays_occasion = any_plan.outfit.occasion
                if any_plan.notes:
                    todays_desc = any_plan.notes

    # 3. If still no outfit, check user's saved outfits
    if not todays_items:
        saved_outfit = Outfit.query.filter(
            Outfit.user_id == user_id,
            Outfit.recommendation_type != "ai_feedback"
        ).order_by(Outfit.created_at.desc()).first()
        if saved_outfit and len(saved_outfit.items) > 0:
            todays_items = list(saved_outfit.items)
            todays_title = saved_outfit.display_name

    # 4. Fallback: pick items from user's wardrobe (Top + Bottom + Other)
    if not todays_items:
        user_items = ClothingItem.query.filter_by(user_id=user_id, is_in_laundry=False).all()
        top = next((i for i in user_items if i.category == "Tops"), None)
        bottom = next((i for i in user_items if i.category == "Bottoms"), None)
        other = next((i for i in user_items if i.category in ("Shoes", "Accessories", "Outerwear")), None)
        for piece in [top, bottom, other]:
            if piece and piece not in todays_items:
                todays_items.append(piece)

    # 5. If only 1 piece (not a dress) is selected/planned, complement with a matching piece from wardrobe for a complete outfit collage
    if len(todays_items) == 1 and getattr(todays_items[0], "category", None) != "Dresses":
        user_items = ClothingItem.query.filter_by(user_id=user_id, is_in_laundry=False).all()
        first_cat = todays_items[0].category
        first_id = todays_items[0].id
        if first_cat == "Tops":
            comp = next((i for i in user_items if i.category == "Bottoms" and i.id != first_id), None)
            if comp:
                todays_items.append(comp)
        elif first_cat == "Bottoms":
            comp = next((i for i in user_items if i.category == "Tops" and i.id != first_id), None)
            if comp:
                todays_items.insert(0, comp)

    collage_url = get_outfit_collage_url(todays_items)

    return {
        "today_str": today_str,
        "today_full_str": today_full_str,
        "today_day_name": today_day_name,
        "items": todays_items,
        "title": todays_title,
        "desc": todays_desc,
        "occasion": todays_occasion,
        "is_planned_today": is_planned_today,
        "collage_url": collage_url,
    }


@main_bp.get("/")
@login_required
def home():
    """Render the dashboard with dynamic user wardrobe stats."""
    # Ensure wardrobe has starter items if empty for demo or admin users
    if getattr(current_user, "is_demo", False) or getattr(current_user, "is_admin", False):
        seed_user_wardrobe(current_user)

    items = ClothingItem.query.filter_by(user_id=current_user.id).order_by(ClothingItem.created_at.desc()).all()
    outfits = Outfit.query.filter_by(user_id=current_user.id).all()
    weekly_plans = WeeklyPlan.query.filter_by(user_id=current_user.id).all()
    favorites = [i for i in items if i.is_favorite]

    recent_items = items[:4]
    look = _resolve_todays_look(current_user.id)

    return render_template(
        "index.html",
        total_items=len(items),
        total_outfits=len(outfits),
        total_plans=len([p for p in weekly_plans if p.outfit_id is not None]),
        total_favorites=len(favorites),
        recent_items=recent_items,
        today_str=look["today_str"],
        todays_look_image=look["collage_url"],
        todays_title=look["title"],
        todays_desc=look["desc"],
    )


@main_bp.get("/todays-look")
@login_required
def todays_look():
    """Render the dedicated standalone Today's Look editorial page."""
    look = _resolve_todays_look(current_user.id)

    return render_template(
        "todays_look.html",
        today_str=look["today_full_str"],
        today_day_name=look["today_day_name"],
        outfit_items=look["items"],
        outfit_title=look["title"],
        outfit_desc=look["desc"],
        outfit_occasion=look["occasion"],
        outfit_score=94,
        is_planned_today=look["is_planned_today"],
        todays_look_image=look["collage_url"],
    )


@main_bp.post("/todays-look/wear")
@login_required
def wear_todays_look():
    """Mark all items in Today's Look as worn."""
    item_ids_raw = request.form.get("item_ids", "")
    item_ids = [int(x) for x in item_ids_raw.split(",") if x.strip().isdigit()]
    items = ClothingItem.query.filter(ClothingItem.id.in_(item_ids), ClothingItem.user_id == current_user.id).all()
    now_utc = datetime.now(tz.utc)
    for it in items:
        it.wear_count += 1
        it.last_worn_at = now_utc
    db.session.commit()
    flash(f"Today's look ({len(items)} items) logged as worn! Wear history updated.", "success")
    return redirect(url_for("main.todays_look"))
