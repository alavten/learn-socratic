from datetime import datetime

import pytest

from scripts.foundation.storage import query_one
from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.api import create_learning_plan
from scripts.learning.state import _mastery_level, update_state_from_record
from tests.helpers import sample_graph_payload


def _setup_plan_and_learner():
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    row = query_one(
        "SELECT learnerId AS learner_id FROM LearningPlan WHERE learningPlanId = ?",
        (plan["plan_id"],),
    )
    return row["learner_id"], plan["plan_id"]


def test_mastery_level_boundaries():
    assert _mastery_level(0.39) == "New"
    assert _mastery_level(0.4) == "Learning"
    assert _mastery_level(0.7) == "Proficient"
    assert _mastery_level(0.9) == "Mastered"


def test_update_state_creates_row_with_expected_counts(isolated_db):
    learner_id, plan_id = _setup_plan_and_learner()

    state = update_state_from_record(
        learner_id=learner_id,
        learning_plan_id=plan_id,
        concept_id="c1",
        mode="quiz",
        record_payload={
            "result": "correct",
            "score": 95,
            "difficulty_bucket": "hard",
        },
    )

    assert state["state_action"] == "created"
    assert state["mastery_level"] == "Mastered"
    assert state["forgetting_risk"] == pytest.approx(0.05)

    row = query_one(
        """
        SELECT quizCount AS quiz_count, hardCount AS hard_count, correctCount AS correct_count
        FROM LearnerConceptState
        WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
        """,
        (learner_id, plan_id, "c1"),
    )
    assert row["quiz_count"] == 1
    assert row["hard_count"] == 1
    assert row["correct_count"] == 1


def test_update_state_existing_row_uses_weighted_mastery_and_increments(isolated_db):
    learner_id, plan_id = _setup_plan_and_learner()

    first = update_state_from_record(
        learner_id=learner_id,
        learning_plan_id=plan_id,
        concept_id="c1",
        mode="learn",
        record_payload={"result": "ok", "score": 100, "difficulty_bucket": "medium"},
    )
    assert first["mastery_score"] == 1.0

    second = update_state_from_record(
        learner_id=learner_id,
        learning_plan_id=plan_id,
        concept_id="c1",
        mode="review",
        record_payload={"result": "wrong", "score": 0, "difficulty_bucket": "easy"},
    )

    assert second["state_action"] == "updated"
    assert second["mastery_score"] == pytest.approx(0.7)
    assert second["mastery_level"] == "Proficient"
    assert second["forgetting_risk"] == pytest.approx(0.3)
    assert datetime.fromisoformat(second["next_review_at"]) > datetime.fromisoformat(
        query_one(
            """
            SELECT createdAt AS created_at
            FROM LearningPlan
            WHERE learningPlanId = ?
            """,
            (plan_id,),
        )["created_at"]
    )

    row = query_one(
        """
        SELECT
            learnCount AS learn_count,
            reviewCount AS review_count,
            easyCount AS easy_count,
            mediumCount AS medium_count,
            wrongCount AS wrong_count,
            confidence
        FROM LearnerConceptState
        WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
        """,
        (learner_id, plan_id, "c1"),
    )
    assert row["learn_count"] == 1
    assert row["review_count"] == 1
    assert row["easy_count"] == 1
    assert row["medium_count"] == 1
    assert row["wrong_count"] == 1
    assert row["confidence"] == pytest.approx(0.91)
