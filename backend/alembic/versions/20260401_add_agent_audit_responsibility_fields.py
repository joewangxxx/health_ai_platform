"""Add responsibility metadata fields to agent audit events

Revision ID: 20260401_agent_audit_responsibility
Revises: 20260401_chat_response_verdict
Create Date: 2026-04-01 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_agent_audit_responsibility"
down_revision: Union[str, Sequence[str], None] = "20260401_chat_response_verdict"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agentauditevent", schema=None) as batch_op:
        batch_op.add_column(sa.Column("governance_version", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("lane", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("verdict", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("selected_rule", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("policy_version", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("response_mode", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("evidence_sufficiency", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("degraded_reason", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("human_escalation_required", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("model_name", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("tool_plan_source", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("cache_hit", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("agentauditevent", schema=None) as batch_op:
        batch_op.drop_column("cache_hit")
        batch_op.drop_column("tool_plan_source")
        batch_op.drop_column("model_name")
        batch_op.drop_column("human_escalation_required")
        batch_op.drop_column("degraded_reason")
        batch_op.drop_column("evidence_sufficiency")
        batch_op.drop_column("response_mode")
        batch_op.drop_column("policy_version")
        batch_op.drop_column("selected_rule")
        batch_op.drop_column("verdict")
        batch_op.drop_column("lane")
        batch_op.drop_column("governance_version")
