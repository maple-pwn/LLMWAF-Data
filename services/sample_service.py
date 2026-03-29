import csv
import io
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import AppError
from models.entities import ImportBatch, SampleRecord, SampleSource, SimilarityGroup
from models.schemas import SampleCreate, SampleUpdate
from services.common import (
    ATTACK_KEYWORDS,
    build_fingerprint,
    compute_similarity_groups,
    compute_quality_score,
    detect_conflicts,
    detect_language,
    emit_audit_event,
    infer_sample_labels,
    normalize_tags,
    normalize_text,
    persist_similarity_groups,
    serialize_sample,
)
from services.filtering import query_filtered_samples


def _create_sample_source(
    db: Session,
    payload: dict[str, Any],
    import_batch_id: str | None = None,
) -> SampleSource:
    source = SampleSource(
        source_type=payload["source_type"],
        source_uri=payload.get("source_uri"),
        source_project=payload.get("source_project"),
        import_batch_id=import_batch_id,
        metadata_json={
            "tenant_slug": payload["tenant_slug"],
            "application_key": payload["application_key"],
            "environment": payload["environment"],
            "scenario": payload["scenario"],
        },
    )
    db.add(source)
    db.flush()
    return source


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["text"] = payload["text"].strip()
    normalized["retrieved_context"] = (payload.get("retrieved_context") or None)
    normalized["model_output"] = (payload.get("model_output") or None)
    normalized["source_uri"] = payload.get("source_uri") or None
    normalized["source_project"] = payload.get("source_project") or None
    normalized["tags"] = normalize_tags(payload.get("tags"))
    normalized["normalized_text"] = normalize_text(payload["text"])
    normalized["canonical_fingerprint"] = build_fingerprint(
        payload["text"],
        payload.get("retrieved_context"),
    )
    normalized["language"] = payload.get("language") or detect_language(payload["text"])
    inferred = infer_sample_labels(normalized)
    for key, value in inferred.items():
        if normalized.get(key) is None:
            normalized[key] = value
    normalized["quality_score"] = compute_quality_score(
        normalized["text"],
        float(normalized["label_confidence"]),
        normalized["expected_result"],
    )
    normalized["review_status"] = normalized.get("review_status") or "pending"
    return normalized


def _apply_sample_changes(
    sample: SampleRecord,
    changes: dict[str, Any],
    *,
    allow_label_overrides: bool = False,
) -> None:
    for key, value in changes.items():
        setattr(sample, key, value)

    normalized = _normalized_payload(
        {
            **serialize_sample(sample),
            **changes,
            "text": sample.text,
            "retrieved_context": sample.retrieved_context,
            "model_output": sample.model_output,
            "source_type": sample.source_type,
            "source_uri": sample.source_uri,
            "source_project": sample.source_project,
            "tenant_slug": sample.tenant_slug,
            "application_key": sample.application_key,
            "environment": sample.environment,
            "scenario": sample.scenario,
            "generation_params": sample.generation_params,
            "language": sample.language,
        }
    )
    sample.normalized_text = normalized["normalized_text"]
    sample.canonical_fingerprint = normalized["canonical_fingerprint"]
    sample.tags = normalized["tags"]
    sample.language = normalized["language"]
    sample.duplicate_group_id = None

    should_refresh_labels = allow_label_overrides or sample.review_status != "approved"
    if should_refresh_labels:
        sample.sample_type = normalized["sample_type"]
        sample.attack_category = normalized["attack_category"]
        sample.attack_subtype = normalized["attack_subtype"]
        sample.risk_level = normalized["risk_level"]
        sample.expected_result = normalized["expected_result"]
        sample.label_confidence = normalized["label_confidence"]
        sample.needs_review = normalized["needs_review"]
    sample.quality_score = normalized["quality_score"]


def create_sample_record(db: Session, payload: SampleCreate | dict[str, Any]) -> dict:
    input_data = payload.model_dump() if isinstance(payload, SampleCreate) else dict(payload)
    # Legacy compatibility: dataset membership is the only persisted source of truth.
    input_data.pop("dataset_id", None)
    input_data.pop("dataset_version_id", None)
    if not input_data.get("text", "").strip():
        raise AppError(400, "Sample text cannot be empty.")
    normalized = _normalized_payload(input_data)
    source = _create_sample_source(db, normalized, normalized.get("import_batch_id"))
    sample = SampleRecord(source_id=source.id, **normalized)
    db.add(sample)
    db.flush()
    emit_audit_event(db, "sample.created", "sample", sample.id, {"source_type": sample.source_type})
    return serialize_sample(sample)


def get_sample_record(db: Session, sample_id: str) -> dict:
    sample = db.get(SampleRecord, sample_id)
    if not sample:
        raise AppError(404, "Sample not found.")
    return serialize_sample(sample)


def list_sample_records(db: Session, filters: dict[str, Any] | None = None) -> list[dict]:
    items = query_filtered_samples(db, filters or {}, order_by=SampleRecord.created_at.desc())
    return [serialize_sample(item) for item in items]


def update_sample_record(db: Session, sample_id: str, payload: SampleUpdate) -> dict:
    sample = db.get(SampleRecord, sample_id)
    if not sample:
        raise AppError(404, "Sample not found.")
    changes = payload.model_dump(exclude_none=True)
    _apply_sample_changes(sample, changes)
    emit_audit_event(db, "sample.updated", "sample", sample.id, {"fields": list(changes.keys())})
    db.commit()
    db.refresh(sample)
    return serialize_sample(sample)


def _parse_import_rows(filename: str, content: bytes) -> list[dict[str, Any]]:
    decoded = content.decode("utf-8")
    if filename.endswith(".jsonl"):
        rows = []
        for line in decoded.splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows
    if filename.endswith(".csv"):
        return list(csv.DictReader(io.StringIO(decoded)))
    raise AppError(400, "Import file must be JSONL or CSV.")


def _parse_optional_bool(value: Any, field_name: str, row_number: int) -> bool | None:
    if value in {None, ""}:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    raise AppError(400, f"Row {row_number}: field {field_name} must be a boolean.")


def _parse_list_field(value: Any, field_name: str, row_number: int) -> list[str]:
    if value in {None, ""}:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                decoded = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise AppError(400, f"Row {row_number}: field {field_name} must be valid JSON.") from exc
            if not isinstance(decoded, list):
                raise AppError(400, f"Row {row_number}: field {field_name} must decode to a list.")
            return [str(item) for item in decoded]
        return [item.strip() for item in stripped.split(",") if item.strip()]
    raise AppError(400, f"Row {row_number}: field {field_name} must be a list.")


def _parse_json_dict(value: Any, field_name: str, row_number: int) -> dict[str, Any]:
    if value in {None, ""}:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise AppError(400, f"Row {row_number}: field {field_name} must be valid JSON.") from exc
        if not isinstance(decoded, dict):
            raise AppError(400, f"Row {row_number}: field {field_name} must decode to an object.")
        return decoded
    raise AppError(400, f"Row {row_number}: field {field_name} must be an object.")


def _prepare_import_payload(row: dict[str, Any], import_meta: dict[str, Any], row_number: int, batch_id: str) -> dict[str, Any]:
    row_tags = _parse_list_field(row.get("tags"), "tags", row_number)
    label_confidence = None
    if row.get("label_confidence") not in {None, ""}:
        try:
            label_confidence = float(row["label_confidence"])
        except (TypeError, ValueError) as exc:
            raise AppError(400, f"Row {row_number}: field label_confidence must be numeric.") from exc
    payload = {
        "text": row.get("text", ""),
        "retrieved_context": row.get("retrieved_context"),
        "model_output": row.get("model_output"),
        "sample_type": row.get("sample_type"),
        "attack_category": row.get("attack_category"),
        "attack_subtype": row.get("attack_subtype"),
        "risk_level": row.get("risk_level"),
        "expected_result": row.get("expected_result"),
        "scenario": row.get("scenario") or import_meta["scenario"],
        "tags": row_tags + import_meta.get("tags", []),
        "label_confidence": label_confidence,
        "needs_review": _parse_optional_bool(row.get("needs_review"), "needs_review", row_number),
        "review_comment": row.get("review_comment"),
        "tenant_slug": row.get("tenant_slug") or import_meta["tenant_slug"],
        "application_key": row.get("application_key") or import_meta["application_key"],
        "environment": row.get("environment") or import_meta["environment"],
        "source_type": import_meta["source_type"],
        "source_uri": row.get("source_uri") or import_meta.get("source_uri"),
        "source_project": row.get("source_project") or import_meta.get("source_project"),
        "import_batch_id": batch_id,
        "generator_model": row.get("generator_model"),
        "generator_prompt_version": row.get("generator_prompt_version"),
        "generation_params": _parse_json_dict(row.get("generation_params"), "generation_params", row_number),
        "language": row.get("language") or detect_language(row.get("text", "")),
    }
    if not payload["text"].strip():
        raise AppError(400, f"Row {row_number}: Sample text cannot be empty.")
    return payload


def import_samples_file(
    db: Session,
    filename: str,
    content_type: str,
    content: bytes,
    import_meta: dict[str, Any],
) -> dict:
    settings = get_settings()
    if len(content) > settings.import_max_bytes:
        raise AppError(400, "Import file exceeds the configured size limit.")
    rows = _parse_import_rows(filename, content)
    if len(rows) > settings.import_max_records:
        raise AppError(400, "Import file exceeds the configured record limit.")
    batch = ImportBatch(
        filename=filename,
        content_type=content_type,
        source_type=import_meta["source_type"],
        source_uri=import_meta.get("source_uri"),
        source_project=import_meta.get("source_project"),
        record_count=0,
        status="pending",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    row_errors: list[dict[str, Any]] = []
    prepared_payloads: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=1):
        try:
            prepared_payloads.append(_prepare_import_payload(row, import_meta, row_number, batch.id))
        except AppError as exc:
            row_errors.append({"row": row_number, "detail": exc.message})

    if row_errors:
        batch.status = "failed"
        batch.error_message = "Import validation failed."
        db.commit()
        raise AppError(400, "Import validation failed.", errors=row_errors)

    try:
        created_items = []
        for payload in prepared_payloads:
            created_items.append(create_sample_record(db, payload))
        batch.record_count = len(created_items)
        batch.status = "completed"
        batch.error_message = None
        emit_audit_event(db, "sample.imported", "import_batch", batch.id, {"record_count": len(created_items)})
        db.commit()
        return {
            "import_batch_id": batch.id,
            "record_count": len(created_items),
            "sample_ids": [item["id"] for item in created_items],
        }
    except Exception as exc:
        db.rollback()
        failed_batch = db.get(ImportBatch, batch.id)
        if failed_batch:
            failed_batch.status = "failed"
            failed_batch.error_message = exc.message if isinstance(exc, AppError) else str(exc)
            db.commit()
        raise


def run_deduplication(db: Session, threshold: float | None = None) -> dict:
    settings = get_settings()
    active_threshold = threshold or settings.similarity_threshold
    samples = db.execute(select(SampleRecord).order_by(SampleRecord.created_at.asc())).scalars().all()
    for sample in samples:
        sample.duplicate_group_id = None
    fingerprint_groups: dict[str, list[SampleRecord]] = {}
    for sample in samples:
        fingerprint_groups.setdefault(sample.canonical_fingerprint, []).append(sample)
    duplicate_groups = []
    for fingerprint, items in fingerprint_groups.items():
        if len(items) < 2:
            continue
        group_id = fingerprint[:16]
        for sample in items:
            sample.duplicate_group_id = group_id
        duplicate_groups.append({"group_id": group_id, "sample_ids": [item.id for item in items]})
    similarity_groups = compute_similarity_groups(samples, active_threshold)
    persist_similarity_groups(db, similarity_groups)
    emit_audit_event(
        db,
        "sample.deduplicated",
        "sample",
        samples[0].id if samples else "none",
        {"duplicate_groups": len(duplicate_groups), "similarity_groups": len(similarity_groups)},
    )
    db.commit()
    return {
        "duplicate_groups": duplicate_groups,
        "similarity_groups": similarity_groups,
        "label_conflicts": detect_conflicts(samples),
    }


def build_audit_report(db: Session) -> dict:
    samples = db.execute(select(SampleRecord).order_by(SampleRecord.created_at.asc())).scalars().all()
    stored_similarity_groups = db.execute(select(SimilarityGroup).order_by(SimilarityGroup.created_at.asc())).scalars().all()
    deduplicated = {sample.canonical_fingerprint for sample in samples}
    source_distribution: dict[str, int] = {}
    scenario_distribution: dict[str, int] = {}
    attack_distribution: dict[str, int] = {}
    low_confidence_samples = 0
    needs_review_samples = 0
    low_quality_items: list[dict[str, Any]] = []
    boundary_samples: list[dict[str, Any]] = []
    abnormal_length_samples: list[dict[str, Any]] = []
    missing_field_samples: list[dict[str, Any]] = []
    sample_type_counts = {"benign": 0, "attack": 0}

    def detect_missing_fields(sample: SampleRecord) -> list[str]:
        missing: list[str] = []
        required_fields = {
            "text": sample.text,
            "sample_type": sample.sample_type,
            "expected_result": sample.expected_result,
            "scenario": sample.scenario,
            "tenant_slug": sample.tenant_slug,
            "application_key": sample.application_key,
            "environment": sample.environment,
            "source_type": sample.source_type,
        }
        for field_name, value in required_fields.items():
            if value in {None, ""}:
                missing.append(field_name)
        if sample.sample_type == "rag_attack" and not sample.retrieved_context:
            missing.append("retrieved_context")
        if sample.sample_type == "attack" and not sample.attack_category:
            missing.append("attack_category")
        if sample.source_type in {"imported", "production_feedback", "redteam"} and not sample.source_uri:
            missing.append("source_uri")
        if sample.source_type == "production_feedback" and not sample.model_output:
            missing.append("model_output")
        return missing

    for sample in samples:
        source_distribution[sample.source_type] = source_distribution.get(sample.source_type, 0) + 1
        scenario_distribution[sample.scenario] = scenario_distribution.get(sample.scenario, 0) + 1
        if sample.attack_category:
            attack_distribution[sample.attack_category] = attack_distribution.get(sample.attack_category, 0) + 1
        if sample.label_confidence < 0.7:
            low_confidence_samples += 1
        if sample.needs_review:
            needs_review_samples += 1
        if sample.sample_type in {"attack", "rag_attack"}:
            sample_type_counts["attack"] += 1
        else:
            sample_type_counts["benign"] += 1

        text_length = len((sample.text or "").strip())
        if text_length < 12 or text_length > 5000:
            abnormal_length_samples.append({"sample_id": sample.id, "length": text_length})
        if sample.quality_score < 0.7:
            low_quality_items.append({"sample_id": sample.id, "quality_score": sample.quality_score})
        if 0.55 <= sample.label_confidence < 0.75:
            boundary_samples.append(
                {
                    "sample_id": sample.id,
                    "label_confidence": sample.label_confidence,
                    "sample_type": sample.sample_type,
                }
            )
        missing_fields = detect_missing_fields(sample)
        if missing_fields:
            missing_field_samples.append({"sample_id": sample.id, "missing_fields": missing_fields})

    expected_attack_categories = sorted(ATTACK_KEYWORDS.keys())
    return {
        "total_samples": len(samples),
        "deduplicated_samples": len(deduplicated),
        "source_distribution": source_distribution,
        "scenario_distribution": scenario_distribution,
        "attack_distribution": attack_distribution,
        "attack_category_coverage": {
            "covered_categories": sorted(attack_distribution.keys()),
            "missing_categories": [category for category in expected_attack_categories if category not in attack_distribution],
        },
        "scenario_coverage": {
            "covered_scenarios": sorted(scenario_distribution.keys()),
            "scenario_count": len(scenario_distribution),
        },
        "sample_type_ratio": {
            "benign": sample_type_counts["benign"],
            "attack": sample_type_counts["attack"],
            "attack_to_benign_ratio": round(
                sample_type_counts["attack"] / sample_type_counts["benign"], 2
            )
            if sample_type_counts["benign"]
            else None,
        },
        "low_confidence_samples": low_confidence_samples,
        "needs_review_samples": needs_review_samples,
        "low_quality_samples": len(low_quality_items),
        "low_quality_items": low_quality_items,
        "boundary_samples": boundary_samples,
        "abnormal_length_samples": abnormal_length_samples,
        "missing_field_samples": missing_field_samples,
        "high_similarity_groups": [
            {"group_key": group.group_key, "sample_ids": group.sample_ids, "score": group.score}
            for group in stored_similarity_groups
        ],
        "label_conflicts": detect_conflicts(samples),
    }
