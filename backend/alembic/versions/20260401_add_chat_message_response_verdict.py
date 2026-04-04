"""Add chat message response verdict field

Revision ID: 20260401_chat_response_verdict
Revises: 20260324_chat_evidence_panel
Create Date: 2026-04-01 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_chat_response_verdict"
down_revision: Union[str, Sequence[str], None] = "20260324_chat_evidence_panel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.add_column(sa.Column("response_verdict", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.drop_column("response_verdict")
