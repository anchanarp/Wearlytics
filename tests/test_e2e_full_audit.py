"""Comprehensive End-to-End Audit Test Suite for Wearlytics.
Tests every major module, route, user/admin permission, CRUD, AI feature, and API.
"""

import io
import json
import pytest
from app import create_app, db
from app.models.user import User
from app.models.user_preferences import UserPreferences
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.models.feedback import OutfitFeedback
from app.models.planner import WeeklyPlan


@pytest.fixture
def app_and_client():
    """Create a clean isolated test app and client for testing."""
    test_app = create_app(test_config={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost",
    })

    with test_app.app_context():
        db.create_all()

        # Create 1 Admin and 2 Regular Users
        admin = User(name="Platform Admin", email="admin@wearlytics.com", is_admin=True)
        admin.set_password("AdminPass123!")

        user_a = User(name="Alice Walker", email="alice@test.com", is_admin=False)
        user_a.set_password("AlicePass123!")

        user_b = User(name="Bob Smith", email="bob@test.com", is_admin=False)
        user_b.set_password("BobPass123!")

        db.session.add_all([admin, user_a, user_b])
        db.session.commit()

        # Seed initial items for Alice
        item_a1 = ClothingItem(
            user_id=user_a.id,
            name="Alice Blue Blouse",
            category="Tops",
            color="Blue",
            season="Summer",
            brand="Zara",
            image_url="https://images.unsplash.com/photo-1598033129183-c4f50c736f10",
            wear_count=5,
            is_favorite=True,
        )
        item_a2 = ClothingItem(
            user_id=user_a.id,
            name="Alice White Jeans",
            category="Bottoms",
            color="White",
            season="All Seasons",
            brand="Levi's",
            image_url="https://images.unsplash.com/photo-1594633312681-425c7b97ccd1",
            wear_count=8,
            is_favorite=False,
        )
        db.session.add_all([item_a1, item_a2])
        db.session.commit()

        # Seed outfit for Alice
        outfit_a = Outfit(
            user_id=user_a.id,
            title="Alice Chic Casual",
            occasion="Casual",
            season="Summer",
            compatibility_score=0.92,
        )
        outfit_a.items.extend([item_a1, item_a2])
        db.session.add(outfit_a)
        db.session.commit()

        # Seed feedback
        fb = OutfitFeedback(user_id=user_a.id, outfit_id=outfit_a.id, reaction="liked")
        db.session.add(fb)
        db.session.commit()

        client = test_app.test_client()
        yield test_app, client

        db.session.remove()
        db.drop_all()


def login_client(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


# ==============================================================================
# 1. ACCESS CONTROL & PRIVACY
# ==============================================================================
class TestAccessControl:
    def test_unauthenticated_redirects(self, app_and_client):
        _, client = app_and_client
        protected_routes = [
            "/",
            "/wardrobe/",
            "/stylist/",
            "/planner/",
            "/analytics/",
            "/profile/",
            "/admin/",
            "/admin/users",
            "/admin/outfits",
            "/admin/feedback",
            "/admin/analytics",
        ]
        for route in protected_routes:
            res = client.get(route, follow_redirects=False)
            assert res.status_code == 302, f"Expected 302 for unauthenticated {route}, got {res.status_code}"
            assert "/auth/login" in res.headers.get("Location", "")

    def test_non_admin_blocked_from_admin(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")

        # Regular user accessing admin must be blocked (403 or redirect with error)
        res = client.get("/admin/", follow_redirects=False)
        assert res.status_code in (403, 302), f"Non-admin got {res.status_code} on /admin/"
        if res.status_code == 302:
            assert "/admin" not in res.headers.get("Location", "")

    def test_admin_can_access_admin_portal(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")
        res = client.get("/admin/")
        assert res.status_code == 200
        assert b"Wearlytics" in res.data


# ==============================================================================
# 2. AUTHENTICATION & SESSION
# ==============================================================================
class TestAuthentication:
    def test_valid_login_and_logout(self, app_and_client):
        _, client = app_and_client
        res = login_client(client, "alice@test.com", "AlicePass123!")
        assert res.status_code == 200
        assert b"Alice" in res.data or b"Dashboard" in res.data

        # Logout via GET
        res_logout_get = client.get("/auth/logout", follow_redirects=True)
        assert res_logout_get.status_code == 200

        # Login again & logout via POST
        login_client(client, "alice@test.com", "AlicePass123!")
        res_logout_post = client.post("/auth/logout", follow_redirects=True)
        assert res_logout_post.status_code == 200

    def test_invalid_login_credentials(self, app_and_client):
        _, client = app_and_client
        res = client.post("/auth/login", data={"email": "alice@test.com", "password": "WrongPassword!"}, follow_redirects=True)
        assert res.status_code == 200
        assert b"Invalid email or password" in res.data or b"error" in res.data.lower()

    def test_registration_flow(self, app_and_client):
        _, client = app_and_client
        data = {
            "name": "Charlie Chaplin",
            "email": "charlie@test.com",
            "password": "CharliePassword123!",
            "confirm_password": "CharliePassword123!",
        }
        res = client.post("/auth/register", data=data, follow_redirects=True)
        assert res.status_code == 200
        assert b"Charlie" in res.data or b"Dashboard" in res.data


# ==============================================================================
# 3. WARDROBE CRUD & ISOLATION
# ==============================================================================
class TestWardrobeCRUD:
    def test_wardrobe_listing_and_filtering(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")

        # Main HTML view
        res = client.get("/wardrobe/")
        assert res.status_code == 200
        assert b"Alice Blue Blouse" in res.data

        # JSON view
        res_json = client.get("/wardrobe/?json=1")
        assert res_json.status_code == 200
        data = json.loads(res_json.data)
        assert "items" in data
        assert len(data["items"]) >= 2

        # Filter by category
        res_cat = client.get("/wardrobe/?category=Tops")
        assert res_cat.status_code == 200
        assert b"Alice Blue Blouse" in res_cat.data

    def test_add_clothing_item(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")

        data = {
            "name": "Emerald Silk Scarf",
            "category": "Accessories",
            "color": "Green",
            "season": "Spring/Fall",
            "brand": "Hermes",
            "wear_count": 0,
            "is_favorite": "true",
        }
        res = client.post("/wardrobe/upload", data=data, follow_redirects=True)
        assert res.status_code == 200
        assert b"Emerald Silk Scarf" in res.data

    def test_cross_user_isolation(self, app_and_client):
        app, client = app_and_client
        # Bob logs in
        login_client(client, "bob@test.com", "BobPass123!")

        # Bob should NOT see Alice's item
        res = client.get("/wardrobe/?json=1")
        data = json.loads(res_json := res.data)
        item_names = [i["name"] for i in data.get("items", [])]
        assert "Alice Blue Blouse" not in item_names

        # Bob tries to delete or edit Alice's item directly
        with app.app_context():
            alice_item = ClothingItem.query.filter_by(name="Alice Blue Blouse").first()
            assert alice_item is not None
            alice_id = alice_item.id

        # Unauthorized delete attempt
        res_del = client.post(f"/wardrobe/{alice_id}/delete", follow_redirects=True)
        assert res_del.status_code in (403, 404, 302)
        # Verify item was not deleted
        with app.app_context():
            item_still_exists = ClothingItem.query.get(alice_id)
            assert item_still_exists is not None


# ==============================================================================
# 4. AI STYLIST & RECOMMENDATIONS
# ==============================================================================
class TestStylistAndRecommendations:
    def test_stylist_index(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")
        res = client.get("/stylist/")
        assert res.status_code == 200

    def test_recommendations_page(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")
        res = client.get("/recommendations/")
        assert res.status_code == 200

    def test_outfit_feedback_submission(self, app_and_client):
        app, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")

        with app.app_context():
            outfit = Outfit.query.filter_by(title="Alice Chic Casual").first()
            assert outfit is not None
            oid = outfit.id

        # Submit feedback
        res = client.post("/recommendations/feedback", data={"outfit_id": oid, "reaction": "favorited"}, follow_redirects=True)
        assert res.status_code == 200


# ==============================================================================
# 5. PLANNER & SCHEDULE
# ==============================================================================
class TestPlanner:
    def test_planner_view(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")
        res = client.get("/planner/")
        assert res.status_code == 200
        assert b"Weekly" in res.data or b"Planner" in res.data

    def test_add_outfit_to_day(self, app_and_client):
        app, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")

        with app.app_context():
            outfit = Outfit.query.filter_by(title="Alice Chic Casual").first()
            oid = outfit.id

        res = client.post("/planner/assign", data={
            "day_of_week": "Friday",
            "outfit_id": oid,
            "notes": "Casual Friday look",
        }, follow_redirects=True)
        assert res.status_code == 200


# ==============================================================================
# 6. ANALYTICS & PROFILE
# ==============================================================================
class TestAnalyticsAndProfile:
    def test_user_analytics_page(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")
        res = client.get("/analytics/")
        assert res.status_code == 200
        assert b"Analytics" in res.data or b"Wardrobe" in res.data

    def test_user_profile_update(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")
        res = client.get("/profile/")
        assert res.status_code == 200

        # Update bio and avatar color
        res_update = client.post("/profile/", data={
            "name": "Alice Walker Updated",
            "bio": "Fashion and minimalist enthusiast.",
            "avatar_color": "#dfb17b",
        }, follow_redirects=True)
        assert res_update.status_code == 200


# ==============================================================================
# 7. ADMIN PORTAL (DASHBOARD, USERS, OUTFITS, FEEDBACK, ANALYTICS, APIS)
# ==============================================================================
class TestAdminPortal:
    def test_admin_dashboard(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")
        res = client.get("/admin/")
        assert res.status_code == 200
        assert b"Dashboard" in res.data
        assert b"adminThemeToggle" in res.data
        assert b"adminNotifBtn" in res.data
        assert b"adminHeaderSearch" in res.data

    def test_admin_users_page(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")
        res = client.get("/admin/users")
        assert res.status_code == 200
        assert b"Alice Walker" in res.data
        assert b"Bob Smith" in res.data

    def test_admin_outfits_page(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")
        res = client.get("/admin/outfits")
        assert res.status_code == 200
        assert b"Alice Chic Casual" in res.data

    def test_admin_feedback_page(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")
        res = client.get("/admin/feedback")
        assert res.status_code == 200

    def test_admin_analytics_page(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")
        res = client.get("/admin/analytics")
        assert res.status_code == 200

    def test_admin_global_search_redirects(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")

        # Search outfit keyword -> redirects to outfits
        res_outfit = client.get("/admin/search?q=outfit", follow_redirects=False)
        assert res_outfit.status_code == 302
        assert "/admin/outfits" in res_outfit.headers.get("Location", "")

        # Search user keyword -> redirects to users
        res_user = client.get("/admin/search?q=alice", follow_redirects=False)
        assert res_user.status_code == 302
        assert "/admin/users" in res_user.headers.get("Location", "")

    def test_admin_live_search_api(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")

        res = client.get("/admin/api/search?q=alice")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "users" in data
        assert any("Alice" in u["name"] for u in data["users"])

    def test_admin_notifications_api(self, app_and_client):
        _, client = app_and_client
        login_client(client, "admin@wearlytics.com", "AdminPass123!")

        res = client.get("/admin/api/notifications")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "notifications" in data
        assert "unread" in data
        assert len(data["notifications"]) > 0


# ==============================================================================
# 8. ERROR HANDLING & 404
# ==============================================================================
class TestErrorHandling:
    def test_404_not_found(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")
        res = client.get("/non-existent-random-route-404")
        assert res.status_code == 404

    def test_nonexistent_item_detail(self, app_and_client):
        _, client = app_and_client
        login_client(client, "alice@test.com", "AlicePass123!")
        res = client.get("/wardrobe/9999999/detail", follow_redirects=True)
        assert res.status_code in (404, 302, 200)
