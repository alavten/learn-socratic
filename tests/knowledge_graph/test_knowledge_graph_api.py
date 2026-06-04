from scripts.knowledge_graph.api import (
    get_concept_evidence,
    get_concept_relations,
    get_concepts,
    get_knowledge_graph,
    ingest_knowledge_graph,
    list_knowledge_graphs,
)
from tests.helpers import sample_graph_payload


def test_ingest_and_list_graphs(isolated_db):
    result = ingest_knowledge_graph("g1", sample_graph_payload())
    assert result["validation_summary"]["ok"] is True
    graphs = list_knowledge_graphs()
    assert graphs["items"][0]["graph_id"] == "g1"
    assert graphs["items"][0]["graph_type"] == "domain"
    assert graphs["items"][0]["parent_graph_id"] is None
    assert "topic_content" in graphs["items"][0]
    assert graphs["items"][0]["topic_content"]


def test_get_graph_and_concept_queries(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    graph = get_knowledge_graph("g1")
    assert graph["graph"]["graph_id"] == "g1"
    assert graph["graph"]["parent_graph_id"] is None
    assert graph["graph"]["graph_type"] == "domain"
    concepts = get_concepts("g1", {"topic_ids": ["t1"]})
    assert concepts["concept_briefs"][0]["concept_id"] == "c1"
    relations = get_concept_relations("g1", {"concept_ids": ["c1"]})
    assert relations["relation_briefs"][0]["relation_type"] == "prerequisite_of"
    evidence = get_concept_evidence("g1", {"concept_ids": ["c1"]})
    assert evidence["evidence_summary"][0]["evidence_id"] == "e1"


def test_ingest_rejects_non_continuous_topic_sort_order(isolated_db):
    payload = sample_graph_payload()
    payload["topics"] = [
        {"topic_id": "t1", "topic_name": "Syntax", "topic_type": "chapter", "sort_order": 1},
        {"topic_id": "t2", "topic_name": "Functions", "topic_type": "chapter", "sort_order": 3},
    ]
    result = ingest_knowledge_graph("g1", payload)
    assert result["validation_summary"]["ok"] is False
    assert "continuous sort_order" in " ".join(result["validation_summary"]["errors"])


def test_ingest_chapter_payload_persists_parent_graph_id(isolated_db):
    parent_payload = {
        "graph": {
            "graph_type": "domain",
            "graph_name": "Parent Book",
            "schema_version": "1.0.0",
            "release_tag": "r1",
        },
        "topics": [],
        "concepts": [],
        "relations": [],
        "evidences": [],
        "topic_concepts": [],
        "relation_evidences": [],
    }
    assert ingest_knowledge_graph("parent-book", parent_payload)["validation_summary"]["ok"] is True

    child = sample_graph_payload()
    child["graph"]["parent_graph_id"] = "parent-book"
    assert ingest_knowledge_graph("child-ch1", child)["validation_summary"]["ok"] is True

    core = get_knowledge_graph("child-ch1")["graph"]
    assert core["parent_graph_id"] == "parent-book"
    listed = {item["graph_id"]: item for item in list_knowledge_graphs()["items"]}
    assert listed["child-ch1"]["parent_graph_id"] == "parent-book"


def test_batch_reindex_respects_payload_sort_order(isolated_db):
    payload = sample_graph_payload()
    payload["topics"] = [
        {
            "topic_id": "ch-a",
            "topic_name": "Chapter A",
            "topic_type": "chapter",
            "sort_order": 1,
        },
        {
            "topic_id": "ch-b",
            "topic_name": "Chapter B",
            "topic_type": "chapter",
            "sort_order": 2,
        },
    ]
    payload["topic_concepts"] = []
    ingest_knowledge_graph("g1", payload)
    graph = get_knowledge_graph("g1")
    topic_ids = [topic["topic_id"] for topic in graph["topics"]]
    assert topic_ids[:2] == ["ch-a", "ch-b"]
    assert graph["topics"][0]["sort_order"] == 1
    assert graph["topics"][1]["sort_order"] == 2


def _minimal_chapter_payload(topic_id: str, topic_name: str) -> dict:
    return {
        "graph": {
            "graph_type": "domain",
            "graph_name": "Incremental Book",
            "schema_version": "1.0.0",
            "release_tag": "r1",
        },
        "topics": [
            {
                "topic_id": topic_id,
                "topic_name": topic_name,
                "topic_type": "chapter",
                "sort_order": 1,
            }
        ],
        "concepts": [],
        "relations": [],
        "evidences": [],
        "topic_concepts": [],
        "relation_evidences": [],
    }


def test_incremental_ingest_appends_root_chapter_sort_order(isolated_db):
    assert ingest_knowledge_graph("inc-book", _minimal_chapter_payload("ch-1", "One"))[
        "validation_summary"
    ]["ok"]
    assert ingest_knowledge_graph("inc-book", _minimal_chapter_payload("ch-2", "Two"))[
        "validation_summary"
    ]["ok"]
    graph = get_knowledge_graph("inc-book")
    roots = [t for t in graph["topics"] if not t.get("parent_topic_id")]
    assert [t["topic_id"] for t in roots] == ["ch-1", "ch-2"]
    assert roots[0]["sort_order"] == 1
    assert roots[1]["sort_order"] == 2


def test_global_normalize_makes_continuous_sibling_orders(isolated_db):
    payload = sample_graph_payload()
    payload["topics"] = [
        {"topic_id": "dup-a", "topic_name": "A", "topic_type": "chapter", "sort_order": 1},
        {"topic_id": "dup-b", "topic_name": "B", "topic_type": "chapter", "sort_order": 2},
    ]
    payload["topic_concepts"] = []
    assert ingest_knowledge_graph("g-dup", payload)["validation_summary"]["ok"]

    from scripts.foundation.storage import transaction

    with transaction() as conn:
        conn.execute("UPDATE Topic SET sortOrder = 1 WHERE topicId IN ('dup-a', 'dup-b')")

    touch = {
        "graph": {
            "graph_type": "domain",
            "graph_name": "Dup",
            "schema_version": "1.0.0",
            "release_tag": "r2",
        },
        "topics": [],
        "concepts": [],
        "relations": [],
        "evidences": [],
        "topic_concepts": [],
        "relation_evidences": [],
    }
    result = ingest_knowledge_graph("g-dup", touch)
    assert result["validation_summary"]["ok"] is True
    assert result["change_summary"]["topics_sort_normalized"] >= 1

    graph = get_knowledge_graph("g-dup")
    roots = sorted(
        [t for t in graph["topics"] if not t.get("parent_topic_id")],
        key=lambda t: t["sort_order"],
    )
    assert [t["sort_order"] for t in roots] == [1, 2]
