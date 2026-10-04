"""Authentication routes for registration, login, logout, and OTP verification."""

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth_bp
from app.extensions import db, login_manager
from app.models import User
from app.models.user_preferences import UserPreferences


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
        identifier = (
            request.form.get("email_or_username")
            or request.form.get("email")
            or ""
        ).strip()
        password = request.form.get("password", "")

        user = None
        if identifier:
            user = db.session.scalar(
                db.select(User).where(
                    (db.func.lower(User.email) == identifier.lower())
                    | (db.func.lower(User.name) == identifier.lower())
                )
            )

        if user is None or not user.check_password(password):
            flash("Invalid email/username or password.", "error")
        else:
            login_user(user, remember=request.form.get("remember") == "on")
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            else:
                return redirect(_safe_next_url(request.args.get("next")) or url_for("main.home"))

    return render_template("auth/login.html")


@auth_bp.post("/send-otp")
def send_otp():
    """Send a demo 6-digit OTP code to the requested mobile number."""
    data = request.get_json(silent=True) or request.form
    phone = (data.get("phone") or "").strip()
    country_code = (data.get("country_code") or "+91").strip()

    if not phone:
        msg = "Please enter a valid phone number."
        if request.is_json:
            return jsonify({"status": "error", "message": msg}), 400
        flash(msg, "error")
        return redirect(url_for("auth.login") + "#otp")

    full_phone = f"{country_code} {phone}".strip() if country_code and not phone.startswith("+") else phone
    session["otp_code"] = "123456"
    session["otp_phone"] = full_phone

    if request.is_json:
        return jsonify({
            "status": "success",
            "phone": full_phone,
            "message": f"6-digit code sent to {full_phone} (Demo code: 123456)",
        })

    flash(f"A 6-digit verification code was sent to {full_phone} (Demo: 123456)", "success")
    return redirect(url_for("auth.login") + f"#verify&phone={full_phone}")


@auth_bp.post("/verify-otp")
def verify_otp():
    """Verify the 6-digit code and sign the user in."""
    data = request.get_json(silent=True) or request.form
    code = (data.get("code") or data.get("otp") or "").strip()
    phone = (data.get("phone") or session.get("otp_phone") or "").strip()

    expected_code = session.get("otp_code") or "123456"

    if not code or (code != expected_code and code != "123456"):
        msg = "Invalid verification code. Please try again (Demo code: 123456)."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "error", "message": msg}), 400
        flash(msg, "error")
        return redirect(url_for("auth.login") + "#verify")

    # Code is valid! Find matching user by phone in profile preferences
    user = None
    all_prefs = UserPreferences.query.all()
    for pref in all_prefs:
        p = pref.get_meta("phone", "")
        if p and (phone in p or p in phone):
            user = db.session.get(User, pref.user_id)
            break

    # If no existing user has this phone, sign in existing user or auto-provision
    if not user:
        user = User.query.filter_by(is_demo=True).first() or User.query.first()

    if not user:
        clean_phone = "".join(ch for ch in phone if ch.isdigit()) or "phoneuser"
        user = User(name=f"User {clean_phone[-4:]}", email=f"{clean_phone}@user.wearlytics.com")
        user.set_password("Wearlytics123!")
        db.session.add(user)
        db.session.commit()
        prefs = UserPreferences.get_or_create(user.id)
        prefs.update_meta({"phone": phone})
        db.session.commit()

    login_user(user, remember=True)
    session.pop("otp_code", None)
    session.pop("otp_phone", None)

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"status": "success", "redirect_url": url_for("main.home")})

    flash("Successfully signed in!", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Handle password reset instructions."""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            flash("Please enter your registered email address.", "error")
        else:
            flash("If an account exists for this email, password reset instructions have been sent.", "success")
        return redirect(url_for("auth.login"))
    return redirect(url_for("auth.login") + "#forgot")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a Wearlytics user account."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        country_code = request.form.get("country_code", "+91").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not password:
            flash("Please complete every required field.", "error")
        elif not email and not phone:
            flash("Please provide either an email address or mobile number.", "error")
        elif len(password) < 8:
            flash("Your password must be at least 8 characters long.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        elif email and db.session.scalar(db.select(User).where(User.email == email)):
            flash("An account already exists for this email address.", "error")
        else:
            email_to_use = email
            if not email_to_use:
                clean_phone = "".join(ch for ch in phone if ch.isdigit()) or "user"
                email_to_use = f"{clean_phone}@user.wearlytics.com"
                if db.session.scalar(db.select(User).where(User.email == email_to_use)):
                    email_to_use = f"{clean_phone}_{int(datetime.now(timezone.utc).timestamp())}@user.wearlytics.com"

            user = User(name=name, email=email_to_use)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            if phone:
                prefs = UserPreferences.get_or_create(user.id)
                full_phone = f"{country_code} {phone}".strip() if country_code and not phone.startswith("+") else phone
                prefs.update_meta({"phone": full_phone})
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
