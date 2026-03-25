"""initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=512), nullable=True),
        sa.Column("source_project", sa.String(length=255), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sample_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=512), nullable=True),
        sa.Column("source_project", sa.String(length=255), nullable=True),
        sa.Column("import_batch_id", sa.String(length=36), sa.ForeignKey("import_batches.id"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filter_spec", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("version_name", sa.String(length=32), nullable=False),
        sa.Column("filter_spec", sa.JSON(), nullable=False),
        sa.Column("split_config", sa.JSON(), nullable=False),
        sa.Column("benchmark_frozen", sa.Boolean(), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("template_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "samples",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("retrieved_context", sa.Text(), nullable=True),
        sa.Column("model_output", sa.Text(), nullable=True),
        sa.Column("sample_type", sa.String(length=64), nullable=False),
        sa.Column("attack_category", sa.String(length=64), nullable=True),
        sa.Column("attack_subtype", sa.String(length=64), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("expected_result", sa.String(length=32), nullable=False),
        sa.Column("scenario", sa.String(length=64), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("label_confidence", sa.Float(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("tenant_slug", sa.String(length=120), nullable=False),
        sa.Column("application_key", sa.String(length=120), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=512), nullable=True),
        sa.Column("source_project", sa.String(length=255), nullable=True),
        sa.Column("import_batch_id", sa.String(length=36), sa.ForeignKey("import_batches.id"), nullable=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=True),
        sa.Column("dataset_version_id", sa.String(length=36), sa.ForeignKey("dataset_versions.id"), nullable=True),
        sa.Column("parent_sample_id", sa.String(length=36), sa.ForeignKey("samples.id"), nullable=True),
        sa.Column("mutation_type", sa.String(length=64), nullable=True),
        sa.Column("pair_id", sa.String(length=64), nullable=True),
        sa.Column("generator_model", sa.String(length=128), nullable=True),
        sa.Column("generator_prompt_version", sa.String(length=32), nullable=True),
        sa.Column("generation_params", sa.JSON(), nullable=False),
        sa.Column("reviewer", sa.String(length=120), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("duplicate_group_id", sa.String(length=64), nullable=True),
        sa.Column("canonical_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sample_sources.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_samples_canonical_fingerprint", "samples", ["canonical_fingerprint"])
    op.create_table(
        "dataset_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_version_id", sa.String(length=36), sa.ForeignKey("dataset_versions.id"), nullable=False),
        sa.Column("sample_id", sa.String(length=36), sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("split_name", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sample_id", sa.String(length=36), sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("assignee", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("review_task_id", sa.String(length=36), sa.ForeignKey("review_tasks.id"), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reviewer", sa.String(length=120), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("relabel_fields", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "generation_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prompt_template_id", sa.String(length=36), sa.ForeignKey("prompt_templates.id"), nullable=True),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("result_sample_ids", sa.JSON(), nullable=False),
        sa.Column("generator_model", sa.String(length=128), nullable=True),
        sa.Column("generator_prompt_version", sa.String(length=32), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "similarity_groups",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("group_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("sample_ids", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("similarity_groups")
    op.drop_table("generation_tasks")
    op.drop_table("review_decisions")
    op.drop_table("review_tasks")
    op.drop_table("dataset_memberships")
    op.drop_index("ix_samples_canonical_fingerprint", table_name="samples")
    op.drop_table("samples")
    op.drop_table("prompt_templates")
    op.drop_table("dataset_versions")
    op.drop_table("datasets")
    op.drop_table("sample_sources")
    op.drop_table("import_batches")
