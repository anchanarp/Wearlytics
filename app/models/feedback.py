"""Outfit feedback model — stores user reactions to outfit recommendations."""

from datetime import datetime, timezone

from app.extensions import db


class OutfitFeedback(db.Model):
    """Stores a user's like / dislike / favorite reaction to an outfit."""

    __tablename__ = "outfit_feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    outfit_id = db.Column(db.Integer, db.ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False, index=True)
    reaction = db.Column(db.String(20), nullable=False)
    """One of: 'liked' / 'disliked' / 'favorited'."""

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("outfit_feedback", lazy="dynamic", cascade="all, delete-orphan"))
    outfit = db.relationship("Outfit", backref=db.backref("feedback", lazy="dynamic", passive_deletes=True))

    VALID_REACTIONS = {"liked", "disliked", "favorited"}

    def __repr__(self):
        return f"<OutfitFeedback user={self.user_id} outfit={self.outfit_id} reaction={self.reaction}>"
