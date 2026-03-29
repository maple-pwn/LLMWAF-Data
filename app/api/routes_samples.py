import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import DbSession, ScanAccess
from models.schemas import SampleCreate, SampleUpdate
from services.sample_service import (
    build_audit_report,
    create_sample_record,
    get_sample_record,
    import_samples_file,
    list_sample_records,
    run_deduplication,
    update_sample_record,
)

router = APIRouter(prefix="/samples", tags=["samples"])


@router.post("")
def create_sample(
    payload: SampleCreate,
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return create_sample_record(db, payload)


@router.post("/import")
async def import_samples(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    tenant_slug: str = Form(...),
    application_key: str = Form(...),
    environment: str = Form(...),
    scenario: str = Form(...),
    source_uri: str | None = Form(default=None),
    source_project: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    file_bytes = await file.read()
    extra_tags = []
    if tags:
        extra_tags = [item.strip() for item in tags.split(",") if item.strip()]
    return import_samples_file(
        db,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        content=file_bytes,
        import_meta={
            "source_type": source_type,
            "source_uri": source_uri,
            "source_project": source_project,
            "tenant_slug": tenant_slug,
            "application_key": application_key,
            "environment": environment,
            "scenario": scenario,
            "tags": extra_tags,
        },
    )


@router.get("")
def list_samples(
    tenant_slug: str | None = None,
    application_key: str | None = None,
    environment: str | None = None,
    sample_type: str | None = None,
    scenario: str | None = None,
    attack_category: str | None = None,
    risk_level: str | None = None,
    source_type: str | None = None,
    review_status: str | None = None,
    tags: str | None = None,
    needs_review: bool | None = None,
    db: Session = DbSession,
) -> dict:
    filters = {
        "tenant_slug": tenant_slug,
        "application_key": application_key,
        "environment": environment,
        "sample_type": sample_type,
        "scenario": scenario,
        "attack_category": attack_category,
        "risk_level": risk_level,
        "source_type": source_type,
        "review_status": review_status,
        "tags": [item.strip() for item in tags.split(",") if item.strip()] if tags else None,
        "needs_review": needs_review,
    }
    return {"items": list_sample_records(db, filters)}


@router.get("/{sample_id}")
def get_sample(sample_id: str, db: Session = DbSession) -> dict:
    return get_sample_record(db, sample_id)


@router.patch("/{sample_id}")
def patch_sample(
    sample_id: str,
    payload: SampleUpdate,
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return update_sample_record(db, sample_id, payload)


@router.post("/deduplicate")
def deduplicate_samples(
    threshold: float | None = None,
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return run_deduplication(db, threshold=threshold)


@router.post("/audit")
def audit_samples(
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return build_audit_report(db)
