from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.deps import AdminAccess, DbSession
from models.schemas import ReviewDecisionCreate, ReviewTaskCreate
from services.review_service import create_review_task, decide_review_task, list_review_queue

router = APIRouter(tags=["review"])


@router.get("/review-queue")
def get_review_queue(
    status: str | None = None,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return {"items": list_review_queue(db, status=status)}


@router.post("/review-tasks")
def create_review_task_endpoint(
    payload: ReviewTaskCreate,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return create_review_task(db, payload)


@router.post("/review-tasks/{task_id}/decide")
def decide_review_task_endpoint(
    task_id: str,
    payload: ReviewDecisionCreate,
    _: None = AdminAccess,
    db: Session = DbSession,
) -> dict:
    return decide_review_task(db, task_id, payload)
