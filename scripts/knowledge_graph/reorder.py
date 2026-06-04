"""Batch reorder Topic.sortOrder for siblings under the same parent (runtime API)."""

from __future__ import annotations

import sqlite3
from typing import Any

from scripts.foundation.storage import transaction
from scripts.knowledge_graph.validate import _validate_topic_sort_orders


def _parse_reorder_payload(payload: dict[str, Any]) -> tuple[str | None, list[tuple[str, int]], list[str]]:
    """Return parent_topic_id, ordered (topic_id, sort_order) pairs, and parse errors."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return None, [], ["payload must be an object"]

    parent_topic_id = payload.get("parent_topic_id")
    if parent_topic_id is not None and not isinstance(parent_topic_id, str):
        errors.append("parent_topic_id must be a string or null")

    has_topic_ids = "topic_ids" in payload and payload.get("topic_ids") is not None
    has_topic_order = "topic_order" in payload and payload.get("topic_order") is not None
    if has_topic_ids and has_topic_order:
        errors.append("provide either topic_ids or topic_order, not both")
        return parent_topic_id, [], errors
    if not has_topic_ids and not has_topic_order:
        errors.append("payload must include topic_ids or topic_order")
        return parent_topic_id, [], errors

    topic_order: list[tuple[str, int]] = []
    if has_topic_ids:
        topic_ids = payload.get("topic_ids")
        if not isinstance(topic_ids, list) or not topic_ids:
            errors.append("topic_ids must be a non-empty array")
            return parent_topic_id, [], errors
        seen: set[str] = set()
        for idx, topic_id in enumerate(topic_ids):
            if not topic_id or not isinstance(topic_id, str):
                errors.append(f"topic_ids[{idx}] must be a non-empty string")
                continue
            if topic_id in seen:
                errors.append(f"topic_ids contains duplicate '{topic_id}'")
            seen.add(topic_id)
            topic_order.append((topic_id, idx + 1))
    else:
        rows = payload.get("topic_order")
        if not isinstance(rows, list) or not rows:
            errors.append("topic_order must be a non-empty array")
            return parent_topic_id, [], errors
        for idx, row in enumerate(rows):
            if not isinstance(row, dict) or not row.get("topic_id"):
                errors.append(f"topic_order[{idx}] must be an object with topic_id")
                continue
            sort_order = row.get("sort_order")
            if not isinstance(sort_order, int) or sort_order < 1:
                errors.append(f"topic_order[{idx}].sort_order must be a positive integer")
                continue
            topic_order.append((str(row["topic_id"]), sort_order))

    if topic_order and not errors:
        sort_errors: list[str] = []
        pseudo_topics = [
            {
                "topic_id": topic_id,
                "sort_order": sort_order,
                "parent_topic_id": parent_topic_id,
            }
            for topic_id, sort_order in topic_order
        ]
        _validate_topic_sort_orders(pseudo_topics, sort_errors)
        errors.extend(sort_errors)

    return parent_topic_id, topic_order, errors


def _fetch_sibling_topic_ids(
    conn: sqlite3.Connection,
    graph_id: str,
    parent_topic_id: str | None,
) -> list[str]:
    if parent_topic_id is None:
        rows = conn.execute(
            """
            SELECT topicId AS topic_id
            FROM Topic
            WHERE graphId = ? AND parentTopicId IS NULL
            ORDER BY sortOrder ASC, topicId ASC
            """,
            (graph_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT topicId AS topic_id
            FROM Topic
            WHERE graphId = ? AND parentTopicId = ?
            ORDER BY sortOrder ASC, topicId ASC
            """,
            (graph_id, parent_topic_id),
        ).fetchall()
    return [str(row["topic_id"]) for row in rows]


def reorder_graph_topics(graph_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    parent_topic_id, topic_order, parse_errors = _parse_reorder_payload(payload)
    if parse_errors:
        return {
            "graph_id": graph_id,
            "parent_topic_id": parent_topic_id,
            "topics_updated": 0,
            "validation_summary": {
                "ok": False,
                "errors": parse_errors,
                "warnings": [],
            },
            "topics_preview": [],
        }

    errors: list[str] = list(parse_errors)
    warnings: list[str] = []

    try:
        with transaction() as conn:
            if not conn.execute(
                "SELECT 1 FROM Graph WHERE graphId = ?",
                (graph_id,),
            ).fetchone():
                errors.append(f"graph not found: {graph_id}")
            else:
                db_ids = _fetch_sibling_topic_ids(conn, graph_id, parent_topic_id)
                payload_ids = [topic_id for topic_id, _ in topic_order]
                db_set = set(db_ids)
                payload_set = set(payload_ids)
                if not db_set and payload_set:
                    errors.append("no topics found for graph_id and parent_topic_id")
                elif db_set != payload_set:
                    missing = sorted(db_set - payload_set)
                    extra = sorted(payload_set - db_set)
                    if missing:
                        errors.append(
                            f"payload missing topic_id(s) for this sibling group: {missing[:10]}"
                            + (" ..." if len(missing) > 10 else "")
                        )
                    if extra:
                        errors.append(
                            f"payload has unknown topic_id(s) for this sibling group: {extra[:10]}"
                            + (" ..." if len(extra) > 10 else "")
                        )
                    if len(payload_ids) != len(payload_set):
                        errors.append("payload topic_ids contain duplicates")

            if errors:
                return {
                    "graph_id": graph_id,
                    "parent_topic_id": parent_topic_id,
                    "topics_updated": 0,
                    "validation_summary": {
                        "ok": False,
                        "errors": errors,
                        "warnings": warnings,
                    },
                    "topics_preview": [],
                }

            updated = 0
            for topic_id, sort_order in topic_order:
                if parent_topic_id is None:
                    cur = conn.execute(
                        """
                        UPDATE Topic SET sortOrder = ?
                        WHERE graphId = ? AND topicId = ? AND parentTopicId IS NULL
                        """,
                        (sort_order, graph_id, topic_id),
                    )
                else:
                    cur = conn.execute(
                        """
                        UPDATE Topic SET sortOrder = ?
                        WHERE graphId = ? AND topicId = ? AND parentTopicId = ?
                        """,
                        (sort_order, graph_id, topic_id, parent_topic_id),
                    )
                if cur.rowcount == 1:
                    updated += 1
                else:
                    errors.append(f"failed to update topic_id '{topic_id}'")

            if errors:
                raise sqlite3.IntegrityError("reorder partial failure")

            preview_rows = []
            for topic_id, sort_order in topic_order[:10]:
                row = conn.execute(
                    """
                    SELECT topicId AS topic_id, topicName AS topic_name, sortOrder AS sort_order
                    FROM Topic WHERE topicId = ?
                    """,
                    (topic_id,),
                ).fetchone()
                if row:
                    preview_rows.append(
                        {
                            "topic_id": row["topic_id"],
                            "topic_name": row["topic_name"],
                            "sort_order": int(row["sort_order"]),
                        }
                    )

    except sqlite3.IntegrityError:
        return {
            "graph_id": graph_id,
            "parent_topic_id": parent_topic_id,
            "topics_updated": 0,
            "validation_summary": {
                "ok": False,
                "errors": errors or ["reorder failed"],
                "warnings": warnings,
            },
            "topics_preview": [],
        }

    return {
        "graph_id": graph_id,
        "parent_topic_id": parent_topic_id,
        "topics_updated": updated,
        "validation_summary": {"ok": True, "errors": [], "warnings": warnings},
        "topics_preview": preview_rows,
    }
