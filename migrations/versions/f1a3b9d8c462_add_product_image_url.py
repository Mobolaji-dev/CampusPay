"""add product image url

Revision ID: f1a3b9d8c462
Revises: 0e61f9f36350
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a3b9d8c462'
down_revision: Union[str, Sequence[str], None] = '0e61f9f36350'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('product', sa.Column('image_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('product', 'image_url')
