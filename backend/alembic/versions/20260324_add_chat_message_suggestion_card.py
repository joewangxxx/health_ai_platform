"""Add chat message suggestion card field

Revision ID: 20260324_chat_suggestion_card
Revises: 20260324_chat_pin_access
Create Date: 2026-03-24 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260324_chat_suggestion_card"
down_revision: Union[str, Sequence[str], None] = "20260324_chat_pin_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "suggestion_card",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.drop_column("suggestion_card")
