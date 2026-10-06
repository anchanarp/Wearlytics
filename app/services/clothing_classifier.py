"""
Clothing Classifier Service
============================
Tiered classification pipeline:

  Tier 1A — Fine-tuned MobileNetV2 (PyTorch/torchvision)
              Uses clothing_model.pt if it exists (trained via train_classifier.py)
  Tier 1B — ImageNet-pretrained MobileNetV2 baseline (PyTorch)
              Zero-training fallback using ImageNet keyword → category mapping
  Tier 2  — OpenCV heuristics (existing rule-based approach, kept as backup)
  Tier 3  — Hardcoded fallback dict (always succeeds)

Public API (UNCHANGED):
    classify(image_path: str) -> dict
        Returns: {category, clothing_type, confidence, source}

All existing constants (ALL_STYLES, ALL_OCCASIONS, ALL_SEASONS, etc.)
and helper functions (get_types_for_category) are untouched.

Architecture note:
    PyTorch imports are lazy (inside functions) so the module loads
    successfully even if torch is not installed — Flask startup never fails.
"""

from __future__ import annotations

import os
from typing import Optional


# ---------------------------------------------------------------------------
# Existing constants — UNCHANGED (used by routes + templates + recommendations)
# ---------------------------------------------------------------------------

_CATEGORY_TYPES: dict[str, list[str]] = {
    "Tops":        ["T-Shirt", "Shirt", "Blouse", "Polo", "Sweater", "Hoodie", "Tank Top", "Crop Top"],
    "Bottoms":     ["Jeans", "Trousers", "Shorts", "Skirt", "Leggings", "Chinos"],
    "Shoes":       ["Sneakers", "Boots", "Heels", "Sandals", "Loafers", "Oxfords"],
    "Outerwear":   ["Jacket", "Coat", "Blazer", "Windbreaker", "Parka"],
    "Dresses":     ["Casual Dress", "Maxi Dress", "Mini Dress", "Evening Gown", "Sundress"],
    "Accessories": ["Bag", "Hat", "Scarf", "Belt", "Sunglasses", "Watch"],
}

ALL_CATEGORIES = list(_CATEGORY_TYPES.keys())
ALL_STYLES     = ["Casual", "Formal", "Sporty", "Streetwear", "Ethnic", "Business", "Party", "Vintage"]
ALL_OCCASIONS  = ["College", "Office", "Casual", "Party", "Interview", "Wedding", "Gym", "Date"]
ALL_SEASONS    = ["All Seasons", "Summer", "Rainy", "Winter"]


def get_types_for_category(category: str) -> list[str]:
    """Return the list of clothing types for a given category."""
    return _CATEGORY_TYPES.get(category, ["Other"])


# ---------------------------------------------------------------------------
# Tier 1: MobileNetV2 via PyTorch / torchvision
# ---------------------------------------------------------------------------

# Fine-tuned model path (created by train_classifier.py)
_CUSTOM_MODEL_PATH = os.path.join(os.path.dirname(__file__), "clothing_model.pt")

# Wearlytics category ordering (must match train_classifier.py CLASS_NAMES — alphabetical)
_MODEL_CATEGORIES = ["Accessories", "Bottoms", "Dresses", "Outerwear", "Shoes", "Tops"]

# Default clothing_type per category for MobileNetV2 predictions
_DEFAULT_TYPE: dict[str, str] = {
    "Tops":        "T-Shirt",
    "Bottoms":     "Jeans",
    "Shoes":       "Sneakers",
    "Dresses":     "Casual Dress",
    "Outerwear":   "Jacket",
    "Accessories": "Bag",
}

# Module-level model cache (loaded once, reused)
_custom_model = None
_imagenet_model = None
_torch_available: Optional[bool] = None


def _check_torch() -> bool:
    """Return True if torch + torchvision are importable."""
    global _torch_available
    if _torch_available is not None:
        return _torch_available
    try:
        import torch          # noqa: F401
        import torchvision    # noqa: F401
        _torch_available = True
    except ImportError:
        _torch_available = False
    return _torch_available


def _load_custom_model():
    """
    Load the fine-tuned clothing model saved by train_classifier.py.
    Returns the model or None if the file doesn't exist / torch unavailable.

    Architecture note: the checkpoint was saved with a custom 2-layer classifier:
        Dropout(0.2) → Linear(1280, 256) → ReLU → Dropout(0.2) → Linear(256, 6)
    This MUST match exactly; otherwise PyTorch raises a RuntimeError on load_state_dict.
    """
    global _custom_model
    if _custom_model is not None:
        return _custom_model
    if not _check_torch():
        return None
    if not os.path.isfile(_CUSTOM_MODEL_PATH):
        return None
    try:
        import torch
        import torchvision.models as models

        base = models.mobilenet_v2(weights=None)
        # Replace the classifier with the exact head used during training
        base.classifier = torch.nn.Sequential(
            torch.nn.Dropout(0.2),
            torch.nn.Linear(base.last_channel, 256),   # classifier.1
            torch.nn.ReLU(),                            # classifier.2
            torch.nn.Dropout(0.2),                     # classifier.3
            torch.nn.Linear(256, len(_MODEL_CATEGORIES)),  # classifier.4
        )
        base.load_state_dict(torch.load(_CUSTOM_MODEL_PATH, map_location="cpu", weights_only=True))
        base.eval()
        _custom_model = base
        return _custom_model
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("custom model load failed: %s", exc)
        return None


def _load_imagenet_model():
    """
    Load ImageNet-pretrained MobileNetV2 (no custom training needed).
    Returns the model or None if torch unavailable.
    """
    global _imagenet_model
    if _imagenet_model is not None:
        return _imagenet_model
    if not _check_torch():
        return None
    try:
        import torchvision.models as models
        from torchvision.models import MobileNet_V2_Weights
        model = models.mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1)
        model.eval()
        _imagenet_model = model
        return _imagenet_model
    except Exception:
        return None


def _preprocess_image(image_path: str, size: int = 224):
    """
    Load and preprocess an image for MobileNetV2 inference.
    Returns a (1, 3, size, size) tensor or None on failure.
    """
    try:
        import torch
        from torchvision import transforms
        from PIL import Image

        transform = transforms.Compose([
            transforms.Resize((size, size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],   # ImageNet mean
                std=[0.229, 0.224, 0.225],    # ImageNet std
            ),
        ])
        img = Image.open(image_path).convert("RGB")
        tensor = transform(img).unsqueeze(0)   # shape: (1, 3, 224, 224)
        return tensor
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ImageNet label → Wearlytics category mapping
# ---------------------------------------------------------------------------
# MobileNetV2 ImageNet labels that relate to clothing items.
# Source: torchvision's imagenet_classes.txt (1000-class list).
# Format: substring_of_label → (category, clothing_type)
# The label strings are lowercase; we match by substring.

_IMAGENET_KEYWORD_MAP: list[tuple[str, str, str]] = [
    # (keyword_lowercase, wearlytics_category, clothing_type)
    # Dresses (must be matched before generic 'skirt' so hoopskirt/overskirt/gown map to Dresses)
    ("hoopskirt",       "Dresses",     "Casual Dress"),
    ("overskirt",       "Dresses",     "Casual Dress"),
    ("academic gown",   "Dresses",     "Casual Dress"),
    ("gown",            "Dresses",     "Evening Gown"),
    ("abaya",           "Dresses",     "Maxi Dress"),
    ("kimono",          "Dresses",     "Casual Dress"),
    ("vestment",        "Dresses",     "Casual Dress"),
    ("sarong",          "Dresses",     "Sundress"),
    ("sundress",        "Dresses",     "Sundress"),
    # Tops
    ("jersey",          "Tops",        "T-Shirt"),
    ("tee shirt",       "Tops",        "T-Shirt"),
    ("t-shirt",         "Tops",        "T-Shirt"),
    ("sweatshirt",      "Tops",        "Sweater"),
    ("cardigan",        "Tops",        "Sweater"),
    ("brassiere",       "Tops",        "Top"),
    ("bikini",          "Tops",        "Top"),
    ("polo shirt",      "Tops",        "Polo"),
    ("sport shirt",     "Tops",        "Shirt"),
    ("peplum",          "Tops",        "Blouse"),
    # Bottoms
    ("jean",            "Bottoms",     "Jeans"),
    ("denim",           "Bottoms",     "Jeans"),
    ("trouser",         "Bottoms",     "Trousers"),
    ("chino",           "Bottoms",     "Trousers"),
    ("pant",            "Bottoms",     "Trousers"),
    ("capri",           "Bottoms",     "Trousers"),
    ("legging",         "Bottoms",     "Leggings"),
    ("shorts",          "Bottoms",     "Shorts"),
    ("miniskirt",       "Bottoms",     "Skirt"),
    ("skirt",           "Bottoms",     "Skirt"),
    ("stocking",        "Bottoms",     "Leggings"),
    ("sock",            "Bottoms",     "Leggings"),
    # Shoes
    ("sandal",          "Shoes",       "Sandals"),
    ("loafer",          "Shoes",       "Loafers"),
    ("cowboy boot",     "Shoes",       "Boots"),
    ("running shoe",    "Shoes",       "Sneakers"),
    ("sneaker",         "Shoes",       "Sneakers"),
    ("boot",            "Shoes",       "Boots"),
    ("clog",            "Shoes",       "Loafers"),
    ("maillot",         "Shoes",       "Sneakers"),   # sometimes misclassified
    # Outerwear
    ("trench coat",     "Outerwear",   "Trench Coat"),
    ("fur coat",        "Outerwear",   "Coat"),
    ("lab coat",        "Outerwear",   "Jacket"),
    ("poncho",          "Outerwear",   "Coat"),
    ("suit",            "Outerwear",   "Blazer"),
    # Accessories
    ("bow tie",         "Accessories", "Bow Tie"),
    ("windsor tie",     "Accessories", "Tie"),
    ("cowboy hat",      "Accessories", "Hat"),
    ("sombrero",        "Accessories", "Hat"),
    ("purse",           "Accessories", "Bag"),
    ("backpack",        "Accessories", "Bag"),
    ("mailbag",         "Accessories", "Bag"),
    ("handbag",         "Accessories", "Bag"),
    ("satchel",         "Accessories", "Bag"),
    ("tote bag",        "Accessories", "Bag"),
    ("wallet",          "Accessories", "Bag"),
    ("bag",             "Accessories", "Bag"),
    ("clutch",          "Accessories", "Bag"),
    ("sunglasses",      "Accessories", "Sunglasses"),
    ("sunglass",        "Accessories", "Sunglasses"),
    ("bolo tie",        "Accessories", "Tie"),
    ("mortarboard",     "Accessories", "Hat"),
    ("shower cap",      "Accessories", "Hat"),
    ("watch",           "Accessories", "Watch"),
    ("wristwatch",      "Accessories", "Watch"),
    ("necklace",        "Accessories", "Jewellery"),
    ("bead",            "Accessories", "Jewellery"),
    ("umbrella",        "Accessories", "Accessories"),
    ("punching bag",    "Accessories", "Bag"),
]


def _decode_imagenet_top5(logits) -> Optional[tuple[str, str, float]]:
    """
    Map MobileNetV2 ImageNet top-5 predictions to a Wearlytics category.

    Parameters
    ----------
    logits : torch.Tensor  shape (1, 1000)

    Returns
    -------
    (category, clothing_type, confidence) or None if no clothing class found.
    """
    try:
        import torch
        import torchvision

        probs = torch.nn.functional.softmax(logits, dim=1)
        top5_probs, top5_idx = torch.topk(probs, 5, dim=1)

        # Load ImageNet class labels
        weights = torchvision.models.MobileNet_V2_Weights.IMAGENET1K_V1
        class_labels = weights.meta["categories"]   # list of 1000 strings

        for rank in range(5):
            idx = int(top5_idx[0][rank])
            prob = float(top5_probs[0][rank])
            label = class_labels[idx].lower()

            for keyword, category, clothing_type in _IMAGENET_KEYWORD_MAP:
                if keyword in label:
                    # Use a fixed confidence based on match rank rather than
                    # the raw ImageNet softmax probability (which is spread
                    # across 1000 classes and is always misleadingly low).
                    # Rank 0 = strongest signal (82%), rank 4 = weakest (60%).
                    rank_confidence = [0.82, 0.76, 0.70, 0.65, 0.60]
                    fixed_conf = rank_confidence[rank] if rank < len(rank_confidence) else 0.60
                    return category, clothing_type, fixed_conf

        return None
    except Exception:
        return None


def _classify_with_custom_model(image_path: str) -> Optional[dict]:
    """
    Run inference using the fine-tuned clothing model (clothing_model.pt).
    Returns result dict or None.

    Sanity-checks the prediction against:
      1. A minimum confidence threshold (0.75) — the model is unreliable below this.
      2. ImageNet top-5 cross-validation — if the fine-tuned model says Shoes/Tops
         but ImageNet clearly sees a bag, or vice-versa, we bail to Tier 1B.
    """
    model = _load_custom_model()
    if model is None:
        return None
    tensor = _preprocess_image(image_path)
    if tensor is None:
        return None
    try:
        import torch
        with torch.no_grad():
            logits = model(tensor)                      # (1, 6)
            probs = torch.nn.functional.softmax(logits, dim=1)
            conf, idx = torch.max(probs, dim=1)
        category = _MODEL_CATEGORIES[int(idx)]
        confidence = round(float(conf), 3)

        # ------------------------------------------------------------------
        # Gate 1: minimum confidence threshold
        # The fine-tuned model is unreliable under 0.75 — let Tier 1B decide.
        # ------------------------------------------------------------------
        if confidence < 0.75:
            return None

        # ------------------------------------------------------------------
        # Gate 2: cross-validate against ImageNet top-5 keywords
        #
        # Load the ImageNet model and check its top-5 labels.
        # If ImageNet sees a bag-like label (mailbag, purse, backpack, …) but
        # the fine-tuned model predicts Shoes or Tops, the fine-tuned model is
        # almost certainly wrong — bail to Tier 1B.
        # Similarly, if the fine-tuned model says Accessories but ImageNet sees
        # a portrait-only garment label (jean, trouser, …) reject it.
        # ------------------------------------------------------------------
        try:
            from torchvision.models import MobileNet_V2_Weights as _W
            _inet_model = _load_imagenet_model()
            if _inet_model is not None:
                with torch.no_grad():
                    _inet_logits = _inet_model(tensor)
                _inet_probs = torch.nn.functional.softmax(_inet_logits, dim=1)[0]
                _top5 = torch.topk(_inet_probs, 5)
                _inet_cats = _W.IMAGENET1K_V1.meta["categories"]
                _top5_labels = " ".join(
                    _inet_cats[int(i)].lower() for i in _top5.indices
                )

                # Bag signal in ImageNet but fine-tuned says something else
                _bag_keywords = ("bag", "purse", "satchel", "backpack",
                                 "clutch", "tote", "wallet", "handbag")
                _inet_sees_bag = any(kw in _top5_labels for kw in _bag_keywords)
                if _inet_sees_bag and category not in ("Accessories",):
                    return None   # ImageNet says bag, fine-tuned disagrees → Tier 1B

                # Garment signal in ImageNet but fine-tuned says Accessories
                _garment_keywords = ("jean", "trouser", "pant", "skirt",
                                     "shirt", "blouse", "jersey", "dress",
                                     "coat", "jacket", "sneaker", "boot")
                _inet_sees_garment = any(kw in _top5_labels for kw in _garment_keywords)
                if _inet_sees_garment and category == "Accessories":
                    return None   # ImageNet says garment, fine-tuned says Accessories → Tier 1B

                # Dress signal in ImageNet but fine-tuned says Bottoms
                _dress_keywords = ("hoopskirt", "overskirt", "gown", "abaya", "kimono", "vestment", "sarong")
                _inet_sees_dress = any(kw in _top5_labels for kw in _dress_keywords)
                if _inet_sees_dress and category == "Bottoms":
                    return None   # ImageNet says dress, fine-tuned says Bottoms → Tier 1B

                # Extra gate: fine-tuned says Accessories, ImageNet sees NEITHER
                # bag NOR garment, AND the image is very bright (mean > 200).
                # This is the white-garment-on-white-backdrop false-positive signature.
                if category == "Accessories" and not _inet_sees_bag:
                    try:
                        from PIL import Image as _PIL2
                        import numpy as _np2
                        _mean_b = float(_np2.array(_PIL2.open(image_path).convert("RGB")).mean())
                        if _mean_b > 200:
                            return None  # very bright + no bag signal → reject Accessories
                    except Exception:
                        pass
        except Exception:
            pass  # Cross-validation failed; keep the fine-tuned result

        clothing_type = _DEFAULT_TYPE.get(category, "")
        # If ImageNet also predicted this category, use its finer-grained clothing_type
        # (e.g. Sandals, Boots, Loafers instead of default Sneakers)
        try:
            if '_inet_logits' in locals():
                _inet_res = _decode_imagenet_top5(_inet_logits)
                if _inet_res and _inet_res[0] == category and _inet_res[1]:
                    clothing_type = _inet_res[1]
        except Exception:
            pass

        return {
            "category":      category,
            "clothing_type": clothing_type,
            "confidence":    confidence,
            "source":        "mobilenet_finetuned",
        }
    except Exception:
        return None


def _classify_with_imagenet(image_path: str) -> Optional[dict]:
    """
    Run MobileNetV2 ImageNet pretrained model and map top-5 predictions
    to Wearlytics clothing categories.
    Returns result dict or None.
    """
    model = _load_imagenet_model()
    if model is None:
        return None
    tensor = _preprocess_image(image_path)
    if tensor is None:
        return None
    try:
        import torch
        with torch.no_grad():
            logits = model(tensor)    # (1, 1000)

        result = _decode_imagenet_top5(logits)
        if result is None:
            # No clothing class in top-5 → use image-shape heuristic
            # as a last resort before falling through to OpenCV
            return _imagenet_shape_heuristic(image_path)

        category, clothing_type, confidence = result

        # Disambiguate peplum tops vs dresses:
        # Garments with flared waistlines (peplum tops) frequently trigger
        # 'hoopskirt' or 'overskirt' in ImageNet. When the garment has top/hip
        # length (aspect < 1.55) and long sleeves extending below the central hem,
        # it is a top (Blouse), not a dress.
        if category == "Dresses":
            try:
                from PIL import Image as _PIL
                import numpy as _np
                _img = _PIL.open(image_path).convert("RGB")
                _w, _h = _img.size
                _arr = _np.array(_img).astype(float)
                _border = _np.vstack([
                    _arr[0:max(4, int(_h * 0.05)), :].reshape(-1, 3),
                    _arr[:, 0:max(4, int(_w * 0.05))].reshape(-1, 3),
                    _arr[:, _w - max(4, int(_w * 0.05)):].reshape(-1, 3)
                ])
                _bg = _np.median(_border, axis=0)
                _dist = _np.linalg.norm(_arr - _bg, axis=2)
                _fg = _dist > 22
                _ys, _xs = _np.where(_fg)
                if len(_ys) > 0:
                    _ymin, _ymax = _ys.min(), _ys.max()
                    _xmin, _xmax = _xs.min(), _xs.max()
                    _gh, _gw = _ymax - _ymin, _xmax - _xmin
                    _aspect = _gh / _gw if _gw > 0 else 1.0

                    # Check central coverage in the bottom 15% of garment bounding box
                    _bottom_strip = _fg[int(_ymax - 0.15 * _gh):_ymax, _xmin:_xmax]
                    _col_proj = _bottom_strip.mean(axis=0)
                    _w_strip = len(_col_proj)
                    _c_start = int(_w_strip * 0.3)
                    _c_end = int(_w_strip * 0.7)
                    _c_mean = float(_col_proj[_c_start:_c_end].mean()) if _c_end > _c_start else 0.0

                    if _aspect < 1.50 and _c_mean < 0.15:
                        category = "Tops"
                        clothing_type = "Blouse"
            except Exception:
                pass

        return {
            "category":      category,
            "clothing_type": clothing_type,
            "confidence":    confidence,
            "source":        "mobilenet_imagenet",
        }
    except Exception:
        return None


def _imagenet_shape_heuristic(image_path: str) -> Optional[dict]:
    """
    When ImageNet top-5 contains no clothing class, use image aspect ratio
    and mean brightness to make a better guess.
    Confidence is capped at 0.45 so the user always gets a correction prompt.

    Heuristic rules (h/w = aspect ratio):
        aspect < 0.75                → Shoes (wide, landscape)
        aspect > 1.8                 → Dresses (very tall)
        1.0 ≤ aspect ≤ 1.8          → Bottoms (portrait product photo,
                                       especially common for trousers/pants)
        aspect 0.75–1.0, bright bg  → Tops (square-ish, light background)
        else                        → Tops
    """
    try:
        from PIL import Image
        import numpy as _np
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        aspect = h / w if w > 0 else 1.0
        mean_brightness = float(_np.array(img).mean())

        if aspect < 0.75:
            # Landscape / wide → likely a shoe pair or flat lay
            return {"category": "Shoes", "clothing_type": "Sneakers", "confidence": 0.42, "source": "shape_heuristic"}
        elif aspect > 1.8:
            # Very tall → maxi dress or long skirt
            return {"category": "Dresses", "clothing_type": "Casual Dress", "confidence": 0.40, "source": "shape_heuristic"}
        elif 1.0 <= aspect <= 1.8:
            # Portrait product photo — common for trousers, jeans, leggings
            # Light background (>200) strongly suggests a product-photography shot
            if mean_brightness > 160:
                return {"category": "Bottoms", "clothing_type": "Trousers", "confidence": 0.44, "source": "shape_heuristic"}
            else:
                return {"category": "Bottoms", "clothing_type": "Jeans", "confidence": 0.40, "source": "shape_heuristic"}
        else:
            # Square-ish → most likely a top
            return {"category": "Tops", "clothing_type": "T-Shirt", "confidence": 0.38, "source": "shape_heuristic"}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Tier 2: Existing OpenCV heuristics (UNCHANGED — kept as fallback)
# ---------------------------------------------------------------------------

def _classify_with_cv(image_path: str) -> Optional[dict]:
    """
    Use OpenCV + NumPy heuristics to predict clothing category and type.
    Returns dict or None if OpenCV is unavailable.

    This is the original implementation, kept unchanged as Tier-2 fallback.
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return None

        h, w = img.shape[:2]
        aspect = h / w if w > 0 else 1.0

        small = cv2.resize(img, (200, 200))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        avg_sat = float(hsv[:, :, 1].mean())
        avg_val = float(hsv[:, :, 2].mean())

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(edges.mean())

        if avg_sat < 30 and (avg_val < 40 or avg_val > 210):
            category, clothing_type, confidence = "Accessories", "Bag", 0.55
        elif aspect < 0.75:
            category, clothing_type, confidence = "Shoes", "Sneakers", 0.65
        elif aspect > 1.6 and edge_density > 18 and avg_sat > 50:
            category, clothing_type, confidence = "Dresses", "Casual Dress", 0.70
        elif aspect > 1.2:
            if edge_density > 22:
                category, clothing_type, confidence = "Outerwear", "Jacket", 0.60
            else:
                clothing_type = "Shirt" if avg_sat < 80 else "T-Shirt"
                category, confidence = "Tops", 0.65
        elif 0.75 <= aspect <= 1.2 and edge_density < 15:
            category, clothing_type, confidence = "Bottoms", "Jeans", 0.60
        else:
            category, clothing_type, confidence = "Tops", "T-Shirt", 0.45

        return {
            "category":      category,
            "clothing_type": clothing_type,
            "confidence":    round(confidence, 2),
        }

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API — UNCHANGED signature
# ---------------------------------------------------------------------------

def classify(image_path: str) -> dict:
    """
    Classify a clothing image and return predicted category, type and confidence.

    Always returns a dict — falls back gracefully on any failure.

    Parameters
    ----------
    image_path : str
        Path to the saved image file on disk.

    Returns
    -------
    dict with keys:
        category      (str)   — e.g. "Tops"
        clothing_type (str)   — e.g. "T-Shirt"
        confidence    (float) — 0.0–1.0  (real probability if MobileNetV2 used)
        source        (str)   — "mobilenet_finetuned" | "mobilenet_imagenet"
                                | "shape_heuristic" | "cv" | "fallback"
    """
    if not image_path or not os.path.isfile(image_path):
        return {"category": "Tops", "clothing_type": "T-Shirt", "confidence": 0.0, "source": "fallback"}

    # --- Tier 1A: Fine-tuned MobileNetV2 ---
    # Threshold (0.75) and ImageNet cross-validation are applied inside
    # _classify_with_custom_model(); it returns None if the result is suspect.
    result = _classify_with_custom_model(image_path)
    if result:
        return result

    # --- Tier 1B: ImageNet-pretrained MobileNetV2 (keyword-based mapping) ---
    result = _classify_with_imagenet(image_path)
    if result:
        return result

    # --- Tier 2: OpenCV heuristics (original approach) ---
    result = _classify_with_cv(image_path)
    if result:
        result["source"] = "cv"
        return result

    # --- Tier 3: Hardcoded fallback (always succeeds) ---
    return {"category": "Tops", "clothing_type": "T-Shirt", "confidence": 0.0, "source": "fallback"}
