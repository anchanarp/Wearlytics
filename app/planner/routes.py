"""Weekly planner routes."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.planner import WeeklyPlan
from app.planner import planner_bp

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@planner_bp.route("/")
@login_required
def index():
    """Display 7-day weekly schedule with assigned outfits."""
    existing_plans = {p.day_of_week: p for p in WeeklyPlan.query.filter_by(user_id=current_user.id).all()}
    outfits = current_user.outfits.order_by(None).all()

    weekly_schedule = []
    for day in DAYS_OF_WEEK:
        weekly_schedule.append({
            "day": day,
            "plan": existing_plans.get(day),
        })

    return render_template("planner/index.html", schedule=weekly_schedule, outfits=outfits)


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

    # Validate outfit belongs to the user if provided
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


@planner_bp.post("/<int:plan_id>/clear")
@login_required
def clear_day(plan_id):
    """Clear the outfit from a specific day's plan."""
    plan = WeeklyPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    day = plan.day_of_week
    plan.outfit_id = None
    plan.notes = ""
    db.session.commit()
    flash(f"{day}'s outfit has been cleared.", "info")
    return redirect(url_for("planner.index"))
