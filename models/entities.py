import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(64))
    source_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SampleSource(Base):
    __tablename__ = "sample_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type: Mapped[str] = mapped_column(String(64))
    source_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SampleRecord(Base, TimestampMixin):
    __tablename__ = "samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text: Mapped[str] = mapped_column(Text)
    retrieved_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_type: Mapped[str] = mapped_column(String(64))
    attack_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attack_subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    expected_result: Mapped[str] = mapped_column(String(32), default="review")
    scenario: Mapped[str] = mapped_column(String(64))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    label_confidence: Mapped[float] = mapped_column(Float, default=0.5)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_slug: Mapped[str] = mapped_column(String(120))
    application_key: Mapped[str] = mapped_column(String(120))
    environment: Mapped[str] = mapped_column(String(64))
    source_type: Mapped[str] = mapped_column(String(64))
    source_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    parent_sample_id: Mapped[str | None] = mapped_column(ForeignKey("samples.id"), nullable=True)
    mutation_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pair_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generator_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generator_prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    generation_params: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.5)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    normalized_text: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sample_sources.id"), nullable=True)

    source = relationship("SampleSource")


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    filter_spec: Mapped[dict] = mapped_column(JSON, default=dict)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_id", "version_name", name="uq_dataset_version_name_per_dataset"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    version_name: Mapped[str] = mapped_column(String(32))
    filter_spec: Mapped[dict] = mapped_column(JSON, default=dict)
    split_config: Mapped[dict] = mapped_column(JSON, default=dict)
    benchmark_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DatasetMembership(Base):
    __tablename__ = "dataset_memberships"
    __table_args__ = (UniqueConstraint("dataset_version_id", "sample_id", name="uq_dataset_membership_version_sample"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    sample_id: Mapped[str] = mapped_column(ForeignKey("samples.id"))
    split_name: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewTask(Base, TimestampMixin):
    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_id: Mapped[str] = mapped_column(ForeignKey("samples.id"))
    assignee: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    priority: Mapped[str] = mapped_column(String(32), default="normal")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_task_id: Mapped[str] = mapped_column(ForeignKey("review_tasks.id"))
    decision: Mapped[str] = mapped_column(String(32))
    reviewer: Mapped[str] = mapped_column(String(120))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    relabel_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GenerationTask(Base, TimestampMixin):
    __tablename__ = "generation_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    prompt_template_id: Mapped[str | None] = mapped_column(ForeignKey("prompt_templates.id"), nullable=True)
    requested_count: Mapped[int] = mapped_column(Integer, default=1)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result_sample_ids: Mapped[list] = mapped_column(JSON, default=list)
    generator_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generator_prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"
    __table_args__ = (UniqueConstraint("template_type", "version", name="uq_prompt_template_type_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_type: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(32))
    template_text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SimilarityGroup(Base):
    __tablename__ = "similarity_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_key: Mapped[str] = mapped_column(String(64), unique=True)
    sample_ids: Mapped[list] = mapped_column(JSON, default=list)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(36))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
