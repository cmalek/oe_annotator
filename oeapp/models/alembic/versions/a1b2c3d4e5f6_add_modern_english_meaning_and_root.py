"""
Add modern_english_meaning and root fields

Revision ID: a1b2c3d4e5f6
Revises: 57399ca978ee
Create Date: 2025-01-27 12:00:00.000000

"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "57399ca978ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Upgrade schema.
    """
    with op.batch_alter_table("annotations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("modern_english_meaning", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("root", sa.String(), nullable=True))


def downgrade() -> None:
    """
    Downgrade schema.
    """
    with op.batch_alter_table("annotations", schema=None) as batch_op:
        batch_op.drop_column("root")
        batch_op.drop_column("modern_english_meaning")

