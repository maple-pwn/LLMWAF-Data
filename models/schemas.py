from typing import Any

from pydantic import BaseModel, Field, field_validator


class SampleCreate(BaseModel):
    text: str
    retrieved_context: str | None = None
    model_output: str | None = None
    sample_type: str | None = None
    attack_category: str | None = None
    attack_subtype: str | None = None
    risk_level: str | None = None
    expected_result: str | None = None
    scenario: str
    tags: list[str] = Field(default_factory=list)
    label_confidence: float | None = None
    needs_review: bool | None = None
    review_comment: str | None = None
    tenant_slug: str
    application_key: str
    environment: str
    source_type: str
    source_uri: str | None = None
    source_project: str | None = None
    import_batch_id: str | None = None
    parent_sample_id: str | None = None
    mutation_type: str | None = None
    pair_id: str | None = None
    generator_model: str | None = None
    generator_prompt_version: str | None = None
    generation_params: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"


class SampleUpdate(BaseModel):
    text: str | None = None
    retrieved_context: str | None = None
    model_output: str | None = None
    sample_type: str | None = None
    attack_category: str | None = None
    attack_subtype: str | None = None
    risk_level: str | None = None
    expected_result: str | None = None
    scenario: str | None = None
    tags: list[str] | None = None
    needs_review: bool | None = None
    review_comment: str | None = None


class GenerationRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=50)
    tenant_slug: str
    application_key: str
    environment: str
    scenario: str
    categories: list[str] = Field(default_factory=list)
    parent_sample_id: str | None = None
    mutation_type: str | None = None
    generator_model: str = "local-rule-engine"
    generator_prompt_version: str | None = None
    generation_params: dict[str, Any] = Field(default_factory=dict)


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    filter_spec: dict[str, Any] = Field(default_factory=dict)


class DatasetVersionCreate(BaseModel):
    version_name: str | None = None
    filter_spec: dict[str, Any] = Field(default_factory=dict)
    split_config: dict[str, float] = Field(
        default_factory=lambda: {"train": 0.7, "validation": 0.15, "test": 0.1, "benchmark": 0.05}
    )
    benchmark_frozen: bool = True


class DatasetExportRequest(BaseModel):
    dataset_version_id: str | None = None
    export_format: str = "jsonl"
    filename: str | None = None

    @field_validator("export_format")
    @classmethod
    def validate_export_format(cls, value: str) -> str:
        if value not in {"jsonl", "csv"}:
            raise ValueError("export_format must be jsonl or csv")
        return value


class ReviewTaskCreate(BaseModel):
    sample_id: str
    assignee: str | None = None
    priority: str = "normal"


class ReviewDecisionCreate(BaseModel):
    decision: str
    reviewer: str
    comment: str | None = None
    relabel_fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        if value not in {"approve", "reject", "relabel"}:
            raise ValueError("decision must be approve, reject, or relabel")
        return value


class IntegrationExportRequest(BaseModel):
    dataset_version_id: str | None = None
    filter_spec: dict[str, Any] = Field(default_factory=dict)
    export_format: str = "jsonl"
    filename: str | None = None


class IntegrationPushRequest(BaseModel):
    dataset_version_id: str | None = None
    filter_spec: dict[str, Any] = Field(default_factory=dict)
    target_url: str | None = None
    dry_run: bool = True


class PromptTemplateCreate(BaseModel):
    template_type: str
    name: str
    version: str
    template_text: str
    is_active: bool = True


class PromptTemplateUpdate(BaseModel):
    name: str | None = None
    template_text: str | None = None
    is_active: bool | None = None
