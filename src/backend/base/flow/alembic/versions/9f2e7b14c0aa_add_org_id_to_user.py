"""Add org_id to user table for Hanzo IAM multi-tenant org scoping.

Revision ID: 9f2e7b14c0aa
Revises: d306e5c17c41
Create Date: 2026-03-01 00:00:00.000000

This migration was originally published under revision id ``a1b2c3d4e5f6``,
which COLLIDED with the upstream ``convert_provider_key_and_deployment`` migration
after an upstream merge (two files, one revision id) — alembic cannot build a
history graph with a duplicate revision, so the app failed to boot. The upstream
migration legitimately owns ``a1b2c3d4e5f6`` (it is chained to the head), so this
Hanzo-local migration is re-id'd to ``9f2e7b14c0aa`` and re-parented onto the
current head (``d306e5c17c41``). The body is made idempotent so it is safe whether
or not an earlier (colliding) run already added the column/index.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "9f2e7b14c0aa"
down_revision: Union[str, None] = "d306e5c17c41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_user_org_id"


def _has_column(bind, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(bind).get_columns(table))


def _has_index(bind, table: str, index: str) -> bool:
    return any(i["name"] == index for i in inspect(bind).get_indexes(table))


def upgrade() -> None:
    # Nullable so existing users are not broken; populated on next OIDC login
    # from the IAM `owner` claim. Idempotent (see module docstring).
    bind = op.get_bind()
    if not _has_column(bind, "user", "org_id"):
        op.add_column("user", sa.Column("org_id", sa.String(), nullable=True))
    if not _has_index(bind, "user", _INDEX):
        op.create_index(op.f(_INDEX), "user", ["org_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "user", _INDEX):
        op.drop_index(op.f(_INDEX), table_name="user")
    if _has_column(bind, "user", "org_id"):
        op.drop_column("user", "org_id")
