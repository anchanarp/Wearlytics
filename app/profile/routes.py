"""Profile management routes."""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.models.user_preferences import UserPreferences
from app.profile import profile_bp
from app.services import clothing_classifier


# Canonical color name to hex mapping for deduplication
COLOR_NAME_TO_HEX = {
    "black": "#1c1c1c",
    "white": "#ffffff",
    "cream": "#f5ede1",
    "off white": "#f5ede1",
    "beige": "#e2d5c3",
    "camel": "#c59b6d",
    "tan": "#c59b6d",
    "brown": "#5c3d28",
    "warm brown": "#5c3d28",
    "navy": "#1e2d42",
    "navy blue": "#1e2d42",
    "olive": "#596547",
    "olive green": "#596547",
    "sage": "#8ea189",
    "sage green": "#8ea189",
    "forest green": "#234a2e",
    "dark green": "#234a2e",
    "green": "#234a2e",
    "pink": "#e8b4b8",
    "blush pink": "#e8b4b8",
    "rust": "#ba583c",
    "gold": "#d4af37",
    "warm gold": "#d4af37",
    "yellow": "#d4af37",
    "blue": "#46688f",
    "denim": "#46688f",
    "denim blue": "#46688f",
    "charcoal": "#555555",
    "charcoal grey": "#555555",
    "gray": "#555555",
    "grey": "#555555",
    "burgundy": "#800020",
    "maroon": "#800020",
    "red": "#ba583c",
}

def normalize_color_hex(c: str) -> str:
    """Normalize any color representation (name or hex) to a canonical 6-digit hex."""
    if not c or not isinstance(c, str):
        return ""
    c_clean = c.strip().lower()
    if c_clean in COLOR_NAME_TO_HEX:
        return COLOR_NAME_TO_HEX[c_clean]
    if c_clean.startswith("#"):
        if len(c_clean) == 4:
            return f"#{c_clean[1]*2}{c_clean[2]*2}{c_clean[3]*2}"
        elif len(c_clean) == 7:
            return c_clean
    return c_clean


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display user profile and update user info."""
    prefs = UserPreferences.get_or_create(current_user.id)

    if request.method == "POST":
        action = request.form.get("action", "profile")

        if action == "profile":
            name = request.form.get("name", "").strip()
            bio = request.form.get("bio", "").strip()
            avatar_color = request.form.get("avatar_color", "").strip()

            if not name:
                flash("Name cannot be empty.", "error")
                return redirect(url_for("profile.index"))

            current_user.name = name
            current_user.bio = bio or None
            if avatar_color:
                current_user.avatar_color = avatar_color

            phone = request.form.get("phone", "").strip()
            dob = request.form.get("dob", "").strip()
            gender = request.form.get("gender", "").strip()
            if phone or dob or gender:
                prefs.update_meta({"phone": phone, "dob": dob, "gender": gender})

            db.session.commit()
            flash("Profile updated successfully!", "success")

        elif action in ("personal_info", "personal"):
            name = request.form.get("name", "").strip()
            if name:
                current_user.name = name
            phone = request.form.get("phone", "").strip()
            dob = request.form.get("dob", "").strip()
            gender = request.form.get("gender", "").strip()
            prefs.update_meta({"phone": phone, "dob": dob, "gender": gender})
            db.session.commit()
            flash("Personal Information updated successfully!", "success")
            return redirect(url_for("profile.index") + "#personal-info")

        elif action == "body_fit":
            height = request.form.get("height", "").strip()
            weight = request.form.get("weight", "").strip()
            body_shape = request.form.get("body_shape", "").strip()
            clothing_size = request.form.get("clothing_size", "").strip()
            shoe_size = request.form.get("shoe_size", "").strip()
            preferred_fit = request.form.get("preferred_fit", "").strip()
            prefs.update_meta({
                "height": height,
                "weight": weight,
                "body_shape": body_shape,
                "clothing_size": clothing_size,
                "shoe_size": shoe_size,
                "preferred_fit": preferred_fit,
            })
            db.session.commit()
            flash("Body & Fit Profile updated successfully!", "success")
            return redirect(url_for("profile.index") + "#body-fit")

        elif action == "style_identity":
            fav_colors_raw = request.form.getlist("favorite_colors")
            avoid_colors_raw = request.form.getlist("colors_to_avoid")
            pref_types = request.form.getlist("clothing_types")
            pref_fabrics = request.form.getlist("fabrics")
            pref_patterns = request.form.getlist("patterns")

            # Deduplicate and normalize colors to canonical hex
            fav_colors = list(dict.fromkeys(normalize_color_hex(c) for c in fav_colors_raw if normalize_color_hex(c)))
            avoid_colors = list(dict.fromkeys(normalize_color_hex(c) for c in avoid_colors_raw if normalize_color_hex(c)))

            prefs.preferred_colors_list = fav_colors
            prefs.disliked_colors_list = avoid_colors

            prefs.update_meta({
                "favorite_colors": fav_colors,
                "colors_to_avoid": avoid_colors,
                "preferred_clothing_types": pref_types,
                "preferred_fabrics": pref_fabrics,
                "preferred_patterns": pref_patterns,
            })
            db.session.commit()
            flash("Style Identity preferences saved!", "success")
            return redirect(url_for("profile.index") + "#style-identity")

        elif action == "ai_personalization":
            prefs.use_preferences = request.form.get("ai_use_preferences") == "on"
            prefs.use_color = request.form.get("ai_consider_favorite_colors") == "on"
            prefs.update_meta({
                "ai_use_preferences": request.form.get("ai_use_preferences") == "on",
                "ai_consider_favorite_colors": request.form.get("ai_consider_favorite_colors") == "on",
                "ai_consider_disliked_colors": request.form.get("ai_consider_disliked_colors") == "on",
                "ai_consider_wardrobe_usage": request.form.get("ai_consider_wardrobe_usage") == "on",
                "ai_avoid_laundry": request.form.get("ai_avoid_laundry") == "on",
                "ai_prefer_new_combinations": request.form.get("ai_prefer_new_combinations") == "on",
            })
            db.session.commit()
            flash("AI Personalization settings updated!", "success")
            return redirect(url_for("profile.index") + "#ai-personalization")

        elif action == "notifications":
            prefs.update_meta({
                "notif_outfit_suggestions": request.form.get("notif_outfit_suggestions") == "on",
                "notif_weekly_planner_reminders": request.form.get("notif_weekly_planner_reminders") == "on",
                "notif_laundry_reminders": request.form.get("notif_laundry_reminders") == "on",
                "notif_recommendation_alerts": request.form.get("notif_recommendation_alerts") == "on",
            })
            db.session.commit()
            flash("Notification preferences updated!", "success")
            return redirect(url_for("profile.index") + "#settings")

        elif action == "settings":
            theme_choice = request.form.get("theme_appearance", "").strip()
            privacy_mode = request.form.get("privacy_mode", "").strip()
            prefs.update_meta({
                "theme_appearance": theme_choice,
                "privacy_mode": privacy_mode,
            })
            db.session.commit()
            flash("Account settings saved successfully!", "success")
            return redirect(url_for("profile.index") + "#settings")

        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not current_user.check_password(current_password):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("profile.index") + "#security")
            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "error")
                return redirect(url_for("profile.index") + "#security")
            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return redirect(url_for("profile.index") + "#security")
            current_user.set_password(new_password)
            db.session.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("profile.index") + "#security")

        elif action == "preferences":
            prefs.preferred_styles_list = request.form.getlist("styles")
            prefs.preferred_occasions_list = request.form.getlist("occasions")
            prefs.preferred_seasons_list = request.form.getlist("seasons")
            db.session.commit()
            flash("Style preferences updated!", "success")
            return redirect(url_for("profile.index") + "#style-prefs")

        return redirect(url_for("profile.index"))



    def calculate_profile_completion(user, user_prefs, user_meta, count_items):
        """Calculate dynamic profile completion percentage (0 - 100%)."""
        score = 0

        # 1. Personal Information (up to 20 pts)
        p_score = 0
        if user.name:
            p_score += 5
        if user.email:
            p_score += 5
        if user_meta.get("phone"):
            p_score += 4
        if user_meta.get("dob"):
            p_score += 3
        if user_meta.get("gender"):
            p_score += 3
        score += min(p_score, 20)

        # 2. Body & Fit Profile (up to 20 pts)
        b_score = 0
        if user_meta.get("height"):
            b_score += 4
        if user_meta.get("weight"):
            b_score += 3
        if user_meta.get("body_shape"):
            b_score += 4
        if user_meta.get("preferred_fit"):
            b_score += 3
        if user_meta.get("clothing_size"):
            b_score += 3
        if user_meta.get("shoe_size"):
            b_score += 3
        score += min(b_score, 20)

        # 3. Style Preferences (up to 20 pts)
        s_score = 0
        if user_prefs.preferred_styles_list:
            s_score += 8
        occasions = user_prefs.preferred_occasions_list or (["College"] if user_prefs.preferred_styles_list else [])
        if occasions:
            s_score += 6
        seasons = user_prefs.preferred_seasons_list or (["All Seasons"] if user_prefs.preferred_styles_list else [])
        if seasons:
            s_score += 6
        score += min(s_score, 20)

        # 4. Style Identity (up to 20 pts)
        i_score = 0
        fav_c = user_prefs.preferred_colors_list or user_meta.get("favorite_colors")
        if fav_c and len(fav_c) > 0:
            i_score += 6
        avoid_c = user_prefs.disliked_colors_list or user_meta.get("colors_to_avoid")
        if avoid_c and len(avoid_c) > 0:
            i_score += 6
        if user_meta.get("preferred_fabrics") or user_meta.get("preferred_clothing_types") or user_meta.get("preferred_patterns"):
            i_score += 8
        score += min(i_score, 20)

        # 5. AI Personalization & Wardrobe (up to 20 pts)
        w_score = 0
        if user_meta.get("ai_use_preferences") is not None or user_prefs.use_preferences:
            w_score += 10
        if count_items > 0:
            w_score += 10
        score += min(w_score, 20)

        return min(max(score, 10), 100)

    items_count = ClothingItem.query.filter_by(user_id=current_user.id).count()
    outfits_count = Outfit.query.filter_by(user_id=current_user.id).count()
    favorites_count = ClothingItem.query.filter_by(user_id=current_user.id, is_favorite=True).count()
    laundry_count = ClothingItem.query.filter_by(user_id=current_user.id, is_in_laundry=True).count()

    raw_favs = prefs.preferred_colors_list if prefs.preferred_colors_list else ["#891C1C", "#E8DDD0", "#1C1C1C", "#C59B6D"]
    raw_avoids = prefs.disliked_colors_list if prefs.disliked_colors_list else ["#9E9E9E", "#4CAF50", "#F48FB1"]
    clean_fav_colors = list(dict.fromkeys(normalize_color_hex(c) for c in raw_favs if normalize_color_hex(c)))
    clean_avoid_colors = list(dict.fromkeys(normalize_color_hex(c) for c in raw_avoids if normalize_color_hex(c)))

    profile_completion_pct = calculate_profile_completion(current_user, prefs, prefs.meta_dict, items_count)

    db.session.commit()

    return render_template(
        "profile/index.html",
        items_count=items_count,
        outfits_count=outfits_count,
        favorites_count=favorites_count,
        laundry_count=laundry_count,
        prefs=prefs,
        fav_colors=clean_fav_colors,
        avoid_colors=clean_avoid_colors,
        meta=prefs.meta_dict,
        all_styles=clothing_classifier.ALL_STYLES,
        all_occasions=clothing_classifier.ALL_OCCASIONS,
        all_seasons=clothing_classifier.ALL_SEASONS,
        profile_completion_pct=profile_completion_pct,
    )
