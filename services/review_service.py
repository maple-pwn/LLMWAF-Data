from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from models.entities import ReviewDecision, ReviewTask, SampleRecord, utcnow
from models.schemas import ReviewDecisionCreate, ReviewTaskCreate
from services.common import emit_audit_event, serialize_sample
from services.sample_service import _apply_sample_changes

ALLOWED_RELABEL_FIELDS = {
    "text",
    "retrieved_context",
    "model_output",
    "sample_type",
    "attack_category",
    "attack_subtype",
    "risk_level",
    "expected_result",
    "scenario",
    "tags",
    "review_comment",
}


def create_review_task(db: Session, payload: ReviewTaskCreate) -> dict:
    sample = db.get(SampleRecord, payload.sample_id)
    if not sample:
        raise AppError(404, "Sample not found.")
    task = ReviewTask(sample_id=payload.sample_id, assignee=payload.assignee, priority=payload.priority, status="pending")
    sample.needs_review = True
    db.add(task)
    db.flush()
    emit_audit_event(db, "review.task_created", "review_task", task.id, {"sample_id": sample.id})
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "sample_id": task.sample_id,
        "assignee": task.assignee,
        "priority": task.priority,
        "status": task.status,
    }


def list_review_queue(db: Session, status: str | None = None) -> list[dict]:
    query = select(ReviewTask).order_by(ReviewTask.created_at.asc())
    if status:
        query = query.where(ReviewTask.status == status)
    tasks = db.execute(query).scalars().all()
    return [
        {
            "id": task.id,
            "sample_id": task.sample_id,
            "assignee": task.assignee,
            "priority": task.priority,
            "status": task.status,
        }
        for task in tasks
    ]


def decide_review_task(db: Session, task_id: str, payload: ReviewDecisionCreate) -> dict:
    task = db.get(ReviewTask, task_id)
    if not task:
        raise AppError(404, "Review task not found.")
    if task.status != "pending":
        raise AppError(409, "Review task has already been decided.")
    sample = db.get(SampleRecord, task.sample_id)
    if not sample:
        raise AppError(404, "Sample not found.")
    decision = ReviewDecision(
        review_task_id=task.id,
        decision=payload.decision,
        reviewer=payload.reviewer,
        comment=payload.comment,
        relabel_fields=payload.relabel_fields,
    )
    db.add(decision)
    task.status = "completed"
    sample.reviewer = payload.reviewer
    sample.review_comment = payload.comment
    sample.reviewed_at = utcnow()
    if payload.decision == "approve":
        sample.review_status = "approved"
        sample.needs_review = False
    elif payload.decision == "reject":
        sample.review_status = "rejected"
        sample.needs_review = True
    else:
        invalid_fields = sorted(set(payload.relabel_fields) - ALLOWED_RELABEL_FIELDS)
        if invalid_fields:
            raise AppError(400, f"Unsupported relabel fields: {', '.join(invalid_fields)}.")
        _apply_sample_changes(sample, payload.relabel_fields, allow_label_overrides=True)
        sample.review_status = "approved"
        sample.needs_review = False
    emit_audit_event(
        db,
        "review.decision_recorded",
        "review_task",
        task.id,
        {"decision": payload.decision, "reviewer": payload.reviewer},
    )
    db.commit()
    db.refresh(sample)
    return serialize_sample(sample)
