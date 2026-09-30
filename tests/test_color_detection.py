import os
import tempfile
from pathlib import Path
from PIL import Image

# Import the function to test
from app.services.color_detector import extract_color

# Define test cases: (name, RGB tuple, expected_color_name)
TEST_CASES = [
    ("white", (255, 255, 255), "White"),
    ("off_white", (245, 245, 245), "Off White"),
    ("black", (0, 0, 0), "Black"),
    ("charcoal", (64, 64, 64), "Charcoal"),
    ("gray", (128, 128, 128), "Gray"),
    ("silver", (192, 192, 192), "Silver"),
    ("red", (255, 0, 0), "Red"),
    ("cherry_red", (255, 36, 0), "Cherry Red"),
    ("maroon", (128, 0, 0), "Maroon"),
    ("blue", (0, 0, 255), "Blue"),
    ("navy_blue", (0, 0, 128), "Navy Blue"),
    ("brown", (165, 42, 42), "Brown"),
    ("tan", (210, 180, 140), "Tan"),
]

def create_solid_image(rgb, size=(100, 100)):
    img = Image.new("RGB", size, rgb)
    return img

def test_color_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname, rgb, expected in TEST_CASES:
            img = create_solid_image(rgb)
            img_path = Path(tmpdir) / f"{fname}.png"
            img.save(img_path)
            result = extract_color(str(img_path))
            assert result is not None, f"extract_color returned None for {fname}"
            assert result["name"] == expected, f"{fname}: expected {expected}, got {result['name']}"
