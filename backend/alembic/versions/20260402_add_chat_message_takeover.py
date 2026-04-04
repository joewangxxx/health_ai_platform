"""Add chat message takeover field

Revision ID: 20260402_chat_takeover
Revises: 20260401_chat_response_verdict
Create Date: 2026-04-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_chat_takeover"
down_revision: Union[str, Sequence[str], None] = "20260401_chat_response_verdict"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.add_column(sa.Column("takeover", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.drop_column("takeover")
