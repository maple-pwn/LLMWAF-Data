"""schema adjustments"""

from alembic import op
import sqlalchemy as sa


revision = "0002_schema_adjustments"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("import_batches") as batch_op:
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))

    with op.batch_alter_table("generation_tasks") as batch_op:
        batch_op.add_column(sa.Column("last_error", sa.Text(), nullable=True))

    with op.batch_alter_table("dataset_memberships") as batch_op:
        batch_op.create_unique_constraint("uq_dataset_membership_version_sample", ["dataset_version_id", "sample_id"])

    with op.batch_alter_table("dataset_versions") as batch_op:
        batch_op.create_unique_constraint("uq_dataset_version_name_per_dataset", ["dataset_id", "version_name"])

    with op.batch_alter_table("prompt_templates") as batch_op:
        batch_op.create_unique_constraint("uq_prompt_template_type_version", ["template_type", "version"])


def downgrade() -> None:
    with op.batch_alter_table("prompt_templates") as batch_op:
        batch_op.drop_constraint("uq_prompt_template_type_version", type_="unique")

    with op.batch_alter_table("dataset_versions") as batch_op:
        batch_op.drop_constraint("uq_dataset_version_name_per_dataset", type_="unique")

    with op.batch_alter_table("dataset_memberships") as batch_op:
        batch_op.drop_constraint("uq_dataset_membership_version_sample", type_="unique")

    with op.batch_alter_table("generation_tasks") as batch_op:
        batch_op.drop_column("last_error")

    with op.batch_alter_table("import_batches") as batch_op:
        batch_op.drop_column("error_message")
