import pytest

from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.learn_chapter import resolve_learn_active_topic
from scripts.orchestration.orchestration_app_service import OrchestrationAppService
from tests.helpers import multi_concept_graph_payload


@pytest.fixture
def multi_plan(isolated_db):
    ingest_knowledge_graph("g-multi", multi_concept_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g-multi", topic_id="t1")
    service.extend_learning_plan_topics(plan["plan_id"], ["t2"])
    return service, plan["plan_id"]


def test_quiz_record_counts_as_touched(multi_plan):
    service, plan_id = multi_plan
    service.add_interaction_record(
        plan_id,
        "quiz",
        {"concept_id": "c1a", "result": "correct", "score": 90, "difficulty_bucket": "easy"},
    )

    prompt = service.get_learn_context(plan_id)
    summary = prompt["context_summary"]
    current = summary["session_queue"]["current_item"]

    assert "c1a" not in {item["concept_id"] for item in summary["session_queue"]["items"]}
    assert current is not None
    assert current["concept_id"] == "c1b"
    assert summary["active_topic_id"] == "t1"


def test_no_backfill_when_recent_activity_on_later_chapter(multi_plan):
    service, plan_id = multi_plan
    service.add_interaction_record(
        plan_id,
        "learn",
        {"concept_id": "c2a", "result": "ok", "score": 80, "difficulty_bucket": "medium"},
    )

    prompt = service.get_learn_context(plan_id)
    summary = prompt["context_summary"]

    assert summary["active_topic_id"] == "t2"
    current = summary["session_queue"]["current_item"]
    assert current is not None
    assert current["concept_id"] == "c2b"
    queue_ids = [item["concept_id"] for item in summary["session_queue"]["items"]]
    assert "c1a" not in queue_ids
    assert "c1b" not in queue_ids


def test_continue_same_chapter_next_concept(multi_plan):
    service, plan_id = multi_plan
    service.add_interaction_record(
        plan_id,
        "learn",
        {"concept_id": "c2a", "result": "ok", "score": 85, "difficulty_bucket": "medium"},
    )

    prompt = service.get_learn_context(
        plan_id,
        session_context={
            "served_concept_ids": ["c2a"],
            "last_completed_concept_id": "c2a",
            "last_result": "ok",
        },
    )
    current = prompt["context_summary"]["session_queue"]["current_item"]
    assert current is not None
    assert current["concept_id"] == "c2b"


def test_chapter_complete_suggests_extend(multi_plan):
    service, plan_id = multi_plan
    for concept_id in ("c2a", "c2b"):
        service.add_interaction_record(
            plan_id,
            "learn",
            {"concept_id": concept_id, "result": "ok", "score": 85, "difficulty_bucket": "medium"},
        )

    prompt = service.get_learn_context(plan_id, topic_id="t2")
    summary = prompt["context_summary"]
    assert summary["session_queue"]["current_item"] is None
    assert summary["chapter_progress"]["next_topic_id"] is None


def test_explicit_topic_id_overrides_recent(multi_plan):
    service, plan_id = multi_plan
    service.add_interaction_record(
        plan_id,
        "learn",
        {"concept_id": "c2a", "result": "ok", "score": 80, "difficulty_bucket": "medium"},
    )

    prompt = service.get_learn_context(plan_id, topic_id="t1")
    summary = prompt["context_summary"]
    assert summary["active_topic_id"] == "t1"
    current = summary["session_queue"]["current_item"]
    assert current is not None
    assert current["topic_id"] == "t1"


def test_resolve_learn_active_topic_forward_scan():
    concepts = [
        {"concept_id": "c1a", "topic_id": "t1"},
        {"concept_id": "c1b", "topic_id": "t1"},
        {"concept_id": "c2a", "topic_id": "t2"},
    ]
    touched = {"c1a"}
    assert resolve_learn_active_topic(["t1", "t2"], concepts, touched, "t1", None) == "t1"
    assert resolve_learn_active_topic(["t1", "t2"], concepts, {"c1a", "c1b"}, "t1", None) == "t2"
    assert resolve_learn_active_topic(["t1", "t2"], concepts, touched, "t2", None) == "t2"
