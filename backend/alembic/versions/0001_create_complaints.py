"""create complaints table

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CATEGORY = sa.Enum(
    "water",
    "electricity",
    "sanitation",
    "roads",
    "streetlights",
    "other",
    name="complaint_category",
)
PRIORITY = sa.Enum("high", "normal", "low", name="complaint_priority")
STATUS = sa.Enum("open", "in_progress", "resolved", "rejected", name="complaint_status")


def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("reporter_contact", sa.String(200), nullable=True),
        sa.Column("category", CATEGORY, nullable=False),
        sa.Column("priority", PRIORITY, nullable=False),
        sa.Column("status", STATUS, nullable=False, server_default="open"),
        sa.Column("ai_summary", sa.String(140), nullable=True),
        sa.Column("triaged_by", sa.String(32), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Enforced in the DB as well as the app: a bug or a manual INSERT can't bypass it.
        sa.CheckConstraint("length(text) BETWEEN 10 AND 2000", name="ck_complaints_text_len"),
        sa.CheckConstraint("length(location) BETWEEN 3 AND 200", name="ck_complaints_location_len"),
        sa.CheckConstraint("triage_latency_ms >= 0", name="ck_complaints_latency_nonneg"),
        sa.CheckConstraint(
            "triaged_by IN ('llm:groq','llm:ollama','rules','rules:fallback','simulated')",
            name="ck_complaints_triaged_by",
        ),
    )
    # Dashboard filter "WHERE status = ? AND priority = ?" (e.g. open + high).
    op.create_index("ix_complaints_status_priority", "complaints", ["status", "priority"])
    # List ordering "ORDER BY created_at DESC LIMIT/OFFSET" (newest first).
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_complaints_created_at", table_name="complaints")
    op.drop_index("ix_complaints_status_priority", table_name="complaints")
    op.drop_table("complaints")
    bind = op.get_bind()
    for enum in (STATUS, PRIORITY, CATEGORY):
        enum.drop(bind, checkfirst=True)
