"""add custom_outfit_id to weekly_plans

Revision ID: 0a1fd2572e04
Revises: 8209cbd35d07
Create Date: 2026-09-30 02:31:01.657562

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a1fd2572e04'
down_revision = '8209cbd35d07'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('weekly_plans', schema=None) as batch_op:
        batch_op.add_column(sa.Column('custom_outfit_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_weekly_plans_custom_outfit_id',
            'custom_outfits', ['custom_outfit_id'], ['id']
        )


def downgrade():
    with op.batch_alter_table('weekly_plans', schema=None) as batch_op:
        batch_op.drop_constraint('fk_weekly_plans_custom_outfit_id', type_='foreignkey')
        batch_op.drop_column('custom_outfit_id')
