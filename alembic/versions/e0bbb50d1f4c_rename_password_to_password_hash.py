from alembic import op
import sqlalchemy as sa

revision = "e0bbb50d1f4c"
down_revision = "e73cf1689148"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password",
        new_column_name="password_hash",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        new_column_name="password",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
