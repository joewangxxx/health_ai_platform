"""Add chat conversation pin and access fields

Revision ID: 20260324_chat_pin_access
Revises: 20260324_chat_archive
Create Date: 2026-03-24 23:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260324_chat_pin_access"
down_revision: Union[str, Sequence[str], None] = "20260324_chat_archive"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chatconversation", schema=None) as batch_op:
        batch_op.add_column(sa.Column("last_accessed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("pinned_at", sa.DateTime(), nullable=True))
        batch_op.create_index(
            "ix_chatconversation_last_accessed_at",
            ["last_accessed_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_chatconversation_pinned_at",
            ["pinned_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("chatconversation", schema=None) as batch_op:
        batch_op.drop_index("ix_chatconversation_pinned_at")
        batch_op.drop_index("ix_chatconversation_last_accessed_at")
        batch_op.drop_column("pinned_at")
        batch_op.drop_column("last_accessed_at")
