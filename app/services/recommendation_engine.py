"""
Recommendation Engine Service
==============================
Content-based outfit recommendation engine.

Algorithm:
  1. Load user's ClothingItem list from DB
  2. Detect wardrobe gaps (missing categories)
  3. Filter by occasion and season if provided
  4. Generate all valid outfit combinations (top+bottom or dress, optional shoes+extras)
  5. Score each combination using compatibility_scorer (returns breakdown dict)
  6. Apply liked-item bonus (per item that the user has liked before)
  7. Exclude combinations dominated by disliked outfits
  8. Return Top N combinations sorted by score descending, each including breakdown
"""

from __future__ import annotations

import itertools
import random
import logging
from typing import Optional

from app.services import compatibility_scorer
from flask import current_app


_TOP_CATEGORIES    = {"Tops", "Dresses", "Outerwear"}
_BOTTOM_CATEGORIES = {"Bottoms", "Dresses"}
_SHOE_CATEGORIES   = {"Shoes"}
_EXTRA_CATEGORIES  = {"Accessories", "Outerwear"}


# ---------------------------------------------------------------------------
# Wardrobe gap detection
# ---------------------------------------------------------------------------

def detect_wardrobe_gaps(items: list) -> list[str]:
    """
    Analyse the user's wardrobe and return a list of human-readable hint strings
    for missing or under-represented categories that would improve recommendations.

    Returns [] when the wardrobe is well-rounded.
    """
    hints: list[str] = []
    if not items:
        hints.append("Your wardrobe is empty — add some clothing items to get started!")
        return hints

    categories = {i.category for i in items}

    has_tops     = bool(categories & {"Tops", "Dresses"})
    has_bottoms  = bool(categories & {"Bottoms", "Dresses"})
    has_shoes    = "Shoes" in categories
    has_outer    = "Outerwear" in categories
    has_access   = "Accessories" in categories

    if not has_tops:
        hints.append("Add at least one Top or Dress to unlock outfit recommendations.")
    if not has_bottoms:
        hints.append("Add a Bottom (trousers, skirt, shorts) — or a Dress — to complete outfit combinations.")
    if not has_shoes:
        hints.append("Adding shoes will raise your compatibility score — outfits with shoes score up to 20 pts higher.")
    if not has_outer and len(items) >= 5:
        hints.append("A jacket or coat can elevate your outfits and expand seasonal recommendations.")
    if not has_access and len(items) >= 8:
        hints.append("Accessories like hats or scarves add the finishing touch to outfit combinations.")

    # Low variety warning — fewer than 3 items per key category
    top_count    = sum(1 for i in items if i.category in {"Tops", "Dresses"})
    bottom_count = sum(1 for i in items if i.category == "Bottoms")
    if has_tops and has_bottoms and top_count < 3:
        hints.append(f"Only {top_count} top(s) in your wardrobe — adding more increases recommendation variety.")
    if has_tops and has_bottoms and bottom_count < 2:
        hints.append(f"Only {bottom_count} bottom(s) — add more to get diverse outfit combinations.")

    return hints


# ---------------------------------------------------------------------------
# Season / occasion filters
# ---------------------------------------------------------------------------

def _filter_by_season(items: list, season: Optional[str]) -> list:
    """Keep items compatible with the target season."""
    if not season or season == "All Seasons":
        return items
    compat = {"All Seasons", season}
    if season == "Rainy":
        compat.add("Spring/Fall")
    return [i for i in items if (i.season or "All Seasons") in compat]


def _filter_by_occasion(items: list, occasion: Optional[str]) -> list:
    """Keep items whose style and clothing_type are appropriate for the occasion."""
    if not occasion:
        return items

    from app.services.compatibility_scorer import _OCCASION_STYLE_FIT, _OCCASION_BAD_TYPES
    ideal_styles = set(_OCCASION_STYLE_FIT.get(occasion, ["Casual"]))
    ideal_styles.add("Casual")   # always include Casual as universal fallback
    bad_types    = _OCCASION_BAD_TYPES.get(occasion, set())

    filtered = []
    for item in items:
        # Reject items whose clothing_type is explicitly bad for this occasion
        item_type = getattr(item, "clothing_type", "") or ""
        if item_type and item_type in bad_types:
            continue
        # Keep items whose style fits the occasion
        if (item.style or "Casual") in ideal_styles:
            filtered.append(item)

    return filtered


# ---------------------------------------------------------------------------
# Feedback helpers
# ---------------------------------------------------------------------------

def _get_disliked_item_ids(user_id: int) -> set[int]:
    """Return clothing item IDs that appeared in outfits the user disliked."""
    try:
        from app.models.feedback import OutfitFeedback
        from app.models.outfit import Outfit

        disliked_outfits = (
            OutfitFeedback.query
            .filter_by(user_id=user_id, reaction="disliked")
            .all()
        )
        bad_outfit_ids = {fb.outfit_id for fb in disliked_outfits}
        bad_item_ids: set[int] = set()
        for oid in bad_outfit_ids:
            o = Outfit.query.get(oid)
            if o:
                bad_item_ids.update(i.id for i in o.items)
        return bad_item_ids
    except Exception:
        return set()


def _get_liked_item_ids(user_id: int) -> set[int]:
    """Return clothing item IDs from outfits the user liked or favorited."""
    try:
        from app.models.feedback import OutfitFeedback
        from app.models.outfit import Outfit

        liked_outfits = (
            OutfitFeedback.query
            .filter_by(user_id=user_id)
            .filter(OutfitFeedback.reaction.in_(["liked", "favorited"]))
            .all()
        )
        good_item_ids: set[int] = set()
        for fb in liked_outfits:
            o = Outfit.query.get(fb.outfit_id)
            if o:
                good_item_ids.update(i.id for i in o.items)
        return good_item_ids
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# Outfit viability check
# ---------------------------------------------------------------------------

def _can_form_outfit(items: list) -> bool:
    """
    Return True if `items` contains enough variety to build at least one
    valid outfit, i.e.:
      - at least one Top/Outerwear  AND  at least one Bottom/Dress
      OR
      - at least one standalone Dress
    This is the correct guard for fallback decisions — a raw item count (< 3)
    is insufficient because 4 Accessories still can't form an outfit.
    """
    categories = {i.category for i in items}
    has_top    = bool(categories & {"Tops", "Outerwear"})
    has_bottom = bool(categories & {"Bottoms"})
    has_dress  = "Dresses" in categories
    return (has_top and (has_bottom or has_dress)) or has_dress


# ---------------------------------------------------------------------------
# Outfit combination builder
# ---------------------------------------------------------------------------

def _build_combinations(items: list, max_combos: int = 300) -> list[list]:
    """
    Build valid outfit combination lists.
    A valid combination must have:
      - 1 top/dress (required)
      - 1 bottom (required unless it's a dress)
      - 1 pair of shoes (optional — but scored higher)
      - At most 1 accessory/outerwear extra
    """
    tops   = [i for i in items if i.category in _TOP_CATEGORIES]
    bottoms = [i for i in items if i.category in _BOTTOM_CATEGORIES]
    shoes   = [i for i in items if i.category in _SHOE_CATEGORIES]
    extras  = [i for i in items if i.category in _EXTRA_CATEGORIES]

    combos: list[list] = []

    for top in tops:
        is_dress = top.category == "Dresses"

        if is_dress:
            # Dress alone + optional shoes + optional extra
            for shoe in ([None] + shoes):
                for extra in ([None] + extras[:3]):
                    combo: list = [top]
                    if shoe:  combo.append(shoe)
                    if extra: combo.append(extra)
                    combos.append(combo)
        else:
            # Top + bottom required
            for bottom in bottoms:
                for shoe in ([None] + shoes):
                    combo = [top, bottom]
                    if shoe: combo.append(shoe)
                    combos.append(combo)

        if len(combos) >= max_combos:
            break

    random.shuffle(combos)
    return combos[:max_combos]


def _build_combinations_with_pinned(
    items: list,
    pinned_items: list,
    max_combos: int = 300,
) -> list[list]:
    """
    Build outfit combinations that ALWAYS contain every pinned item.

    Strategy:
    - Determine what categories the pinned items already cover.
    - Only vary the remaining (completion) slots using non-pinned items.
    - Every returned combination contains ALL pinned items exactly once.

    This guarantees that pinned item IDs pass the final
    `pinned_set.issubset(...)` check regardless of random shuffle or cap.
    """
    pinned_ids  = {i.id for i in pinned_items}
    pinned_cats = {i.category for i in pinned_items}
    free_items  = [i for i in items if i.id not in pinned_ids]

    # Categorise free (non-pinned) items for completion
    free_tops    = [i for i in free_items if i.category in _TOP_CATEGORIES]
    free_bottoms = [i for i in free_items if i.category in _BOTTOM_CATEGORIES]
    free_shoes   = [i for i in free_items if i.category in _SHOE_CATEGORIES]
    free_extras  = [i for i in free_items if i.category in _EXTRA_CATEGORIES]

    # Also allow pinned shoes/extras to satisfy their own slot
    # (they are already in pinned_items which is always added to each combo)

    has_pinned_top    = bool(pinned_cats & _TOP_CATEGORIES)
    has_pinned_bottom = bool(pinned_cats & _BOTTOM_CATEGORIES)
    has_pinned_shoe   = bool(pinned_cats & _SHOE_CATEGORIES)
    has_pinned_dress  = "Dresses" in pinned_cats

    combos: list[list] = []

    def make_combo(*extra_items) -> list:
        """Return pinned items + any non-None extra items (deduplicated by id)."""
        seen: set[int] = set(pinned_ids)
        combo = list(pinned_items)
        for item in extra_items:
            if item is not None and item.id not in seen:
                seen.add(item.id)
                combo.append(item)
        return combo

    if has_pinned_dress or (has_pinned_top and has_pinned_bottom):
        # Core is complete — just add optional shoe + extra completions
        shoe_pool  = free_shoes  if not has_pinned_shoe else [None]
        extra_pool = free_extras[:3]
        for shoe in ([None] + shoe_pool):
            for extra in ([None] + extra_pool):
                combos.append(make_combo(shoe, extra))
                if len(combos) >= max_combos:
                    return combos

    elif has_pinned_top and not has_pinned_bottom:
        # Need a bottom; dress already counts as top+bottom
        if not free_bottoms:
            # No bottoms available — build dress-style outfits if pinned is a dress
            for shoe in ([None] + free_shoes):
                for extra in ([None] + free_extras[:3]):
                    combos.append(make_combo(shoe, extra))
                    if len(combos) >= max_combos:
                        return combos
        else:
            for bottom in free_bottoms:
                for shoe in ([None] + free_shoes):
                    combos.append(make_combo(bottom, shoe))
                    if len(combos) >= max_combos:
                        return combos

    elif has_pinned_bottom and not has_pinned_top:
        # Need a top (or dress)
        top_pool = free_tops
        if not top_pool:
            # Can't form a valid outfit
            return []
        for top in top_pool:
            for shoe in ([None] + free_shoes):
                combos.append(make_combo(top, shoe))
                if len(combos) >= max_combos:
                    return combos

    elif has_pinned_shoe or (pinned_cats <= _EXTRA_CATEGORIES | _SHOE_CATEGORIES):
        # Pinned item is a shoe or accessory — need a full top+bottom or dress base
        if free_tops and free_bottoms:
            for top in free_tops:
                is_dress = top.category == "Dresses"
                if is_dress:
                    for extra in ([None] + free_extras[:3]):
                        combos.append(make_combo(top, extra))
                        if len(combos) >= max_combos:
                            return combos
                else:
                    for bottom in free_bottoms:
                        combos.append(make_combo(top, bottom))
                        if len(combos) >= max_combos:
                            return combos
        elif free_tops:
            # Only tops (might be dresses)
            for top in free_tops:
                combos.append(make_combo(top))
                if len(combos) >= max_combos:
                    return combos

    if not combos:
        # Final fallback: just return pinned items as a minimal outfit
        combos.append(list(pinned_items))

    return combos




# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def get_recommendations(
    user_id:         int,
    occasion:        Optional[str] = None,
    season:          Optional[str] = None,
    top_n:           int = 3,
    pinned_item_ids: Optional[list] = None,
) -> list[dict]:
    """
    Generate the Top-N personalised outfit recommendations for a user.

    Parameters
    ----------
    user_id          : int
    occasion         : str or None  (internal engine key, e.g. "College", "Office")
    season           : str or None  (e.g. "Summer", "Winter")
    top_n            : int — number of recommendations to return (default 3)
    pinned_item_ids  : list[int] or None
        When provided, ONLY combinations that contain ALL specified item IDs
        are considered.  If no valid outfit can be built with all pinned items,
        an empty list is returned (caller should surface an error to the user).

    Returns
    -------
    List of dicts, each with:
        clothing_items   : list of ClothingItem ORM objects
        score            : float  (0–100)
        breakdown        : dict   {color, category, occasion, season,
                                   preference, novelty, favourite}  each 0–100
        occasion         : str
        season           : str
        color_breakdown  : list of color strings
        category_summary : str
    """
    from app.models.clothing import ClothingItem
    from app.models.user_preferences import UserPreferences

    # --- Load wardrobe (only available items — exclude in-laundry) ---
    all_items = ClothingItem.query.filter_by(user_id=user_id).all()
    available_items = [i for i in all_items if not i.is_in_laundry]
    if not available_items:
        return []

    # --- User preferences and feedback ---
    user_prefs   = UserPreferences.query.filter_by(user_id=user_id).first()

    # Respect feedback learning toggle
    apply_feedback = True
    if user_prefs is not None:
        apply_feedback = getattr(user_prefs, 'use_feedback_learning', True)

    disliked_ids = _get_disliked_item_ids(user_id) if apply_feedback else set()
    liked_ids    = _get_liked_item_ids(user_id)    if apply_feedback else set()

    # --- Soft-remove disliked items only if valid outfits can still be formed ---
    candidate_items = [i for i in available_items if i.id not in disliked_ids]
    if not _can_form_outfit(candidate_items):
        # Dislike filtering wiped out all usable categories — fall back to available wardrobe.
        candidate_items = available_items

    # --- Season + occasion filter ---
    # IMPORTANT: pinned items are ALWAYS kept in the pool regardless of filters,
    # so that the pinned constraint can always be satisfied.
    pinned_set = set(pinned_item_ids) if pinned_item_ids else set()
    pinned_items = [i for i in candidate_items if i.id in pinned_set]

    # Apply season and occasion filters
    filtered = _filter_by_season(candidate_items, season)
    filtered = _filter_by_occasion(filtered, occasion)
    # If filters result in no viable outfit, keep filtered as is (could be empty) and log for debugging
    if not _can_form_outfit(filtered):
        current_app.logger.debug(
            f"Filtered items after season/occasion filters cannot form outfit (occasion={occasion}, season={season}). Returning empty result set."
        )
        # Do not fallback to candidate_items; downstream will handle empty combos



    # Re-add any pinned items that were removed by the filters so they are
    # always available as hard constraints in combination building.
    if pinned_items:
        filtered_ids = {i.id for i in filtered}
        for pi in pinned_items:
            if pi.id not in filtered_ids:
                filtered.append(pi)

    # --- Build combinations ---
    if pinned_items:
        # Build combinations that ALWAYS include every pinned item.
        combos = _build_combinations_with_pinned(filtered, pinned_items)
    else:
        combos = _build_combinations(filtered)

    if not combos:
        return []

    # --- Verify pinned constraint (final safety check) ---
    if pinned_set:
        combos = [c for c in combos if pinned_set.issubset({i.id for i in c})]
        if not combos:
            # Cannot form any outfit with all pinned items → caller surfaces error
            return []


    # --- Score all combinations ---
    scored: list[tuple[float, dict, list]] = []
    for combo in combos:
        result = compatibility_scorer.calculate(combo, occasion, season, user_prefs)
        total  = result["total"]

        # Liked-item bonus: each liked item adds 2 pts to total (meaningful but capped)
        if apply_feedback:
            liked_bonus = sum(2.0 for i in combo if i.id in liked_ids)
            total = min(100.0, total + liked_bonus)

        scored.append((total, result, combo))

    # --- Sort descending ---
    scored.sort(key=lambda x: x[0], reverse=True)

    # --- Deduplicate & collect Top N ---
    seen_item_sets: list[frozenset] = []
    results: list[dict] = []

    for total, breakdown, combo in scored:
        item_set = frozenset(i.id for i in combo)
        if item_set in seen_item_sets:
            continue
        seen_item_sets.append(item_set)

        categories = sorted({i.category for i in combo})
        results.append({
            "clothing_items":   combo,
            "score":            total,
            "breakdown": {
                "color":      round(breakdown["color"]      * 100),
                "category":   round(breakdown["category"]   * 100),
                "occasion":   round(breakdown["occasion"]   * 100),
                "season":     round(breakdown["season"]     * 100),
                "preference": round(breakdown["preference"] * 100),
                "novelty":    round(breakdown["novelty"]    * 100),
                "favourite":  round(breakdown["favourite"]  * 100),
            },
            "occasion":         occasion or "Any",
            "season":           season or "All Seasons",
            "color_breakdown":  list({i.color for i in combo if i.color}),
            "category_summary": " + ".join(categories),
        })

        if len(results) >= top_n:
            break

    return results


def get_dashboard_preview(user_id: int, top_n: int = 3) -> list[dict]:
    """
    Quick recommendation for the dashboard — no occasion/season filter.
    Returns at most top_n results.
    """
    return get_recommendations(user_id, top_n=top_n)
