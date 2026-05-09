import sqlite3
import uuid

import pytest

from scripts.learning.api import (
    add_interaction_record,
    create_learning_plan,
    extend_learning_plan_topics,
    get_learning_context,
    get_quiz_context,
    get_review_context,
    list_learning_plans,
)
from scripts.learning.validation import LearningPayloadError
from scripts.foundation.storage import transaction
from scripts.knowledge_graph.api import ingest_knowledge_graph
from tests.helpers import sample_graph_payload


def test_plan_create_extend_and_list(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    assert plan["graph_id"] == "g1"
    extended = extend_learning_plan_topics(plan["plan_id"], ["t2"])
    assert extended["added_topics"] == ["t2"]
    plans = list_learning_plans()
    assert plans["items"][0]["plan_id"] == plan["plan_id"]


def test_list_plans_returns_all_focus_topics(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO Topic(topicId, graphId, parentTopicId, topicName, topicType, sortOrder, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("t3", "g1", None, "Topic 3", "chapter", 3, "active"),
        )
        conn.execute(
            """
            INSERT INTO Topic(topicId, graphId, parentTopicId, topicName, topicType, sortOrder, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("t4", "g1", None, "Topic 4", "chapter", 4, "active"),
        )
        conn.execute(
            """
            INSERT INTO Topic(topicId, graphId, parentTopicId, topicName, topicType, sortOrder, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("t5", "g1", None, "Topic 5", "chapter", 5, "active"),
        )
        conn.execute(
            """
            INSERT INTO Topic(topicId, graphId, parentTopicId, topicName, topicType, sortOrder, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("t6", "g1", None, "Topic 6", "chapter", 6, "active"),
        )
    extend_learning_plan_topics(plan["plan_id"], ["t2", "t3", "t4", "t5", "t6"])
    plans = list_learning_plans()
    topic_ids = [item["topic_id"] for item in plans["items"][0]["focus_topics"]]
    assert topic_ids == ["t1", "t2", "t3", "t4", "t5", "t6"]
    assert "topic_name" in plans["items"][0]["focus_topics"][0]
    assert plans["items"][0]["topic_content"]


def test_list_plans_focus_topics_follow_graph_sort_order(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t2")
    extend_learning_plan_topics(plan["plan_id"], ["t1"])
    plans = list_learning_plans()
    topic_ids = [item["topic_id"] for item in plans["items"][0]["focus_topics"]]
    assert topic_ids[:2] == ["t1", "t2"]


def test_list_plans_returns_completed_and_pending_task_counts(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO LearningTask(
                learningTaskId, learningPlanId, conceptId, taskType, reasonType, strategy,
                priorityScore, dueAt, generatedAt, batchId, status, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                plan["plan_id"],
                "c1",
                "review",
                "manual",
                "test",
                0.5,
                None,
                "2026-01-01T00:00:00+00:00",
                None,
                "completed",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
    plans = list_learning_plans()
    item = plans["items"][0]
    assert item["completed_tasks"] >= 1
    assert item["pending_tasks"] >= 0


def test_context_and_append_record_flow(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    learning_context = get_learning_context(plan["plan_id"], topic_id="t1")
    assert "concept_pack_brief" in learning_context
    quiz_context = get_quiz_context(plan["plan_id"], topic_id="t1")
    assert "quiz_scope" in quiz_context
    append_result = add_interaction_record(
        plan["plan_id"],
        "quiz",
        {
            "concept_id": "c1",
            "result": "correct",
            "score": 85,
            "difficulty_bucket": "medium",
            "latency_ms": 1200,
        },
    )
    assert append_result["commit_result"]["record_type"] == "quiz"
    assert append_result["plan_delta_summary"]["plan_id"] == plan["plan_id"]
    assert append_result["plan_delta_summary"]["plan_touched"] is True
    assert "task_status_delta_summary" in append_result
    review_context = get_review_context(plan["plan_id"])
    assert "due_items" in review_context


def test_review_context_includes_scope_and_candidate_scoring(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    add_interaction_record(
        plan["plan_id"],
        "quiz",
        {
            "concept_id": "c1",
            "result": "incorrect",
            "score": 30,
            "difficulty_bucket": "medium",
        },
    )
    context = get_review_context(plan["plan_id"], topic_id="t1")
    assert context["scope"]["topic_ids"] == ["t1"]
    assert "candidate_items" in context
    assert "review_score_factors" in context
    assert "c1" in context["review_score_factors"]
    assert context["queue_policy"]["weights"]["overdue_score"] == 0.35


def test_append_record_bumps_plan_updated_at_and_reorders_plans(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    p1 = create_learning_plan("g1", topic_id="t1")
    p2 = create_learning_plan("g1", topic_id="t2")
    assert p2["plan_id"] == p1["plan_id"]
    assert p2["plan_reused"] is True
    before = list_learning_plans()
    assert len(before["items"]) == 1
    assert before["items"][0]["plan_id"] == p1["plan_id"]

    add_interaction_record(
        p1["plan_id"],
        "review",
        {
            "concept_id": "c1",
            "result": "correct",
            "score": 90,
            "difficulty_bucket": "easy",
        },
    )
    after = list_learning_plans()
    assert after["items"][0]["plan_id"] == p1["plan_id"]


def test_add_interaction_record_syncs_task_status_to_completed_and_pending(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    first = add_interaction_record(
        plan["plan_id"],
        "quiz",
        {
            "concept_id": "c1",
            "result": "correct",
            "score": 92,
            "difficulty_bucket": "medium",
        },
    )
    assert first["task_status_delta_summary"]["status"] == "completed"

    second = add_interaction_record(
        plan["plan_id"],
        "quiz",
        {
            "concept_id": "c1",
            "result": "incorrect",
            "score": 30,
            "difficulty_bucket": "hard",
        },
    )
    assert second["task_status_delta_summary"]["status"] == "pending"


def test_create_plan_reuses_existing_graph_plan_and_extends_scope(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    created = create_learning_plan("g1", topic_id="t1")
    reused = create_learning_plan("g1", topic_id="t2")
    assert created["plan_reused"] is False
    assert reused["plan_reused"] is True
    assert reused["plan_id"] == created["plan_id"]

    context = get_learning_context(created["plan_id"])
    assert set(context["concept_scope"]["topic_ids"]) == {"t1", "t2"}


def test_add_interaction_record_rolls_back_on_state_failure(isolated_db, monkeypatch):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")

    from scripts.learning import api as learning_api_module

    def _boom(**_: object) -> dict[str, object]:
        raise RuntimeError("state_failed")

    monkeypatch.setattr(learning_api_module, "update_state_from_record", _boom)

    with pytest.raises(RuntimeError, match="state_failed"):
        add_interaction_record(
            plan["plan_id"],
            "quiz",
            {
                "concept_id": "c1",
                "result": "correct",
                "score": 85,
                "difficulty_bucket": "medium",
            },
        )

    with transaction() as conn:
        record_count = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM LearningRecord lr
            JOIN LearningSession ls ON ls.sessionId = lr.sessionId
            WHERE ls.learningPlanId = ?
            """,
            (plan["plan_id"],),
        ).fetchone()["cnt"]
    assert record_count == 0


def test_list_learning_plans_progress_includes_concepts_and_records(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    add_interaction_record(
        plan["plan_id"],
        "quiz",
        {
            "concept_id": "c1",
            "result": "correct",
            "score": 90,
            "difficulty_bucket": "medium",
        },
    )
    plans = list_learning_plans()
    prog = plans["items"][0]["progress"]
    assert prog["concepts_touched"] >= 1
    assert prog["records_by_mode"]["quiz"] >= 1
    assert prog["records_by_mode"]["learn"] == 0


def test_add_interaction_record_wraps_sqlite_integrity_error(isolated_db, monkeypatch):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")

    def boom(*args: object, **kwargs: object) -> dict[str, object]:
        raise sqlite3.IntegrityError("FOREIGN KEY constraint failed")

    monkeypatch.setattr("scripts.learning.api.append_record_impl", boom)
    with pytest.raises(LearningPayloadError) as excinfo:
        add_interaction_record(plan["plan_id"], "learn", {"concept_id": "c1", "result": "ok"})
    assert excinfo.value.code == "db_constraint_failed"
    assert "FOREIGN KEY" in excinfo.value.message


def test_add_interaction_record_rejects_unknown_concept(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    with pytest.raises(LearningPayloadError) as excinfo:
        add_interaction_record(
            plan["plan_id"],
            "learn",
            {"concept_id": "no-such-concept", "result": "ok"},
        )
    assert excinfo.value.code == "concept_not_in_plan_graph"


def test_add_interaction_record_rejects_concept_from_other_graph(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    other = sample_graph_payload()
    other["concepts"] = [
        {
            "concept_id": "g2-only",
            "canonical_name": "Other graph concept",
            "definition": "Exists only under graph g2.",
            "concept_type": "fundamental",
            "difficulty_level": "easy",
        }
    ]
    other["topics"] = [
        {"topic_id": "g2t1", "topic_name": "G2 chapter", "topic_type": "chapter", "sort_order": 1},
    ]
    other["topic_concepts"] = [
        {
            "topic_concept_id": "g2tc1",
            "topic_id": "g2t1",
            "concept_id": "g2-only",
            "role": "core",
            "rank": 1,
        },
    ]
    other["relations"] = []
    other["evidences"] = []
    other["relation_evidences"] = []
    ingest_knowledge_graph("g2", other)
    plan = create_learning_plan("g1", topic_id="t1")
    with pytest.raises(LearningPayloadError) as excinfo:
        add_interaction_record(plan["plan_id"], "learn", {"concept_id": "g2-only", "result": "ok"})
    assert excinfo.value.code == "concept_not_in_plan_graph"


def test_add_interaction_record_invalid_mode_raises(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    with pytest.raises(LearningPayloadError) as excinfo:
        add_interaction_record(plan["plan_id"], "invalid", {"concept_id": "c1"})
    assert excinfo.value.code == "invalid_mode"


def test_add_interaction_record_blocked_with_high_score_rejected(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    with pytest.raises(LearningPayloadError) as excinfo:
        add_interaction_record(
            plan["plan_id"],
            "quiz",
            {"concept_id": "c1", "result": "blocked", "score": 95},
        )
    assert excinfo.value.code == "score_result_mismatch"


def test_add_interaction_record_inserts_completed_when_no_prior_task(isolated_db, monkeypatch):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")

    from scripts.learning import api as learning_api_module

    def _noop_upsert(**_: object) -> dict[str, object]:
        return {"task_action": "skipped"}

    monkeypatch.setattr(learning_api_module, "upsert_task_for_state", _noop_upsert)

    result = add_interaction_record(
        plan["plan_id"],
        "quiz",
        {
            "concept_id": "c1",
            "result": "correct",
            "score": 92,
            "difficulty_bucket": "medium",
        },
    )
    assert result["task_status_delta_summary"]["status_action"] == "inserted_completed"
