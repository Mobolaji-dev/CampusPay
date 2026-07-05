"""update_approles_enum_casing

Revision ID: ad40e6033360
Revises: bf8ea64cd283
Create Date: 2026-07-06 00:24:29.753540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad40e6033360'
down_revision: Union[str, Sequence[str], None] = 'bf8ea64cd283'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE approles RENAME VALUE 'vendor' TO 'Vendor'")
    op.execute("ALTER TYPE approles RENAME VALUE 'admin' TO 'Admin'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE approles RENAME VALUE 'Vendor' TO 'vendor'")
    op.execute("ALTER TYPE approles RENAME VALUE 'Admin' TO 'admin'")

