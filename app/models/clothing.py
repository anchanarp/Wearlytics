"""Clothing item database model."""

from datetime import datetime, timezone

from app.extensions import db


class ClothingItem(db.Model):
    """Individual clothing item in a user's wardrobe."""

    __tablename__ = "clothing_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="Tops")
    color = db.Column(db.String(50), nullable=False, default="Black")
    season = db.Column(db.String(50), nullable=False, default="All Seasons")
    brand = db.Column(db.String(100), nullable=True)
    image_url = db.Column(db.String(500), nullable=False)
    wear_count = db.Column(db.Integer, default=0, nullable=False)
    last_worn_at = db.Column(db.DateTime(timezone=True), nullable=True)
    """Timestamp of the most recent wear event."""

    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    is_in_laundry = db.Column(db.Boolean, default=False, nullable=False)
    """True when the item is in the laundry — excluded from recommendations."""

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --- AI-enhanced fields (all nullable / defaulted for backward compatibility) ---
    style = db.Column(db.String(50), nullable=True, default="Casual")
    """Style tag: Casual / Formal / Sporty / Streetwear / Ethnic."""

    clothing_type = db.Column(db.String(80), nullable=True)
    """AI or manually specified clothing type, e.g. T-Shirt, Jeans, Sneakers."""

    detected_color_hex = db.Column(db.String(10), nullable=True)
    """Dominant color hex extracted from the image via K-Means, e.g. #3A5F8A."""

    ai_confidence = db.Column(db.Float, nullable=True)
    """Classifier confidence score (0.0–1.0) for the auto-detected category."""

    # Relationships
    user = db.relationship(
        "User",
        backref=db.backref("clothing_items", lazy="dynamic", cascade="all, delete-orphan"),
    )


    def to_dict(self):
        """Serialize clothing item data."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "color": self.color,
            "season": self.season,
            "brand": self.brand or "",
            "image_url": self.image_url,
            "wear_count": self.wear_count,
            "last_worn_at": self.last_worn_at.isoformat() if self.last_worn_at else None,
            "is_favorite": self.is_favorite,
            "is_in_laundry": self.is_in_laundry,
            "style": self.style or "Casual",
            "clothing_type": self.clothing_type or "",
            "detected_color_hex": self.detected_color_hex or "",
            "ai_confidence": self.ai_confidence,
        }

