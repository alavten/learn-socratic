import pytest

from scripts.foundation.storage import query_one
from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.api import create_learning_plan
from scripts.learning.tasking import sync_task_status_from_result, upsert_task_for_state
from tests.helpers import sample_graph_payload


def _setup_plan():
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    return plan["plan_id"]


def test_upsert_task_creates_review_for_high_forgetting(isolated_db):
    plan_id = _setup_plan()

    result = upsert_task_for_state(
        learning_plan_id=plan_id,
        concept_id="c1",
        state_summary={"mastery_score": 0.2, "forgetting_risk": 0.8},
    )

    assert result["task_action"] == "created"
    assert result["task_type"] == "review"
    assert result["priority_score"] == 0.8

    row = query_one(
        """
        SELECT taskType AS task_type, reasonType AS reason_type, status
        FROM LearningTask
        WHERE learningTaskId = ?
        """,
        (result["learning_task_id"],),
    )
    assert row["task_type"] == "review"
    assert row["reason_type"] == "weak_point"
    assert row["status"] == "pending"


def test_upsert_task_creates_learn_for_low_forgetting(isolated_db):
    plan_id = _setup_plan()

    result = upsert_task_for_state(
        learning_plan_id=plan_id,
        concept_id="c2",
        state_summary={"mastery_score": 0.9, "forgetting_risk": 0.2},
    )

    assert result["task_action"] == "created"
    assert result["task_type"] == "learn"
    assert result["priority_score"] == pytest.approx(0.16)


def test_upsert_task_updates_existing_pending_task(isolated_db):
    plan_id = _setup_plan()
    first = upsert_task_for_state(
        learning_plan_id=plan_id,
        concept_id="c1",
        state_summary={"mastery_score": 0.5, "forgetting_risk": 0.5},
    )

    second = upsert_task_for_state(
        learning_plan_id=plan_id,
        concept_id="c1",
        state_summary={"mastery_score": 0.95, "forgetting_risk": 0.1},
        reason_type="manual",
    )

    assert first["learning_task_id"] == second["learning_task_id"]
    assert second["task_action"] == "updated"
    assert second["task_type"] == "learn"

    row = query_one(
        """
        SELECT reasonType AS reason_type, taskType AS task_type
        FROM LearningTask
        WHERE learningTaskId = ?
        """,
        (second["learning_task_id"],),
    )
    assert row["reason_type"] == "manual"
    assert row["task_type"] == "learn"


def test_sync_task_status_marks_pending_to_completed_on_success(isolated_db):
    plan_id = _setup_plan()
    created = upsert_task_for_state(
        learning_plan_id=plan_id,
        concept_id="c1",
        state_summary={"mastery_score": 0.8, "forgetting_risk": 0.2},
        last_result="incorrect",
    )
    out = sync_task_status_from_result(
        learning_plan_id=plan_id,
        concept_id="c1",
        state_summary={"mastery_score": 0.82, "forgetting_risk": 0.2},
        last_result="correct",
    )
    assert out["status_action"] == "pending_to_completed"
    assert out["learning_task_id"] == created["learning_task_id"]
    row = query_one(
        "SELECT status FROM LearningTask WHERE learningTaskId = ?",
        (created["learning_task_id"],),
    )
    assert row["status"] == "completed"


def test_sync_task_status_reopens_completed_to_pending_on_failure(isolated_db):
    plan_id = _setup_plan()
    created = upsert_task_for_state(
        learning_plan_id=plan_id,
        concept_id="c2",
        state_summary={"mastery_score": 0.8, "forgetting_risk": 0.2},
        last_result="incorrect",
    )
    first = sync_task_status_from_result(
        learning_plan_id=plan_id,
        concept_id="c2",
        state_summary={"mastery_score": 0.9, "forgetting_risk": 0.1},
        last_result="correct",
    )
    assert first["status_action"] == "pending_to_completed"
    second = sync_task_status_from_result(
        learning_plan_id=plan_id,
        concept_id="c2",
        state_summary={"mastery_score": 0.4, "forgetting_risk": 0.7},
        last_result="incorrect",
    )
    assert second["status_action"] == "completed_to_pending"
    assert second["learning_task_id"] == created["learning_task_id"]
    row = query_one(
        "SELECT status FROM LearningTask WHERE learningTaskId = ?",
        (created["learning_task_id"],),
    )
    assert row["status"] == "pending"
