from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.knowledge_graph.store import (
    collect_concept_ids_with_descendants,
    get_next_sibling_topic_id,
    get_topic_concepts,
    list_graphs,
    list_scope_concepts_ordered,
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


def test_list_scope_concepts_ordered_follows_topic_rank_not_alphabet(isolated_db):
    payload = sample_graph_payload()
    payload["concepts"] = [
        {
            "concept_id": "c-zebra",
            "canonical_name": "Zebra Term",
            "definition": "Later in rank.",
            "concept_type": "fundamental",
            "difficulty_level": "easy",
        },
        {
            "concept_id": "c-apple",
            "canonical_name": "Apple Term",
            "definition": "Earlier in rank.",
            "concept_type": "fundamental",
            "difficulty_level": "easy",
        },
    ]
    payload["topic_concepts"] = [
        {
            "topic_concept_id": "tc-z",
            "topic_id": "t1",
            "concept_id": "c-zebra",
            "role": "core",
            "rank": 1,
        },
        {
            "topic_concept_id": "tc-a",
            "topic_id": "t1",
            "concept_id": "c-apple",
            "role": "core",
            "rank": 2,
        },
    ]
    payload["relations"] = []
    payload["evidences"] = []
    payload["relation_evidences"] = []
    ingest_knowledge_graph("g-order", payload)

    ordered = list_scope_concepts_ordered("g-order", {"topic_ids": ["t1"]})
    ids = [item["concept_id"] for item in ordered["concept_briefs"]]
    assert ids == ["c-zebra", "c-apple"]


def test_get_next_sibling_topic_id_returns_following_chapter(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    assert get_next_sibling_topic_id("g1", "t1") == "t2"
    assert get_next_sibling_topic_id("g1", "t2") is None


def test_collect_concept_ids_with_descendants_part_of_chain(isolated_db):
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
    ingest_knowledge_graph("g-part", payload)

    assert set(collect_concept_ids_with_descendants("g-part", ["c1"])) == {"c1", "c3"}
    assert collect_concept_ids_with_descendants("g-part", ["c3"]) == ["c3"]
    assert collect_concept_ids_with_descendants("g-part", []) == []
