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

# Nearest-color lookup table (CSS named colors → hex)
_COLOR_MAP: list[tuple[tuple[int, int, int], str, str]] = [
    # Neutrals
    ((0,   0,   0),   "#000000", "Black"),
    ((255, 255, 255), "#FFFFFF", "White"),
    ((128, 128, 128), "#808080", "Gray"),
    ((192, 192, 192), "#C0C0C0", "Silver"),
    ((64,   64,  64), "#404040", "Charcoal"),
    # Browns & earth tones
    ((165,  42,  42), "#A52A2A", "Brown"),
    ((210, 180, 140), "#D2B48C", "Tan"),
    ((245, 245, 220), "#F5F5DC", "Beige"),
    ((128, 128,   0), "#808000", "Olive"),
    ((240, 230, 140), "#F0E68C", "Khaki"),
    # Reds & pinks
    ((255,   0,   0), "#FF0000", "Red"),
    ((220,  20,  60), "#DC143C", "Crimson"),
    ((255, 192, 203), "#FFC0CB", "Pink"),
    ((255, 105, 180), "#FF69B4", "Hot Pink"),
    ((255, 127, 80),  "#FF7F50", "Coral"),
    # Oranges & yellows
    ((255, 165,   0), "#FFA500", "Orange"),
    ((255, 215,   0), "#FFD700", "Gold"),
    ((255, 255,   0), "#FFFF00", "Yellow"),
    # Greens — full range from lime to dark
    ((200, 240, 140), "#C8F08C", "Lime"),           # high-brightness lime/neon green (e.g. sports t-shirts)
    ((173, 255,  47), "#ADFF2F", "Green Yellow"),
    ((50,  205,  50), "#32CD32", "Lime Green"),
    ((154, 205,  50), "#9ACD32", "Yellow Green"),
    ((124, 252,   0), "#7CFC00", "Lawn Green"),
    ((144, 238, 144), "#90EE90", "Light Green"),
    ((0,   255,   0), "#00FF00", "Green"),
    ((0,   128,   0), "#008000", "Dark Green"),
    ((0,   128, 128), "#008080", "Teal"),
    ((64,  224, 208), "#40E0D0", "Turquoise"),
    ((152, 251, 152), "#98FB98", "Pale Green"),
    ((0,   255, 127), "#00FF7F", "Mint"),
    # Blues
    ((0,   255, 255), "#00FFFF", "Cyan"),
    ((173, 216, 230), "#ADD8E6", "Light Blue"),
    ((30,  144, 255), "#1E90FF", "Dodger Blue"),
    ((0,     0, 255), "#0000FF", "Blue"),
    ((0,     0, 128), "#000080", "Navy"),
    ((70,  130, 180), "#4682B4", "Steel Blue"),
    # Purples
    ((128,   0, 128), "#800080", "Purple"),
    ((75,    0, 130), "#4B0082", "Indigo"),
    ((138,  43, 226), "#8B2BE2", "Violet"),
    ((216, 191, 216), "#D8BFD8", "Lavender"),
    ((139,   0,   0), "#8B0000", "Maroon"),
]


def _nearest_color(r: int, g: int, b: int) -> tuple[str, str]:
    """Return (hex_code, color_name) for the closest entry in _COLOR_MAP."""
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
        # Step 2: Background pixel mask
        # Removes near-white AND mid-gray low-saturation pixels.
        # ------------------------------------------------------------------
        norm       = pixels / 255.0
        brightness = norm.max(axis=1)                       # V  (0-1)
        saturation = norm.max(axis=1) - norm.min(axis=1)   # S  (0-1, unnormalised)

        # Tight threshold: catches white, off-white, AND gray studio backdrops
        fg_mask    = ~((brightness > 0.70) & (saturation < 0.12))
        foreground = pixels[fg_mask]

        # Fallback 1: relax thresholds slightly if too few pixels survive
        if len(foreground) < 200:
            fg_mask    = ~((brightness > 0.80) & (saturation < 0.18))
            foreground = pixels[fg_mask]

        # Fallback 2: use all cropped pixels (background removal skipped)
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
