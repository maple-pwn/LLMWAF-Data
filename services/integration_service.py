import json
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from models.entities import DatasetMembership, SampleRecord
from models.schemas import IntegrationExportRequest, IntegrationPushRequest
from services.common import emit_audit_event, export_rows, serialize_llmguard_row
from services.filtering import query_filtered_samples


def _resolve_export_samples(db: Session, dataset_version_id: str | None, filter_spec: dict) -> list[SampleRecord]:
    if dataset_version_id:
        memberships = db.execute(
            select(DatasetMembership).where(DatasetMembership.dataset_version_id == dataset_version_id)
        ).scalars().all()
        sample_ids = [membership.sample_id for membership in memberships]
        if not sample_ids:
            return []
        return db.execute(select(SampleRecord).where(SampleRecord.id.in_(sample_ids))).scalars().all()
    return query_filtered_samples(db, filter_spec, order_by=SampleRecord.created_at.asc())


def export_for_llmguard(db: Session, payload: IntegrationExportRequest) -> dict:
    samples = _resolve_export_samples(db, payload.dataset_version_id, payload.filter_spec)
    rows = [serialize_llmguard_row(sample) for sample in samples]
    result = export_rows(rows, payload.export_format, payload.filename, f"llmguard_export.{payload.export_format}")
    emit_audit_event(db, "integration.exported", "integration", payload.dataset_version_id or "filtered_export", result)
    db.commit()
    return result


def push_to_llmguard(db: Session, payload: IntegrationPushRequest) -> dict:
    samples = _resolve_export_samples(db, payload.dataset_version_id, payload.filter_spec)
    rows = [serialize_llmguard_row(sample) for sample in samples]
    response_body = None
    status = "dry_run"
    if not payload.dry_run:
        if not payload.target_url:
            raise AppError(400, "target_url is required when dry_run is false.")
        request = urllib.request.Request(
            payload.target_url,
            data=json.dumps({"samples": rows}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            response_body = response.read().decode("utf-8")
            status = "pushed"
    emit_audit_event(
        db,
        "integration.pushed",
        "integration",
        payload.dataset_version_id or "filtered_push",
        {"record_count": len(rows), "status": status},
    )
    db.commit()
    return {
        "status": status,
        "record_count": len(rows),
        "payload_preview": rows[:3],
        "response_body": response_body,
    }
