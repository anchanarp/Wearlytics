"""Application factory for Wearlytics."""

from flask import Flask

from config import Config
from app.extensions import db, login_manager, migrate


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Override DB URI for test environment to use in‑memory SQLite, avoiding external MySQL dependency.
    if app.config.get("TESTING"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    # Limit uploads to 16 MB
    app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access your dashboard."
    login_manager.login_message_category = "info"

    # Import models before Flask-Migrate inspects SQLAlchemy metadata.
    from app import models  # noqa: F401

    from app.analytics import analytics_bp
    from app.auth import auth_bp
    from app.main import main_bp
    from app.outfits import outfits_bp
    from app.planner import planner_bp
    from app.profile import profile_bp
    from app.recommendations import recommendations_bp
    from app.admin import admin_bp
    from app.stylist import stylist_bp
    app.register_blueprint(admin_bp)
    from app.wardrobe import wardrobe_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(wardrobe_bp)
    app.register_blueprint(outfits_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(stylist_bp)

    # --- Global Error Handlers ---
    @app.errorhandler(404)
    def page_not_found(e):
        from flask import render_template as rt
        return rt("errors/404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        from flask import flash, redirect, request, url_for
        flash("File too large. Maximum upload size is 16 MB.", "error")
        return redirect(request.referrer or url_for("wardrobe.upload"))

    @app.errorhandler(500)
    def internal_server_error(e):
        from flask import render_template as rt
        db.session.rollback()
        return rt("errors/500.html"), 500

    return app
