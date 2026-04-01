from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from models.entities import PromptTemplate
from models.schemas import PromptTemplateCreate, PromptTemplateUpdate


def list_prompt_templates(
    db: Session,
    template_type: str | None = None,
    is_active: bool | None = None,
) -> list[dict]:
    query = select(PromptTemplate).order_by(PromptTemplate.template_type.asc(), PromptTemplate.version.desc())
    if template_type:
        query = query.where(PromptTemplate.template_type == template_type)
    if is_active is not None:
        query = query.where(PromptTemplate.is_active == is_active)
    items = db.execute(query).scalars().all()
    return [
        {
            "id": item.id,
            "template_type": item.template_type,
            "name": item.name,
            "version": item.version,
            "template_text": item.template_text,
            "is_active": item.is_active,
        }
        for item in items
    ]


def create_prompt_template(db: Session, payload: PromptTemplateCreate) -> dict:
    existing = db.execute(
        select(PromptTemplate).where(
            PromptTemplate.template_type == payload.template_type,
            PromptTemplate.version == payload.version,
        )
    ).scalars().first()
    if existing:
        raise AppError(409, "Prompt template version already exists for this type.")
    template = PromptTemplate(
        template_type=payload.template_type,
        name=payload.name,
        version=payload.version,
        template_text=payload.template_text,
        is_active=payload.is_active,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {
        "id": template.id,
        "template_type": template.template_type,
        "name": template.name,
        "version": template.version,
        "template_text": template.template_text,
        "is_active": template.is_active,
    }


def update_prompt_template(db: Session, template_id: str, payload: PromptTemplateUpdate) -> dict:
    template = db.get(PromptTemplate, template_id)
    if not template:
        raise AppError(404, "Prompt template not found.")
    changes = payload.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return {
        "id": template.id,
        "template_type": template.template_type,
        "name": template.name,
        "version": template.version,
        "template_text": template.template_text,
        "is_active": template.is_active,
    }
