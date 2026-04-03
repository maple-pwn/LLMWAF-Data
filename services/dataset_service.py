from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from models.entities import Dataset, DatasetMembership, DatasetVersion, SampleRecord, utcnow
from models.schemas import DatasetCreate, DatasetExportRequest, DatasetVersionCreate
from services.common import emit_audit_event, export_rows, serialize_llmguard_row, write_export_manifest
from services.filtering import query_filtered_samples


def create_dataset(db: Session, payload: DatasetCreate) -> dict:
    if db.execute(select(Dataset).where(Dataset.name == payload.name)).scalars().first():
        raise AppError(409, "Dataset name already exists.")
    dataset = Dataset(name=payload.name, description=payload.description, filter_spec=payload.filter_spec)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    emit_audit_event(db, "dataset.created", "dataset", dataset.id, {"name": dataset.name})
    db.commit()
    return {"id": dataset.id, "name": dataset.name, "description": dataset.description, "filter_spec": dataset.filter_spec}


def list_datasets(db: Session) -> list[dict]:
    items = db.execute(select(Dataset).order_by(Dataset.created_at.desc())).scalars().all()
    return [
        {"id": item.id, "name": item.name, "description": item.description, "filter_spec": item.filter_spec}
        for item in items
    ]


def create_dataset_version(db: Session, dataset_id: str, payload: DatasetVersionCreate) -> dict:
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise AppError(404, "Dataset not found.")
    existing_versions = db.execute(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.created_at.asc())
    ).scalars().all()
    version_name = payload.version_name or f"v{len(existing_versions) + 1}"
    if any(version.version_name == version_name for version in existing_versions):
        raise AppError(409, "Dataset version name already exists and is immutable.")
    version = DatasetVersion(
        dataset_id=dataset_id,
        version_name=version_name,
        filter_spec=payload.filter_spec or dataset.filter_spec,
        split_config=payload.split_config,
        benchmark_frozen=payload.benchmark_frozen,
    )
    db.add(version)
    db.flush()
    samples = query_filtered_samples(db, version.filter_spec, order_by=SampleRecord.created_at.asc())
    if not samples:
        raise AppError(400, "No samples match the dataset filter.")
    total = len(samples)
    splits = []
    consumed = 0
    split_items = list(payload.split_config.items())
    for index, (split_name, ratio) in enumerate(split_items):
        if index == len(split_items) - 1:
            split_count = total - consumed
        else:
            split_count = int(total * ratio)
        splits.extend([split_name] * split_count)
        consumed += split_count
    if len(splits) < total:
        splits.extend(["train"] * (total - len(splits)))
    for sample, split_name in zip(samples, splits, strict=False):
        db.add(DatasetMembership(dataset_version_id=version.id, sample_id=sample.id, split_name=split_name))
    emit_audit_event(db, "dataset.version_created", "dataset_version", version.id, {"sample_count": total})
    db.commit()
    return {
        "id": version.id,
        "dataset_id": dataset.id,
        "version_name": version.version_name,
        "sample_count": total,
        "benchmark_frozen": version.benchmark_frozen,
        "split_config": version.split_config,
    }


def list_dataset_versions(db: Session, dataset_id: str) -> list[dict]:
    versions = db.execute(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": version.id,
            "dataset_id": version.dataset_id,
            "version_name": version.version_name,
            "filter_spec": version.filter_spec,
            "split_config": version.split_config,
            "benchmark_frozen": version.benchmark_frozen,
        }
        for version in versions
    ]


def export_dataset_version(db: Session, dataset_id: str, payload: DatasetExportRequest) -> dict:
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise AppError(404, "Dataset not found.")
    version: DatasetVersion | None
    if payload.dataset_version_id:
        version = db.execute(
            select(DatasetVersion).where(
                DatasetVersion.id == payload.dataset_version_id,
                DatasetVersion.dataset_id == dataset_id,
            )
        ).scalars().first()
    else:
        version = db.execute(
            select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.created_at.desc())
        ).scalars().first()
    if not version:
        raise AppError(404, "Dataset version not found.")
    memberships = db.execute(
        select(DatasetMembership).where(DatasetMembership.dataset_version_id == version.id).order_by(DatasetMembership.created_at.asc())
    ).scalars().all()
    sample_ids = [membership.sample_id for membership in memberships]
    samples = db.execute(select(SampleRecord).where(SampleRecord.id.in_(sample_ids))).scalars().all()
    rows = [serialize_llmguard_row(sample) for sample in samples]
    result = export_rows(rows, payload.export_format, payload.filename, f"{dataset.name}_{version.version_name}.{payload.export_format}")
    split_counts: dict[str, int] = {}
    benchmark_sample_ids: list[str] = []
    for membership in memberships:
        split_counts[membership.split_name] = split_counts.get(membership.split_name, 0) + 1
        if membership.split_name == "benchmark":
            benchmark_sample_ids.append(membership.sample_id)
    exported_at = utcnow()
    manifest = {
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "default_filter_spec": dataset.filter_spec,
        },
        "dataset_version": {
            "id": version.id,
            "version_name": version.version_name,
            "filter_spec": version.filter_spec,
            "split_config": version.split_config,
            "benchmark_frozen": version.benchmark_frozen,
            "split_counts": split_counts,
            "benchmark_sample_ids": benchmark_sample_ids,
        },
        "export": {
            "format": payload.export_format,
            "data_path": result["path"],
            "record_count": result["record_count"],
            "exported_at": exported_at.isoformat(),
        },
    }
    manifest_path = write_export_manifest(result["path"], manifest)
    version.exported_at = exported_at
    emit_audit_event(db, "dataset.exported", "dataset_version", version.id, {**result, "manifest_path": manifest_path})
    db.commit()
    return {
        "dataset_id": dataset.id,
        "dataset_version_id": version.id,
        "version_name": version.version_name,
        "manifest_path": manifest_path,
        **result,
    }
