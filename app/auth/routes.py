"""Authentication routes for registration, login, and logout."""

from urllib.parse import urljoin, urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth_bp
from app.extensions import db, login_manager
from app.models import User


@login_manager.user_loader
def load_user(user_id):
    """Restore a logged-in user from Flask-Login's session identifier."""
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def _safe_next_url(target):
    """Return an internal redirect target, preventing open redirects."""
    if not target:
        return None

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    if redirect_url.scheme in {"http", "https"} and host_url.netloc == redirect_url.netloc:
        return target
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Sign an existing user into Wearlytics."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.email == email))

        if user is None or not user.check_password(password):
            flash("Invalid email or password.", "error")
        else:
            login_user(user, remember=request.form.get("remember") == "on")
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            else:
                return redirect(_safe_next_url(request.args.get("next")) or url_for("main.home"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a Wearlytics user account."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please complete every required field.", "error")
        elif len(password) < 8:
            flash("Your password must be at least 8 characters long.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        elif db.session.scalar(db.select(User).where(User.email == email)):
            flash("An account already exists for this email address.", "error")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Your account has been created. Welcome to Wearlytics!", "success")
            return redirect(url_for("main.home"))

    return render_template("auth/register.html")


@auth_bp.post("/logout")
@login_required
def logout():
    """End the active user session."""
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
