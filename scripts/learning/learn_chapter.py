"""Learn-mode chapter anchoring and touched-concept resolution."""

from __future__ import annotations

from typing import Any

from scripts.foundation.storage import query_all, query_one


def fetch_touched_concept_ids(plan_id: str) -> set[str]:
    """Concepts with any learn/quiz/review LearningRecord for this plan."""
    rows = query_all(
        """
        SELECT DISTINCT lr.conceptId AS concept_id
        FROM LearningRecord lr
        JOIN LearningSession ls ON ls.sessionId = lr.sessionId
        WHERE ls.learningPlanId = ?
        """,
        (plan_id,),
    )
    return {row["concept_id"] for row in rows if row.get("concept_id")}


def fetch_recent_activity(plan_id: str) -> tuple[str | None, str | None]:
    """Most recent interaction (any mode) → (concept_id, topic_id)."""
    row = query_one(
        """
        SELECT
            lr.conceptId AS concept_id,
            (
                SELECT tc.topicId
                FROM TopicConcept tc
                JOIN Topic t ON t.topicId = tc.topicId
                JOIN LearningPlan lp ON lp.graphId = t.graphId
                WHERE tc.conceptId = lr.conceptId
                  AND lp.learningPlanId = ls.learningPlanId
                ORDER BY t.sortOrder ASC, t.topicId ASC, tc.rank ASC
                LIMIT 1
            ) AS topic_id
        FROM LearningRecord lr
        JOIN LearningSession ls ON ls.sessionId = lr.sessionId
        WHERE ls.learningPlanId = ?
        ORDER BY lr.occurredAt DESC, lr.createdAt DESC
        LIMIT 1
        """,
        (plan_id,),
    )
    if not row:
        return None, None
    return row.get("concept_id"), row.get("topic_id")


def topic_concept_ids(ordered_concepts: list[dict[str, Any]], topic_id: str) -> list[str]:
    """Concept ids for one topic in book order (ordered_concepts is already ranked)."""
    return [
        c["concept_id"]
        for c in ordered_concepts
        if c.get("topic_id") == topic_id and c.get("concept_id")
    ]


def derive_topic_order(plan_topic_ids: list[str], ordered_concepts: list[dict[str, Any]]) -> list[str]:
    """Plan topic list, or topic order inferred from ordered_concepts when plan has no rows."""
    if plan_topic_ids:
        return list(plan_topic_ids)
    seen: list[str] = []
    for concept in ordered_concepts:
        topic_id = concept.get("topic_id")
        if topic_id and topic_id not in seen:
            seen.append(topic_id)
    return seen


def topic_has_untouched_gap(
    topic_id: str,
    ordered_concepts: list[dict[str, Any]],
    touched: set[str],
) -> bool:
    ids = topic_concept_ids(ordered_concepts, topic_id)
    return any(cid not in touched for cid in ids)


def resolve_learn_active_topic(
    plan_topic_ids: list[str],
    ordered_concepts: list[dict[str, Any]],
    touched: set[str],
    recent_topic_id: str | None,
    explicit_topic_id: str | None,
) -> str | None:
    """Pick the chapter to teach: explicit override, then forward scan from recent anchor."""
    if explicit_topic_id:
        return explicit_topic_id

    topic_order = derive_topic_order(plan_topic_ids, ordered_concepts)
    if not topic_order:
        return recent_topic_id

    if recent_topic_id and recent_topic_id in topic_order:
        start_idx = topic_order.index(recent_topic_id)
    else:
        start_idx = 0

    for topic_id in topic_order[start_idx:]:
        if topic_has_untouched_gap(topic_id, ordered_concepts, touched):
            return topic_id

    return None


def next_topic_in_plan_order(plan_topic_ids: list[str], current_topic_id: str | None) -> str | None:
    """Next topic id in plan order after current_topic_id."""
    if not plan_topic_ids or not current_topic_id:
        return None
    if current_topic_id not in plan_topic_ids:
        return None
    idx = plan_topic_ids.index(current_topic_id)
    if idx + 1 >= len(plan_topic_ids):
        return None
    return plan_topic_ids[idx + 1]
