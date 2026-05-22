"""Tests for get_mastery_diagnostics."""

from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.api import (
    add_interaction_record,
    create_learning_plan,
    get_mastery_diagnostics,
)
from tests.helpers import sample_graph_payload


def _graph_with_part_of() -> dict:
    payload = sample_graph_payload()
    payload["concepts"].append(
        {
            "concept_id": "c3",
            "canonical_name": "Sub-variable",
            "definition": "Nested variable detail.",
            "concept_type": "fundamental",
            "difficulty_level": "easy",
        }
    )
    payload["relations"].append(
        {
            "concept_relation_id": "r-part",
            "from_concept_id": "c3",
            "to_concept_id": "c1",
            "relation_type": "part_of",
        }
    )
    payload["relation_evidences"].append(
        {
            "relation_evidence_id": "re-part",
            "concept_relation_id": "r-part",
            "evidence_id": "e1",
            "support_score": 0.8,
        }
    )
    return payload


def test_get_mastery_diagnostics_plan_scope(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    add_interaction_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c1", "result": "wrong", "score": 30},
    )

    out = get_mastery_diagnostics(plan["plan_id"])
    assert out["graph_id"] == "g1"
    assert out["scope"]["kind"] == "plan"
    assert "c1" in out["scope"]["concept_ids"]
    assert out["summary"]["concepts_in_scope"] >= 1
    assert out["summary"]["records_by_mode"]["quiz"] >= 1
    concept_ids = {item["concept_id"] for item in out["by_concept"]}
    assert "c1" in concept_ids
    assert out["ranked_weak_concepts"]


def test_get_mastery_diagnostics_topic_scope(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")

    out = get_mastery_diagnostics(plan["plan_id"], topic_id="t1")
    assert out["scope"]["kind"] == "topic"
    assert out["scope"]["anchor_topic_id"] == "t1"
    assert set(out["scope"]["concept_ids"]) == {"c1"}
    assert len(out["by_topic"]) == 1
    assert out["by_topic"][0]["topic_id"] == "t1"


def test_get_mastery_diagnostics_concept_scope_includes_part_of_child(isolated_db):
    ingest_knowledge_graph("g-part", _graph_with_part_of())
    plan = create_learning_plan("g-part", topic_id="t1")

    out = get_mastery_diagnostics(plan["plan_id"], concept_id="c1")
    assert out["scope"]["kind"] == "concept"
    assert set(out["scope"]["concept_ids"]) == {"c1", "c3"}
    by_id = {item["concept_id"]: item for item in out["by_concept"]}
    assert "c3" in by_id
    assert by_id["c1"]["is_scope_anchor"] is True
    assert by_id["c3"]["is_scope_anchor"] is False


def test_get_mastery_diagnostics_mutually_exclusive_scope(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    plan = create_learning_plan("g1", topic_id="t1")
    out = get_mastery_diagnostics(plan["plan_id"], topic_id="t1", concept_id="c1")
    assert out["error"] == "invalid_scope"


def test_get_mastery_diagnostics_plan_not_found(isolated_db):
    out = get_mastery_diagnostics("missing-plan")
    assert out["error"] == "plan_not_found"
