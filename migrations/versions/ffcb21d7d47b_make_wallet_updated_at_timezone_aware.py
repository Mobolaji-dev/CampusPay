"""make wallet.updated_at timezone-aware

Revision ID: ffcb21d7d47b
Revises: 40541ea47af9
Create Date: 2026-07-05 01:04:26.753695
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ffcb21d7d47b'
down_revision: Union[str, Sequence[str], None] = '40541ea47af9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE wallet "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE wallet "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )