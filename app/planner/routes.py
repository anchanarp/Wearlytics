"""Weekly planner routes."""

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
    """Display 7-day weekly schedule with assigned outfits and saved outfit library."""
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

    weekly_schedule = []
    for day in DAYS_OF_WEEK:
        weekly_schedule.append({
            "day": day,
            "plan": existing_plans.get(day),
        })

    return render_template(
        "planner/index.html",
        schedule=weekly_schedule,
        outfits=outfits,
        days_of_week=DAYS_OF_WEEK,
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


# ── Assign AI outfit to a day ─────────────────────────────────────────────────

@planner_bp.post("/assign")
@login_required
def assign_outfit():
    """Assign an outfit and note to a specific day of the week."""
    day = request.form.get("day_of_week")
    outfit_id_raw = request.form.get("outfit_id", "").strip()
    notes = request.form.get("notes", "").strip()

    if day not in DAYS_OF_WEEK:
        flash("Invalid day specified.", "error")
        return redirect(url_for("planner.index"))

    outfit_id = int(outfit_id_raw) if outfit_id_raw.isdigit() else None

    if outfit_id:
        outfit = current_user.outfits.filter_by(id=outfit_id).first()
        if not outfit:
            flash("Selected outfit not found in your collection.", "error")
            return redirect(url_for("planner.index"))

    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, day_of_week=day).first()
    if not plan:
        plan = WeeklyPlan(user_id=current_user.id, day_of_week=day)
        db.session.add(plan)

    plan.outfit_id = outfit_id
    plan.notes = notes
    db.session.commit()

    if outfit_id:
        flash(f"Outfit assigned to {day}!", "success")
    else:
        flash(f"{day} cleared — no outfit assigned.", "info")
    return redirect(url_for("planner.index"))


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
    return redirect(url_for("planner.index"))


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
    return redirect(url_for("planner.index"))


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
