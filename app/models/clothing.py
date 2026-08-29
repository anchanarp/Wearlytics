"""Clothing item database model."""

from datetime import datetime, timezone

from app.extensions import db


class ClothingItem(db.Model):
    """Individual clothing item in a user's wardrobe."""

    __tablename__ = "clothing_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="Tops")  # Tops, Bottoms, Shoes, Outerwear, Accessories, Dresses
    color = db.Column(db.String(50), nullable=False, default="Black")
    season = db.Column(db.String(50), nullable=False, default="All Seasons")  # All Seasons, Summer, Winter, Spring/Fall
    brand = db.Column(db.String(100), nullable=True)
    image_url = db.Column(db.String(500), nullable=False)
    wear_count = db.Column(db.Integer, default=0, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("clothing_items", lazy="dynamic", cascade="all, delete-orphan"))

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
            "is_favorite": self.is_favorite,
        }
