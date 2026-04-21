"""Data access helpers for knowledge graph module."""

from __future__ import annotations

from typing import Any

from scripts.foundation.storage import paginate, query_all, query_one


def list_graphs(limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
    page_limit, offset = paginate(limit, cursor)
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
        (page_limit + 1, offset),
    )
    has_more = len(rows) > page_limit
    visible = rows[:page_limit]
    next_cursor = str(offset + page_limit) if has_more else None
    return {"items": visible, "has_more": has_more, "next_cursor": next_cursor}


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
    cursor: str | None = None,
) -> dict[str, Any]:
    page_limit, offset = paginate(concept_limit, cursor)
    params: list[Any] = [graph_id]
    topic_clause = ""
    if topic_id:
        topic_clause = "AND tc.topicId = ?"
        params.append(topic_id)
    params.extend([page_limit + 1, offset])
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
    next_cursor = str(offset + page_limit) if has_more else None
    return {"items": visible, "has_more": has_more, "next_cursor": next_cursor}


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
