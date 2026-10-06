"""
Color Detector Service
======================
Extracts the dominant color from a clothing image using:
  - Pillow for image loading
  - NumPy for array conversion
  - scikit-learn KMeans for dominant cluster extraction

Gracefully returns None on any error so image upload always succeeds.
"""

from __future__ import annotations

import os
from typing import Optional
import colorsys

# Nearest-color lookup table (CSS named colors → hex)
_COLOR_MAP: list[tuple[tuple[int, int, int], str, str]] = [
    # Neutrals
    ((0,   0,   0),   "#000000", "Black"),
    ((255, 255, 255), "#FFFFFF", "White"),
    ((128, 128, 128), "#808080", "Gray"),
    ((192, 192, 192), "#C0C0C0", "Silver"),
    ((64,   64,  64), "#404040", "Charcoal"),
    ((245, 245, 245), "#F5F5F5", "Off White"),
    ((255, 250, 240), "#FFFAF0", "Cream"),
    # Browns & earth tones
    ((165,  42,  42), "#A52A2A", "Brown"),
    ((210, 180, 140), "#D2B48C", "Tan"),
    ((245, 245, 220), "#F5F5DC", "Beige"),
    ((128, 128,   0), "#808000", "Olive"),
    ((240, 230, 140), "#F0E68C", "Khaki"),
    # Reds & pinks
    ((255,   0,   0), "#FF0000", "Red"),
    ((255,  36,   0), "#FF2400", "Cherry Red"),
    ((220,  20,  60), "#DC143C", "Crimson"),
    ((255, 192, 203), "#FFC0CB", "Pink"),
    ((255, 105, 180), "#FF69B4", "Hot Pink"),
    ((255, 127,  80), "#FF7F50", "Coral"),
    ((128,   0,   0), "#800000", "Maroon"),
    # Oranges & yellows
    ((255, 165,   0), "#FFA500", "Orange"),
    ((255, 215,   0), "#FFD700", "Gold"),
    ((255, 255,   0), "#FFFF00", "Yellow"),
    # Greens — full range
    ((0, 255,   0), "#00FF00", "Green"),
    ((0, 128,   0), "#008000", "Dark Green"),
    ((173, 255,  47), "#ADFF2F", "Green Yellow"),
    # Blues
    ((0,   0, 255), "#0000FF", "Blue"),
    ((0,   0, 128), "#000080", "Navy Blue"),
    ((70, 130, 180), "#4682B4", "Steel Blue"),
    # Purples
    ((128,   0, 128), "#800080", "Purple"),
    ((138,  43, 226), "#8B2BE2", "Violet"),
    ((216, 191, 216), "#D8BFD8", "Lavender"),
    # Additional colors can be added as needed
]


def _nearest_color(r: int, g: int, b: int) -> tuple[str, str]:
    """Return (hex_code, color_name) for the given RGB.

    Uses HSV thresholds for neutrals and hue-angle rules for the red family
    before falling back to Euclidean distance against the canonical _COLOR_MAP.

    Neutral ladder (saturation < 0.15):
        v >= 0.97  → White
        v >= 0.78  → Off White   (was incorrectly hitting Silver at v>0.75)
        v >= 0.60  → Silver
        v >= 0.32  → Gray
        v >= 0.12  → Charcoal
        else       → Black

    Red family (hue near 0°/360°, saturation >= 0.40):
        h ∈ [5°, 20°]  → Cherry Red
        v < 0.55       → Maroon
        else           → Red
    """
    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(rn, gn, bn)
    h_deg = h * 360.0

    # ------------------------------------------------------------------
    # Neutral ladder  (low saturation → achromatic)
    # ------------------------------------------------------------------
    if s < 0.15:
        if v >= 0.97:
            return "#FFFFFF", "White"
        elif v >= 0.78:
            return "#F5F5F5", "Off White"
        elif v >= 0.60:
            return "#C0C0C0", "Silver"
        elif v >= 0.32:
            return "#808080", "Gray"
        elif v >= 0.12:
            return "#404040", "Charcoal"
        else:
            return "#000000", "Black"

    # ------------------------------------------------------------------
    # Red / Brown family  (hue wraps around 0°/360°)
    # ------------------------------------------------------------------
    if (h_deg <= 20 or h_deg >= 345) and s >= 0.35:
        # Brown: same hue angle as red but lower saturation + mid value
        # e.g. RGB(165,42,42) → H=0°, S=0.75, V=0.65
        if s < 0.82 and 0.35 <= v <= 0.72:
            return "#A52A2A", "Brown"
        if v < 0.55:
            return "#800000", "Maroon"
        elif 5 <= h_deg <= 20:
            return "#FF2400", "Cherry Red"
        else:
            return "#FF0000", "Red"

    # ------------------------------------------------------------------
    # Yellow / Gold / Olive family  (hue around 40°–68°)
    # ------------------------------------------------------------------
    if 40 <= h_deg <= 68 and s >= 0.18:
        if v >= 0.70:
            return "#FFFF00", "Yellow"
        elif v >= 0.40:
            return "#808000", "Olive"

    # ------------------------------------------------------------------
    # Green family  (hue around 75°–165°)
    # ------------------------------------------------------------------
    if 75 <= h_deg <= 165 and s >= 0.20:
        if v < 0.45 or g < 90:
            return "#008000", "Dark Green"
        else:
            return "#00FF00", "Green"

    # ------------------------------------------------------------------
    # Blue / Navy Blue family  (hue around 190°–255°)
    # ------------------------------------------------------------------
    if 190 <= h_deg <= 255 and s >= 0.25:
        if v < 0.55:
            return "#000080", "Navy Blue"
        else:
            return "#0000FF", "Blue"

    # ------------------------------------------------------------------
    # Fallback: nearest Euclidean distance in RGB space
    # ------------------------------------------------------------------
    best_dist = float("inf")
    best_hex, best_name = "#000000", "Black"
    for (cr, cg, cb), hex_code, name in _COLOR_MAP:
        dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_hex = hex_code
            best_name = name
    return best_hex, best_name


def extract_color(image_path: str, n_clusters: int = 3) -> Optional[dict]:
    """
    Analyse a saved image file and return its dominant color.

    Parameters
    ----------
    image_path : str
        Absolute or relative path to the saved image file.
    n_clusters : int
        Number of K-Means clusters to use (default 3).

    Returns
    -------
    dict with keys: hex, name, rgb  — or None on failure.

    Strategy
    --------
    Two-step foreground extraction applied before K-Means:

    Step 1 — Center crop (60% of width and height):
        Product and model images concentrate the garment in the center.
        Cropping to the central 60% discards peripheral background, edges,
        and in model shots it also removes most face/hair pixels at the top.

    Step 2 — Background pixel mask:
        Removes pixels that are near-white, off-white, or mid-gray studio
        backgrounds.  A pixel is classified as background when:
            brightness  > 0.70   (V = max(R,G,B) / 255)
          AND
            saturation  < 0.12   (S = (max-min) / 255  — unnormalised)
        This threshold is tighter than before (was 0.88 / 0.15) so that
        gray studio backdrops (~190,190,190) are also caught.

    If fewer than 200 foreground pixels survive both steps, we progressively
    fall back: first relax the mask thresholds, then use the full image, so
    we always return a result.
    """
    if not image_path or not os.path.isfile(image_path):
        return None

    try:
        from PIL import Image
        import numpy as np
        from sklearn.cluster import KMeans

        img = Image.open(image_path).convert("RGB")

        # ------------------------------------------------------------------
        # Step 1: Center crop — keep the central 60% of width AND height
        # ------------------------------------------------------------------
        w, h = img.size
        left   = int(w * 0.20)
        right  = int(w * 0.80)
        top    = int(h * 0.20)
        bottom = int(h * 0.80)
        img_crop = img.crop((left, top, right, bottom))

        # Resize the crop to a fixed size for consistent K-Means speed
        img_crop = img_crop.resize((120, 120))
        pixels = np.array(img_crop).reshape(-1, 3).astype(np.float32)

        # ------------------------------------------------------------------
        # Step 2: Dynamic border-based background subtraction
        #
        # Sample the outermost 5 % of pixels on three sides of the FULL image
        # to estimate the studio backdrop colour.  Then keep only crop pixels
        # whose Euclidean distance from that backdrop exceeds a threshold.
        #
        # This correctly handles white/off-white garments on white/light-gray
        # studio backdrops — the old static brightness mask would remove both
        # the backdrop AND the light garment, leaving only shadow pixels which
        # then mapped to Tan/Brown.
        # ------------------------------------------------------------------
        border_h = max(4, int(h * 0.05))
        border_w = max(4, int(w * 0.05))

        top_strip   = np.array(img.crop((0, 0, w, border_h))).reshape(-1, 3)
        left_strip  = np.array(img.crop((0, 0, border_w, h))).reshape(-1, 3)
        right_strip = np.array(img.crop((w - border_w, 0, w, h))).reshape(-1, 3)
        border_pix  = np.vstack([top_strip, left_strip, right_strip]).astype(np.float32)

        # Median backdrop colour — robust to logos / watermarks at edges
        bg_median = np.median(border_pix, axis=0)  # shape (3,)

        # Is the backdrop achromatic (white/gray studio)?
        bg_norm = bg_median / 255.0
        bg_sat  = float(bg_norm.max() - bg_norm.min())
        # Tighter threshold for neutral backdrops keeps light garments intact
        dist_threshold = 20 if bg_sat < 0.15 else 25

        dist_to_bg = np.linalg.norm(pixels - bg_median, axis=1)
        fg_mask    = dist_to_bg > dist_threshold
        foreground = pixels[fg_mask]

        # Fallback 1: relax threshold when garment/backdrop contrast is tiny
        if len(foreground) < 200:
            fg_mask    = dist_to_bg > (dist_threshold * 0.6)
            foreground = pixels[fg_mask]

        # Fallback 2: use all cropped pixels
        sample = foreground if len(foreground) >= 200 else pixels

        # ------------------------------------------------------------------
        # K-Means clustering on the foreground sample
        # ------------------------------------------------------------------
        km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        km.fit(sample)

        # Pick the largest cluster (most foreground pixels)
        counts       = np.bincount(km.labels_)
        dominant_idx = int(counts.argmax())
        r, g, b      = [int(v) for v in km.cluster_centers_[dominant_idx]]

        hex_code, color_name = _nearest_color(r, g, b)
        return {"hex": hex_code, "name": color_name, "rgb": (r, g, b)}

    except Exception:
        return None


def extract_color_from_url(image_url: str) -> Optional[dict]:
    """
    Download an image from a URL and extract its dominant color.
    Returns None if URL is unreachable or processing fails.
    """
    if not image_url:
        return None
    try:
        import urllib.request
        import tempfile

        suffix = ".jpg"
        for ext in (".png", ".webp", ".gif", ".jpeg"):
            if image_url.lower().split("?")[0].endswith(ext):
                suffix = ext
                break

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name

        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(image_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            with open(tmp_path, "wb") as f:
                f.write(resp.read())

        result = extract_color(tmp_path)
        os.unlink(tmp_path)
        return result
    except Exception:
        return None
