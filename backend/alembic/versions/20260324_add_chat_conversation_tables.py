"""Add chat conversation tables

Revision ID: 20260324_chat
Revises: 4492e569ccf9
Create Date: 2026-03-24 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260324_chat"
down_revision: Union[str, Sequence[str], None] = "4492e569ccf9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chatconversation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chatconversation_updated_at"), "chatconversation", ["updated_at"], unique=False)
    op.create_index(op.f("ix_chatconversation_user_id"), "chatconversation", ["user_id"], unique=False)

    op.create_table(
        "chatmessage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["chatconversation.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chatmessage_conversation_id"), "chatmessage", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_chatmessage_created_at"), "chatmessage", ["created_at"], unique=False)
    op.create_index(op.f("ix_chatmessage_sequence"), "chatmessage", ["sequence"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chatmessage_sequence"), table_name="chatmessage")
    op.drop_index(op.f("ix_chatmessage_created_at"), table_name="chatmessage")
    op.drop_index(op.f("ix_chatmessage_conversation_id"), table_name="chatmessage")
    op.drop_table("chatmessage")

    op.drop_index(op.f("ix_chatconversation_user_id"), table_name="chatconversation")
    op.drop_index(op.f("ix_chatconversation_updated_at"), table_name="chatconversation")
    op.drop_table("chatconversation")
