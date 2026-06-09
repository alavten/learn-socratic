"""Session queue and quiz pacing state for learn/quiz/review mode context."""

from __future__ import annotations

from typing import Any

from scripts.knowledge_graph.store import get_next_sibling_topic_id

QUIZ_PACINGS = frozenset({"per_concept", "per_chapter"})

_PER_CONCEPT_HINTS = (
    "一题一题",
    "逐题",
    "per_concept",
    "one at a time",
    "one-by-one",
    "single question",
)
_PER_CHAPTER_HINTS = (
    "批量",
    "一章测验",
    "一章",
    "per_chapter",
    "batch",
    "chapter quiz",
)


def is_incorrect_result(result: Any) -> bool:
    return str(result or "").lower() in {"wrong", "incorrect", "fail", "blocked"}


def is_blocked_result(result: Any) -> bool:
    return str(result or "").lower() == "blocked"


def infer_learn_granularity(recent_learn_concepts: list[str] | None) -> str | None:
    """Return single | multi | chapter hint from recent learn concept ids."""
    concepts = [c for c in (recent_learn_concepts or []) if c]
    if not concepts:
        return None
    unique = list(dict.fromkeys(concepts))
    if len(unique) <= 1:
        return "single"
    if len(unique) >= 3:
        return "chapter"
    return "multi"


def resolve_quiz_pacing(
    session_context: dict[str, Any] | None,
    *,
    recent_learn_granularity: str | None = None,
) -> str:
    """Resolve quiz_pacing from explicit value, pacing_hint, or recent learn granularity."""
    incoming = dict(session_context or {})

    explicit = str(incoming.get("quiz_pacing") or "").strip()
    if explicit in QUIZ_PACINGS:
        return explicit

    hint = str(incoming.get("pacing_hint") or "").strip().lower()
    if hint:
        if any(marker in hint for marker in _PER_CONCEPT_HINTS):
            return "per_concept"
        if any(marker in hint for marker in _PER_CHAPTER_HINTS):
            return "per_chapter"

    granularity = recent_learn_granularity or incoming.get("learn_granularity")
    if granularity in {"multi", "chapter"}:
        return "per_chapter"
    if granularity == "single":
        return "per_concept"

    served = incoming.get("served_concept_ids") or []
    if isinstance(served, list) and len(served) > 1:
        return "per_chapter"

    return "per_concept"


def prepare_quiz_session_state(
    context: dict[str, Any],
    session_context: dict[str, Any] | None,
) -> dict[str, Any]:
    incoming = dict(session_context or {})
    constraints = context.get("constraints") or {}
    max_question_count = int(constraints.get("max_question_count") or 10)
    recent_granularity = infer_learn_granularity(context.get("recent_learn_concepts"))
    pacing = resolve_quiz_pacing(incoming, recent_learn_granularity=recent_granularity)

    concept_pack = (context.get("detail") or {}).get("concept_pack_brief") or {}
    concepts = concept_pack.get("concepts") or []
    concept_count = len(concepts)

    raw_batch = incoming.get("batch_size")
    if raw_batch is not None:
        try:
            suggested_batch_size = max(1, min(int(raw_batch), max_question_count))
        except (TypeError, ValueError):
            suggested_batch_size = 1
    elif pacing == "per_chapter":
        suggested_batch_size = min(max(concept_count, 1), max_question_count) if concept_count else min(5, max_question_count)
    else:
        suggested_batch_size = 1

    pending_items = list(incoming.get("pending_items") or [])
    served_concept_ids = list(incoming.get("served_concept_ids") or [])

    next_session_context = {
        "quiz_pacing": pacing,
        "batch_size": suggested_batch_size,
        "pending_items": pending_items,
        "served_concept_ids": served_concept_ids,
    }

    return {
        "quiz_pacing": pacing,
        "suggested_batch_size": suggested_batch_size,
        "pending_items": pending_items,
        "served_concept_ids": served_concept_ids,
        "next_session_context": next_session_context,
    }


def prepare_learn_session_state(
    context: dict[str, Any],
    session_context: dict[str, Any] | None,
) -> dict[str, Any]:
    incoming = dict(session_context or {})
    served = set(incoming.get("served_concept_ids") or [])
    if not incoming.get("served_concept_ids"):
        recent_learn = context.get("recent_learn_concepts") or []
        if recent_learn:
            served.add(recent_learn[0])

    learned_exposure = set(context.get("learned_exposure_concept_ids") or [])
    retry_state = dict(incoming.get("retry_state") or {})
    last_completed = incoming.get("last_completed_concept_id")
    last_result = incoming.get("last_result")
    blocked_retry: set[str] = set()

    if last_completed:
        if is_blocked_result(last_result):
            blocked_retry.add(last_completed)
        elif is_incorrect_result(last_result):
            retries = int(retry_state.get(last_completed, 0))
            if retries < 1:
                retry_state[last_completed] = retries + 1
            else:
                served.add(last_completed)
                retry_state.pop(last_completed, None)
        else:
            served.add(last_completed)
            retry_state.pop(last_completed, None)

    ordered_concepts = context.get("ordered_concepts") or []
    queue_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []

    for concept in ordered_concepts:
        concept_id = concept.get("concept_id")
        if not concept_id:
            continue
        item = {
            "concept_id": concept_id,
            "canonical_name": concept.get("canonical_name"),
            "topic_id": concept.get("topic_id"),
        }
        if concept_id in blocked_retry:
            blocked_items.append(item)
            continue
        if concept_id in retry_state and retry_state.get(concept_id, 0) > 0:
            queue_items.append(item)
            continue
        if concept_id in served:
            continue
        if concept_id in learned_exposure:
            continue
        queue_items.append(item)

    queue_items = blocked_items + queue_items

    depth_level = incoming.get("depth_level")
    graph_id = context.get("graph_id")
    active_topic_id = context.get("active_topic_id")
    plan_topic_ids = set(context.get("plan_topic_ids") or [])

    concepts_in_topic = [
        c for c in ordered_concepts if c.get("topic_id") == active_topic_id
    ]
    concepts_served = {
        c["concept_id"]
        for c in concepts_in_topic
        if c.get("concept_id") in served or c.get("concept_id") in learned_exposure
    }

    next_topic_id: str | None = None
    suggested_plan_action: dict[str, Any] | None = None
    if not queue_items and active_topic_id and graph_id:
        next_topic_id = get_next_sibling_topic_id(graph_id, active_topic_id)
        if next_topic_id and next_topic_id not in plan_topic_ids:
            suggested_plan_action = {
                "action": "extend_learning_plan_topics",
                "topic_ids": [next_topic_id],
            }

    chapter_progress = {
        "current_topic_id": active_topic_id,
        "concepts_total": len(concepts_in_topic),
        "concepts_served": len(concepts_served),
        "next_topic_id": next_topic_id,
    }

    return {
        "session_queue": {
            "items": queue_items[:20],
            "current_item": queue_items[0] if queue_items else None,
            "next_item": queue_items[1] if len(queue_items) > 1 else None,
        },
        "served_concept_ids": sorted(served),
        "depth_level": depth_level,
        "chapter_progress": chapter_progress,
        "suggested_plan_action": suggested_plan_action,
        "next_session_context": {
            "served_concept_ids": sorted(served),
            "retry_state": retry_state,
            "depth_level": depth_level,
            "queue_length": len(queue_items),
        },
    }


def prepare_review_session_state(
    context: dict[str, Any],
    session_context: dict[str, Any] | None,
) -> dict[str, Any]:
    incoming = dict(session_context or {})
    served = set(incoming.get("served_concept_ids") or [])
    if not incoming.get("served_concept_ids"):
        recent_review_concepts = context.get("recent_review_concepts") or []
        if recent_review_concepts:
            served.add(recent_review_concepts[0])
    retry_state = dict(incoming.get("retry_state") or {})
    last_completed = incoming.get("last_completed_concept_id")
    last_result = incoming.get("last_result")

    if last_completed:
        if is_incorrect_result(last_result):
            retries = int(retry_state.get(last_completed, 0))
            if retries < 1:
                retry_state[last_completed] = retries + 1
            else:
                served.add(last_completed)
                retry_state.pop(last_completed, None)
        else:
            served.add(last_completed)
            retry_state.pop(last_completed, None)

    candidate_items = context.get("candidate_items") or context.get("due_items") or []
    queue_items: list[dict[str, Any]] = []
    for item in candidate_items:
        concept_id = item.get("concept_id")
        if not concept_id:
            continue
        if concept_id in served and retry_state.get(concept_id, 0) == 0:
            continue
        queue_items.append(item)

    return {
        "queue_snapshot": queue_items[:20],
        "current_item": queue_items[0] if queue_items else None,
        "next_item": queue_items[1] if len(queue_items) > 1 else None,
        "served_concept_ids": sorted(served),
        "next_session_context": {
            "served_concept_ids": sorted(served),
            "retry_state": retry_state,
            "queue_length": len(queue_items),
        },
    }
