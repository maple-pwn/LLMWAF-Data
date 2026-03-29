from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from models.entities import SampleRecord
from services.common import normalize_tags

SCALAR_FILTER_FIELDS = {
    "tenant_slug": SampleRecord.tenant_slug,
    "application_key": SampleRecord.application_key,
    "environment": SampleRecord.environment,
    "scenario": SampleRecord.scenario,
    "sample_type": SampleRecord.sample_type,
    "attack_category": SampleRecord.attack_category,
    "attack_subtype": SampleRecord.attack_subtype,
    "risk_level": SampleRecord.risk_level,
    "source_type": SampleRecord.source_type,
    "review_status": SampleRecord.review_status,
    "needs_review": SampleRecord.needs_review,
}


def apply_sample_filter_spec(query: Select, filter_spec: dict[str, Any]) -> Select:
    for field_name, column in SCALAR_FILTER_FIELDS.items():
        value = filter_spec.get(field_name)
        if value is None:
            continue
        if isinstance(value, list):
            query = query.where(column.in_(value))
        else:
            query = query.where(column == value)
    return query


def filter_samples_in_memory(samples: list[SampleRecord], filter_spec: dict[str, Any]) -> list[SampleRecord]:
    required_tags = filter_spec.get("tags")
    if required_tags:
        normalized = set(normalize_tags(required_tags if isinstance(required_tags, list) else [required_tags]))
        samples = [sample for sample in samples if normalized.issubset(set(sample.tags or []))]
    return samples


def query_filtered_samples(
    db: Session,
    filter_spec: dict[str, Any] | None = None,
    *,
    order_by=None,
) -> list[SampleRecord]:
    filter_spec = filter_spec or {}
    query = select(SampleRecord)
    if order_by is not None:
        query = query.order_by(order_by)
    query = apply_sample_filter_spec(query, filter_spec)
    samples = db.execute(query).scalars().all()
    return filter_samples_in_memory(samples, filter_spec)
