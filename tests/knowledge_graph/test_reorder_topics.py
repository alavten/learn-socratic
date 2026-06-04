from scripts.knowledge_graph.api import get_knowledge_graph, ingest_knowledge_graph, reorder_graph_topics
from tests.helpers import sample_graph_payload


def test_reorder_graph_topics_by_topic_ids(isolated_db):
    ingest_knowledge_graph("g-reorder", sample_graph_payload())
    result = reorder_graph_topics(
        "g-reorder",
        {"parent_topic_id": None, "topic_ids": ["t2", "t1"]},
    )
    assert result["validation_summary"]["ok"] is True
    assert result["topics_updated"] == 2
    graph = get_knowledge_graph("g-reorder")
    topic_ids = [t["topic_id"] for t in graph["topics"] if not t.get("parent_topic_id")]
    assert topic_ids == ["t2", "t1"]
    assert graph["topics"][0]["sort_order"] == 1
    assert graph["topics"][1]["sort_order"] == 2


def test_reorder_rejects_missing_topic(isolated_db):
    ingest_knowledge_graph("g-reorder", sample_graph_payload())
    result = reorder_graph_topics(
        "g-reorder",
        {"parent_topic_id": None, "topic_ids": ["t1"]},
    )
    assert result["validation_summary"]["ok"] is False
    assert any("missing" in err for err in result["validation_summary"]["errors"])


def test_reorder_rejects_extra_topic(isolated_db):
    ingest_knowledge_graph("g-reorder", sample_graph_payload())
    result = reorder_graph_topics(
        "g-reorder",
        {"parent_topic_id": None, "topic_ids": ["t1", "t2", "t99"]},
    )
    assert result["validation_summary"]["ok"] is False
    assert any("unknown" in err for err in result["validation_summary"]["errors"])


def test_reorder_rejects_both_topic_ids_and_topic_order(isolated_db):
    ingest_knowledge_graph("g-reorder", sample_graph_payload())
    result = reorder_graph_topics(
        "g-reorder",
        {
            "parent_topic_id": None,
            "topic_ids": ["t1", "t2"],
            "topic_order": [{"topic_id": "t1", "sort_order": 1}],
        },
    )
    assert result["validation_summary"]["ok"] is False
