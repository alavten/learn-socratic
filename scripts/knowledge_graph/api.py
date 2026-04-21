"""Public API for knowledge graph module."""

from __future__ import annotations

from typing import Any

from scripts.foundation.storage import paginate, query_all
from scripts.knowledge_graph.ingest import ingest_knowledge_graph as ingest_graph_impl
from scripts.knowledge_graph.store import (
    get_graph_core,
    get_topic_concepts,
    get_topics,
    list_graphs,
    resolve_scope_concepts,
)


def list_knowledge_graphs(limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
    page = list_graphs(limit=limit, cursor=cursor)
    return {
        "items": page["items"],
        "has_more": page["has_more"],
        "cursor": page["next_cursor"],
    }


def get_knowledge_graph(
    graph_id: str,
    topic_id: str | None = None,
    concept_limit: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    core = get_graph_core(graph_id)
    if not core:
        return {"error": "graph_not_found", "graph_id": graph_id}

    topics = get_topics(graph_id, topic_id=topic_id)
    topic_concepts_page = get_topic_concepts(
        graph_id=graph_id,
        topic_id=topic_id,
        concept_limit=concept_limit,
        cursor=cursor,
    )
    concept_briefs = [
        {
            "concept_id": item["concept_id"],
            "canonical_name": item["canonical_name"],
            "short_definition": item["short_definition"][:160],
            "difficulty": item["difficulty"],
        }
        for item in topic_concepts_page["items"]
    ]
    return {
        "graph": core,
        "topics": topics,
        "topic_concepts": topic_concepts_page["items"],
        "concept_briefs": concept_briefs,
        "has_more": topic_concepts_page["has_more"],
        "cursor": topic_concepts_page["next_cursor"],
    }


def ingest_knowledge_graph(graph_id: str, structured_payload: dict[str, Any]) -> dict[str, Any]:
    return ingest_graph_impl(graph_id, structured_payload)


def get_concepts(
    graph_id: str,
    concept_scope: dict[str, Any],
    detail: str = "brief",
    concept_limit: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    concept_ids = resolve_scope_concepts(graph_id, concept_scope)
    page_limit, offset = paginate(concept_limit, cursor)
    if not concept_ids:
        return {"concept_briefs": [], "has_more": False, "cursor": None}
    placeholders = ",".join("?" for _ in concept_ids)
    rows = query_all(
        f"""
        SELECT
            conceptId AS concept_id,
            canonicalName AS canonical_name,
            definition,
            difficultyLevel AS difficulty,
            conceptType AS concept_type,
            language
        FROM Concept
        WHERE graphId = ? AND dr = 0 AND conceptId IN ({placeholders})
        ORDER BY canonicalName ASC
        LIMIT ? OFFSET ?
        """,
        (graph_id, *concept_ids, page_limit + 1, offset),
    )
    has_more = len(rows) > page_limit
    visible = rows[:page_limit]
    brief = [
        {
            "concept_id": row["concept_id"],
            "canonical_name": row["canonical_name"],
            "short_definition": row["definition"][:160],
            "difficulty": row["difficulty"],
        }
        for row in visible
    ]
    payload: dict[str, Any] = {
        "concept_briefs": brief,
        "has_more": has_more,
        "cursor": str(offset + page_limit) if has_more else None,
    }
    if detail == "full":
        payload["detail"] = {"concepts": visible}
    return payload


def get_concept_relations(
    graph_id: str,
    concept_scope: dict[str, Any],
    depth: int = 1,
    relation_limit: int = 50,
) -> dict[str, Any]:
    del depth  # constrained to one-hop in current implementation
    concept_ids = resolve_scope_concepts(graph_id, concept_scope)
    if not concept_ids:
        return {"relation_briefs": []}
    placeholders = ",".join("?" for _ in concept_ids)
    rows = query_all(
        f"""
        SELECT
            conceptRelationId AS concept_relation_id,
            fromConceptId AS from_concept_id,
            toConceptId AS to_concept_id,
            relationType AS relation_type,
            weight AS strength,
            confidence
        FROM ConceptRelation
        WHERE graphId = ? AND dr = 0
          AND (fromConceptId IN ({placeholders}) OR toConceptId IN ({placeholders}))
        LIMIT ?
        """,
        (graph_id, *concept_ids, *concept_ids, relation_limit),
    )
    brief = [
        {
            "concept_relation_id": row["concept_relation_id"],
            "from_concept_id": row["from_concept_id"],
            "to_concept_id": row["to_concept_id"],
            "relation_type": row["relation_type"],
            "strength": row["strength"],
        }
        for row in rows
    ]
    return {"relation_briefs": brief}


def get_concept_evidence(
    graph_id: str,
    concept_scope: dict[str, Any],
    mode: str = "summary",
    evidence_limit: int = 20,
) -> dict[str, Any]:
    concept_ids = resolve_scope_concepts(graph_id, concept_scope)
    if not concept_ids:
        return {"evidence_summary": []}
    placeholders = ",".join("?" for _ in concept_ids)
    rows = query_all(
        f"""
        SELECT
            cr.fromConceptId AS from_concept_id,
            cr.toConceptId AS to_concept_id,
            e.evidenceId AS evidence_id,
            e.quoteText AS quote_text,
            e.sourceTitle AS source_title,
            e.sourceUri AS source_uri,
            re.supportScore AS support_score
        FROM ConceptRelation cr
        JOIN RelationEvidence re ON re.conceptRelationId = cr.conceptRelationId
        JOIN Evidence e ON e.evidenceId = re.evidenceId
        WHERE cr.graphId = ? AND cr.dr = 0
          AND (cr.fromConceptId IN ({placeholders}) OR cr.toConceptId IN ({placeholders}))
        ORDER BY re.supportScore DESC
        LIMIT ?
        """,
        (graph_id, *concept_ids, *concept_ids, evidence_limit),
    )
    summary = [
        {
            "evidence_id": row["evidence_id"],
            "source": row["source_title"] or row["source_uri"],
            "summary": row["quote_text"][:180],
            "support_score": row["support_score"],
            "for_relation": [row["from_concept_id"], row["to_concept_id"]],
        }
        for row in rows
    ]
    payload: dict[str, Any] = {"evidence_summary": summary}
    if mode == "detail":
        payload["detail"] = {"evidence": rows}
    return payload
