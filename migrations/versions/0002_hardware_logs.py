"""Add owner-scoped timestamped hardware command journal."""

import sqlalchemy as sa
from alembic import op

revision = "0002_hardware_logs"
down_revision = "0001_business_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hardware_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("command", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hardware_logs_user_id", "hardware_logs", ["user_id"])
    op.create_index("ix_hardware_logs_created_at", "hardware_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_hardware_logs_created_at", table_name="hardware_logs")
    op.drop_index("ix_hardware_logs_user_id", table_name="hardware_logs")
    op.drop_table("hardware_logs")
