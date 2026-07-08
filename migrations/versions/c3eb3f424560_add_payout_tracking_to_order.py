"""add payout tracking to order
Revision ID: c3eb3f424560
Revises: 219db5d9acbc
Create Date: 2026-07-08 21:37:51.028818
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3eb3f424560'
down_revision: Union[str, Sequence[str], None] = '219db5d9acbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

payoutstat_enum = sa.Enum("not_attempted", "success", "failed", name="payoutstat")


def upgrade() -> None:
    """Upgrade schema."""
    payoutstat_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "order",
        sa.Column("payout_status", payoutstat_enum, nullable=False, server_default="not_attempted"),
    )
    op.add_column("order", sa.Column("payout_last_error", sa.Text(), nullable=True))
    op.add_column(
        "order",
        sa.Column("payout_attempts", sa.Integer(), nullable=False, server_default="0"),
    )

    # Backfill existing rows based on current state.
    # NOTE: orderstat enum values are title-cased ('Confirmed'), payoutstat is snake_case.
    op.execute("""
        UPDATE "order"
        SET payout_status = CASE
            WHEN nomba_transfer_ref IS NOT NULL THEN 'success'
            WHEN order_status = 'Confirmed' THEN 'failed'
            ELSE 'not_attempted'
        END
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order", "payout_attempts")
    op.drop_column("order", "payout_last_error")
    op.drop_column("order", "payout_status")
    payoutstat_enum.drop(op.get_bind(), checkfirst=True)