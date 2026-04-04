"""Add chat message metadata columns

Revision ID: 20260324_chat_meta
Revises: 20260324_chat
Create Date: 2026-03-24 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260324_chat_meta"
down_revision: Union[str, Sequence[str], None] = "20260324_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sources", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("evidence_tags", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("decision_summary", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chatmessage", schema=None) as batch_op:
        batch_op.drop_column("decision_summary")
        batch_op.drop_column("evidence_tags")
        batch_op.drop_column("sources")
