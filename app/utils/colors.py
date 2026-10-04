"""Color utility module for mapping fashion color names to hex codes."""

import re

# Comprehensive mapping of fashion and everyday color names to hex values
COLOR_NAME_TO_HEX: dict[str, str] = {
    # Whites & Creams
    "white": "#FFFFFF",
    "off white": "#FAF9F6",
    "off-white": "#FAF9F6",
    "offwhite": "#FAF9F6",
    "cream": "#FFFDD0",
    "ivory": "#FFFFF0",
    "ivory white": "#FFFFF0",
    "beige": "#F5F5DC",
    "vanilla": "#F3E5AB",
    "alabaster": "#F2F0EB",
    "eggshell": "#F0EAD6",
    "pearl": "#EAE0C8",
    "bone": "#E3DAC9",

    # Grays & Blacks
    "black": "#111111",
    "charcoal": "#36454F",
    "charcoal gray": "#36454F",
    "charcoal grey": "#36454F",
    "gray": "#808080",
    "grey": "#808080",
    "light gray": "#D3D3D3",
    "light grey": "#D3D3D3",
    "dark gray": "#505050",
    "dark grey": "#505050",
    "slate": "#708090",
    "slate gray": "#708090",
    "silver": "#C0C0C0",
    "graphite": "#383838",
    "ash": "#B2BEB5",

    # Pinks & Magentas
    "rani pink": "#E0218A",
    "rani": "#E0218A",
    "hot pink": "#FF69B4",
    "pink": "#FFC0CB",
    "baby pink": "#F4C2C2",
    "blush": "#DE5D83",
    "blush pink": "#FFD1DC",
    "rose": "#FF007F",
    "dusty rose": "#DCAE96",
    "rose gold": "#B76E79",
    "magenta": "#FF00FF",
    "fuchsia": "#FF00FF",
    "bubblegum": "#FFC1CC",
    "salmon": "#FA8072",
    "coral": "#FF7F50",
    "peach": "#FFCBA4",

    # Reds, Wines & Earth Tones
    "red": "#E53935",
    "cherry red": "#FF2400",
    "crimson": "#DC143C",
    "ruby": "#E0115F",
    "wine": "#722F37",
    "maroon": "#800000",
    "burgundy": "#800020",
    "bordeaux": "#5C0120",
    "rust": "#B7410E",
    "terracotta": "#E2725B",
    "brick red": "#CB4154",
    "oxblood": "#4A0000",

    # Yellows, Oranges & Browns
    "orange": "#FB8C00",
    "tangerine": "#F28500",
    "yellow": "#FDD835",
    "mustard": "#E1AD01",
    "mustard yellow": "#E1AD01",
    "gold": "#FFD700",
    "golden": "#FFD700",
    "amber": "#FFBF00",
    "tan": "#D2B48C",
    "khaki": "#C3B091",
    "camel": "#C19A6B",
    "caramel": "#AF6E4D",
    "brown": "#8B4513",
    "coffee": "#6F4E37",
    "chocolate": "#3D1C02",
    "taupe": "#483C32",
    "sand": "#C2B280",
    "mocha": "#967969",
    "cinnamon": "#D2691E",

    # Greens
    "olive": "#808000",
    "olive green": "#556B2F",
    "sage": "#9DC183",
    "sage green": "#87A96B",
    "mint": "#98FF98",
    "mint green": "#98FB98",
    "green": "#43A047",
    "dark green": "#006400",
    "forest green": "#228B22",
    "bottle green": "#006A4E",
    "emerald": "#50C878",
    "emerald green": "#50C878",
    "lime": "#32CD32",
    "lime green": "#32CD32",
    "seafoam": "#93E9BE",
    "pistachio": "#93C572",
    "moss green": "#8A9A5B",

    # Blues & Teals
    "blue": "#1E88E5",
    "navy": "#000080",
    "navy blue": "#000080",
    "midnight blue": "#191970",
    "royal blue": "#4169E1",
    "sky blue": "#87CEEB",
    "baby blue": "#89CFF0",
    "light blue": "#ADD8E6",
    "ice blue": "#D0F0FD",
    "steel blue": "#4682B4",
    "powder blue": "#B0E0E6",
    "cobalt": "#0047AB",
    "cobalt blue": "#0047AB",
    "denim": "#4A777A",
    "indigo": "#4B0082",
    "teal": "#008080",
    "turquoise": "#40E0D0",
    "cyan": "#00BCD4",
    "aqua": "#00FFFF",
    "cerulean": "#007BA7",

    # Purples & Violets
    "purple": "#8E24AA",
    "violet": "#8B2BE2",
    "lavender": "#E6E6FA",
    "lilac": "#C8A2C8",
    "mauve": "#E0B0FF",
    "plum": "#DDA0DD",
    "periwinkle": "#CCCCFF",
    "aubergine": "#3D0734",
    "eggplant": "#614051",

    # Metallics & Patterns
    "bronze": "#CD7F32",
    "copper": "#B87333",
    "multicolor": "#7C6A96",
    "multi": "#7C6A96",
    "print": "#7C6A96",
    "pattern": "#7C6A96",
}


def resolve_color_hex(color_name: str | None, sample_hex: str | None = None) -> str:
    """Resolve a color string to a valid CSS hex code.

    Args:
        color_name: Name of color (e.g. 'rani pink', 'Charcoal', 'Off White', '#FF0000').
        sample_hex: Optional fallback hex code (e.g. from item.detected_color_hex).

    Returns:
        A 7-character hex string (e.g. '#E0218A').
    """
    if not color_name:
        if sample_hex and sample_hex.startswith("#") and len(sample_hex) in (4, 7, 9):
            return sample_hex
        return "#808080"

    cleaned = color_name.strip()

    # If it's already a valid hex string
    if cleaned.startswith("#") and len(cleaned) in (4, 7, 9):
        return cleaned

    lower = cleaned.lower()

    # Exact match in lookup table
    if lower in COLOR_NAME_TO_HEX:
        return COLOR_NAME_TO_HEX[lower]

    # Normalized match (replace hyphens and punctuation)
    norm = re.sub(r"[^\w\s]", " ", lower).strip()
    norm = re.sub(r"\s+", " ", norm)
    if norm in COLOR_NAME_TO_HEX:
        return COLOR_NAME_TO_HEX[norm]

    # Substring match (e.g. "dark charcoal" -> "charcoal", "vibrant rani pink" -> "rani pink")
    for key, hex_val in COLOR_NAME_TO_HEX.items():
        if f" {key} " in f" {norm} ":
            return hex_val

    # If item has a detected_color_hex, use that
    if sample_hex and sample_hex.startswith("#") and len(sample_hex) in (4, 7, 9):
        return sample_hex

    return "#808080"
