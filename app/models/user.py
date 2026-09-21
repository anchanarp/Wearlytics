"""User account model."""

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """Registered Wearlytics user."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # Admin flag
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_color = db.Column(db.String(20), nullable=True, default="#6c5ce7")
    """Hex color for the user's avatar (profile photo placeholder)."""
    bio = db.Column(db.String(200), nullable=True)
    """Short profile bio / tagline."""
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def set_password(self, password):
        """Store a secure password hash instead of the plaintext password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return whether a submitted password matches this account."""
        return check_password_hash(self.password_hash, password)

    @property
    def clothing_count(self):
        """Number of clothing items owned by this user."""
        return self.clothing_items.count()

    @property
    def outfit_count(self):
        """Number of outfits created by this user."""
        from app.models.outfit import Outfit  # lazy import avoids circular dependency
        return Outfit.query.filter_by(user_id=self.id).count()

