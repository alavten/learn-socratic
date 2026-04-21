"""Test helper functions."""

from __future__ import annotations

from scripts.knowledge_graph.api import ingest_knowledge_graph


def sample_graph_payload() -> dict:
    return {
        "graph": {
            "graph_type": "domain",
            "graph_name": "Python Basics",
            "schema_version": "1.0.0",
            "release_tag": "r1",
        },
        "topics": [
            {"topic_id": "t1", "topic_name": "Syntax", "topic_type": "chapter", "sort_order": 1},
            {"topic_id": "t2", "topic_name": "Functions", "topic_type": "chapter", "sort_order": 2},
        ],
        "concepts": [
            {
                "concept_id": "c1",
                "canonical_name": "Variable",
                "definition": "A named storage location.",
                "concept_type": "fundamental",
                "difficulty_level": "easy",
            },
            {
                "concept_id": "c2",
                "canonical_name": "Function",
                "definition": "Reusable block of code.",
                "concept_type": "fundamental",
                "difficulty_level": "medium",
            },
        ],
        "topic_concepts": [
            {"topic_concept_id": "tc1", "topic_id": "t1", "concept_id": "c1", "role": "core", "rank": 1},
            {"topic_concept_id": "tc2", "topic_id": "t2", "concept_id": "c2", "role": "core", "rank": 1},
        ],
        "relations": [
            {
                "concept_relation_id": "r1",
                "from_concept_id": "c1",
                "to_concept_id": "c2",
                "relation_type": "prerequisite_of",
            }
        ],
        "evidences": [
            {
                "evidence_id": "e1",
                "source_type": "doc",
                "source_title": "Guide",
                "quote_text": "Variables are used before function logic.",
            }
        ],
        "relation_evidences": [
            {
                "relation_evidence_id": "re1",
                "concept_relation_id": "r1",
                "evidence_id": "e1",
                "support_score": 0.9,
            }
        ],
    }


def ingest_sample_graph(graph_id: str = "g1") -> dict:
    return ingest_knowledge_graph(graph_id, sample_graph_payload())
