"""Add org_id to user table for Hanzo IAM multi-tenant org scoping.

Revision ID: a1b2c3d4e5f6
Revises: 369268b9af8b
Create Date: 2026-03-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "369268b9af8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add org_id column to user table. Nullable so existing users are not broken.
    # Will be populated on next OIDC login from the IAM `owner` claim.
    op.add_column("user", sa.Column("org_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_user_org_id"), "user", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_org_id"), table_name="user")
    op.drop_column("user", "org_id")
