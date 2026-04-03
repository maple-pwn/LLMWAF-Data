from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.deps import AdminAccess, DbSession
from models.schemas import DatasetCreate, DatasetExportRequest, DatasetVersionCreate
from services.dataset_service import (
    create_dataset,
    create_dataset_version,
    export_dataset_version,
    list_dataset_versions,
    list_datasets,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("")
def create_dataset_endpoint(
    payload: DatasetCreate,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return create_dataset(db, payload)


@router.post("/{dataset_id}/versions")
def create_dataset_version_endpoint(
    dataset_id: str,
    payload: DatasetVersionCreate,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return create_dataset_version(db, dataset_id, payload)


@router.get("")
def list_datasets_endpoint(db: Session = DbSession) -> dict:
    return {"items": list_datasets(db)}


@router.get("/{dataset_id}/versions")
def list_dataset_versions_endpoint(dataset_id: str, db: Session = DbSession) -> dict:
    return {"items": list_dataset_versions(db, dataset_id)}


@router.post("/{dataset_id}/export")
def export_dataset_endpoint(
    dataset_id: str,
    payload: DatasetExportRequest,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return export_dataset_version(db, dataset_id, payload)
