from alembic import op
import sqlalchemy as sa

revision = "e0bbb50d1f4c"
down_revision = "e73cf1689148"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())

    # Fresh database: create users with password_hash.
    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=150), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index("ix_users_id", "users", ["id"], unique=False)
        op.create_index("ix_users_email", "users", ["email"], unique=True)

        return

    # Existing database: inspect the current users columns.
    columns = {column["name"] for column in inspector.get_columns("users")}

    has_password = "password" in columns
    has_password_hash = "password_hash" in columns

    if has_password and has_password_hash:
        raise RuntimeError(
            "Users table contains both password and password_hash. "
            "Manual schema review is required."
        )

    if has_password:
        op.alter_column(
            "users",
            "password",
            new_column_name="password_hash",
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )

    elif not has_password_hash:
        raise RuntimeError(
            "Users table exists but neither password nor password_hash was found."
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}

    has_password = "password" in columns
    has_password_hash = "password_hash" in columns

    if has_password and has_password_hash:
        raise RuntimeError(
            "Users table contains both password and password_hash. "
            "Manual schema review is required."
        )

    if has_password_hash:
        op.alter_column(
            "users",
            "password_hash",
            new_column_name="password",
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )

    elif not has_password:
        raise RuntimeError("Users table contains neither password nor password_hash.")
