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
    assert "topic_content" in graphs["items"][0]
    assert graphs["items"][0]["topic_content"]


def test_get_graph_and_concept_queries(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    graph = get_knowledge_graph("g1")
    assert graph["graph"]["graph_id"] == "g1"
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


def test_ingest_reindexes_chapter1_priority_topics(isolated_db):
    payload = sample_graph_payload()
    payload["topics"] = [
        {
            "topic_id": "cc-ch1-harness-intro",
            "topic_name": "Harness Engineering 概述",
            "topic_type": "chapter",
            "sort_order": 1,
        },
        {
            "topic_id": "cc-ch1-unstable-model",
            "topic_name": "模型不可信前提",
            "topic_type": "chapter",
            "sort_order": 2,
        },
    ]
    payload["topic_concepts"] = [
        {
            "topic_concept_id": "tc1",
            "topic_id": "cc-ch1-harness-intro",
            "concept_id": "c1",
            "role": "core",
            "rank": 1,
        },
        {
            "topic_concept_id": "tc2",
            "topic_id": "cc-ch1-unstable-model",
            "concept_id": "c2",
            "role": "core",
            "rank": 1,
        },
    ]
    ingest_knowledge_graph("g1", payload)
    graph = get_knowledge_graph("g1")
    topic_ids = [topic["topic_id"] for topic in graph["topics"]]
    assert topic_ids[:2] == ["cc-ch1-unstable-model", "cc-ch1-harness-intro"]
