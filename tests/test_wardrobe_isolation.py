import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app import create_app, db
from app.models.user import User

@pytest.fixture
def app_client():
    app = create_app(test_config={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///test_wardrobe_isolation.db",
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    print("[TEST DEBUG] SQLALCHEMY_DATABASE_URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def login(client, email, password):
    resp = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=False)
    assert resp.status_code in (200, 302)
    # Follow redirect if present to establish session
    if resp.status_code == 302:
        resp = client.get(resp.headers.get('Location'), follow_redirects=True)
    assert resp.status_code == 200
    return resp

def register(client, name, email, password, is_demo=False):
    data = {
        "name": name,
        "email": email,
        "password": password,
        "confirm_password": password,
        "is_demo": "1" if is_demo else "0",
    }
    resp = client.post("/auth/register", data=data, follow_redirects=False)
    assert resp.status_code in (200, 302)
    if resp.status_code == 302:
        resp = client.get(resp.headers.get('Location'), follow_redirects=True)
    return User.query.filter_by(email=email).first()


def add_item(client, name):
    data = {
        "name": name,
        "category": "Tops",
        "color": "Red",
        "season": "All Seasons",
        "brand": "TestBrand",
        "image_url": "",
        "wear_count": 0,
        "is_favorite": False,
    }
    resp = client.post("/wardrobe/upload", data=data, follow_redirects=True)
    assert resp.status_code == 200
    return resp

def get_wardrobe(client):
    resp = client.get("/wardrobe/?json=1", follow_redirects=False)
    if resp.status_code == 302:
        # Follow redirect to establish session or login page
        resp = client.get(resp.headers.get('Location'), follow_redirects=True)
    assert resp.status_code == 200
    return resp.get_json().get("items", [])

def test_new_user_has_empty_wardrobe(app_client):
    client = app_client
    register(client, "newuser", "new@example.com", "strongpwd123")
    items = get_wardrobe(client)
    assert items == []

def test_user_isolation(app_client):
    client = app_client
    # User A
    register(client, "usera", "a@example.com", "strongpwd123")
    add_item(client, "Shirt A")
    items_a = get_wardrobe(client)
    client.get("/auth/logout")
    # User B
    register(client, "userb", "b@example.com", "strongpwd123")
    add_item(client, "Shirt B")
    items_b = get_wardrobe(client)
    assert any(item["name"] == "Shirt A" for item in items_a)
    assert not any(item["name"] == "Shirt B" for item in items_a)
    assert any(item["name"] == "Shirt B" for item in items_b)
    assert not any(item["name"] == "Shirt A" for item in items_b)

def test_demo_user_seeds_wardrobe(app_client):
    client = app_client
    register(client, "demo", "demo@demo.com", "strongpwd123", is_demo=True)
    items = get_wardrobe(client)
    assert len(items) > 0


def test_new_user_has_clean_profile_and_no_fake_outfits(app_client):
    client = app_client
    register(client, "Clean User", "clean@example.com", "strongpwd123", is_demo=False)

    # 1. Dashboard has no fake look image and clean empty state
    resp_home = client.get("/")
    assert resp_home.status_code == 200
    html_home = resp_home.data.decode("utf-8")
    assert "ref-todays-empty" in html_home
    assert "ref-look-thumbnail" not in html_home
    assert "Your wardrobe is empty" in html_home

    # 2. Today's Look standalone page has clean empty card and no fake score
    resp_look = client.get("/todays-look")
    assert resp_look.status_code == 200
    html_look = resp_look.data.decode("utf-8")
    assert "todays-look-empty-card" in html_look
    assert "No Outfit for Today Yet" in html_look
    assert '<div class="editorial-hero-card">' not in html_look
    assert '<div class="compatibility-score-pill">' not in html_look
    assert "94/100" not in html_look

    # 3. Profile has empty inputs and no fake phone or DOB
    resp_prof = client.get("/profile/")
    assert resp_prof.status_code == 200
    html_prof = resp_prof.data.decode("utf-8")
    assert "98765 43210" not in html_prof
    assert "2004-08-07" not in html_prof
    assert "07 Aug 2004" not in html_prof
    assert "169 cm" not in html_prof
    assert "46 kg" not in html_prof

