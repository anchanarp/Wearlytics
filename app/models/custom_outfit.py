from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.extensions import db

# Association table linking custom outfits to clothing items
custom_outfit_items = Table(
    "custom_outfit_items",
    db.metadata,
    Column("outfit_id", Integer, ForeignKey("custom_outfits.id"), primary_key=True),
    Column("item_id", Integer, ForeignKey("clothing_items.id"), primary_key=True),
)

class CustomOutfit(db.Model):
    __tablename__ = "custom_outfits"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=True)  # optional custom name
    note = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # many-to-many relationship to ClothingItem
    items = relationship("ClothingItem", secondary=custom_outfit_items, backref="custom_outfits")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "note": self.note,
            "item_ids": [i.id for i in self.items],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
