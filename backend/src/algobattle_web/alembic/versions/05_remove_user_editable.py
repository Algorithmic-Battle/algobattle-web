"""Remove the user_editable column from programs.

Revision ID: 8b7c5e2a1f94
Revises: 4d2e1c9b7a31
"""

import sqlalchemy as sa
from alembic import op

revision = "8b7c5e2a1f94"
down_revision = "4d2e1c9b7a31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("programs", "user_editable")


def downgrade() -> None:
    op.add_column(
        "programs",
        sa.Column("user_editable", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
