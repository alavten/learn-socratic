"""Data access helpers for knowledge graph module."""

from __future__ import annotations

from typing import Any

from scripts.foundation.storage import paginate, query_all, query_one, transaction


def list_graphs(limit: int = 20, offset: str | None = None) -> dict[str, Any]:
    page_limit, offset_value = paginate(limit, offset)
    rows = query_all(
        """
        SELECT
            g.graphId AS graph_id,
            g.graphName AS name,
            g.revision AS revision,
            g.status AS status,
            (SELECT COUNT(*) FROM Topic t WHERE t.graphId = g.graphId) AS topic_count,
            (SELECT COUNT(*) FROM Concept c WHERE c.graphId = g.graphId AND c.dr = 0) AS concept_count,
            g.releasedAt AS updated_at
        FROM Graph g
        ORDER BY g.releasedAt DESC, g.graphId ASC
        LIMIT ? OFFSET ?
        """,
        (page_limit + 1, offset_value),
    )
    has_more = len(rows) > page_limit
    visible = rows[:page_limit]
    next_offset = str(offset_value + page_limit) if has_more else None
    graph_ids = [row["graph_id"] for row in visible]
    topic_preview_by_graph: dict[str, list[str]] = {}
    if graph_ids:
        placeholders = ",".join("?" for _ in graph_ids)
        topic_rows = query_all(
            f"""
            SELECT graphId AS graph_id, topicName AS topic_name
            FROM Topic
            WHERE graphId IN ({placeholders})
            ORDER BY sortOrder ASC, topicId ASC
            """,
            tuple(graph_ids),
        )
        for topic_row in topic_rows:
            topic_preview_by_graph.setdefault(topic_row["graph_id"], [])
            names = topic_preview_by_graph[topic_row["graph_id"]]
            if len(names) < 3:
                names.append(topic_row["topic_name"])
    for row in visible:
        topics = topic_preview_by_graph.get(row["graph_id"], [])
        row["topic_content"] = "；".join(topics) if topics else "（暂无主题摘要）"
    return {"items": visible, "has_more": has_more, "next_offset": next_offset}


def get_graph_core(graph_id: str) -> dict[str, Any] | None:
    return query_one(
        """
        SELECT
            graphId AS graph_id,
            graphName AS name,
            graphType AS graph_type,
            purpose,
            owner,
            schemaVersion AS schema_version,
            releaseTag AS release_tag,
            revision,
            status
        FROM Graph
        WHERE graphId = ?
        """,
        (graph_id,),
    )


def get_topics(graph_id: str, topic_id: str | None = None) -> list[dict[str, Any]]:
    if topic_id:
        return query_all(
            """
            SELECT
                topicId AS topic_id,
                parentTopicId AS parent_topic_id,
                topicName AS topic_name,
                topicType AS topic_type,
                sortOrder AS sort_order,
                status
            FROM Topic
            WHERE graphId = ? AND topicId = ?
            ORDER BY sortOrder ASC, topicId ASC
            """,
            (graph_id, topic_id),
        )
    return query_all(
        """
        SELECT
            topicId AS topic_id,
            parentTopicId AS parent_topic_id,
            topicName AS topic_name,
            topicType AS topic_type,
            sortOrder AS sort_order,
            status
        FROM Topic
        WHERE graphId = ?
        ORDER BY sortOrder ASC, topicId ASC
        """,
        (graph_id,),
    )


def get_topic_concepts(
    graph_id: str,
    topic_id: str | None = None,
    concept_limit: int = 20,
    offset: str | None = None,
) -> dict[str, Any]:
    page_limit, offset_value = paginate(concept_limit, offset)
    params: list[Any] = [graph_id]
    topic_clause = ""
    if topic_id:
        topic_clause = "AND tc.topicId = ?"
        params.append(topic_id)
    params.extend([page_limit + 1, offset_value])
    rows = query_all(
        f"""
        SELECT
            tc.topicConceptId AS topic_concept_id,
            tc.topicId AS topic_id,
            tc.conceptId AS concept_id,
            tc.role,
            tc.rank,
            c.canonicalName AS canonical_name,
            c.definition AS short_definition,
            c.difficultyLevel AS difficulty
        FROM TopicConcept tc
        JOIN Topic t ON t.topicId = tc.topicId AND t.graphId = ?
        JOIN Concept c ON c.conceptId = tc.conceptId AND c.dr = 0
        WHERE 1=1 {topic_clause}
        ORDER BY tc.rank ASC, tc.topicConceptId ASC
        LIMIT ? OFFSET ?
        """,
        tuple(params),
    )
    has_more = len(rows) > page_limit
    visible = rows[:page_limit]
    next_offset = str(offset_value + page_limit) if has_more else None
    return {"items": visible, "has_more": has_more, "next_offset": next_offset}


def resolve_scope_concepts(graph_id: str, concept_scope: dict[str, Any]) -> list[str]:
    concept_ids = concept_scope.get("concept_ids") or []
    if concept_ids:
        return concept_ids
    topic_ids = concept_scope.get("topic_ids") or []
    if topic_ids:
        placeholders = ",".join("?" for _ in topic_ids)
        rows = query_all(
            f"""
            SELECT DISTINCT tc.conceptId AS concept_id
            FROM TopicConcept tc
            JOIN Topic t ON t.topicId = tc.topicId
            WHERE t.graphId = ? AND tc.topicId IN ({placeholders})
            """,
            (graph_id, *topic_ids),
        )
        return [row["concept_id"] for row in rows]
    rows = query_all(
        "SELECT conceptId AS concept_id FROM Concept WHERE graphId = ? AND dr = 0",
        (graph_id,),
    )
    return [row["concept_id"] for row in rows]


def collect_topic_ids_with_descendants(graph_id: str, root_topic_ids: list[str]) -> list[str]:
    """Return root topic ids plus all descendant topic ids under the same graph."""
    if not root_topic_ids:
        return []
    rows = query_all(
        """
        SELECT topicId AS topic_id, parentTopicId AS parent_topic_id
        FROM Topic
        WHERE graphId = ?
        """,
        (graph_id,),
    )
    children: dict[str | None, list[str]] = {}
    for row in rows:
        parent = row["parent_topic_id"]
        children.setdefault(parent, []).append(row["topic_id"])
    collected: set[str] = set()
    stack = [t for t in root_topic_ids if t]
    while stack:
        tid = stack.pop()
        if tid in collected:
            continue
        collected.add(tid)
        for child in children.get(tid, []):
            stack.append(child)
    return list(collected)


def list_concept_ids_for_prune_scope(
    graph_id: str,
    topic_ids: list[str] | None,
    concept_id_prefix: str | None,
) -> list[str]:
    """Concept ids (dr=0) matching prune scope: optional topic filter AND optional id prefix."""
    topic_ids = [t for t in (topic_ids or []) if t]
    prefix = (concept_id_prefix or "").strip()
    if topic_ids:
        ph = ",".join("?" for _ in topic_ids)
        rows = query_all(
            f"""
            SELECT DISTINCT c.conceptId AS concept_id
            FROM Concept c
            JOIN TopicConcept tc ON tc.conceptId = c.conceptId
            JOIN Topic t ON t.topicId = tc.topicId AND t.graphId = ?
            WHERE c.graphId = ? AND c.dr = 0 AND tc.topicId IN ({ph})
            """,
            (graph_id, graph_id, *topic_ids),
        )
        cids = [r["concept_id"] for r in rows]
    else:
        rows = query_all(
            "SELECT conceptId AS concept_id FROM Concept WHERE graphId = ? AND dr = 0",
            (graph_id,),
        )
        cids = [r["concept_id"] for r in rows]
    if prefix:
        cids = [cid for cid in cids if cid.startswith(prefix)]
    return cids


def list_relation_ids_for_concepts(graph_id: str, concept_ids: list[str]) -> list[str]:
    if not concept_ids:
        return []
    ph = ",".join("?" for _ in concept_ids)
    rows = query_all(
        f"""
        SELECT conceptRelationId AS concept_relation_id
        FROM ConceptRelation
        WHERE graphId = ? AND dr = 0
          AND (fromConceptId IN ({ph}) OR toConceptId IN ({ph}))
        """,
        (graph_id, *concept_ids, *concept_ids),
    )
    return [r["concept_relation_id"] for r in rows]


def _delete_orphan_evidence(conn) -> int:
    cur = conn.execute(
        """
        DELETE FROM Evidence
        WHERE evidenceId NOT IN (SELECT DISTINCT evidenceId FROM RelationEvidence)
        """
    )
    return cur.rowcount or 0


def hard_delete_knowledge_graph_entities(
    graph_id: str,
    concept_ids: list[str],
    relation_ids: list[str],
    topic_ids: list[str],
) -> dict[str, Any]:
    """Physically remove topics, concepts, relations and dependent graph rows for one graph."""
    cids = sorted({c for c in (concept_ids or []) if c})
    rids_explicit = sorted({r for r in (relation_ids or []) if r})
    tids_root = sorted({t for t in (topic_ids or []) if t})

    summary: dict[str, Any] = {
        "concepts_deleted": 0,
        "relations_deleted": 0,
        "topics_deleted": 0,
        "topic_concepts_deleted": 0,
        "orphan_evidences_deleted": 0,
        "concepts_not_found": [],
        "relations_not_found": [],
        "topics_not_found": [],
    }

    if not query_one("SELECT 1 AS ok FROM Graph WHERE graphId = ?", (graph_id,)):
        summary["error"] = "graph_not_found"
        return summary

    expanded_topics = collect_topic_ids_with_descendants(graph_id, tids_root) if tids_root else []

    # Validate requested ids belong to this graph
    if cids:
        ph = ",".join("?" for _ in cids)
        found = query_all(
            f"SELECT conceptId AS concept_id FROM Concept WHERE graphId = ? AND dr = 0 AND conceptId IN ({ph})",
            (graph_id, *cids),
        )
        found_set = {r["concept_id"] for r in found}
        summary["concepts_not_found"] = [c for c in cids if c not in found_set]
    if rids_explicit:
        ph = ",".join("?" for _ in rids_explicit)
        found = query_all(
            f"SELECT conceptRelationId AS id FROM ConceptRelation WHERE graphId = ? AND dr = 0 AND conceptRelationId IN ({ph})",
            (graph_id, *rids_explicit),
        )
        found_set = {r["id"] for r in found}
        summary["relations_not_found"] = [r for r in rids_explicit if r not in found_set]
    if expanded_topics:
        ph = ",".join("?" for _ in expanded_topics)
        found = query_all(
            f"SELECT topicId AS topic_id FROM Topic WHERE graphId = ? AND topicId IN ({ph})",
            (graph_id, *expanded_topics),
        )
        found_set = {r["topic_id"] for r in found}
        summary["topics_not_found"] = [t for t in expanded_topics if t not in found_set]

    relation_ids_from_concepts = list_relation_ids_for_concepts(graph_id, cids) if cids else []
    all_relation_ids = sorted({*rids_explicit, *relation_ids_from_concepts})

    with transaction() as conn:
        if all_relation_ids:
            ph = ",".join("?" for _ in all_relation_ids)
            cur = conn.execute(
                f"DELETE FROM ConceptRelation WHERE graphId = ? AND conceptRelationId IN ({ph})",
                (graph_id, *all_relation_ids),
            )
            summary["relations_deleted"] = cur.rowcount or 0

        summary["orphan_evidences_deleted"] += _delete_orphan_evidence(conn)

        if cids or expanded_topics:
            clauses: list[str] = []
            params: list[Any] = [graph_id]
            if cids:
                phc = ",".join("?" for _ in cids)
                clauses.append(f"tc.conceptId IN ({phc})")
                params.extend(cids)
            if expanded_topics:
                pht = ",".join("?" for _ in expanded_topics)
                clauses.append(f"tc.topicId IN ({pht})")
                params.extend(expanded_topics)
            where_tc = " OR ".join(clauses)
            cur = conn.execute(
                f"""
                DELETE FROM TopicConcept
                WHERE topicConceptId IN (
                    SELECT tc.topicConceptId FROM TopicConcept tc
                    JOIN Topic t ON t.topicId = tc.topicId
                    WHERE t.graphId = ? AND ({where_tc})
                )
                """,
                tuple(params),
            )
            summary["topic_concepts_deleted"] = cur.rowcount or 0

        if expanded_topics:
            rows = conn.execute(
                """
                SELECT topicId AS topic_id, parentTopicId AS parent_topic_id
                FROM Topic
                WHERE graphId = ?
                """,
                (graph_id,),
            ).fetchall()
            topic_set = set(expanded_topics)
            children: dict[str | None, list[str]] = {}
            for row in rows:
                tid = row["topic_id"]
                pid = row["parent_topic_id"]
                children.setdefault(pid, []).append(tid)
            deleted_topics = 0
            remaining = set(topic_set)
            while remaining:
                leaf = None
                for tid in remaining:
                    child_in_remaining = any(
                        c in remaining for c in children.get(tid, [])
                    )
                    if not child_in_remaining:
                        leaf = tid
                        break
                if leaf is None:
                    leaf = next(iter(remaining))
                cur = conn.execute("DELETE FROM Topic WHERE graphId = ? AND topicId = ?", (graph_id, leaf))
                deleted_topics += cur.rowcount or 0
                remaining.discard(leaf)
            summary["topics_deleted"] = deleted_topics

        if cids:
            ph = ",".join("?" for _ in cids)
            cur = conn.execute(
                f"DELETE FROM Concept WHERE graphId = ? AND dr = 0 AND conceptId IN ({ph})",
                (graph_id, *cids),
            )
            summary["concepts_deleted"] = cur.rowcount or 0

        summary["orphan_evidences_deleted"] += _delete_orphan_evidence(conn)

    return summary
