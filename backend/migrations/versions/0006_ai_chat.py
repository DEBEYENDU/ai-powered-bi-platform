"""AI chat tables - conversations and messages.

Revision ID: 0006_ai_chat
Revises: 0005_dashboards
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_ai_chat"
down_revision = "0005_dashboards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), server_default="New conversation"),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("model", sa.String(100), server_default="gpt-4o-mini"),
        sa.Column("provider", sa.String(50), server_default="openai"),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("settings", sa.JSON, nullable=True),
        sa.Column("message_count", sa.Integer, server_default="0"),
        sa.Column("total_tokens", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])
    op.create_index("ix_ai_conversations_updated_at", "ai_conversations", ["updated_at"])

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, server_default="0"),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    op.create_index("ix_ai_messages_created_at", "ai_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
