"""add ihui3 metadata to ai_reports

Revision ID: 937034725ac3
Revises: 3445659f13a6
Create Date: 2026-05-05 02:56:47.459481

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "937034725ac3"
down_revision: Union[str, Sequence[str], None] = "3445659f13a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_reports",
        sa.Column(
            "engine_version",
            sa.String(length=16),
            nullable=False,
            server_default="2",
        ),
    )

    op.add_column(
        "ai_reports",
        sa.Column(
            "ai_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.add_column(
        "ai_reports",
        sa.Column(
            "validation_status",
            sa.String(length=32),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_reports", "validation_status")
    op.drop_column("ai_reports", "ai_metadata")
    op.drop_column("ai_reports", "engine_version")
