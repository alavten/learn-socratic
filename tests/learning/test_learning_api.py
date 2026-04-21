from scripts.learning.api import (
    append_learning_record,
    create_learning_plan,
    extend_learning_plan_topics,
    get_learning_context,
    get_quiz_context,
    get_review_context,
    list_learning_plans,
)
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


def test_context_and_append_record_flow(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    learning_context = get_learning_context(plan["plan_id"], topic_id="t1")
    assert "concept_pack_brief" in learning_context
    quiz_context = get_quiz_context(plan["plan_id"], topic_id="t1")
    assert "quiz_scope" in quiz_context
    append_result = append_learning_record(
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
    review_context = get_review_context(plan["plan_id"])
    assert "due_items" in review_context
