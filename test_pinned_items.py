"""
Wearlytics — Pinned Wardrobe Item Regression Tests
====================================================
Verifies that when a user selects specific wardrobe items
("Select from My Wardrobe"), those items are HARD CONSTRAINTS
in every recommendation result.

Tests:
  1.  No pinned items → existing free AI recommendation works.
  2.  Pinned Top → every result contains that exact Top.
  3.  Pinned Bottom → every result contains that exact Bottom.
  4.  Pinned Dress → every result contains that exact Dress.
  5.  Multiple pinned (Top + Bottom) → every result contains BOTH.
  6.  Pinned item in laundry → excluded from display; not selectable.
  7.  No compatible combination → returns empty (caller shows error).
  8.  More Outfit Options → all results contain pinned items.
  9.  Let AI Choose (no item_ids) → free recommendation works normally.
  10. Pinned item survives season filter → still appears in results.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.clothing import ClothingItem
from app.models.user_preferences import UserPreferences
from app.services import recommendation_engine

# ── Test configuration ──────────────────────────────────────────────────────
TEST_EMAIL = "pinnedtest@wearlytics.test"
TEST_PASS  = "pinnedtestpass"


def _make_app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    return app


def _seed(app):
    """Seed a rich wardrobe for pin constraint testing."""
    with app.app_context():
        _db.create_all()
        u = User.query.filter_by(email=TEST_EMAIL).first()
        if not u:
            u = User(name="Pin Tester", email=TEST_EMAIL)
            u.set_password(TEST_PASS)
            _db.session.add(u)
            _db.session.flush()
        UserPreferences.get_or_create(u.id)
        uid = u.id

        ClothingItem.query.filter_by(user_id=uid).delete()

        items = [
            # Tops
            ClothingItem(user_id=uid, name="Black Cashmere Sweater", category="Tops",
                         color="Black", season="Winter", style="Casual",
                         image_url="https://example.com/sweater.jpg"),
            ClothingItem(user_id=uid, name="White Tee", category="Tops",
                         color="White", season="Summer", style="Casual",
                         image_url="https://example.com/tee.jpg"),
            # Bottoms
            ClothingItem(user_id=uid, name="Blue Jeans", category="Bottoms",
                         color="Blue", season="All Seasons", style="Casual",
                         image_url="https://example.com/jeans.jpg"),
            ClothingItem(user_id=uid, name="Black Trousers", category="Bottoms",
                         color="Black", season="All Seasons", style="Casual",
                         image_url="https://example.com/trousers.jpg"),
            # Dress
            ClothingItem(user_id=uid, name="Silk Floral Summer Dress", category="Dresses",
                         color="Multicolor", season="Summer", style="Casual",
                         image_url="https://example.com/dress.jpg"),
            # Shoes
            ClothingItem(user_id=uid, name="White Sneakers", category="Shoes",
                         color="White", season="Summer", style="Casual",
                         image_url="https://example.com/sneakers.jpg"),
            # Accessory
            ClothingItem(user_id=uid, name="Leather Belt", category="Accessories",
                         color="Brown", season="All Seasons", style="Casual",
                         image_url="https://example.com/belt.jpg"),
            # Laundry item (should never appear)
            ClothingItem(user_id=uid, name="Dirty T-Shirt", category="Tops",
                         color="Grey", season="All Seasons", style="Casual",
                         is_in_laundry=True,
                         image_url="https://example.com/dirty.jpg"),
        ]
        for it in items:
            _db.session.add(it)
        _db.session.commit()
        return uid


# ── Test runner ─────────────────────────────────────────────────────────────
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
        print(f"  ❌ ERROR {name}: {type(e).__name__}: {e}")


# ── Helper ───────────────────────────────────────────────────────────────────
def _get_id(app, uid, name):
    with app.app_context():
        item = ClothingItem.query.filter_by(user_id=uid, name=name).first()
        assert item, f"Item '{name}' not found in DB"
        return item.id


def _assert_all_recs_contain(recs, pinned_ids, label="all pinned items"):
    pinned_set = set(pinned_ids)
    assert recs, "No recommendations returned"
    for i, rec in enumerate(recs):
        rec_ids = {item.id for item in rec["clothing_items"]}
        missing = pinned_set - rec_ids
        assert not missing, (
            f"Recommendation #{i+1} is missing {label} "
            f"(missing IDs: {missing}, got IDs: {rec_ids})"
        )


# ── Tests ─────────────────────────────────────────────────────────────────────
def run_tests():
    app  = _make_app()
    uid  = _seed(app)

    print("\nWearlytics — Pinned Item Regression Tests")
    print("=" * 60)

    # ── 1. No pinned items → free recommendation ────────────────────────────
    print("\n[1] No pinned items — free AI recommendation")

    def test_free_recommendation():
        with app.app_context():
            recs = recommendation_engine.get_recommendations(user_id=uid, top_n=3)
            assert len(recs) >= 1, "Engine should return at least 1 result with no pins"
            assert "clothing_items" in recs[0]
            assert "score" in recs[0]

    run_test("No pinned items → AI recommendation returns results", test_free_recommendation)

    # ── 2. Pinned Top ───────────────────────────────────────────────────────
    print("\n[2] Pinned Top")
    sweater_id = _get_id(app, uid, "Black Cashmere Sweater")

    def test_pinned_top():
        with app.app_context():
            recs = recommendation_engine.get_recommendations(
                user_id=uid, top_n=3, pinned_item_ids=[sweater_id]
            )
            _assert_all_recs_contain(recs, [sweater_id], "Black Cashmere Sweater")

    run_test("Pinned Top → every recommendation contains that Top", test_pinned_top)

    # ── 3. Pinned Bottom ────────────────────────────────────────────────────
    print("\n[3] Pinned Bottom")
    jeans_id = _get_id(app, uid, "Blue Jeans")

    def test_pinned_bottom():
        with app.app_context():
            recs = recommendation_engine.get_recommendations(
                user_id=uid, top_n=3, pinned_item_ids=[jeans_id]
            )
            _assert_all_recs_contain(recs, [jeans_id], "Blue Jeans")

    run_test("Pinned Bottom → every recommendation contains that Bottom", test_pinned_bottom)

    # ── 4. Pinned Dress ─────────────────────────────────────────────────────
    print("\n[4] Pinned Dress")
    dress_id = _get_id(app, uid, "Silk Floral Summer Dress")

    def test_pinned_dress():
        with app.app_context():
            recs = recommendation_engine.get_recommendations(
                user_id=uid, top_n=3, pinned_item_ids=[dress_id]
            )
            _assert_all_recs_contain(recs, [dress_id], "Silk Floral Summer Dress")

    run_test("Pinned Dress → every recommendation contains that Dress", test_pinned_dress)

    # ── 5. Multiple pinned items (Top + Bottom) ─────────────────────────────
    print("\n[5] Multiple pinned items")
    trousers_id = _get_id(app, uid, "Black Trousers")

    def test_multiple_pinned():
        with app.app_context():
            recs = recommendation_engine.get_recommendations(
                user_id=uid, top_n=3, pinned_item_ids=[sweater_id, trousers_id]
            )
            _assert_all_recs_contain(recs, [sweater_id, trousers_id],
                                     "Black Cashmere Sweater + Black Trousers")

    run_test("Multiple pinned (Top+Bottom) → every result contains BOTH", test_multiple_pinned)

    # ── 6. Laundry item excluded ─────────────────────────────────────────────
    print("\n[6] Laundry item excluded")

    def test_laundry_excluded():
        with app.app_context():
            dirty_id = ClothingItem.query.filter_by(
                user_id=uid, name="Dirty T-Shirt"
            ).first().id
            recs = recommendation_engine.get_recommendations(user_id=uid, top_n=5)
            for rec in recs:
                ids = [i.id for i in rec["clothing_items"]]
                assert dirty_id not in ids, "In-laundry item appeared in results"

    run_test("Laundry item is never included in recommendations", test_laundry_excluded)

    # ── 7. No compatible combination → empty list ────────────────────────────
    print("\n[7] No compatible combination")

    def test_no_compatible_combination():
        with app.app_context():
            # Use an impossible set of IDs that don't exist
            recs = recommendation_engine.get_recommendations(
                user_id=uid, top_n=3, pinned_item_ids=[999999]
            )
            assert recs == [], (
                f"Expected empty list when pinned ID doesn't exist, got {recs}"
            )

    run_test("Non-existent pinned ID → engine returns [] (caller shows error)", test_no_compatible_combination)

    # ── 8. More Outfit Options → all contain pinned items ───────────────────
    print("\n[8] More Outfit Options all contain pinned items")

    def test_more_outfit_options_pinned():
        with app.app_context():
            recs = recommendation_engine.get_recommendations(
                user_id=uid, top_n=3, pinned_item_ids=[sweater_id]
            )
            # All top_n results must contain the pinned item
            _assert_all_recs_contain(recs, [sweater_id], "Black Cashmere Sweater")
            # Should have at least 1 (and potentially 2-3 More Outfit Options)
            assert len(recs) >= 1

    run_test("More Outfit Options → all results contain pinned item", test_more_outfit_options_pinned)

    # ── 9. Let AI Choose (no pins) → free recommendation ───────────────────
    print("\n[9] Let AI Choose — no item_ids → free recommendation")

    def test_let_ai_choose():
        with app.app_context():
            recs = recommendation_engine.get_recommendations(
                user_id=uid, top_n=3, pinned_item_ids=None
            )
            assert len(recs) >= 1, "Let AI Choose should return results"
            # Results should NOT be restricted to any specific item
            assert "clothing_items" in recs[0]

    run_test("Let AI Choose (no pins) → free recommendation works", test_let_ai_choose)

    # ── 10. Pinned item survives season filter ──────────────────────────────
    print("\n[10] Pinned item survives season filter")

    def test_pinned_survives_season_filter():
        with app.app_context():
            # Black Cashmere Sweater is season=Winter
            # Request Summer season — sweater would normally be filtered out
            # but since it's pinned it must still appear in results
            recs = recommendation_engine.get_recommendations(
                user_id=uid,
                season="Summer",
                top_n=3,
                pinned_item_ids=[sweater_id],
            )
            # Engine should still return results containing the sweater
            # (it bypasses the season filter for pinned items)
            _assert_all_recs_contain(recs, [sweater_id],
                                     "pinned sweater (Winter item, despite Summer filter)")

    run_test("Pinned item survives conflicting season filter", test_pinned_survives_season_filter)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TEST SUMMARY — Pinned Item Constraints")
    print("=" * 60)
    passed = sum(1 for ok, _ in RESULTS if ok)
    total  = len(RESULTS)
    for ok, name in RESULTS:
        print(f"  {'✅' if ok else '❌'}  {name}")
    print(f"\nResult: {passed}/{total} tests passed")
    if passed == total:
        print("All pinned item tests PASSED ✓")
    else:
        print(f"WARNING: {total - passed} test(s) FAILED")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
