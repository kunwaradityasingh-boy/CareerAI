"""baseline existing database

Revision ID: e73cf1689148
Revises:
Create Date: 2026-11-04 12:44:28.419151
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e73cf1689148"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline migration for an existing database."""
    pass


def downgrade() -> None:
    """No schema changes were made by this baseline."""
    pass
