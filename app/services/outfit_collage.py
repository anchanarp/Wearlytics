"""Outfit collage generator service.

Creates high-fashion, editorial outfit collages from saved clothing item images.
"""

import hashlib
import os
import urllib.request
from PIL import Image, ImageOps
from flask import current_app


def get_outfit_collage_url(items, canvas_size=(800, 800)) -> str:
    """Generate or retrieve a cached collage image for a list of ClothingItem objects.

    Returns the public static URL to the collage image, or a fallback image URL.
    """
    fallback_url = "/static/img/ai_outfit_casual_chic.jpg"

    if not items:
        return fallback_url

    # Resolve local file paths for items
    valid_paths = []
    item_keys = []

    for item in items:
        if not getattr(item, "image_url", None):
            continue
        raw_url = item.image_url.strip()
        full_path = ""

        # Convert /static/... URL to local file path
        if raw_url.startswith("/static/"):
            rel_path = raw_url[len("/static/"):]
            full_path = os.path.join(current_app.static_folder, rel_path)
        elif raw_url.startswith("static/"):
            rel_path = raw_url[len("static/"):]
            full_path = os.path.join(current_app.static_folder, rel_path)
        elif raw_url.startswith("http://") or raw_url.startswith("https://"):
            # Download & cache remote images locally
            cache_dir = os.path.join(current_app.static_folder, "uploads", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            url_hash = hashlib.md5(raw_url.encode("utf-8")).hexdigest()
            cached_file = os.path.join(cache_dir, f"remote_{url_hash}.jpg")
            if not (os.path.exists(cached_file) and os.path.getsize(cached_file) > 0):
                try:
                    req = urllib.request.Request(
                        raw_url,
                        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
                    )
                    with urllib.request.urlopen(req, timeout=3.0) as resp:
                        content = resp.read()
                        if content and len(content) > 100:
                            with open(cached_file, "wb") as f:
                                f.write(content)
                except Exception:
                    pass
            if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
                full_path = cached_file
        else:
            full_path = raw_url

        if full_path and os.path.exists(full_path):
            valid_paths.append(full_path)
            item_keys.append(f"{item.id}_{os.path.basename(full_path)}")

    if not valid_paths:
        # Fallback to the first available item image URL if present
        for it in items:
            if getattr(it, "image_url", None) and it.image_url.strip():
                return it.image_url.strip()
        return fallback_url

    # Cache key
    key_str = "_".join(item_keys)
    cache_hash = hashlib.md5(key_str.encode("utf-8")).hexdigest()
    collage_rel_dir = "uploads/collages"
    collage_abs_dir = os.path.join(current_app.static_folder, collage_rel_dir)
    os.makedirs(collage_abs_dir, exist_ok=True)

    collage_filename = f"outfit_{cache_hash}.jpg"
    collage_abs_path = os.path.join(collage_abs_dir, collage_filename)
    collage_url = f"/static/{collage_rel_dir}/{collage_filename}"

    if os.path.exists(collage_abs_path) and os.path.getsize(collage_abs_path) > 0:
        return collage_url

    # Generate collage with Pillow
    try:
        canvas_w, canvas_h = canvas_size
        canvas = Image.new("RGB", (canvas_w, canvas_h), "#faf7f4")
        gap = 4

        valid_imgs = []
        for p in valid_paths:
            try:
                img = Image.open(p)
                # Handle EXIF orientation if present
                img = ImageOps.exif_transpose(img)
                valid_imgs.append(img.convert("RGB"))
            except Exception:
                continue

        n = len(valid_imgs)
        if n == 0:
            return fallback_url
        elif n == 1:
            img = ImageOps.fit(valid_imgs[0], (canvas_w, canvas_h), Image.Resampling.LANCZOS)
            canvas.paste(img, (0, 0))
        elif n == 2:
            w = (canvas_w - gap) // 2
            img1 = ImageOps.fit(valid_imgs[0], (w, canvas_h), Image.Resampling.LANCZOS)
            img2 = ImageOps.fit(valid_imgs[1], (canvas_w - w - gap, canvas_h), Image.Resampling.LANCZOS)
            canvas.paste(img1, (0, 0))
            canvas.paste(img2, (w + gap, 0))
        elif n == 3:
            left_w = int(canvas_w * 0.58)
            right_w = canvas_w - left_w - gap
            right_h = (canvas_h - gap) // 2
            img1 = ImageOps.fit(valid_imgs[0], (left_w, canvas_h), Image.Resampling.LANCZOS)
            img2 = ImageOps.fit(valid_imgs[1], (right_w, right_h), Image.Resampling.LANCZOS)
            img3 = ImageOps.fit(valid_imgs[2], (right_w, canvas_h - right_h - gap), Image.Resampling.LANCZOS)
            canvas.paste(img1, (0, 0))
            canvas.paste(img2, (left_w + gap, 0))
            canvas.paste(img3, (left_w + gap, right_h + gap))
        else:
            # 4 or more pieces
            w = (canvas_w - gap) // 2
            h = (canvas_h - gap) // 2
            for idx in range(min(4, n)):
                img = ImageOps.fit(valid_imgs[idx], (w, h), Image.Resampling.LANCZOS)
                x = (idx % 2) * (w + gap)
                y = (idx // 2) * (h + gap)
                canvas.paste(img, (x, y))

        canvas.save(collage_abs_path, format="JPEG", quality=92, optimize=True)
        return collage_url
    except Exception as exc:
        if current_app:
            current_app.logger.warning(f"Failed to generate outfit collage: {exc}")
        return fallback_url
