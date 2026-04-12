from models.schemas import IntegrationExportRequest
from services.integration_service import export_for_llmguard
from services.sample_service import create_sample_record


def _seed_export_sample(db_session):
    create_sample_record(
        db_session,
        {
            "text": "Summarize the compliance note for the reviewer.",
            "scenario": "compliance",
            "tenant_slug": "tenant-int",
            "application_key": "app-int",
            "environment": "dev",
            "source_type": "manual",
        },
    )


def test_integration_export_matches_llmguard_fields(db_session):
    _seed_export_sample(db_session)
    response = export_for_llmguard(
        db_session,
        IntegrationExportRequest(filter_spec={"tenant_slug": "tenant-int"}, export_format="jsonl"),
    )
    assert response["record_count"] == 1
    assert response["path"].endswith(".jsonl")


def test_integration_export_csv_writes_file(db_session):
    _seed_export_sample(db_session)
    response = export_for_llmguard(
        db_session,
        IntegrationExportRequest(filter_spec={"tenant_slug": "tenant-int"}, export_format="csv"),
    )
    assert response["record_count"] == 1
    assert response["path"].endswith(".csv")


def test_export_scope_rejects_path_traversal(db_session):
    _seed_export_sample(db_session)
    try:
        export_for_llmguard(
            db_session,
            IntegrationExportRequest(
                filter_spec={"tenant_slug": "tenant-int"},
                export_format="jsonl",
                filename="../bad.jsonl",
            ),
        )
    except Exception as exc:
        detail = str(exc)
    else:
        detail = ""
    assert "path segments" in detail
