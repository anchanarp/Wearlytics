"""
Compatibility Scorer Service
=============================
Calculates a weighted compatibility score (0–100) for a candidate outfit
assembled from the user's clothing items.

Scoring weights (must sum to 1.0):
  - Color harmony       25%   — expanded palette, neutral + harmony rules
  - Category balance    20%   — top + bottom (or dress) + shoes completeness
  - Occasion match      20%   — style AND clothing_type vs. occasion matrix
  - Season match        15%   — seasonal appropriateness
  - Personalization     12%   — preferred colors, styles, occasions, seasons
  - Novelty (wear_count) 5%   — low-wear items prioritised
  - Favourite boost      3%   — is_favorite items boosted

Returns
-------
calculate() → dict with keys:
    total      : float   0–100 (rounded to 1 d.p.)
    color      : float   0–1  (raw sub-score)
    category   : float   0–1
    occasion   : float   0–1
    season     : float   0–1
    preference : float   0–1
    novelty    : float   0–1
    favourite  : float   0–1
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Color harmony rules
# ---------------------------------------------------------------------------
# Every entry is a frozenset so lookup is symmetric.
# Colors must match exactly what color_detector.py produces as `name`.
_HARMONIOUS_PAIRS: set[frozenset] = {
    # ---- Classic neutrals ----
    frozenset({"Black",    "White"}),
    frozenset({"Black",    "Gray"}),
    frozenset({"Black",    "Silver"}),
    frozenset({"Black",    "Charcoal"}),
    frozenset({"Black",    "Red"}),
    frozenset({"Black",    "Crimson"}),
    frozenset({"Black",    "Navy"}),
    frozenset({"Black",    "Beige"}),
    frozenset({"Black",    "Tan"}),
    frozenset({"Black",    "Khaki"}),
    frozenset({"Black",    "Gold"}),
    frozenset({"Charcoal", "White"}),
    frozenset({"Charcoal", "Gray"}),
    frozenset({"Charcoal", "Beige"}),
    frozenset({"Charcoal", "Navy"}),
    frozenset({"Charcoal", "Red"}),
    frozenset({"Charcoal", "Lime"}),
    frozenset({"Charcoal", "Yellow Green"}),
    frozenset({"Charcoal", "Lime Green"}),
    frozenset({"Charcoal", "Green Yellow"}),
    frozenset({"White",    "Navy"}),
    frozenset({"White",    "Blue"}),
    frozenset({"White",    "Gray"}),
    frozenset({"White",    "Silver"}),
    frozenset({"White",    "Beige"}),
    frozenset({"White",    "Pink"}),
    frozenset({"White",    "Hot Pink"}),
    frozenset({"White",    "Coral"}),
    frozenset({"White",    "Light Blue"}),
    frozenset({"White",    "Lime"}),
    frozenset({"White",    "Lime Green"}),
    frozenset({"White",    "Mint"}),
    frozenset({"White",    "Lavender"}),
    frozenset({"White",    "Red"}),
    frozenset({"Gray",     "Navy"}),
    frozenset({"Gray",     "Beige"}),
    frozenset({"Gray",     "Pink"}),
    frozenset({"Gray",     "Blue"}),
    frozenset({"Gray",     "Teal"}),
    frozenset({"Gray",     "Lime"}),
    frozenset({"Gray",     "Lime Green"}),
    frozenset({"Gray",     "Yellow Green"}),
    frozenset({"Gray",     "Maroon"}),
    frozenset({"Silver",   "Navy"}),
    frozenset({"Silver",   "Black"}),
    frozenset({"Silver",   "Purple"}),
    # ---- Earth tones ----
    frozenset({"Brown",    "Beige"}),
    frozenset({"Brown",    "Khaki"}),
    frozenset({"Brown",    "Tan"}),
    frozenset({"Brown",    "Olive"}),
    frozenset({"Brown",    "Cream"}),
    frozenset({"Brown",    "White"}),
    frozenset({"Olive",    "Khaki"}),
    frozenset({"Olive",    "Beige"}),
    frozenset({"Olive",    "Brown"}),
    frozenset({"Olive",    "Tan"}),
    frozenset({"Tan",      "Beige"}),
    frozenset({"Tan",      "White"}),
    frozenset({"Khaki",    "White"}),
    frozenset({"Khaki",    "Navy"}),
    # ---- Blues ----
    frozenset({"Navy",     "Gray"}),
    frozenset({"Navy",     "Beige"}),
    frozenset({"Navy",     "White"}),
    frozenset({"Navy",     "Red"}),
    frozenset({"Navy",     "Gold"}),
    frozenset({"Navy",     "Khaki"}),
    frozenset({"Blue",     "Gray"}),
    frozenset({"Blue",     "White"}),
    frozenset({"Blue",     "Beige"}),
    frozenset({"Blue",     "Brown"}),
    frozenset({"Blue",     "Olive"}),
    frozenset({"Light Blue", "White"}),
    frozenset({"Light Blue", "Navy"}),
    frozenset({"Light Blue", "Gray"}),
    frozenset({"Steel Blue", "White"}),
    frozenset({"Steel Blue", "Navy"}),
    frozenset({"Steel Blue", "Gray"}),
    frozenset({"Dodger Blue", "White"}),
    frozenset({"Dodger Blue", "Navy"}),
    frozenset({"Teal",     "Gray"}),
    frozenset({"Teal",     "White"}),
    frozenset({"Teal",     "Beige"}),
    frozenset({"Teal",     "Navy"}),
    frozenset({"Turquoise","White"}),
    frozenset({"Turquoise","Gray"}),
    # ---- Greens ----
    frozenset({"Lime",         "Black"}),
    frozenset({"Lime",         "White"}),
    frozenset({"Lime",         "Navy"}),
    frozenset({"Lime",         "Gray"}),
    frozenset({"Lime",         "Charcoal"}),
    frozenset({"Lime Green",   "Black"}),
    frozenset({"Lime Green",   "White"}),
    frozenset({"Lime Green",   "Navy"}),
    frozenset({"Yellow Green", "Black"}),
    frozenset({"Yellow Green", "White"}),
    frozenset({"Yellow Green", "Navy"}),
    frozenset({"Green Yellow", "Black"}),
    frozenset({"Green Yellow", "White"}),
    frozenset({"Green",        "White"}),
    frozenset({"Green",        "Beige"}),
    frozenset({"Green",        "Khaki"}),
    frozenset({"Dark Green",   "Beige"}),
    frozenset({"Dark Green",   "Khaki"}),
    frozenset({"Dark Green",   "Brown"}),
    frozenset({"Light Green",  "White"}),
    frozenset({"Light Green",  "Beige"}),
    frozenset({"Pale Green",   "White"}),
    frozenset({"Mint",         "White"}),
    frozenset({"Mint",         "Beige"}),
    # ---- Pinks / Reds ----
    frozenset({"Pink",     "Gray"}),
    frozenset({"Pink",     "White"}),
    frozenset({"Pink",     "Navy"}),
    frozenset({"Pink",     "Beige"}),
    frozenset({"Hot Pink", "Black"}),
    frozenset({"Hot Pink", "White"}),
    frozenset({"Coral",    "White"}),
    frozenset({"Coral",    "Navy"}),
    frozenset({"Coral",    "Beige"}),
    frozenset({"Red",      "Black"}),
    frozenset({"Red",      "White"}),
    frozenset({"Red",      "Navy"}),
    frozenset({"Red",      "Gray"}),
    frozenset({"Crimson",  "Black"}),
    frozenset({"Crimson",  "White"}),
    frozenset({"Crimson",  "Gray"}),
    frozenset({"Maroon",   "Beige"}),
    frozenset({"Maroon",   "Khaki"}),
    frozenset({"Maroon",   "Gray"}),
    frozenset({"Maroon",   "White"}),
    # ---- Purples ----
    frozenset({"Purple",   "Gray"}),
    frozenset({"Purple",   "White"}),
    frozenset({"Purple",   "Black"}),
    frozenset({"Purple",   "Beige"}),
    frozenset({"Violet",   "Gray"}),
    frozenset({"Violet",   "White"}),
    frozenset({"Indigo",   "White"}),
    frozenset({"Indigo",   "Gray"}),
    frozenset({"Lavender", "White"}),
    frozenset({"Lavender", "Gray"}),
    frozenset({"Lavender", "Beige"}),
    # ---- Yellows / Gold / Orange ----
    frozenset({"Yellow",   "Black"}),
    frozenset({"Yellow",   "Navy"}),
    frozenset({"Yellow",   "Gray"}),
    frozenset({"Gold",     "Navy"}),
    frozenset({"Gold",     "Black"}),
    frozenset({"Gold",     "Brown"}),
    frozenset({"Gold",     "White"}),
    frozenset({"Orange",   "Navy"}),
    frozenset({"Orange",   "White"}),
    frozenset({"Orange",   "Gray"}),
    frozenset({"Orange",   "Black"}),
}

# Colors that pair harmoniously with virtually everything
_NEUTRAL_COLORS: set[str] = {
    "Black", "White", "Gray", "Silver", "Charcoal",
    "Beige", "Tan", "Khaki", "Navy",
}

# ---------------------------------------------------------------------------
# Occasion compatibility matrix
# Maps occasion → ideal styles AND clothing types
# ---------------------------------------------------------------------------
_OCCASION_STYLE_FIT: dict[str, list[str]] = {
    "College":   ["Casual", "Streetwear", "Sporty"],
    "Office":    ["Formal", "Business", "Casual"],
    "Casual":    ["Casual", "Streetwear", "Sporty", "Vintage"],
    "Party":     ["Party", "Streetwear", "Ethnic"],
    "Interview": ["Formal", "Business"],
    "Wedding":   ["Formal", "Ethnic", "Party"],
    "Gym":       ["Sporty"],
    "Date":      ["Casual", "Party", "Formal"],
}

# Clothing types that are clearly inappropriate for an occasion
_OCCASION_BAD_TYPES: dict[str, set[str]] = {
    "Gym":       {"Heels", "Oxford", "Blazer", "Evening Gown", "Maxi Dress", "Casual Dress"},
    "Interview": {"Sneakers", "Sandals", "T-Shirt", "Tank Top", "Crop Top", "Shorts"},
    "Wedding":   {"Sneakers", "Shorts", "Tank Top", "Crop Top"},
    "Office":    {"Shorts", "Tank Top", "Crop Top", "Sneakers"},
}

# ---------------------------------------------------------------------------
# Season compatibility matrix
# ---------------------------------------------------------------------------
_SEASON_COMPAT: dict[str, set[str]] = {
    "Summer":      {"Summer", "All Seasons"},
    "Rainy":       {"Rainy", "All Seasons"},
    "Winter":      {"Winter", "All Seasons"},
    "All Seasons": {"Summer", "Rainy", "Winter", "All Seasons", "Spring/Fall"},
    "Spring/Fall": {"Spring/Fall", "All Seasons"},
}


# ---------------------------------------------------------------------------
# Sub-scorers (each returns 0.0 – 1.0)
# ---------------------------------------------------------------------------

def _color_score(items: list) -> float:
    """Score color harmony across all items (0–1)."""
    colors = [getattr(i, "color", "Black") or "Black" for i in items]
    if len(colors) <= 1:
        return 1.0

    non_neutrals = [c for c in colors if c not in _NEUTRAL_COLORS]

    # All neutrals → perfect harmony
    if not non_neutrals:
        return 1.0

    # More than 2 bold (non-neutral) colors → clashing
    if len(non_neutrals) > 2:
        return 0.3

    harmonious = 0.0
    total_pairs = 0
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            total_pairs += 1
            ci, cj = colors[i], colors[j]
            pair = frozenset({ci, cj})
            if ci == cj:
                harmonious += 1.0                       # same color: monochrome
            elif pair in _HARMONIOUS_PAIRS:
                harmonious += 1.0                       # explicit harmony
            elif ci in _NEUTRAL_COLORS or cj in _NEUTRAL_COLORS:
                harmonious += 0.75                      # neutral pairs with anything

    return round(harmonious / total_pairs, 3) if total_pairs else 1.0


def _category_score(items: list) -> float:
    """Score category completeness — top + bottom (or dress) + shoes = perfect."""
    categories = {getattr(i, "category", "") for i in items}
    has_top    = bool(categories & {"Tops", "Dresses", "Outerwear"})
    has_bottom = bool(categories & {"Bottoms", "Dresses"})
    has_shoes  = "Shoes" in categories

    score = 0.0
    if has_top:    score += 0.40
    if has_bottom: score += 0.40
    if has_shoes:  score += 0.20
    return score


def _occasion_score(items: list, occasion: Optional[str]) -> float:
    """Score how well items match the target occasion using style AND clothing_type."""
    if not occasion:
        return 0.7  # neutral when no occasion selected

    ideal_styles = set(_OCCASION_STYLE_FIT.get(occasion, ["Casual"]))
    bad_types    = _OCCASION_BAD_TYPES.get(occasion, set())

    style_matches = 0
    type_penalties = 0

    for item in items:
        item_style = getattr(item, "style", "Casual") or "Casual"
        item_type  = getattr(item, "clothing_type", "") or ""

        if item_style in ideal_styles:
            style_matches += 1
        if item_type and item_type in bad_types:
            type_penalties += 1

    style_ratio = style_matches / len(items) if items else 0.5

    # Each inappropriate clothing_type deducts 0.2 (capped at full penalty)
    penalty = min(1.0, type_penalties * 0.20)
    return round(max(0.0, style_ratio - penalty), 3)


def _season_score(items: list, season: Optional[str]) -> float:
    """Score seasonal appropriateness of items."""
    if not season:
        return 0.7

    compat      = _SEASON_COMPAT.get(season, {"All Seasons"})
    item_seasons = [getattr(i, "season", "All Seasons") or "All Seasons" for i in items]
    matches     = sum(1 for s in item_seasons if s in compat)
    return round(matches / len(item_seasons), 3) if item_seasons else 0.5


def _color_in_set(color_val: str, color_hex: str, target_set: set[str]) -> bool:
    """Helper to check if an item's color or hex matches any target in target_set."""
    if not color_val and not color_hex:
        return False
    from app.utils.colors import resolve_color_hex
    norm_val = (color_val or "").strip().lower()
    norm_hex = (color_hex or resolve_color_hex(color_val)).strip().lower()

    for target in target_set:
        t_clean = target.strip().lower()
        if t_clean == norm_val or t_clean == norm_hex:
            return True
        t_hex = resolve_color_hex(t_clean).strip().lower()
        if t_hex == norm_hex or t_hex == norm_val:
            return True
    return False


def _preference_score(items: list, user_prefs, occasion: Optional[str] = None) -> float:
    """
    Boost score for items matching user's preferred colors, styles, occasions,
    and seasons. Penalise disliked colors.
    Respects master switch use_preferences and individual category toggles:
    use_color, use_style, use_occasion, use_season, use_fit_preference.
    """
    if not user_prefs or not getattr(user_prefs, "use_preferences", True):
        return 0.5

    # Category toggles
    use_color     = getattr(user_prefs, "use_color", True)
    use_style     = getattr(user_prefs, "use_style", True)
    use_occasion  = getattr(user_prefs, "use_occasion", True)
    use_season    = getattr(user_prefs, "use_season", True)
    use_fit       = getattr(user_prefs, "use_fit_preference", False)

    preferred_colors    = set(user_prefs.preferred_colors_list) if use_color else set()
    disliked_colors     = set(user_prefs.disliked_colors_list) if use_color else set()
    preferred_styles    = set(user_prefs.preferred_styles_list) if use_style else set()
    preferred_occasions = set(getattr(user_prefs, "preferred_occasions_list", []) or []) if use_occasion else set()
    preferred_seasons   = set(getattr(user_prefs, "preferred_seasons_list", []) or []) if use_season else set()

    score = 0.5

    # Check occasion match
    if use_occasion and occasion and preferred_occasions:
        occ_clean = occasion.strip().lower()
        if any(po.strip().lower() == occ_clean for po in preferred_occasions):
            score += 0.08

    # Check fit preference match
    fit_pref = (getattr(user_prefs, "fit_preference", "") or "").strip().lower() if use_fit else ""

    for item in items:
        color  = getattr(item, "color", "") or ""
        color_hex = getattr(item, "detected_color_hex", "") or ""
        style  = (getattr(item, "style", "") or "").strip().lower()
        season = (getattr(item, "season", "") or "").strip().lower()
        clothing_type = (getattr(item, "clothing_type", "") or "").strip().lower()
        notes = (getattr(item, "notes", "") or "").strip().lower()

        # Preferred color bonus
        if preferred_colors and _color_in_set(color, color_hex, preferred_colors):
            score += 0.12

        # Disliked color penalty
        if disliked_colors and _color_in_set(color, color_hex, disliked_colors):
            score -= 0.25

        # Preferred style bonus
        if preferred_styles and any(ps.strip().lower() in style or style in ps.strip().lower() for ps in preferred_styles):
            score += 0.10

        # Preferred season bonus
        if preferred_seasons and any(ss.strip().lower() == season for ss in preferred_seasons):
            score += 0.06

        # Fit preference bonus
        if fit_pref and (fit_pref in clothing_type or fit_pref in notes):
            score += 0.05

    return round(max(0.0, min(1.0, score)), 3)


def _novelty_score(items: list) -> float:
    """
    Prefer items the user hasn't worn much yet.
    wear_count = 0  → 1.0 (brand new, highest novelty)
    wear_count = 5  → 0.67
    wear_count = 10 → 0.5
    wear_count = 20+→ approaching 0.33
    Formula: 1 / (1 + wear_count/10)
    """
    if not items:
        return 0.5
    scores = []
    for item in items:
        wc = getattr(item, "wear_count", 0) or 0
        scores.append(1.0 / (1.0 + wc / 10.0))
    return round(sum(scores) / len(scores), 3)


def _favourite_score(items: list) -> float:
    """
    Boost outfits that contain at least one of the user's favourite items.
    No favourites → 0.5 (neutral).
    One favourite → 0.8.
    All favourites → 1.0.
    """
    if not items:
        return 0.5
    favs = sum(1 for i in items if getattr(i, "is_favorite", False))
    if favs == 0:
        return 0.5
    return round(0.5 + 0.5 * (favs / len(items)), 3)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate(
    items: list,
    occasion: Optional[str] = None,
    season:   Optional[str] = None,
    user_prefs=None,
) -> dict:
    """
    Calculate the compatibility score for an outfit.

    Parameters
    ----------
    items       : list of ClothingItem ORM objects
    occasion    : selected occasion string or None
    season      : selected season string or None
    user_prefs  : UserPreferences ORM object or None

    Returns
    -------
    dict:
        total      : float   0–100  (the headline score)
        color      : float   0–1    (raw color harmony sub-score)
        category   : float   0–1
        occasion   : float   0–1
        season     : float   0–1
        preference : float   0–1
        novelty    : float   0–1
        favourite  : float   0–1
    """
    if not items:
        return {
            "total": 0.0, "color": 0.0, "category": 0.0,
            "occasion": 0.0, "season": 0.0, "preference": 0.0,
            "novelty": 0.0, "favourite": 0.0,
        }

    color  = _color_score(items)
    cat    = _category_score(items)
    occ    = _occasion_score(items, occasion)
    seas   = _season_score(items, season)
    pref   = _preference_score(items, user_prefs, occasion)
    nov    = _novelty_score(items)
    fav    = _favourite_score(items)

    # Weighted sum — weights must total 1.0
    raw = (
        color  * 0.25 +
        cat    * 0.20 +
        occ    * 0.20 +
        seas   * 0.15 +
        pref   * 0.12 +
        nov    * 0.05 +
        fav    * 0.03
    ) * 100

    total = round(min(100.0, max(0.0, raw)), 1)

    return {
        "total":      total,
        "color":      color,
        "category":   cat,
        "occasion":   occ,
        "season":     seas,
        "preference": pref,
        "novelty":    nov,
        "favourite":  fav,
    }
