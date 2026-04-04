"""Add bounded assistant answer replay table

Revision ID: 20260401_agent_answer_replay
Revises: 20260401_agent_audit_responsibility
Create Date: 2026-04-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_agent_answer_replay"
down_revision: Union[str, Sequence[str], None] = "20260401_agent_audit_responsibility"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agentanswerreplay",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("chat_message_id", sa.Integer(), nullable=False),
        sa.Column("audit_event_id", sa.Integer(), nullable=False),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False),
        sa.Column("execution_snapshot", sa.JSON(), nullable=False),
        sa.Column("context_budget_summary", sa.JSON(), nullable=True),
        sa.Column("tool_result_summary", sa.JSON(), nullable=False),
        sa.Column("rag_source_refs", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["chat_message_id"], ["chatmessage.id"]),
        sa.ForeignKeyConstraint(["audit_event_id"], ["agentauditevent.id"]),
        sa.UniqueConstraint("chat_message_id"),
        sa.UniqueConstraint("audit_event_id"),
    )
    op.create_index(op.f("ix_agentanswerreplay_created_at"), "agentanswerreplay", ["created_at"], unique=False)
    op.create_index(op.f("ix_agentanswerreplay_user_id"), "agentanswerreplay", ["user_id"], unique=False)
    op.create_index(op.f("ix_agentanswerreplay_conversation_id"), "agentanswerreplay", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_agentanswerreplay_chat_message_id"), "agentanswerreplay", ["chat_message_id"], unique=False)
    op.create_index(op.f("ix_agentanswerreplay_audit_event_id"), "agentanswerreplay", ["audit_event_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agentanswerreplay_audit_event_id"), table_name="agentanswerreplay")
    op.drop_index(op.f("ix_agentanswerreplay_chat_message_id"), table_name="agentanswerreplay")
    op.drop_index(op.f("ix_agentanswerreplay_conversation_id"), table_name="agentanswerreplay")
    op.drop_index(op.f("ix_agentanswerreplay_user_id"), table_name="agentanswerreplay")
    op.drop_index(op.f("ix_agentanswerreplay_created_at"), table_name="agentanswerreplay")
    op.drop_table("agentanswerreplay")
