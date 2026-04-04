"""Add chat conversation archive field

Revision ID: 20260324_chat_archive
Revises: 20260324_chat_meta
Create Date: 2026-03-24 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260324_chat_archive"
down_revision: Union[str, Sequence[str], None] = "20260324_chat_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chatconversation", schema=None) as batch_op:
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_chatconversation_archived_at", ["archived_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("chatconversation", schema=None) as batch_op:
        batch_op.drop_index("ix_chatconversation_archived_at")
        batch_op.drop_column("archived_at")
