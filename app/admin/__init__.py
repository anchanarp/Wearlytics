# app/admin/__init__.py
"""Admin blueprint package with admin protection."""

from flask import Blueprint, abort, redirect, request, url_for
from flask_login import current_user, login_required
from functools import wraps

# Admin blueprint definition
admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

# Admin‑only decorator
def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view_func(*args, **kwargs)
    return wrapper

# Blueprint-wide guard – ensures every request is from an authenticated admin.
@admin_bp.before_request
def _admin_guard():
    if not current_user.is_authenticated:
        # redirect to login preserving next URL
        login_url = url_for('auth.login')
        return redirect(f"{login_url}?next={request.path}")
    if not getattr(current_user, "is_admin", False):
        abort(403)

# Import routes (they can use @admin_required if needed)
from . import routes  # noqa: F401
