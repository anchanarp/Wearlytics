"""Weekly planner database model."""

from datetime import datetime, timezone

from app.extensions import db


class WeeklyPlan(db.Model):
    """Weekly outfit plan entry for a specific day."""

    __tablename__ = "weekly_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
    outfit_id = db.Column(db.Integer, db.ForeignKey("outfits.id", ondelete="SET NULL"), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("weekly_plans", lazy="dynamic", cascade="all, delete-orphan"))
    outfit = db.relationship("Outfit", backref=db.backref("weekly_plans", lazy="dynamic"))
