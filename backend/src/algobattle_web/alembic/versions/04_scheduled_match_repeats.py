"""Add repeat grouping to scheduled matches.

Revision ID: 4d2e1c9b7a31
Revises: 591afb07e507
"""

import sqlalchemy as sa
from alembic import op

revision = "4d2e1c9b7a31"
down_revision = "591afb07e507"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduledmatches", sa.Column("repeats_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("scheduledmatches", "repeats_id")
