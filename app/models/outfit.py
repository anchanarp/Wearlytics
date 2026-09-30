"""Outfit database model and association table."""

from datetime import datetime, timezone

from app.extensions import db


# Many-to-many relationship between outfits and clothing items
outfit_items = db.Table(
    "outfit_items",
    db.Column("outfit_id", db.Integer, db.ForeignKey("outfits.id", ondelete="CASCADE"), primary_key=True),
    db.Column("clothing_item_id", db.Integer, db.ForeignKey("clothing_items.id", ondelete="CASCADE"), primary_key=True),
)


class Outfit(db.Model):
    """User or AI-generated outfit combination."""

    __tablename__ = "outfits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    occasion = db.Column(db.String(50), nullable=False, default="Casual")  # Casual, Work, Formal, Sporty, Date Night
    season = db.Column(db.String(50), nullable=False, default="All Seasons")
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --- AI-enhanced fields ---
    compatibility_score = db.Column(db.Float, nullable=True)
    """Weighted compatibility score (0–100) calculated by the recommendation engine."""

    recommendation_type = db.Column(db.String(30), nullable=True, default="ai_random")
    """How this outfit was created: 'ai_smart' / 'ai_random' / 'manual'."""

    # Relationships
    user = db.relationship("User", backref=db.backref("outfits", lazy="dynamic", cascade="all, delete-orphan"))
    items = db.relationship(
        "ClothingItem",
        secondary=outfit_items,
        backref=db.backref("outfits", lazy="dynamic"),
        lazy="subquery",
    )

    @property
    def display_name(self):
        """User-friendly name showing garments in the outfit and occasion."""
        if self.items:
            cat_priority = {
                "Outerwear": 1,
                "Tops": 2,
                "Top": 2,
                "One-Piece": 2,
                "Dresses": 2,
                "Bottoms": 3,
                "Bottom": 3,
                "Shoes": 4,
                "Footwear": 4,
                "Accessories": 5,
            }
            sorted_items = sorted(
                self.items,
                key=lambda x: cat_priority.get(x.category, 10),
            )
            item_names = [item.name for item in sorted_items]
            if len(item_names) == 1:
                names_str = item_names[0]
            elif len(item_names) == 2:
                names_str = f"{item_names[0]} & {item_names[1]}"
            else:
                names_str = f"{item_names[0]}, {item_names[1]} & {len(item_names) - 2} more"

            occ = f" ({self.occasion})" if self.occasion and self.occasion not in ("Any", "Any Occasion") else ""
            return f"{names_str}{occ}"
        return self.title or "Outfit"
