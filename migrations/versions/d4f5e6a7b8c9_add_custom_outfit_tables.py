"""Add custom_outfits table and custom_outfit_items association.
Revision ID: d4f5e6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-09-12 20:03:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4f5e6a7b8c9'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('custom_outfits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=True),
        sa.Column('note', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('custom_outfit_items',
        sa.Column('outfit_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['outfit_id'], ['custom_outfits.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['clothing_items.id'], ),
        sa.PrimaryKeyConstraint('outfit_id', 'item_id')
    )

def downgrade():
    op.drop_table('custom_outfit_items')
    op.drop_table('custom_outfits')
