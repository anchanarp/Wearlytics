"""add wear date laundry status and profile fields

Revision ID: a1b2c3d4e5f6
Revises: 932f89933323
Create Date: 2026-09-12 19:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '932f89933323'
branch_labels = None
depends_on = None


def upgrade():
    # clothing_items: wear history date + laundry status
    with op.batch_alter_table('clothing_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_worn_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('is_in_laundry', sa.Boolean(), nullable=False, server_default=sa.false()))

    # users: avatar color + short bio
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('avatar_color', sa.String(length=20), nullable=True, server_default='#6c5ce7'))
        batch_op.add_column(sa.Column('bio', sa.String(length=200), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('bio')
        batch_op.drop_column('avatar_color')

    with op.batch_alter_table('clothing_items', schema=None) as batch_op:
        batch_op.drop_column('is_in_laundry')
        batch_op.drop_column('last_worn_at')
