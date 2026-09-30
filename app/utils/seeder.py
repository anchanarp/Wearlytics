"""Utility module for auto-seeding sample wardrobe data."""

from app.extensions import db
from app.models.clothing import ClothingItem
from app.models.outfit import Outfit
from app.models.planner import WeeklyPlan


SAMPLE_ITEMS = [
    {
        "name": "Classic White Linen Shirt",
        "category": "Tops",
        "color": "White",
        "season": "Summer",
        "brand": "Uniqlo",
        "image_url": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=600&auto=format&fit=crop&q=80",
        "wear_count": 14,
        "is_favorite": True,
    },
    {
        "name": "Vintage Denim Jacket",
        "category": "Outerwear",
        "color": "Denim",
        "season": "Spring/Fall",
        "brand": "Levi's",
        "image_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=600&auto=format&fit=crop&q=80",
        "wear_count": 22,
        "is_favorite": True,
    },
    {
        "name": "Tailored Navy Trousers",
        "category": "Bottoms",
        "color": "Navy",
        "season": "All Seasons",
        "brand": "COS",
        "image_url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&auto=format&fit=crop&q=80",
        "wear_count": 18,
        "is_favorite": False,
    },
    {
        "name": "Minimalist White Sneakers",
        "category": "Shoes",
        "color": "White",
        "season": "All Seasons",
        "brand": "Common Projects",
        "image_url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&auto=format&fit=crop&q=80",
        "wear_count": 31,
        "is_favorite": True,
    },
    {
        "name": "Black Cashmere Crewneck Sweater",
        "category": "Tops",
        "color": "Black",
        "season": "Winter",
        "brand": "Everlane",
        "image_url": "https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=600&auto=format&fit=crop&q=80",
        "wear_count": 9,
        "is_favorite": True,
    },
    {
        "name": "Slim Fit Beige Chinos",
        "category": "Bottoms",
        "color": "Beige",
        "season": "Spring/Fall",
        "brand": "J.Crew",
        "image_url": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=600&auto=format&fit=crop&q=80",
        "wear_count": 11,
        "is_favorite": False,
    },
    {
        "name": "Leather Chelsea Boots",
        "category": "Shoes",
        "color": "Brown",
        "season": "Winter",
        "brand": "Dr. Martens",
        "image_url": "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=600&auto=format&fit=crop&q=80",
        "wear_count": 15,
        "is_favorite": False,
    },
    {
        "name": "Olive Green Trench Coat",
        "category": "Outerwear",
        "color": "Olive",
        "season": "Spring/Fall",
        "brand": "Burberry",
        "image_url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=600&auto=format&fit=crop&q=80",
        "wear_count": 7,
        "is_favorite": True,
    },
    {
        "name": "Silk Floral Summer Dress",
        "category": "Dresses",
        "color": "Multicolor",
        "season": "Summer",
        "brand": "Reformation",
        "image_url": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=600&auto=format&fit=crop&q=80",
        "wear_count": 5,
        "is_favorite": True,
    },
    {
        "name": "Classic Leather Chronograph Watch",
        "category": "Accessories",
        "color": "Brown",
        "season": "All Seasons",
        "brand": "Seiko",
        "image_url": "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=600&auto=format&fit=crop&q=80",
        "wear_count": 45,
        "is_favorite": True,
    },
]


def seed_user_wardrobe(user):
    """Seed initial clothing items, outfits, and weekly plans for a new user if empty.
    Only runs for demo users (is_demo flag)."""
    # Only seed demo accounts
    if not getattr(user, "is_demo", False):
        return
    if user.clothing_items.count() > 0:
        return

    items_dict = {}
    for item_data in SAMPLE_ITEMS:
        item = ClothingItem(
            user_id=user.id,
            name=item_data["name"],
            category=item_data["category"],
            color=item_data["color"],
            season=item_data["season"],
            brand=item_data["brand"],
            image_url=item_data["image_url"],
            wear_count=item_data["wear_count"],
            is_favorite=item_data["is_favorite"],
        )
        db.session.add(item)
        db.session.flush()
        items_dict[item_data["name"]] = item

    # Seed Sample Outfits
    outfit1 = Outfit(
        user_id=user.id,
        title="Smart Casual Office Look",
        description="Crisp linen shirt paired with tailored navy trousers and clean white sneakers.",
        occasion="Work",
        season="Spring/Fall",
        is_favorite=True,
    )
    outfit1.items.extend([items_dict["Classic White Linen Shirt"], items_dict["Tailored Navy Trousers"], items_dict["Minimalist White Sneakers"]])

    outfit2 = Outfit(
        user_id=user.id,
        title="Weekend Cozy Layering",
        description="Black cashmere crewneck topped with a vintage denim jacket and beige chinos.",
        occasion="Casual",
        season="Spring/Fall",
        is_favorite=True,
    )
    outfit2.items.extend([items_dict["Black Cashmere Crewneck Sweater"], items_dict["Vintage Denim Jacket"], items_dict["Slim Fit Beige Chinos"], items_dict["Leather Chelsea Boots"]])

    outfit3 = Outfit(
        user_id=user.id,
        title="Summer Breeze Elegant",
        description="Flowy silk floral dress with white sneakers and leather watch.",
        occasion="Date Night",
        season="Summer",
        is_favorite=False,
    )
    outfit3.items.extend([items_dict["Silk Floral Summer Dress"], items_dict["Minimalist White Sneakers"], items_dict["Classic Leather Chronograph Watch"]])

    db.session.add_all([outfit1, outfit2, outfit3])
    db.session.flush()

    # Seed Weekly Plan
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    plans = [
        WeeklyPlan(user_id=user.id, day_of_week="Monday", outfit_id=outfit1.id, notes="Team sync & client presentations"),
        WeeklyPlan(user_id=user.id, day_of_week="Tuesday", outfit_id=outfit2.id, notes="Work from cafe & coffee meeting"),
        WeeklyPlan(user_id=user.id, day_of_week="Wednesday", outfit_id=outfit1.id, notes="Midweek office day"),
        WeeklyPlan(user_id=user.id, day_of_week="Thursday", outfit_id=outfit2.id, notes="Casual Thursday"),
        WeeklyPlan(user_id=user.id, day_of_week="Friday", outfit_id=outfit3.id, notes="Dinner & drinks after work"),
        WeeklyPlan(user_id=user.id, day_of_week="Saturday", outfit_id=outfit2.id, notes="Weekend market walk"),
        WeeklyPlan(user_id=user.id, day_of_week="Sunday", outfit_id=outfit1.id, notes="Relaxed family brunch"),
    ]
    db.session.add_all(plans)
    db.session.commit()
