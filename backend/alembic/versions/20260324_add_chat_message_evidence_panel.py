"""Add chat message evidence panel field

Revision ID: 20260324_chat_evidence_panel
Revises: 20260324_chat_suggestion_card
Create Date: 2026-03-24 23:59:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260324_chat_evidence_panel"
down_revision: Union[str, Sequence[str], None] = "20260324_chat_suggestion_card"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.add_column(sa.Column("evidence_panel", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.drop_column("evidence_panel")
