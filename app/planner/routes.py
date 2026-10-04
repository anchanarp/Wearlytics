"""Weekly planner routes."""

from datetime import date, timedelta
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.clothing import ClothingItem
from app.models.planner import WeeklyPlan
from app.models.custom_outfit import CustomOutfit
from app.models.outfit import Outfit
from app.models.feedback import OutfitFeedback
from app.planner import planner_bp

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@planner_bp.route("/")
@login_required
def index():
    """Display 7-day weekly schedule with compact selector, selected day details, and AI presets."""
    week_offset = request.args.get("week", 0, type=int)
    today = date.today()
    # Start of the week (Monday)
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    # Format week range string, e.g. "Oct 6 – Oct 12, 2026"
    start_month = start_of_week.strftime("%b")
    start_day_num = start_of_week.day
    end_month = end_of_week.strftime("%b")
    end_day_num = end_of_week.day
    year = end_of_week.year

    if start_month == end_month:
        week_range_str = f"{start_month} {start_day_num} – {end_day_num}, {year}"
    else:
        week_range_str = f"{start_month} {start_day_num} – {end_month} {end_day_num}, {year}"

    existing_plans = {p.day_of_week: p for p in WeeklyPlan.query.filter_by(user_id=current_user.id).all()}

    # Only include real saved outfits (exclude internal ai_feedback rows), ensure items exist and unique combos
    all_user_outfits = current_user.outfits.order_by(Outfit.created_at.desc()).all()
    seen_combos = set()
    outfits = []
    for o in all_user_outfits:
        if len(o.items) == 0:
            continue
        if o.recommendation_type == "ai_feedback":
            continue
        combo_key = tuple(sorted(it.id for it in o.items))
        if combo_key in seen_combos:
            continue
        seen_combos.add(combo_key)
        outfits.append(o)

    # Build weekly schedule list
    weekly_schedule = []
    days_planned_count = 0

    for idx, day in enumerate(DAYS_OF_WEEK):
        day_date = start_of_week + timedelta(days=idx)
        date_short = f"{day_date.strftime('%b')} {day_date.day}"
        date_full = f"{day}, {day_date.strftime('%B')} {day_date.day}"

        plan = existing_plans.get(day)
        has_custom = bool(plan and plan.custom_outfit and len(plan.custom_outfit.items) > 0)
        has_ai = bool(plan and plan.outfit and len(plan.outfit.items) > 0)
        has_outfit = has_custom or has_ai

        items_preview = []
        outfit_title = ""
        outfit_type = ""
        edit_url = None
        plan_notes = plan.notes if plan else ""

        if has_custom:
            items_preview = plan.custom_outfit.items
            outfit_title = plan.custom_outfit.name or "My Custom Outfit"
            outfit_type = "custom"
            edit_url = url_for("planner.edit_custom_outfit", outfit_id=plan.custom_outfit.id)
            if plan.custom_outfit.note and not plan_notes:
                plan_notes = plan.custom_outfit.note
        elif has_ai:
            items_preview = plan.outfit.items
            outfit_title = plan.outfit.display_name
            outfit_type = "ai"

        if has_outfit:
            days_planned_count += 1

        weekly_schedule.append({
            "day": day,
            "date_short": date_short,
            "date_full": date_full,
            "plan": plan,
            "has_outfit": has_outfit,
            "has_custom": has_custom,
            "has_ai": has_ai,
            "items_preview": items_preview,
            "outfit_title": outfit_title,
            "outfit_type": outfit_type,
            "edit_url": edit_url,
            "notes": plan_notes,
        })

    planned_pct = int(round((days_planned_count / 7.0) * 100))

    # Active day: from query string or default to today's day (or first day: Monday)
    today_name = today.strftime("%A")
    requested_day = request.args.get("day", "").capitalize()
    if requested_day in DAYS_OF_WEEK:
        active_day = requested_day
    elif today_name in DAYS_OF_WEEK and week_offset == 0:
        active_day = today_name
    else:
        active_day = "Monday"

    # AI Suggestions / presets tailored to user's wardrobe
    user_items = ClothingItem.query.filter_by(user_id=current_user.id, is_in_laundry=False).all()
    item_map = {item.name: item for item in user_items}

    def pick_items(*names, fallback_cats=None):
        picked = [item_map[n] for n in names if n in item_map]
        if not picked and fallback_cats:
            for cat in fallback_cats:
                it = next((i for i in user_items if i.category == cat and i not in picked), None)
                if it:
                    picked.append(it)
        return picked

    casual_chic_items = pick_items("Maroon Sweater", "Off White T-Shirt", "Off White Trousers", fallback_cats=["Tops", "Bottoms"])
    minimal_classic_items = pick_items("Black top", "Off White Trousers", "Charcoal Jeans", fallback_cats=["Tops", "Bottoms"])
    fresh_simple_items = pick_items("Off White T-Shirt", "Charcoal Jeans", fallback_cats=["Tops", "Bottoms"])

    ai_presets = [
        {
            "id": "casual_chic",
            "title": "Casual Chic",
            "subtitle": "Work / Casual • 3 items",
            "image_url": "/static/img/ai_outfit_casual_chic.jpg",
            "clothing_items": casual_chic_items,
            "item_ids": ",".join(str(i.id) for i in casual_chic_items),
        },
        {
            "id": "minimal_classic",
            "title": "Minimal Classic",
            "subtitle": "Office • 3 items",
            "image_url": "/static/img/ai_outfit_minimal_classic.jpg",
            "clothing_items": minimal_classic_items,
            "item_ids": ",".join(str(i.id) for i in minimal_classic_items),
        },
        {
            "id": "fresh_simple",
            "title": "Fresh & Simple",
            "subtitle": "Casual • 2 items",
            "image_url": "/static/img/ai_outfit_fresh_simple.jpg",
            "clothing_items": fresh_simple_items,
            "item_ids": ",".join(str(i.id) for i in fresh_simple_items),
        },
    ]

    return render_template(
        "planner/index.html",
        schedule=weekly_schedule,
        outfits=outfits,
        days_of_week=DAYS_OF_WEEK,
        active_day=active_day,
        week_range_str=week_range_str,
        week_offset=week_offset,
        days_planned_count=days_planned_count,
        planned_pct=planned_pct,
        ai_presets=ai_presets,
    )


# ── Custom Outfit: show selection form (GET) ──────────────────────────────────

@planner_bp.get('/custom/create/<day>')
@login_required
def custom_outfit_page(day):
    """Render the custom outfit selection page for a given day."""
    if day not in DAYS_OF_WEEK:
        flash('Invalid day specified.', 'error')
        return redirect(url_for('planner.index'))

    wardrobe_items = ClothingItem.query.filter_by(user_id=current_user.id).all()
    available = [i for i in wardrobe_items if not i.is_in_laundry]
    categories = {}
    for item in available:
        categories.setdefault(item.category, []).append(item)

    return render_template('planner/custom_outfit.html', day=day, categories=categories)


# ── Custom Outfit: save new outfit (POST) ─────────────────────────────────────

@planner_bp.post('/custom/create/<day>')
@login_required
def create_custom_outfit(day):
    """Save a new custom outfit and link it to the chosen day."""
    if day not in DAYS_OF_WEEK:
        flash('Invalid day specified.', 'error')
        return redirect(url_for('planner.index'))

    name = request.form.get('name', '').strip()
    note = request.form.get('note', '').strip()
    item_ids_raw = request.form.get('item_ids', '')
    item_ids = [int(i) for i in item_ids_raw.split(',') if i.strip().isdigit()]

    # Load items — must belong to user and be available
    items = ClothingItem.query.filter(
        ClothingItem.id.in_(item_ids),
        ClothingItem.user_id == current_user.id,
        ClothingItem.is_in_laundry == False,
    ).all()

    if not item_ids or len(items) != len(item_ids):
        flash('One or more selected items are invalid or unavailable.', 'error')
        return redirect(url_for('planner.custom_outfit_page', day=day))

    # Enforce selection rules
    cats = [i.category for i in items]
    if 'Dresses' in cats and ('Tops' in cats or 'Bottoms' in cats):
        flash('When a Dress is selected, do not add Tops or Bottoms.', 'error')
        return redirect(url_for('planner.custom_outfit_page', day=day))
    for single_cat in ('Tops', 'Bottoms', 'Shoes', 'Outerwear'):
        if cats.count(single_cat) > 1:
            flash(f'Select at most one {single_cat.rstrip("s")} per outfit.', 'error')
            return redirect(url_for('planner.custom_outfit_page', day=day))

    # Create and save custom outfit
    custom = CustomOutfit(user_id=current_user.id, name=name or None, note=note or None)
    custom.items = items
    db.session.add(custom)
    db.session.flush()  # get custom.id

    # Link to weekly plan
    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, day_of_week=day).first()
    if not plan:
        plan = WeeklyPlan(user_id=current_user.id, day_of_week=day)
        db.session.add(plan)
    plan.custom_outfit_id = custom.id

    db.session.commit()
    flash(f'Custom outfit saved for {day}!', 'success')
    return redirect(url_for('planner.index'))


# ── Assign AI outfit or update notes for a day ────────────────────────────────

@planner_bp.post("/assign")
@login_required
def assign_outfit():
    """Assign an outfit and note to a specific day of the week."""
    day = request.form.get("day_of_week")
    outfit_id_raw = request.form.get("outfit_id", "").strip()
    notes = request.form.get("notes", "").strip()
    action = request.form.get("action", "").strip()

    if day not in DAYS_OF_WEEK:
        flash("Invalid day specified.", "error")
        return redirect(url_for("planner.index"))

    outfit_id = int(outfit_id_raw) if outfit_id_raw.isdigit() else None

    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, day_of_week=day).first()
    if not plan:
        plan = WeeklyPlan(user_id=current_user.id, day_of_week=day)
        db.session.add(plan)

    plan.notes = notes

    if action == "update_day":
        if outfit_id:
            outfit = current_user.outfits.filter_by(id=outfit_id).first()
            if outfit:
                plan.outfit_id = outfit.id
                plan.custom_outfit_id = None
        db.session.commit()
        flash(f"{day} updated successfully!", "success")
        return redirect(url_for("planner.index", day=day))

    if outfit_id:
        outfit = current_user.outfits.filter_by(id=outfit_id).first()
        if not outfit:
            flash("Selected outfit not found in your collection.", "error")
            return redirect(url_for("planner.index", day=day))
        plan.outfit_id = outfit.id
        plan.custom_outfit_id = None
        flash(f"Outfit assigned to {day}!", "success")
    else:
        plan.outfit_id = None
        flash(f"{day} cleared — no outfit assigned.", "info")

    db.session.commit()
    return redirect(url_for("planner.index", day=day))


# ── Assign AI Preset Outfit to a day ──────────────────────────────────────────

@planner_bp.post("/assign-preset")
@login_required
def assign_preset():
    """Assign a suggested AI preset outfit to a day."""
    day = request.form.get("day_of_week")
    title = request.form.get("title", "AI Preset Outfit").strip()
    item_ids_raw = request.form.get("item_ids", "").strip()
    item_ids = [int(x) for x in item_ids_raw.split(",") if x.strip().isdigit()]

    if day not in DAYS_OF_WEEK:
        flash("Invalid day specified.", "error")
        return redirect(url_for("planner.index"))

    items = []
    if item_ids:
        items = ClothingItem.query.filter(
            ClothingItem.id.in_(item_ids),
            ClothingItem.user_id == current_user.id,
            ClothingItem.is_in_laundry == False,
        ).all()

    # Fallback to available tops/bottoms if specific IDs not in user wardrobe
    if not items:
        top = ClothingItem.query.filter_by(user_id=current_user.id, category="Tops", is_in_laundry=False).first()
        bottom = ClothingItem.query.filter_by(user_id=current_user.id, category="Bottoms", is_in_laundry=False).first()
        if top:
            items.append(top)
        if bottom:
            items.append(bottom)

    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, day_of_week=day).first()
    if not plan:
        plan = WeeklyPlan(user_id=current_user.id, day_of_week=day)
        db.session.add(plan)

    if items:
        custom = CustomOutfit(user_id=current_user.id, name=title, note=f"AI Suggestion: {title}")
        custom.items = items
        db.session.add(custom)
        db.session.flush()
        plan.custom_outfit_id = custom.id
        plan.outfit_id = None
    else:
        outfit = Outfit(user_id=current_user.id, title=title, occasion="Casual", season="All Seasons")
        db.session.add(outfit)
        db.session.flush()
        plan.outfit_id = outfit.id
        plan.custom_outfit_id = None

    db.session.commit()
    flash(f"'{title}' assigned to {day}!", "success")
    return redirect(url_for("planner.index", day=day))


# ── Clear a day ───────────────────────────────────────────────────────────────

@planner_bp.post("/<int:plan_id>/clear")
@login_required
def clear_day(plan_id):
    """Clear the outfit from a specific day's plan."""
    plan = WeeklyPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    day = plan.day_of_week
    plan.outfit_id = None
    plan.custom_outfit_id = None
    plan.notes = ""
    db.session.commit()
    flash(f"{day}'s outfit has been cleared.", "info")
    return redirect(url_for("planner.index", day=day))


@planner_bp.post("/clear-day/<day>")
@login_required
def clear_day_by_name(day):
    """Clear the outfit from a specific day by day name."""
    if day not in DAYS_OF_WEEK:
        flash("Invalid day specified.", "error")
        return redirect(url_for("planner.index"))

    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, day_of_week=day).first()
    if plan:
        plan.outfit_id = None
        plan.custom_outfit_id = None
        plan.notes = ""
        db.session.commit()
        flash(f"{day}'s outfit has been cleared.", "info")
    return redirect(url_for("planner.index", day=day))


# ── Edit custom outfit (GET) ──────────────────────────────────────────────────

@planner_bp.get('/custom/edit/<int:outfit_id>')
@login_required
def edit_custom_outfit(outfit_id):
    """Render edit form for a custom outfit."""
    outfit = CustomOutfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    wardrobe_items = ClothingItem.query.filter_by(user_id=current_user.id, is_in_laundry=False).all()
    categories = {}
    for item in wardrobe_items:
        categories.setdefault(item.category, []).append(item)
    selected_ids = {i.id for i in outfit.items}
    return render_template(
        'planner/custom_outfit_edit.html',
        outfit=outfit,
        categories=categories,
        selected_ids=selected_ids,
    )


# ── Edit custom outfit (POST) ─────────────────────────────────────────────────

@planner_bp.post('/custom/edit/<int:outfit_id>')
@login_required
def edit_custom_outfit_post(outfit_id):
    """Process edit form submission for a custom outfit."""
    outfit = CustomOutfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    name = request.form.get('name', '').strip()
    note = request.form.get('note', '').strip()
    item_ids_raw = request.form.get('item_ids', '')
    item_ids = [int(i) for i in item_ids_raw.split(',') if i.strip().isdigit()]

    items = ClothingItem.query.filter(
        ClothingItem.id.in_(item_ids),
        ClothingItem.user_id == current_user.id,
        ClothingItem.is_in_laundry == False,
    ).all()

    if not item_ids or len(items) != len(item_ids):
        flash('One or more selected items are invalid or unavailable.', 'error')
        return redirect(url_for('planner.edit_custom_outfit', outfit_id=outfit_id))

    cats = [i.category for i in items]
    if 'Dresses' in cats and ('Tops' in cats or 'Bottoms' in cats):
        flash('When a Dress is selected, do not add Tops or Bottoms.', 'error')
        return redirect(url_for('planner.edit_custom_outfit', outfit_id=outfit_id))
    for single_cat in ('Tops', 'Bottoms', 'Shoes', 'Outerwear'):
        if cats.count(single_cat) > 1:
            flash(f'Select at most one {single_cat.rstrip("s")} per outfit.', 'error')
            return redirect(url_for('planner.edit_custom_outfit', outfit_id=outfit_id))

    outfit.name = name or None
    outfit.note = note or None
    outfit.items = items
    db.session.commit()
    flash('Custom outfit updated.', 'success')
    return redirect(url_for('planner.index'))


# ── Delete custom outfit (POST) ───────────────────────────────────────────────

@planner_bp.post('/custom/delete/<int:outfit_id>')
@login_required
def delete_custom_outfit(outfit_id):
    """Delete a custom outfit and clear any linked weekly plan."""
    outfit = CustomOutfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    WeeklyPlan.query.filter_by(
        custom_outfit_id=outfit.id, user_id=current_user.id
    ).update({"custom_outfit_id": None})
    db.session.delete(outfit)
    db.session.commit()
    flash('Custom outfit removed.', 'success')
    return redirect(url_for('planner.index'))


# ── Quick Assign from Saved Outfits library ───────────────────────────────────

@planner_bp.post("/assign-quick")
@login_required
def assign_quick():
    """Quickly assign an outfit to a selected day of the week."""
    day = request.form.get("day_of_week")
    outfit_id = request.form.get("outfit_id", type=int)

    if day not in DAYS_OF_WEEK or not outfit_id:
        flash("Please select a valid day and outfit.", "error")
        return redirect(url_for("planner.index"))

    outfit = current_user.outfits.filter_by(id=outfit_id).first()
    if not outfit:
        flash("Saved outfit not found.", "error")
        return redirect(url_for("planner.index"))

    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, day_of_week=day).first()
    if not plan:
        plan = WeeklyPlan(user_id=current_user.id, day_of_week=day)
        db.session.add(plan)

    plan.outfit_id = outfit.id
    plan.custom_outfit_id = None  # replace any custom outfit on that day
    db.session.commit()
    flash(f"'{outfit.title}' added to {day}!", "success")
    return redirect(url_for("planner.index", day=day))


# ── Delete saved outfit from collection ────────────────────────────────────────

@planner_bp.post("/outfit/<int:outfit_id>/delete")
@login_required
def delete_saved_outfit(outfit_id):
    """Delete a saved outfit from the user's collection."""
    outfit = current_user.outfits.filter_by(id=outfit_id).first_or_404()
    title = outfit.title
    WeeklyPlan.query.filter_by(user_id=current_user.id, outfit_id=outfit.id).update({"outfit_id": None})
    db.session.delete(outfit)
    db.session.commit()
    flash(f"Saved outfit '{title}' removed.", "success")
    return redirect(url_for("planner.index"))
