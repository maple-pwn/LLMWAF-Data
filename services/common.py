import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import AppError
from models.entities import AuditEvent, SampleRecord, SimilarityGroup

WHITESPACE_RE = re.compile(r"\s+")

ATTACK_KEYWORDS = {
    "direct_prompt_injection": ("ignore previous", "system prompt", "override instruction"),
    "indirect_prompt_injection": ("retrieved instruction", "hidden prompt", "document says ignore"),
    "jailbreak": ("jailbreak", "bypass policy", "developer mode"),
    "sensitive_info_exfiltration": ("secret", "api key", "credential", "token"),
    "role_override": ("pretend to be", "act as system", "roleplay admin"),
    "tool_misuse_attempt": ("run shell", "execute tool", "call function"),
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", value.strip()).lower()


def normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    cleaned = {normalize_text(tag).replace(" ", "_") for tag in tags if normalize_text(tag)}
    return sorted(cleaned)


def build_fingerprint(text: str, retrieved_context: str | None) -> str:
    canonical = f"{normalize_text(text)}||{normalize_text(retrieved_context)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_language(text: str) -> str:
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        return "zh"
    return "en"


def tokenize(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-zA-Z0-9_]+", normalize_text(text)) if token}


def infer_sample_labels(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text", "")
    context = payload.get("retrieved_context") or ""
    full_text = normalize_text(f"{text} {context}")
    matched_category = None
    match_count = 0
    for category, keywords in ATTACK_KEYWORDS.items():
        if any(keyword in full_text for keyword in keywords):
            matched_category = category
            match_count += 1
    if matched_category:
        sample_type = "rag_attack" if context and "ignore" in normalize_text(context) else "attack"
        expected_result = "block"
        confidence = 0.55 + min(match_count * 0.15, 0.35)
        needs_review = confidence < 0.75 or sample_type == "rag_attack"
        return {
            "sample_type": sample_type,
            "attack_category": matched_category,
            "attack_subtype": payload.get("attack_subtype") or matched_category,
            "risk_level": "high" if matched_category in {"jailbreak", "sensitive_info_exfiltration"} else "medium",
            "expected_result": expected_result,
            "label_confidence": round(confidence, 2),
            "needs_review": needs_review,
        }
    confidence = 0.62 if any(token in full_text for token in ("policy", "invoice", "summary", "report")) else 0.51
    return {
        "sample_type": "benign",
        "attack_category": None,
        "attack_subtype": None,
        "risk_level": "low",
        "expected_result": "allow",
        "label_confidence": round(confidence, 2),
        "needs_review": confidence < 0.7,
    }


def compute_quality_score(text: str, label_confidence: float, expected_result: str) -> float:
    length = len(text.strip())
    if length == 0:
        return 0.0
    length_score = 0.3 if length < 12 or length > 5000 else 0.75
    result_bonus = 0.1 if expected_result in {"allow", "block"} else 0.0
    return round(min(1.0, length_score + (label_confidence * 0.5) + result_bonus), 2)


def ensure_export_filename(filename: str | None, default_name: str) -> Path:
    settings = get_settings()
    target_name = filename or default_name
    if Path(target_name).name != target_name:
        raise AppError(400, "Export filename must not include path segments.")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", target_name)
    target_path = (settings.export_path / safe_name).resolve()
    if settings.export_path not in target_path.parents and target_path != settings.export_path:
        raise AppError(400, "Resolved export path is outside the export directory.")
    return target_path


def export_rows(rows: list[dict[str, Any]], export_format: str, filename: str | None, default_name: str) -> dict:
    target_path = ensure_export_filename(filename, default_name)
    if export_format == "jsonl":
        payload = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
        target_path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
    elif export_format == "csv":
        buffer = io.StringIO()
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        target_path.write_text(buffer.getvalue(), encoding="utf-8")
    else:
        raise AppError(400, "Unsupported export format.")
    return {"path": str(target_path), "record_count": len(rows), "format": export_format}


def write_export_manifest(data_path: str, manifest: dict[str, Any]) -> str:
    target = Path(data_path)
    manifest_path = target.with_name(f"{target.stem}.manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return str(manifest_path)


def emit_audit_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )


def jaccard_similarity(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return round(intersection / union, 2) if union else 0.0


def detect_conflicts(samples: list[SampleRecord]) -> list[dict[str, Any]]:
    by_fingerprint: dict[str, list[SampleRecord]] = defaultdict(list)
    for sample in samples:
        by_fingerprint[sample.canonical_fingerprint].append(sample)
    conflicts: list[dict[str, Any]] = []
    for fingerprint, items in by_fingerprint.items():
        label_set = {(item.sample_type, item.attack_category) for item in items}
        if len(label_set) > 1:
            conflicts.append(
                {
                    "fingerprint": fingerprint,
                    "sample_ids": [item.id for item in items],
                    "labels": [
                        {"sample_type": sample_type, "attack_category": attack_category}
                        for sample_type, attack_category in sorted(label_set)
                    ],
                }
            )
    return conflicts


def compute_similarity_groups(samples: list[SampleRecord], threshold: float) -> list[dict[str, Any]]:
    parents = {sample.id: sample.id for sample in samples}
    pair_scores: dict[tuple[str, str], float] = {}

    def find(node: str) -> str:
        while parents[node] != node:
            parents[node] = parents[parents[node]]
            node = parents[node]
        return node

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parents[root_right] = root_left

    for index, left in enumerate(samples):
        for right in samples[index + 1 :]:
            score = jaccard_similarity(left.text, right.text)
            if score >= threshold:
                pair_scores[(left.id, right.id)] = score
                union(left.id, right.id)

    grouped: dict[str, list[str]] = defaultdict(list)
    for sample in samples:
        grouped[find(sample.id)].append(sample.id)

    groups: list[dict[str, Any]] = []
    for root, sample_ids in grouped.items():
        if len(sample_ids) < 2:
            continue
        related_scores = [score for (left, right), score in pair_scores.items() if left in sample_ids and right in sample_ids]
        avg_score = round(sum(related_scores) / len(related_scores), 2) if related_scores else threshold
        group_key = hashlib.md5(",".join(sorted(sample_ids)).encode("utf-8")).hexdigest()[:16]
        groups.append({"group_key": group_key, "sample_ids": sample_ids, "score": avg_score})
    return groups


def persist_similarity_groups(db: Session, groups: list[dict[str, Any]]) -> None:
    db.query(SimilarityGroup).delete()
    for group in groups:
        db.add(
            SimilarityGroup(
                group_key=group["group_key"],
                sample_ids=group["sample_ids"],
                score=group["score"],
                status="open",
            )
        )


def serialize_sample(sample: SampleRecord) -> dict[str, Any]:
    return {
        "id": sample.id,
        "text": sample.text,
        "retrieved_context": sample.retrieved_context,
        "model_output": sample.model_output,
        "sample_type": sample.sample_type,
        "attack_category": sample.attack_category,
        "attack_subtype": sample.attack_subtype,
        "risk_level": sample.risk_level,
        "expected_result": sample.expected_result,
        "scenario": sample.scenario,
        "tags": sample.tags,
        "label_confidence": sample.label_confidence,
        "needs_review": sample.needs_review,
        "review_comment": sample.review_comment,
        "tenant_slug": sample.tenant_slug,
        "application_key": sample.application_key,
        "environment": sample.environment,
        "source_type": sample.source_type,
        "source_uri": sample.source_uri,
        "source_project": sample.source_project,
        "import_batch_id": sample.import_batch_id,
        "dataset_id": None,
        "dataset_version_id": None,
        "parent_sample_id": sample.parent_sample_id,
        "mutation_type": sample.mutation_type,
        "pair_id": sample.pair_id,
        "generator_model": sample.generator_model,
        "generator_prompt_version": sample.generator_prompt_version,
        "generation_params": sample.generation_params,
        "reviewer": sample.reviewer,
        "review_status": sample.review_status,
        "reviewed_at": sample.reviewed_at.isoformat() if sample.reviewed_at else None,
        "quality_score": sample.quality_score,
        "duplicate_group_id": sample.duplicate_group_id,
        "canonical_fingerprint": sample.canonical_fingerprint,
        "language": sample.language,
        "created_at": sample.created_at.isoformat(),
        "updated_at": sample.updated_at.isoformat(),
    }


def serialize_llmguard_row(sample: SampleRecord) -> dict[str, Any]:
    return {
        "text": sample.text,
        "retrieved_context": sample.retrieved_context,
        "model_output": sample.model_output,
        "sample_type": sample.sample_type,
        "attack_category": sample.attack_category,
        "attack_subtype": sample.attack_subtype,
        "risk_level": sample.risk_level,
        "expected_result": sample.expected_result,
        "scenario": sample.scenario,
        "tags": sample.tags,
        "label_confidence": sample.label_confidence,
        "needs_review": sample.needs_review,
        "review_comment": sample.review_comment,
        "tenant_slug": sample.tenant_slug,
        "application_key": sample.application_key,
        "environment": sample.environment,
    }
