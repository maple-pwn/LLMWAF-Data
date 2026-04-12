from core.errors import AppError
from models.schemas import PromptTemplateCreate, PromptTemplateUpdate
from services.prompt_template_service import create_prompt_template, list_prompt_templates, update_prompt_template


def test_prompt_template_can_be_created_and_updated(db_session):
    created = create_prompt_template(
        db_session,
        PromptTemplateCreate(
            template_type="attack_generation",
            name="New attack template",
            version="v2",
            template_text="Generate a new placeholder-only attack variant.",
        ),
    )
    assert created["version"] == "v2"
    updated = update_prompt_template(
        db_session,
        created["id"],
        PromptTemplateUpdate(is_active=False, template_text="Updated template body."),
    )
    assert updated["is_active"] is False
    assert updated["template_text"] == "Updated template body."


def test_prompt_template_duplicate_version_is_rejected(db_session):
    try:
        create_prompt_template(
            db_session,
            PromptTemplateCreate(
                template_type="attack_generation",
                name="Duplicate attack template",
                version="v1",
                template_text="Duplicate body.",
            ),
        )
    except AppError as exc:
        detail = exc.message
    else:
        detail = ""
    assert "already exists" in detail


def test_list_prompt_templates_supports_active_filter(db_session):
    created = create_prompt_template(
        db_session,
        PromptTemplateCreate(
            template_type="benign_overlap_generation",
            name="Inactive benign template",
            version="v2",
            template_text="Inactive body.",
            is_active=False,
        ),
    )
    inactive_items = list_prompt_templates(db_session, template_type="benign_overlap_generation", is_active=False)
    assert any(item["id"] == created["id"] for item in inactive_items)
