from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.knowledge_graph.store import (
    get_topic_concepts,
    list_graphs,
    resolve_scope_concepts,
)
from tests.helpers import sample_graph_payload


def _ingest_graph_with_suffix(graph_id: str, suffix: str):
    payload = sample_graph_payload()
    for topic in payload["topics"]:
        topic["topic_id"] = f"{topic['topic_id']}-{suffix}"
        topic["topic_name"] = f"{topic['topic_name']}-{suffix}"
    for concept in payload["concepts"]:
        concept["concept_id"] = f"{concept['concept_id']}-{suffix}"
        concept["canonical_name"] = f"{concept['canonical_name']}-{suffix}"
    payload["topic_concepts"] = [
        {
            "topic_concept_id": f"tc1-{suffix}",
            "topic_id": f"t1-{suffix}",
            "concept_id": f"c1-{suffix}",
            "role": "core",
            "rank": 1,
        },
        {
            "topic_concept_id": f"tc2-{suffix}",
            "topic_id": f"t2-{suffix}",
            "concept_id": f"c2-{suffix}",
            "role": "core",
            "rank": 1,
        },
    ]
    payload["relations"] = [
        {
            "concept_relation_id": f"r1-{suffix}",
            "from_concept_id": f"c1-{suffix}",
            "to_concept_id": f"c2-{suffix}",
            "relation_type": "prerequisite_of",
        }
    ]
    payload["evidences"] = [
        {
            "evidence_id": f"e1-{suffix}",
            "source_type": "doc",
            "source_title": "Guide",
            "quote_text": "Variables are used before function logic.",
        }
    ]
    payload["relation_evidences"] = [
        {
            "relation_evidence_id": f"re1-{suffix}",
            "concept_relation_id": f"r1-{suffix}",
            "evidence_id": f"e1-{suffix}",
            "support_score": 0.9,
        }
    ]
    ingest_knowledge_graph(graph_id, payload)


def test_list_graphs_pagination(isolated_db):
    _ingest_graph_with_suffix("g1", "a")
    _ingest_graph_with_suffix("g2", "b")
    _ingest_graph_with_suffix("g3", "c")

    first = list_graphs(limit=2, offset=None)
    assert len(first["items"]) == 2
    assert first["has_more"] is True
    assert first["next_offset"] == "2"

    second = list_graphs(limit=2, offset=first["next_offset"])
    assert len(second["items"]) == 1
    assert second["has_more"] is False
    assert second["next_offset"] is None


def test_get_topic_concepts_filters_and_paginates(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    page = get_topic_concepts(graph_id="g1", topic_id="t1", concept_limit=1, offset=None)

    assert len(page["items"]) == 1
    assert page["items"][0]["topic_id"] == "t1"
    assert page["items"][0]["concept_id"] == "c1"
    assert page["has_more"] is False
    assert page["next_offset"] is None


def test_resolve_scope_concepts_priority_and_fallback(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())

    direct = resolve_scope_concepts("g1", {"concept_ids": ["manual-cx"]})
    assert direct == ["manual-cx"]

    by_topic = resolve_scope_concepts("g1", {"topic_ids": ["t1"]})
    assert by_topic == ["c1"]

    all_concepts = resolve_scope_concepts("g1", {})
    assert set(all_concepts) == {"c1", "c2"}


def test_resolve_scope_concepts_empty_when_no_data(isolated_db):
    concepts = resolve_scope_concepts("unknown-graph", {})
    assert concepts == []
