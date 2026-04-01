from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.deps import DbSession, ScanAccess
from models.schemas import GenerationRequest
from services.generation_service import enqueue_generation_task, get_generation_task

router = APIRouter(prefix="/generation", tags=["generation"])


@router.post("/attacks")
def generate_attacks(
    payload: GenerationRequest,
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return enqueue_generation_task(db, "attack_generation", payload)


@router.post("/benign")
def generate_benign(
    payload: GenerationRequest,
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return enqueue_generation_task(db, "benign_overlap_generation", payload)


@router.post("/rag")
def generate_rag(
    payload: GenerationRequest,
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return enqueue_generation_task(db, "rag_indirect_generation", payload)


@router.post("/mutations")
def generate_mutations(
    payload: GenerationRequest,
    _: None = ScanAccess,
    db: Session = DbSession,
) -> dict:
    return enqueue_generation_task(db, "mutation_generation", payload)


@router.get("/tasks/{task_id}")
def read_generation_task(task_id: str, db: Session = DbSession) -> dict:
    return get_generation_task(db, task_id)
