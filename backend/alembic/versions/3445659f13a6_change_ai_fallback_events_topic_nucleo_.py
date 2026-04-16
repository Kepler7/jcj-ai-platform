"""change ai_fallback_events topic_nucleo to jsonb

Revision ID: 3445659f13a6
Revises: 9c1f2e7a4b10
Create Date: 2026-04-15 18:25:12.570677

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json


# revision identifiers, used by Alembic.
revision = "3445659f13a6"
down_revision = "9c1f2e7a4b10"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            """
            SELECT id, topic_nucleo
            FROM ai_fallback_events
            WHERE topic_nucleo IS NOT NULL
            """
        )
    ).fetchall()

    for row in rows:
        raw_topic = row.topic_nucleo
        if raw_topic is None:
            continue

        topic_parts = [x.strip() for x in str(raw_topic).split(",") if x.strip()]

        conn.execute(
            sa.text(
                """
                UPDATE ai_fallback_events
                SET topic_nucleo = :topic_val
                WHERE id = :id
                """
            ),
            {"topic_val": json.dumps(topic_parts), "id": row.id},
        )

    op.alter_column(
        "ai_fallback_events",
        "topic_nucleo",
        existing_type=sa.String(length=64),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
        postgresql_using="topic_nucleo::jsonb",
    )


def downgrade():
    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            """
            SELECT id, topic_nucleo
            FROM ai_fallback_events
            WHERE topic_nucleo IS NOT NULL
            """
        )
    ).fetchall()

    for row in rows:
        raw_topic = row.topic_nucleo
        if raw_topic is None:
            continue

        if isinstance(raw_topic, list):
            topic_val = ", ".join(str(x).strip() for x in raw_topic if str(x).strip())
        else:
            topic_val = str(raw_topic)

        conn.execute(
            sa.text(
                """
                UPDATE ai_fallback_events
                SET topic_nucleo = :topic_val
                WHERE id = :id
                """
            ),
            {"topic_val": topic_val, "id": row.id},
        )

    op.alter_column(
        "ai_fallback_events",
        "topic_nucleo",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.String(length=64),
        existing_nullable=True,
        postgresql_using="topic_nucleo::text",
    )
