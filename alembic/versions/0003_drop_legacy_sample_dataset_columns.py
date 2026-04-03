"""drop legacy sample dataset columns"""

from alembic import op


revision = "0003_drop_legacy_sample_dataset_columns"
down_revision = "0002_schema_adjustments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("samples") as batch_op:
        batch_op.drop_column("dataset_id")
        batch_op.drop_column("dataset_version_id")


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for dropped legacy columns.")
