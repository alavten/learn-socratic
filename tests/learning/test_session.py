import pytest

from scripts.foundation.storage import query_all, query_one
from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.api import create_learning_plan
from scripts.learning.session import add_interaction_record, get_or_create_active_session
from tests.helpers import sample_graph_payload


def _setup_plan():
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    learner = query_one(
        "SELECT learnerId AS learner_id FROM LearningPlan WHERE learningPlanId = ?",
        (plan["plan_id"],),
    )
    return plan["plan_id"], learner["learner_id"]


def test_get_or_create_active_session_reuses_existing(isolated_db):
    plan_id, learner_id = _setup_plan()
    first = get_or_create_active_session(plan_id)
    second = get_or_create_active_session(plan_id)

    assert first["session_id"] == second["session_id"]
    assert first["learner_id"] == learner_id

    rows = query_all(
        "SELECT sessionId AS session_id FROM LearningSession WHERE learningPlanId = ?",
        (plan_id,),
    )
    assert len(rows) == 1


def test_get_or_create_active_session_missing_plan_raises(isolated_db):
    with pytest.raises(ValueError, match="learning_plan_not_found"):
        get_or_create_active_session("missing-plan")


def test_add_interaction_record_validations(isolated_db):
    plan_id, _ = _setup_plan()

    with pytest.raises(ValueError, match="invalid_mode"):
        add_interaction_record(plan_id, "invalid", {"concept_id": "c1"})

    with pytest.raises(ValueError, match="missing_concept_id"):
        add_interaction_record(plan_id, "learn", {"score": 80})


def test_add_interaction_record_persists_payload_fields(isolated_db):
    plan_id, learner_id = _setup_plan()
    result = add_interaction_record(
        plan_id,
        "quiz",
        {
            "concept_id": "c1",
            "result": "correct",
            "score": 88,
            "latency_ms": 900,
            "difficulty_bucket": "hard",
            "feedback_type": "detailed",
        },
    )
    assert result["learner_id"] == learner_id
    assert result["record_type"] == "quiz"

    row = query_one(
        """
        SELECT
            conceptId AS concept_id,
            recordType AS record_type,
            score,
            latencyMs AS latency_ms,
            difficultyBucket AS difficulty_bucket,
            feedbackType AS feedback_type
        FROM LearningRecord
        WHERE learningRecordId = ?
        """,
        (result["learning_record_id"],),
    )
    assert row["concept_id"] == "c1"
    assert row["record_type"] == "quiz"
    assert row["score"] == 88.0
    assert row["latency_ms"] == 900
    assert row["difficulty_bucket"] == "hard"
    assert row["feedback_type"] == "detailed"
