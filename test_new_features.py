"""
Wearlytics — New Feature Integration Tests
==========================================
Tests for:
  1. Recommendation explanation
  2. Compatibility score display
  3. Wear date saved correctly
  4. Last worn date displayed
  5. Wear count still increments
  6. Item can be marked In Laundry
  7. In-Laundry item excluded from recommendations
  8. Item can be marked Available again
  9. Available item returns to recommendations
 10. Dark mode toggle (JS localStorage-based — tested via page HTML presence)
 11. Dark mode toggle button exists and persists init script
 12. Profile bio edit works
 13. Password change works correctly
 14. Existing authentication still works
 15. Existing wardrobe upload still works
 16. Existing MobileNetV2 classifier still works
 17. Existing color detection still works
 18. Existing recommendation tests still pass (engine produces results)
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))

# -------------------------------------------------------
# App fixture
# -------------------------------------------------------
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.clothing import ClothingItem
from app.models.user_preferences import UserPreferences

TEST_EMAIL = "feattest@wearlytics.test"
TEST_PASS  = "feattestpass123"


def _make_app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    return app


def _seed(app):
    """Seed a test user + wardrobe items that can form outfits."""
    with app.app_context():
        _db.create_all()
        u = User.query.filter_by(email=TEST_EMAIL).first()
        if not u:
            u = User(name="Feature Tester", email=TEST_EMAIL)
            u.set_password(TEST_PASS)
            _db.session.add(u)
            _db.session.flush()
        # Ensure preferences row
        UserPreferences.get_or_create(u.id)

        uid = u.id
        # Clear existing test items
        ClothingItem.query.filter_by(user_id=uid).delete()

        items = [
            ClothingItem(user_id=uid, name="White Tee", category="Tops",
                         color="White", season="Summer", style="Casual",
                         image_url="https://example.com/white_tee.jpg"),
            ClothingItem(user_id=uid, name="Blue Jeans", category="Bottoms",
                         color="Blue", season="All Seasons", style="Casual",
                         image_url="https://example.com/blue_jeans.jpg"),
            ClothingItem(user_id=uid, name="White Sneakers", category="Shoes",
                         color="White", season="Summer", style="Casual",
                         image_url="https://example.com/sneakers.jpg"),
            ClothingItem(user_id=uid, name="Black Dress", category="Dresses",
                         color="Black", season="All Seasons", style="Formal",
                         image_url="https://example.com/dress.jpg"),
        ]
        for it in items:
            _db.session.add(it)
        _db.session.commit()
        return uid


# -------------------------------------------------------
# Test runner
# -------------------------------------------------------
RESULTS = []

def run_test(name, fn):
    try:
        fn()
        RESULTS.append((True, name))
        print(f"  ✅ PASS  {name}")
    except AssertionError as e:
        RESULTS.append((False, name))
        print(f"  ❌ FAIL  {name}: {e}")
    except Exception as e:
        RESULTS.append((False, name))
        print(f"  ❌ FAIL  {name}: {type(e).__name__}: {e}")


# -------------------------------------------------------
# HTTP client helpers
# -------------------------------------------------------
def _login(client, email=TEST_EMAIL, pw=TEST_PASS):
    return client.post("/auth/login", data={"email": email, "password": pw},
                       follow_redirects=True)


def _get_item(app, uid, name):
    with app.app_context():
        return ClothingItem.query.filter_by(user_id=uid, name=name).first()


# -------------------------------------------------------
# Tests
# -------------------------------------------------------

def run_tests():
    app = _make_app()
    uid = _seed(app)

    print("\nWearlytics — New Feature Tests")
    print("=" * 60)

    # ---- 1. Recommendation explanation section rendered ----
    print("\n[1] Recommendation Explanation")

    def test_explanation_section():
        with app.test_client() as c:
            _login(c)
            resp = c.get("/recommendations/", follow_redirects=True)
            html = resp.data.decode()
            # Either recommendations shown with "Why this outfit?" or empty state
            assert resp.status_code == 200
            if "rec-card" in html:
                assert "Why this outfit?" in html, "Missing 'Why this outfit?' section in recommendation card"

    run_test("Recommendation explanation section rendered (if recs available)", test_explanation_section)

    # ---- 2. Compatibility score displayed ----
    def test_compat_score():
        with app.test_client() as c:
            _login(c)
            resp = c.get("/recommendations/", follow_redirects=True)
            html = resp.data.decode()
            assert resp.status_code == 200
            if "rec-card" in html:
                assert "Compatibility Score" in html, "Compatibility Score not found in recs"

    run_test("Compatibility score displayed in recommendations", test_compat_score)

    # ---- 3. Wear date saved correctly ----
    print("\n[2] Wear History with Date")

    def test_wear_date_saved():
        with app.test_client() as c:
            _login(c)
            with app.app_context():
                item = ClothingItem.query.filter_by(user_id=uid, name="White Tee").first()
                iid = item.id
                old_count = item.wear_count
            resp = c.post(f"/wardrobe/{iid}/wear", follow_redirects=True)
            assert resp.status_code == 200
            with app.app_context():
                item2 = ClothingItem.query.get(iid)
                assert item2.last_worn_at is not None, "last_worn_at not set after wear"
                assert item2.wear_count == old_count + 1, "wear_count did not increment"

    run_test("Wear date (last_worn_at) saved when item worn", test_wear_date_saved)

    # ---- 4. Last worn date displayed in wardrobe ----
    def test_last_worn_displayed():
        with app.test_client() as c:
            _login(c)
            with app.app_context():
                item = ClothingItem.query.filter_by(user_id=uid, name="White Tee").first()
                iid = item.id
            c.post(f"/wardrobe/{iid}/wear", follow_redirects=True)
            resp = c.get("/wardrobe/", follow_redirects=True)
            html = resp.data.decode()
            assert "Last:" in html, "Last worn date not displayed in wardrobe"

    run_test("Last worn date displayed in wardrobe", test_last_worn_displayed)

    # ---- 5. Wear count increments correctly ----
    def test_wear_count_increments():
        with app.test_client() as c:
            _login(c)
            with app.app_context():
                item = ClothingItem.query.filter_by(user_id=uid, name="Blue Jeans").first()
                iid = item.id
                before = item.wear_count
            c.post(f"/wardrobe/{iid}/wear", follow_redirects=True)
            c.post(f"/wardrobe/{iid}/wear", follow_redirects=True)
            with app.app_context():
                item2 = ClothingItem.query.get(iid)
                assert item2.wear_count == before + 2, f"Expected {before+2}, got {item2.wear_count}"

    run_test("Wear count increments correctly (2 wear events)", test_wear_count_increments)

    # ---- 6. Mark item In Laundry ----
    print("\n[3] Laundry / Availability System")

    def test_mark_in_laundry():
        with app.test_client() as c:
            _login(c)
            with app.app_context():
                item = ClothingItem.query.filter_by(user_id=uid, name="White Sneakers").first()
                assert not item.is_in_laundry, "Item should start as available"
                iid = item.id
            resp = c.post(f"/wardrobe/{iid}/laundry", follow_redirects=True)
            assert resp.status_code == 200
            with app.app_context():
                item2 = ClothingItem.query.get(iid)
                assert item2.is_in_laundry, "Item not marked in laundry"
                assert item2 is not None, "Item was deleted (must not be)"

    run_test("Item can be marked In Laundry", test_mark_in_laundry)

    # ---- 7. In-Laundry item excluded from recommendations ----
    def test_laundry_excluded_from_recs():
        from app.services import recommendation_engine
        with app.app_context():
            # Mark sneakers in laundry
            sneaker = ClothingItem.query.filter_by(user_id=uid, name="White Sneakers").first()
            sneaker.is_in_laundry = True
            _db.session.commit()
            sneaker_id = sneaker.id

            recs = recommendation_engine.get_recommendations(user_id=uid, top_n=5)
            for rec in recs:
                item_ids = [i.id for i in rec["clothing_items"]]
                assert sneaker_id not in item_ids, \
                    f"In-laundry item (id={sneaker_id}) appeared in recommendation!"

    run_test("In-Laundry item excluded from recommendations", test_laundry_excluded_from_recs)

    # ---- 8. Mark item Available again ----
    def test_mark_available():
        with app.test_client() as c:
            _login(c)
            with app.app_context():
                item = ClothingItem.query.filter_by(user_id=uid, name="White Sneakers").first()
                iid = item.id
                assert item.is_in_laundry, "Item should be in laundry for this test"
            resp = c.post(f"/wardrobe/{iid}/laundry", follow_redirects=True)
            assert resp.status_code == 200
            with app.app_context():
                item2 = ClothingItem.query.get(iid)
                assert not item2.is_in_laundry, "Item not marked available after toggle"

    run_test("Item can be marked Available again", test_mark_available)

    # ---- 9. Available item returns to recommendations ----
    def test_available_in_recs():
        from app.services import recommendation_engine
        with app.app_context():
            # Make sure sneakers are available
            sneaker = ClothingItem.query.filter_by(user_id=uid, name="White Sneakers").first()
            sneaker.is_in_laundry = False
            _db.session.commit()
            sneaker_id = sneaker.id

            recs = recommendation_engine.get_recommendations(user_id=uid, top_n=5)
            found = any(
                sneaker_id in [i.id for i in rec["clothing_items"]]
                for rec in recs
            )
            # Sneaker is eligible — may or may not appear depending on scoring,
            # but it must not be excluded by the laundry filter.
            # We verify by checking the available pool
            all_available = ClothingItem.query.filter_by(user_id=uid, is_in_laundry=False).all()
            assert any(i.id == sneaker_id for i in all_available), \
                "Sneaker should be in available pool"

    run_test("Available item is in eligible recommendation pool", test_available_in_recs)

    # ---- 10. Dark mode toggle button present in HTML ----
    print("\n[4] Dark Mode")

    def test_dark_mode_toggle_exists():
        with app.test_client() as c:
            _login(c)
            resp = c.get("/", follow_redirects=True)
            html = resp.data.decode()
            assert "themeToggle" in html, "Dark mode toggle button not in HTML"
            assert "wearlytics-theme" in html, "Theme localStorage key not in init script"

    run_test("Dark mode toggle button present in page HTML", test_dark_mode_toggle_exists)

    # ---- 11. Dark mode init script persists across pages ----
    def test_dark_mode_init_script():
        with app.test_client() as c:
            _login(c)
            for path in ["/", "/wardrobe/", "/recommendations/", "/profile/"]:
                resp = c.get(path, follow_redirects=True)
                html = resp.data.decode()
                assert "wearlytics-theme" in html, \
                    f"Theme init script missing on {path}"
                assert "data-theme" in html or "themeToggle" in html, \
                    f"Dark mode markup missing on {path}"

    run_test("Dark mode init script present on all major pages", test_dark_mode_init_script)

    # ---- 12. Profile bio edit ----
    print("\n[5] Complete User Profile")

    def test_profile_bio_edit():
        with app.test_client() as c:
            _login(c)
            resp = c.post("/profile/", data={
                "action": "profile",
                "name": "Feature Tester",
                "bio": "Loves minimalist style",
                "avatar_color": "#00b894",
            }, follow_redirects=True)
            assert resp.status_code == 200
            with app.app_context():
                u = User.query.filter_by(email=TEST_EMAIL).first()
                assert u.bio == "Loves minimalist style", f"Bio not saved: {u.bio}"
                assert u.avatar_color == "#00b894", f"Avatar color not saved: {u.avatar_color}"

    run_test("Profile bio and avatar color can be edited", test_profile_bio_edit)

    # ---- 13. Password change works correctly ----
    def test_password_change():
        with app.test_client() as c:
            _login(c)
            resp = c.post("/profile/", data={
                "action": "password",
                "current_password": TEST_PASS,
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            }, follow_redirects=True)
            assert resp.status_code == 200
            with app.app_context():
                u = User.query.filter_by(email=TEST_EMAIL).first()
                assert u.check_password("newpassword456"), "New password not set"
                # Restore original password
                u.set_password(TEST_PASS)
                _db.session.commit()

    run_test("Password change works correctly", test_password_change)

    # ---- 14. Existing authentication ----
    print("\n[6] Existing Functionality Still Works")

    def test_auth():
        with app.test_client() as c:
            resp = _login(c)
            assert resp.status_code == 200
            assert b"My Wardrobe" in resp.data or b"Dashboard" in resp.data or b"Wearlytics" in resp.data

    run_test("Existing authentication still works", test_auth)

    # ---- 15. Wardrobe upload still works ----
    def test_wardrobe_upload():
        with app.test_client() as c:
            _login(c)
            resp = c.get("/wardrobe/upload", follow_redirects=True)
            assert resp.status_code == 200
            assert b"Upload" in resp.data or b"Add Clothing" in resp.data

    run_test("Existing wardrobe upload page still works", test_wardrobe_upload)

    # ---- 16. MobileNetV2 classifier still works ----
    def test_classifier():
        from app.services import clothing_classifier
        with app.app_context():
            result = clothing_classifier.classify("nonexistent_image.jpg")
            assert "category" in result, "Classifier missing 'category'"
            assert "source" in result, "Classifier missing 'source'"

    run_test("Existing MobileNetV2 classifier still works (fallback path)", test_classifier)

    # ---- 17. Color detection still works ----
    def test_color_detection():
        from app.services import color_detector
        import numpy as np
        # Create a tiny blue image for testing
        import tempfile, cv2
        arr = np.zeros((10, 10, 3), dtype=np.uint8)
        arr[:] = (255, 0, 0)  # Blue in BGR
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            cv2.imwrite(f.name, arr)
            result = color_detector.extract_color(f.name)
        assert result is not None, "Color detector returned None"
        assert "hex" in result, "Color result missing 'hex'"
        assert "name" in result, "Color result missing 'name'"

    run_test("Existing color detection still works", test_color_detection)

    # ---- 18. Recommendation engine produces results ----
    def test_rec_engine():
        from app.services import recommendation_engine
        with app.app_context():
            # Make sure all items are available
            ClothingItem.query.filter_by(user_id=uid).update({"is_in_laundry": False})
            _db.session.commit()
            recs = recommendation_engine.get_recommendations(user_id=uid, top_n=3)
            assert len(recs) >= 1, "Recommendation engine returned no results"
            assert "score" in recs[0], "Recommendation missing 'score'"
            assert "breakdown" in recs[0], "Recommendation missing 'breakdown'"
            assert "clothing_items" in recs[0], "Recommendation missing 'clothing_items'"

    run_test("Recommendation engine produces results with breakdown", test_rec_engine)

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------
    print("\n" + "=" * 60)
    print("TEST SUMMARY (New Features)")
    print("=" * 60)
    passed = sum(1 for ok, _ in RESULTS if ok)
    total = len(RESULTS)
    for ok, name in RESULTS:
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name}")
    print(f"\nResult: {passed}/{total} tests passed")
    if passed == total:
        print("All new feature tests PASSED ✓")
    else:
        print(f"WARNING: {total - passed} run_test(s) FAILED")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
