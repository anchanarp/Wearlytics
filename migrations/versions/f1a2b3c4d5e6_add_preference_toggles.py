"""add preference toggle columns to user_preferences

Revision ID: f1a2b3c4d5e6
Revises: 932f89933323
Create Date: 2026-09-13 00:03:00.000000

Adds boolean toggle columns to user_preferences:
  use_preferences      — master switch; False = ignore all preferences
  use_style            — apply preferred styles to scoring
  use_color            — apply preferred/disliked colors to scoring
  use_occasion         — apply preferred occasions to scoring
  use_season           — apply preferred seasons to scoring
  use_body_shape       — placeholder (no body shape data yet)
  use_clothing_size    — placeholder
  use_fit_preference   — placeholder
  use_feedback_learning — apply liked/disliked item bonuses

Safe defaults for existing users preserve current behavior (all True
except the three placeholder fields which default False).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'd4f5e6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_preferences', schema=None) as batch_op:
        batch_op.add_column(sa.Column('use_preferences',      sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('use_style',            sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('use_color',            sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('use_occasion',         sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('use_season',           sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('use_body_shape',       sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('use_clothing_size',    sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('use_fit_preference',   sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('use_feedback_learning',sa.Boolean(), nullable=False, server_default='1'))


def downgrade():
    with op.batch_alter_table('user_preferences', schema=None) as batch_op:
        batch_op.drop_column('use_feedback_learning')
        batch_op.drop_column('use_fit_preference')
        batch_op.drop_column('use_clothing_size')
        batch_op.drop_column('use_body_shape')
        batch_op.drop_column('use_season')
        batch_op.drop_column('use_occasion')
        batch_op.drop_column('use_color')
        batch_op.drop_column('use_style')
        batch_op.drop_column('use_preferences')
