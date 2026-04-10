from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9c1f2e7a4b10"
down_revision = "817b6dd86ea2"
branch_labels = None
depends_on = None


def upgrade():
    ai_prediction_status = postgresql.ENUM(
        "confirmed_jcj",
        "pending_human_review",
        "general_fallback",
        name="ai_prediction_status",
        create_type=False,
    )
    ai_feedback_verdict = postgresql.ENUM(
        "correct",
        "incorrect",
        "none_apply",
        name="ai_feedback_verdict",
        create_type=False,
    )

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE ai_prediction_status AS ENUM (
                'confirmed_jcj',
                'pending_human_review',
                'general_fallback'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE ai_feedback_verdict AS ENUM (
                'correct',
                'incorrect',
                'none_apply'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    op.create_table(
        "ai_predictions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predicted_playbook_id", sa.String(length=255), nullable=True),
        sa.Column("predicted_playbook_base_row", sa.String(length=50), nullable=True),
        sa.Column("status", ai_prediction_status, nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("confidence_gap", sa.Float(), nullable=True),
        sa.Column(
            "top_candidates_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "top_scores_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("retrieval_version", sa.String(length=100), nullable=True),
        sa.Column("reranker_version", sa.String(length=100), nullable=True),
        sa.Column(
            "used_hyde", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "resolved_by_human",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("final_playbook_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["report_id"], ["student_reports.id"], ondelete="CASCADE"
        ),
    )

    op.create_index("ix_ai_predictions_report_id", "ai_predictions", ["report_id"])
    op.create_index("ix_ai_predictions_status", "ai_predictions", ["status"])
    op.create_index(
        "ix_ai_predictions_predicted_playbook_id",
        "ai_predictions",
        ["predicted_playbook_id"],
    )
    op.create_index(
        "ix_ai_predictions_final_playbook_id", "ai_predictions", ["final_playbook_id"]
    )
    op.create_index("ix_ai_predictions_created_at", "ai_predictions", ["created_at"])

    op.create_table(
        "ai_prediction_feedback",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verdict", ai_feedback_verdict, nullable=False),
        sa.Column("corrected_playbook_id", sa.String(length=255), nullable=True),
        sa.Column("corrected_playbook_base_row", sa.String(length=50), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"], ["ai_predictions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )

    op.create_index(
        "ix_ai_prediction_feedback_prediction_id",
        "ai_prediction_feedback",
        ["prediction_id"],
    )
    op.create_index(
        "ix_ai_prediction_feedback_verdict", "ai_prediction_feedback", ["verdict"]
    )
    op.create_index(
        "ix_ai_prediction_feedback_corrected_playbook_id",
        "ai_prediction_feedback",
        ["corrected_playbook_id"],
    )
    op.create_index(
        "ix_ai_prediction_feedback_created_at", "ai_prediction_feedback", ["created_at"]
    )


def downgrade():
    op.drop_index(
        "ix_ai_prediction_feedback_created_at", table_name="ai_prediction_feedback"
    )
    op.drop_index(
        "ix_ai_prediction_feedback_corrected_playbook_id",
        table_name="ai_prediction_feedback",
    )
    op.drop_index(
        "ix_ai_prediction_feedback_verdict", table_name="ai_prediction_feedback"
    )
    op.drop_index(
        "ix_ai_prediction_feedback_prediction_id", table_name="ai_prediction_feedback"
    )
    op.drop_table("ai_prediction_feedback")

    op.drop_index("ix_ai_predictions_created_at", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_final_playbook_id", table_name="ai_predictions")
    op.drop_index(
        "ix_ai_predictions_predicted_playbook_id", table_name="ai_predictions"
    )
    op.drop_index("ix_ai_predictions_status", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_report_id", table_name="ai_predictions")
    op.drop_table("ai_predictions")

    op.execute("DROP TYPE IF EXISTS ai_feedback_verdict")
    op.execute("DROP TYPE IF EXISTS ai_prediction_status")
