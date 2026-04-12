from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _make_alembic_config(db_url: str) -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def test_alembic_upgrade_chain_applies_incremental_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "migration.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    config = _make_alembic_config(db_url)

    command.upgrade(config, "0001_initial")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    import_batch_columns = {column["name"] for column in inspector.get_columns("import_batches")}
    generation_task_columns = {column["name"] for column in inspector.get_columns("generation_tasks")}
    sample_columns = {column["name"] for column in inspector.get_columns("samples")}
    assert "error_message" not in import_batch_columns
    assert "last_error" not in generation_task_columns
    assert "dataset_id" in sample_columns
    assert "dataset_version_id" in sample_columns

    command.upgrade(config, "head")
    inspector = inspect(engine)
    import_batch_columns = {column["name"] for column in inspector.get_columns("import_batches")}
    generation_task_columns = {column["name"] for column in inspector.get_columns("generation_tasks")}
    sample_columns = {column["name"] for column in inspector.get_columns("samples")}
    dataset_membership_uniques = {item["name"] for item in inspector.get_unique_constraints("dataset_memberships")}
    dataset_version_uniques = {item["name"] for item in inspector.get_unique_constraints("dataset_versions")}
    prompt_template_uniques = {item["name"] for item in inspector.get_unique_constraints("prompt_templates")}

    assert "error_message" in import_batch_columns
    assert "last_error" in generation_task_columns
    assert "dataset_id" not in sample_columns
    assert "dataset_version_id" not in sample_columns
    assert "uq_dataset_membership_version_sample" in dataset_membership_uniques
    assert "uq_dataset_version_name_per_dataset" in dataset_version_uniques
    assert "uq_prompt_template_type_version" in prompt_template_uniques
