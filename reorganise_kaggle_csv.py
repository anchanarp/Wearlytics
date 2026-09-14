#!/usr/bin/env python3
"""Reorganise Kaggle clothing dataset using CSV mapping.
Creates category subfolders under `data/organised/` and symlinks images from
`data/kaggle_clothing/images_compressed/`.
"""
import csv
import os
import pathlib
import sys

# Paths (relative to this script location)
BASE_DIR = pathlib.Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "kaggle_clothing"
CSV_PATH = RAW_DIR / "images.csv"
IMG_DIR = RAW_DIR / "images_compressed"
ORG_DIR = BASE_DIR / "data" / "organised"

# Category mapping (label -> Wearlytics category)
LABEL_TO_CATEGORY = {
    # Tops
    "T-Shirt": "Tops",
    "Longsleeve": "Tops",
    "Shirt": "Tops",
    "Blouse": "Tops",
    "Polo": "Tops",
    "Top": "Tops",
    "Body": "Tops",
    "Undershirt": "Tops",
    # Bottoms
    "Pants": "Bottoms",
    "Shorts": "Bottoms",
    "Skirt": "Bottoms",
    # Shoes
    "Shoes": "Shoes",
    # Outerwear
    "Outwear": "Outerwear",
    "Blazer": "Outerwear",
    "Hoodie": "Outerwear",
    # Dresses
    "Dress": "Dresses",
    # Accessories
    "Hat": "Accessories",
}

# Labels to discard (no category)
DISCARD_LABELS = {"Not sure", "Other", "Skip"}

def main():
    if not CSV_PATH.is_file():
        print(f"CSV file not found: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)
    if not IMG_DIR.is_dir():
        print(f"Image directory not found: {IMG_DIR}", file=sys.stderr)
        sys.exit(1)

    # Ensure output category directories exist
    categories = set(LABEL_TO_CATEGORY.values())
    for cat in categories:
        (ORG_DIR / cat).mkdir(parents=True, exist_ok=True)

    counts = {cat: 0 for cat in categories}
    discarded = 0
    missing = 0
    duplicate_rows = 0
    rows_processed = 0
    duplicate_check = set()

    with CSV_PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        # Optional subset for sanity check
        subset = None
        if len(sys.argv) > 1:
            try:
                subset = int(sys.argv[1])
            except ValueError:
                print(f"Invalid subset argument: {sys.argv[1]}", file=sys.stderr)
                subset = None
        for idx, row in enumerate(reader):
            if subset is not None and idx >= subset:
                break
            rows_processed += 1
            img_id = row["image"].strip()
            label = row["label"].strip()
            # Duplicate image ID guard
            if img_id in duplicate_check:
                duplicate_rows += 1
                print(f"Duplicate image ID detected: {img_id}", file=sys.stderr)
                continue
            duplicate_check.add(img_id)

            # Determine action
            if label in DISCARD_LABELS:
                discarded += 1
                continue
            category = LABEL_TO_CATEGORY.get(label)
            if not category:
                print(f"Warning: label '{label}' not mapped to any category.", file=sys.stderr)
                discarded += 1
                continue
            src = IMG_DIR / f"{img_id}.jpg"
            if not src.is_file():
                missing += 1
                print(f"Missing image file for ID {img_id}", file=sys.stderr)
                continue
            dst = ORG_DIR / category / f"{img_id}.jpg"
            try:
                if not dst.exists():
                    os.symlink(src, dst)
                counts[category] += 1
            except OSError as e:
                print(f"Failed to symlink {src} -> {dst}: {e}", file=sys.stderr)

    # Summary output
    print("=== Summary ===")
    print(f"Rows processed: {rows_processed}")
    total_mapped = sum(counts.values())
    print(f"Total mapped images: {total_mapped}")
    for cat, cnt in counts.items():
        print(f"{cat}: {cnt}")
    print(f"Discarded images: {discarded}")
    print(f"Missing files: {missing}")
    print(f"Duplicate IDs: {duplicate_rows}")

if __name__ == "__main__":
    main()
