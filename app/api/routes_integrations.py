from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.deps import AdminAccess, DbSession
from models.schemas import IntegrationExportRequest, IntegrationPushRequest
from services.integration_service import export_for_llmguard, push_to_llmguard

router = APIRouter(prefix="/integrations/llmguard", tags=["integrations"])


@router.post("/export")
def export_llmguard_endpoint(
    payload: IntegrationExportRequest,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return export_for_llmguard(db, payload)


@router.post("/push")
def push_llmguard_endpoint(
    payload: IntegrationPushRequest,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return push_to_llmguard(db, payload)
