from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.deps import AdminAccess, DbSession
from models.schemas import PromptTemplateCreate, PromptTemplateUpdate
from services.prompt_template_service import create_prompt_template, list_prompt_templates, update_prompt_template

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])


@router.get("")
def list_prompt_templates_endpoint(
    template_type: str | None = None,
    is_active: bool | None = None,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return {"items": list_prompt_templates(db, template_type=template_type, is_active=is_active)}


@router.post("")
def create_prompt_template_endpoint(
    payload: PromptTemplateCreate,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return create_prompt_template(db, payload)


@router.patch("/{template_id}")
def update_prompt_template_endpoint(
    template_id: str,
    payload: PromptTemplateUpdate,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return update_prompt_template(db, template_id, payload)
