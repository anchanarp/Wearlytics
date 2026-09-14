"""
test_classifier_integration.py
================================
Automated tests for the MobileNetV2 clothing classification upgrade.
Covers all 10 scenarios requested.

Run:  .venv/bin/python test_classifier_integration.py
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import io
from app import create_app
from config import Config

class TestConfig(Config):
    TESTING = True

app = create_app(config_class=TestConfig)

# Test credentials
TEST_EMAIL = "ammu@gmail.com"
TEST_PASS  = "password123"

from app.extensions import db
from app.models.user import User

# Create all tables in the in‑memory test DB and add a test user.
# Create all tables in the in‑memory test DB and add a test user.
# Use a persistent app context so the same SQLite connection is used across requests.
app_ctx = app.app_context()
app_ctx.push()

db.create_all()
if not User.query.filter_by(email=TEST_EMAIL).first():
    test_user = User(name='Test User', email=TEST_EMAIL)
    test_user.set_password(TEST_PASS)
    db.session.add(test_user)
    db.session.commit()

# Flask test client for making requests
client = app.test_client()
PASS       = "✅ PASS"
FAIL       = "❌ FAIL"
WARN       = "⚠️  WARN"

results = []

def record(test_name, status, detail=""):
    tag = PASS if status else FAIL
    results.append((test_name, status, detail))
    print(f"  {tag}  {test_name}" + (f" — {detail}" if detail else ""))


# ── Helpers ──────────────────────────────────────────────────────────────────

def login():
    """Log in with test credentials so session cookie is set."""
    r = client.post("/auth/login", data={"email": TEST_EMAIL, "password": TEST_PASS}, follow_redirects=True)
    return r.status_code == 200


def make_fake_jpg(width=100, height=140, color=(100, 149, 237)):
    """Create a small real JPEG in memory using Pillow."""
    from PIL import Image
    import io
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def make_invalid_file():
    """Return bytes that are not a valid image."""
    import io
    return io.BytesIO(b"this is not an image file -- INVALID")


# ── Classifier unit tests (no network) ───────────────────────────────────────

def test_classifier_module():
    print("\n[A] Classifier module unit tests")

    sys.path.insert(0, str(Path(__file__).parent))
    from app.services import clothing_classifier as cc

    # A1: Module imports without error
    record("Module imports cleanly", True)

    # A2: All public constants still exist
    ok = all([
        hasattr(cc, "ALL_STYLES"),
        hasattr(cc, "ALL_OCCASIONS"),
        hasattr(cc, "ALL_SEASONS"),
        hasattr(cc, "ALL_CATEGORIES"),
        hasattr(cc, "get_types_for_category"),
    ])
    record("All public constants exist", ok)

    # A3: classify() returns correct 4-key dict even for missing file
    result = cc.classify("/nonexistent/path/image.jpg")
    ok = (isinstance(result, dict) and
          all(k in result for k in ["category", "clothing_type", "confidence", "source"]) and
          result["source"] == "fallback")
    record("Missing file → fallback dict returned", ok, f"source={result.get('source')}")

    # A4: classify() on a real image (portrait JPEG)
    from PIL import Image
    import tempfile
    img = Image.new("RGB", (100, 140), (60, 100, 180))
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img.save(f, format="JPEG")
        tmp_path = f.name
    try:
        result = cc.classify(tmp_path)
        ok = (isinstance(result, dict) and
              result.get("category") in cc.ALL_CATEGORIES and
              0.0 <= result.get("confidence", -1) <= 1.0)
        record("Real image → valid category + confidence", ok,
               f"cat={result.get('category')} conf={result.get('confidence'):.2f} src={result.get('source')}")
    finally:
        os.unlink(tmp_path)

    # A5: classify() returns known source values only
    valid_sources = {"mobilenet_finetuned", "mobilenet_imagenet",
                     "shape_heuristic", "cv", "fallback"}
    record("Source field is a known value", result.get("source") in valid_sources,
           result.get("source"))

    # A6: get_types_for_category works
    types = cc.get_types_for_category("Tops")
    record("get_types_for_category('Tops') returns list", isinstance(types, list) and len(types) > 0)


# ── Color detector tests ──────────────────────────────────────────────────────

def test_color_detector():
    print("\n[B] Color detector unit tests (unchanged)")
    from app.services import color_detector as cd
    from PIL import Image
    import tempfile

    img = Image.new("RGB", (80, 80), (30, 30, 200))   # blue image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img.save(f, format="JPEG")
        tmp_path = f.name
    try:
        result = cd.extract_color(tmp_path)
        ok = (result is not None and
              "hex" in result and "name" in result)
        record("Color detector returns hex + name", ok,
               f"hex={result.get('hex')} name={result.get('name')}" if result else "None returned")
    finally:
        os.unlink(tmp_path)


# ── Flask route tests (via HTTP) ──────────────────────────────────────────────

def test_routes():
    print("\n[C] Route tests (via HTTP)")

    login_ok = login()
    record("Login with test credentials", login_ok)

    # C1: Upload page loads
    r = client.get("/wardrobe/upload")
    record("Upload page loads (200)", r.status_code == 200)

    # C2: /wardrobe/analyze with valid image returns JSON with success=True
    buf = make_fake_jpg(100, 140)
    r = client.post("/wardrobe/analyze", data={"image_file": (buf, "test.jpg", "image/jpeg")}, content_type='multipart/form-data')
    ok = (r.status_code == 200)
    try:
        data = r.get_json()
        ok = data.get("success") == True
        source = data.get("source", "?")
        conf   = data.get("confidence", 0)
        cat    = data.get("category", "?")
        record("/wardrobe/analyze returns success=True", ok,
               f"cat={cat} conf={conf}% src={source}")
    except Exception as e:
        record("/wardrobe/analyze returns valid JSON", False, str(e))
        data = {}

    # C3: /wardrobe/analyze response has all expected keys
    expected_keys = {"success", "category", "clothing_type", "confidence", "source"}
    has_keys = expected_keys.issubset(set(data.keys()))
    record("/wardrobe/analyze JSON has all expected keys", has_keys)

    # C4: /wardrobe/analyze with invalid file → success=False
    inv = make_invalid_file()
    r = client.post("/wardrobe/analyze", data={"image_file": (inv, "bad.txt")}, content_type='multipart/form-data')
    try:
        d = r.get_json()
        record("/wardrobe/analyze with invalid file → success=False",
               d.get("success") == False, f"response={d}")
    except Exception:
        record("/wardrobe/analyze invalid file returns JSON", r.status_code in (200, 400))

    # C5: Dashboard still loads
    r = client.get("/")
    record("Dashboard (/) loads (200)", r.status_code == 200)

    # C6: Wardrobe page still loads
    r = client.get("/wardrobe/")
    record("Wardrobe page loads (200)", r.status_code == 200)

    # C7: Recommendations still load
    r = client.get("/recommendations/")
    record("Recommendations page loads (200)", r.status_code == 200)

    # C8: Analytics still loads
    r = client.get("/analytics/")
    record("Analytics page loads (200)", r.status_code == 200)

    # C9: Planner still loads
    r = client.get("/planner/")
    record("Planner page loads (200)", r.status_code == 200)

    # C10: Profile still loads
    r = client.get("/profile/")
    record("Profile page loads (200)", r.status_code == 200)


# ── Fallback tests (without torch) ────────────────────────────────────────────

def test_fallback_chain():
    print("\n[D] Fallback chain test")

    # Simulate torch unavailability by patching _check_torch
    import app.services.clothing_classifier as cc

    original = cc._check_torch

    # Monkey-patch torch check to return False
    cc._torch_available = False
    cc._custom_model = None
    cc._imagenet_model = None

    from PIL import Image
    import tempfile
    img = Image.new("RGB", (100, 80), (200, 100, 50))   # landscape → Shoes
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img.save(f, format="JPEG")
        tmp_path = f.name
    try:
        result = cc.classify(tmp_path)
        ok_fallback = result.get("source") in ("cv", "fallback", "shape_heuristic")
        record("Torch disabled → OpenCV/fallback used", ok_fallback,
               f"source={result.get('source')} cat={result.get('category')}")
        record("Fallback returns valid dict", "category" in result and "confidence" in result)
    finally:
        os.unlink(tmp_path)
        # Restore
        cc._torch_available = None
        cc._custom_model = None
        cc._imagenet_model = None


# ── Upload form + DB save test ─────────────────────────────────────────────────

def test_upload_and_save():
    print("\n[E] Upload form submission and DB save")

    # Ensure user is logged in
    login_ok = login()
    record("Login before upload", login_ok)

    # Create fake image buffer
    buf = make_fake_jpg(120, 160, color=(180, 100, 60))

    # Use Flask test client for upload
    r = client.post(
        "/wardrobe/upload",
        data={
            "name": "Test AI Shirt",
            "category": "Tops",
            "color": "Blue",
            "season": "All Seasons",
            "brand": "TestBrand",
            "style": "Casual",
            "clothing_type": "T-Shirt",
            "image_file": (buf, "shirt.jpg"),
        },
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    ok = r.status_code == 200
    record("Upload form POST succeeds (200 after redirect)", ok)

    # Verify item appears in wardrobe
    r2 = client.get("/wardrobe/")
    record("Item appears in wardrobe after save", "Test AI Shirt" in r2.text,
           "found in HTML" if "Test AI Shirt" in r2.text else "NOT found")


# ── Manual correction test ─────────────────────────────────────────────────────

def test_manual_correction():
    print("\n[F] Manual correction — user overrides AI prediction")

    # Ensure logged in
    login_ok = login()
    record("Login before manual correction", login_ok)

    buf = make_fake_jpg(100, 100)
    # Use client to post upload with manual overrides
    r = client.post(
        "/wardrobe/upload",
        data={
            "name": "Manual Override Test",
            "category": "Shoes",  # user manually chooses Shoes
            "color": "White",
            "season": "Summer",
            "clothing_type": "Custom Type",
            "image_file": (buf, "shoe.jpg"),
        },
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    record("Manual override upload succeeds", r.status_code == 200)



# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total  = len(results)
    for name, ok, detail in results:
        tag = "✅" if ok else "❌"
        print(f"  {tag}  {name}")
    print(f"\nResult: {passed}/{total} tests passed")
    if passed == total:
        print("All tests PASSED ✓")
    else:
        print(f"{total - passed} test(s) FAILED")
    print("=" * 60)


if __name__ == "__main__":
    print("Wearlytics MobileNetV2 — Integration Tests")
    print("=" * 60)
    test_classifier_module()
    test_color_detector()
    test_routes()
    test_fallback_chain()
    test_upload_and_save()
    test_manual_correction()
    print_summary()
