"""merge vendor migrations

Revision ID: 2a2c1c1069b4
Revises: c6518063f6f1, f1a3b9d8c462
Create Date: 2026-07-07 04:09:03.099561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a2c1c1069b4'
down_revision: Union[str, Sequence[str], None] = ('c6518063f6f1', 'f1a3b9d8c462')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
