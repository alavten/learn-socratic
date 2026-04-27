"""Hard delete and prune behavior for knowledge graph."""

from scripts.knowledge_graph.api import (
    get_concepts,
    get_concept_relations,
    ingest_knowledge_graph,
    remove_knowledge_graph_entities,
)
from scripts.learning import api as learning_api
from scripts.orchestration.orchestration_app_service import OrchestrationAppService
from tests.helpers import sample_graph_payload


def test_remove_concept_via_orchestration_after_force_cleanup(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")
    service.append_learning_record(
        plan["plan_id"],
        "learn",
        {"concept_id": "c1", "result": "ok"},
    )

    blocked = service.remove_knowledge_graph_entities(
        "g1",
        {"concept_ids": ["c1"]},
        force_delete=False,
    )
    assert blocked.get("error") == "dependency_conflict"
    assert blocked["forced"] is False

    ok = service.remove_knowledge_graph_entities(
        "g1",
        {"concept_ids": ["c1"]},
        force_delete=True,
    )
    assert ok.get("error") is None
    assert ok["forced"] is True
    assert ok["cleanup_summary"]["learning_records_deleted"] >= 1
    assert ok["delete_summary"]["concepts_deleted"] == 1

    concepts = get_concepts("g1", {"concept_ids": ["c1", "c2"]})
    ids = {b["concept_id"] for b in concepts["concept_briefs"]}
    assert "c1" not in ids
    assert "c2" in ids


def test_remove_relation_only_no_learning_conflict(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    out = remove_knowledge_graph_entities("g1", {"relation_ids": ["r1"]})
    assert out.get("error") is None
    assert out["relations_deleted"] >= 1
    rels = get_concept_relations("g1", {"concept_ids": ["c1", "c2"]})
    assert rels["relation_briefs"] == []


def test_ingest_prune_removes_missing_concept_in_scope(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    slim = sample_graph_payload()
    slim["concepts"] = [c for c in slim["concepts"] if c["concept_id"] == "c1"]
    slim["relations"] = []
    slim["evidences"] = []
    slim["relation_evidences"] = []
    slim["topic_concepts"] = [tc for tc in slim["topic_concepts"] if tc["concept_id"] == "c1"]

    result = ingest_knowledge_graph(
        "g1",
        slim,
        sync_mode="upsert_and_prune",
        prune_scope={"topic_ids": ["t1", "t2"]},
        force_delete=False,
    )
    assert result["validation_summary"]["ok"] is True
    pr = result.get("prune_result") or {}
    assert pr.get("blocked") is False
    assert "c2" in (pr.get("pruned_concept_ids") or [])


def test_check_plan_dependencies_topic_scope(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    service.create_learning_plan("g1", topic_id="t1")
    dep = learning_api.check_plan_dependencies("g1", concept_ids=[], topic_ids=["t1"])
    assert dep["has_blocking"] is True
    assert any(d["dep_type"] == "learning_plan_topic" for d in dep["blocking_dependencies"])
