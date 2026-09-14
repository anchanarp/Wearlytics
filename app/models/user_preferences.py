"""User preferences model — stores learned style preferences and toggle flags per user."""

import json
from datetime import datetime, timezone

from app.extensions import db


class UserPreferences(db.Model):
    """One row per user storing their inferred style preferences and toggle flags."""

    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # JSON-encoded lists stored as Text for MySQL/SQLite compatibility
    preferred_colors = db.Column(db.Text, nullable=True, default="[]")
    preferred_styles = db.Column(db.Text, nullable=True, default="[]")
    preferred_occasions = db.Column(db.Text, nullable=True, default="[]")
    preferred_seasons = db.Column(db.Text, nullable=True, default="[]")
    disliked_colors = db.Column(db.Text, nullable=True, default="[]")

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Preference toggle flags ───────────────────────────────────────────────
    # Master switch: when False, all sub-toggles are ignored and scoring
    # falls back to neutral (0.5) for all preference-related sub-scores.
    use_preferences       = db.Column(db.Boolean, nullable=False, default=True)

    # Per-category toggles — only applied when use_preferences is True
    use_style             = db.Column(db.Boolean, nullable=False, default=True)
    use_color             = db.Column(db.Boolean, nullable=False, default=True)
    use_occasion          = db.Column(db.Boolean, nullable=False, default=True)
    use_season            = db.Column(db.Boolean, nullable=False, default=True)

    # Placeholder toggles (no underlying data yet — both default False)
    use_body_shape        = db.Column(db.Boolean, nullable=False, default=False)
    use_clothing_size     = db.Column(db.Boolean, nullable=False, default=False)
    use_fit_preference    = db.Column(db.Boolean, nullable=False, default=False)

    # Feedback learning toggle: when False, liked/disliked item bonuses
    # and preference updates from feedback are not applied to scoring.
    use_feedback_learning = db.Column(db.Boolean, nullable=False, default=True)

    # Relationship
    user = db.relationship(
        "User",
        backref=db.backref("preferences", uselist=False, cascade="all, delete-orphan"),
    )

    # ── JSON helpers ──────────────────────────────────────────────────────────

    def _get_list(self, field: str) -> list:
        raw = getattr(self, field)
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    def _set_list(self, field: str, value: list) -> None:
        setattr(self, field, json.dumps(list(value)))

    @property
    def preferred_colors_list(self) -> list:
        return self._get_list("preferred_colors")

    @preferred_colors_list.setter
    def preferred_colors_list(self, value: list):
        self._set_list("preferred_colors", value)

    @property
    def preferred_styles_list(self) -> list:
        return self._get_list("preferred_styles")

    @preferred_styles_list.setter
    def preferred_styles_list(self, value: list):
        self._set_list("preferred_styles", value)

    @property
    def preferred_occasions_list(self) -> list:
        return self._get_list("preferred_occasions")

    @preferred_occasions_list.setter
    def preferred_occasions_list(self, value: list):
        self._set_list("preferred_occasions", value)

    @property
    def preferred_seasons_list(self) -> list:
        return self._get_list("preferred_seasons")

    @preferred_seasons_list.setter
    def preferred_seasons_list(self, value: list):
        self._set_list("preferred_seasons", value)

    @property
    def disliked_colors_list(self) -> list:
        return self._get_list("disliked_colors")

    @disliked_colors_list.setter
    def disliked_colors_list(self, value: list):
        self._set_list("disliked_colors", value)

    # ── Effective preference view (respects toggles) ──────────────────────────

    def effective_preferred_colors(self) -> list:
        """Returns preferred colors only if use_preferences and use_color are on."""
        if not self.use_preferences or not self.use_color:
            return []
        return self.preferred_colors_list

    def effective_disliked_colors(self) -> list:
        """Returns disliked colors only if use_preferences and use_color are on."""
        if not self.use_preferences or not self.use_color:
            return []
        return self.disliked_colors_list

    def effective_preferred_styles(self) -> list:
        """Returns preferred styles only if use_preferences and use_style are on."""
        if not self.use_preferences or not self.use_style:
            return []
        return self.preferred_styles_list

    def effective_preferred_occasions(self) -> list:
        """Returns preferred occasions only if use_preferences and use_occasion are on."""
        if not self.use_preferences or not self.use_occasion:
            return []
        return self.preferred_occasions_list

    def effective_preferred_seasons(self) -> list:
        """Returns preferred seasons only if use_preferences and use_season are on."""
        if not self.use_preferences or not self.use_season:
            return []
        return self.preferred_seasons_list

    @classmethod
    def get_or_create(cls, user_id: int) -> "UserPreferences":
        """Return the preferences row for user_id, creating it if it doesn't exist."""
        from app.extensions import db as _db
        prefs = cls.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = cls(user_id=user_id)
            _db.session.add(prefs)
            _db.session.flush()
        return prefs

    def __repr__(self):
        return f"<UserPreferences user={self.user_id}>"
