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
