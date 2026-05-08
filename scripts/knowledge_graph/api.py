"""Public API for knowledge graph module."""

from __future__ import annotations

from typing import Any

from scripts.foundation.storage import paginate, query_all
from scripts.knowledge_graph.ingest import ingest_knowledge_graph as ingest_graph_impl
from scripts.knowledge_graph.store import (
    get_graph_core,
    get_topic_concepts,
    get_topics,
    hard_delete_knowledge_graph_entities,
    list_concept_ids_for_prune_scope,
    list_graphs,
    list_relation_ids_for_concepts,
    resolve_scope_concepts,
)


def list_knowledge_graphs(limit: int = 20, offset: str | None = None) -> dict[str, Any]:
    page = list_graphs(limit=limit, offset=offset)
    return {
        "items": page["items"],
        "has_more": page["has_more"],
        "next_offset": page["next_offset"],
    }


def get_knowledge_graph(
    graph_id: str,
    topic_id: str | None = None,
    concept_limit: int = 20,
    offset: str | None = None,
) -> dict[str, Any]:
    core = get_graph_core(graph_id)
    if not core:
        return {"error": "graph_not_found", "graph_id": graph_id}

    topics = get_topics(graph_id, topic_id=topic_id)
    topic_concepts_page = get_topic_concepts(
        graph_id=graph_id,
        topic_id=topic_id,
        concept_limit=concept_limit,
        offset=offset,
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
        "next_offset": topic_concepts_page["next_offset"],
    }


def _prune_after_successful_ingest(
    graph_id: str,
    structured_payload: dict[str, Any],
    prune_scope: dict[str, Any],
    force_delete: bool,
) -> dict[str, Any]:
    """Hard-delete concepts/relations in scope that are absent from the ingested payload."""
    from scripts.learning import api as learning_api

    topic_scope = [t for t in (prune_scope.get("topic_ids") or []) if t]
    prefix_raw = prune_scope.get("concept_id_prefix")
    prefix = prefix_raw.strip() if isinstance(prefix_raw, str) else ""
    if not topic_scope and not prefix:
        return {
            "error": "invalid_prune_scope",
            "message": "Provide topic_ids and/or non-empty concept_id_prefix",
        }

    universe = list_concept_ids_for_prune_scope(
        graph_id,
        topic_scope if topic_scope else None,
        prefix if prefix else None,
    )
    payload_cids = {c["concept_id"] for c in structured_payload.get("concepts", []) if c.get("concept_id")}
    to_remove_c = sorted({c for c in universe if c not in payload_cids})
    payload_rid = {
        r["concept_relation_id"] for r in structured_payload.get("relations", []) if r.get("concept_relation_id")
    }

    if not universe:
        return {"pruned_concepts": [], "pruned_relations": [], "skipped": True, "reason": "empty_universe"}

    ph_u = ",".join("?" for _ in universe)
    rows = query_all(
        f"""
        SELECT
            conceptRelationId AS concept_relation_id,
            fromConceptId AS from_concept_id,
            toConceptId AS to_concept_id
        FROM ConceptRelation
        WHERE graphId = ? AND dr = 0
          AND fromConceptId IN ({ph_u})
          AND toConceptId IN ({ph_u})
        """,
        (graph_id, *universe, *universe),
    )
    to_remove_r: set[str] = set()
    for row in rows:
        rid = row["concept_relation_id"]
        if rid not in payload_rid:
            to_remove_r.add(rid)
        if row["from_concept_id"] in to_remove_c or row["to_concept_id"] in to_remove_c:
            to_remove_r.add(rid)
    to_remove_r.update(list_relation_ids_for_concepts(graph_id, to_remove_c))
    to_remove_r_list = sorted(to_remove_r)

    dep = learning_api.check_plan_dependencies(graph_id, concept_ids=to_remove_c, topic_ids=[])
    if dep["has_blocking"] and not force_delete:
        return {
            "blocked": True,
            "error": "dependency_conflict",
            "blocking_dependencies": dep["blocking_dependencies"],
            "would_prune": {"concept_ids": to_remove_c, "relation_ids": to_remove_r_list},
        }
    cleanup_summary: dict[str, Any] | None = None
    if dep["has_blocking"] and force_delete:
        cleanup_summary = learning_api.cleanup_learning_refs_for_graph_entity_removal(
            graph_id, concept_ids=to_remove_c, topic_ids=[]
        )

    delete_summary = hard_delete_knowledge_graph_entities(
        graph_id,
        concept_ids=to_remove_c,
        relation_ids=to_remove_r_list,
        topic_ids=[],
    )
    return {
        "blocked": False,
        "forced": bool(dep["has_blocking"] and force_delete),
        "dependency_check": dep,
        "cleanup_summary": cleanup_summary,
        "delete_summary": delete_summary,
        "pruned_concept_ids": to_remove_c,
        "pruned_relation_ids": to_remove_r_list,
    }


def ingest_knowledge_graph(
    graph_id: str,
    structured_payload: dict[str, Any],
    *,
    sync_mode: str = "upsert_only",
    prune_scope: dict[str, Any] | None = None,
    force_delete: bool = False,
) -> dict[str, Any]:
    result = ingest_graph_impl(graph_id, structured_payload)
    if sync_mode != "upsert_and_prune":
        return result
    if not result.get("validation_summary", {}).get("ok"):
        return result
    prune_scope = prune_scope or {}
    prune_result = _prune_after_successful_ingest(graph_id, structured_payload, prune_scope, force_delete)
    result["prune_result"] = prune_result
    if prune_result.get("error") == "invalid_prune_scope" or prune_result.get("blocked"):
        vs = dict(result.get("validation_summary", {}))
        errs = list(vs.get("errors", []))
        if prune_result.get("error") == "invalid_prune_scope":
            errs.append(prune_result.get("message", "invalid prune scope"))
        else:
            errs.append("prune blocked by learning plan dependencies")
        vs["ok"] = False
        vs["errors"] = errs
        result["validation_summary"] = vs
    return result


def remove_knowledge_graph_entities(graph_id: str, remove_payload: dict[str, Any]) -> dict[str, Any]:
    """Hard-delete graph entities (no learning-domain checks; use orchestration for guards)."""
    concept_ids = [str(x) for x in (remove_payload.get("concept_ids") or []) if x]
    relation_ids = [str(x) for x in (remove_payload.get("relation_ids") or []) if x]
    topic_ids = [str(x) for x in (remove_payload.get("topic_ids") or []) if x]
    if not concept_ids and not relation_ids and not topic_ids:
        return {
            "graph_id": graph_id,
            "error": "empty_remove_payload",
            "message": "Provide concept_ids, relation_ids, and/or topic_ids",
        }
    summary = hard_delete_knowledge_graph_entities(
        graph_id,
        concept_ids=concept_ids,
        relation_ids=relation_ids,
        topic_ids=topic_ids,
    )
    summary["graph_id"] = graph_id
    return summary


def get_concepts(
    graph_id: str,
    concept_scope: dict[str, Any],
    detail: str = "brief",
    concept_limit: int = 20,
    offset: str | None = None,
) -> dict[str, Any]:
    concept_ids = resolve_scope_concepts(graph_id, concept_scope)
    page_limit, offset_value = paginate(concept_limit, offset)
    if not concept_ids:
        return {"concept_briefs": [], "has_more": False, "next_offset": None}
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
        (graph_id, *concept_ids, page_limit + 1, offset_value),
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
        "next_offset": str(offset_value + page_limit) if has_more else None,
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
