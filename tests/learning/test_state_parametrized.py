import pytest

from scripts.foundation.storage import query_one
from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.api import create_learning_plan
from scripts.learning.state import update_state_from_record
from tests.helpers import sample_graph_payload


def _setup():
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    learner = query_one(
        "SELECT learnerId AS learner_id FROM LearningPlan WHERE learningPlanId = ?",
        (plan["plan_id"],),
    )
    return learner["learner_id"], plan["plan_id"]


@pytest.mark.parametrize(
    ("score", "expected_mastery"),
    [
        (None, 0.6),
        (-10, 0.0),
        (40, 0.4),
        (120, 1.0),
    ],
)
def test_update_state_score_normalization(score, expected_mastery, isolated_db):
    learner_id, plan_id = _setup()
    payload = {"concept_id": "c1", "result": "ok", "difficulty_bucket": "medium"}
    if score is not None:
        payload["score"] = score
    state = update_state_from_record(
        learner_id=learner_id,
        learning_plan_id=plan_id,
        concept_id="c1",
        mode="learn",
        record_payload=payload,
    )
    assert state["mastery_score"] == pytest.approx(expected_mastery)


@pytest.mark.parametrize(
    ("result", "expected_correct", "expected_wrong"),
    [
        ("correct", 1, 0),
        ("pass", 1, 0),
        ("ok", 1, 0),
        ("wrong", 0, 1),
        ("fail", 0, 1),
        ("incorrect", 0, 1),
        ("unknown", 0, 0),
    ],
)
def test_update_state_result_buckets(result, expected_correct, expected_wrong, isolated_db):
    learner_id, plan_id = _setup()
    update_state_from_record(
        learner_id=learner_id,
        learning_plan_id=plan_id,
        concept_id="c1",
        mode="quiz",
        record_payload={"concept_id": "c1", "result": result, "score": 70},
    )
    row = query_one(
        """
        SELECT correctCount AS correct_count, wrongCount AS wrong_count
        FROM LearnerConceptState
        WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
        """,
        (learner_id, plan_id, "c1"),
    )
    assert row["correct_count"] == expected_correct
    assert row["wrong_count"] == expected_wrong
