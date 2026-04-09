from sqlalchemy import func, select

from models.entities import GenerationTask
from models.schemas import GenerationRequest
from services.generation_service import enqueue_generation_task, execute_generation_task, process_pending_generation_tasks


def test_generation_attack_task_creates_samples(db_session):
    queued = enqueue_generation_task(
        db_session,
        "attack_generation",
        GenerationRequest(
            count=2,
            tenant_slug="t1",
            application_key="a1",
            environment="dev",
            scenario="chat",
            categories=["jailbreak"],
        ),
    )
    assert queued["status"] == "pending"
    body = execute_generation_task(db_session, queued["id"])
    assert body["status"] == "completed"
    assert len(body["result_sample_ids"]) == 2
    assert db_session.scalar(select(func.count()).select_from(GenerationTask)) == 1


def test_generation_mutation_requires_parent(db_session):
    queued = enqueue_generation_task(
        db_session,
        "mutation_generation",
        GenerationRequest(
            count=1,
            tenant_slug="t1",
            application_key="a1",
            environment="dev",
            scenario="chat",
        ),
    )
    try:
        execute_generation_task(db_session, queued["id"])
    except Exception as exc:
        detail = str(exc)
    else:
        detail = ""
    assert "parent_sample_id" in detail


def test_worker_continues_after_failed_generation_task(db_session):
    bad_task = enqueue_generation_task(
        db_session,
        "mutation_generation",
        GenerationRequest(
            count=1,
            tenant_slug="t1",
            application_key="a1",
            environment="dev",
            scenario="chat",
        ),
    )
    good_task = enqueue_generation_task(
        db_session,
        "attack_generation",
        GenerationRequest(
            count=1,
            tenant_slug="t1",
            application_key="a1",
            environment="dev",
            scenario="chat",
            categories=["jailbreak"],
        ),
    )
    processed = process_pending_generation_tasks(db_session)
    assert processed == 2
    bad_row = db_session.get(GenerationTask, bad_task["id"])
    good_row = db_session.get(GenerationTask, good_task["id"])
    assert bad_row is not None
    assert good_row is not None
    assert bad_row.status == "failed"
    assert good_row.status == "completed"
