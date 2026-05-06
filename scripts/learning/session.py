"""Session and record lifecycle operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from scripts.foundation.storage import query_one, transaction


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_or_create_active_session(learning_plan_id: str) -> dict[str, Any]:
    session = query_one(
        """
        SELECT sessionId AS session_id, learnerId AS learner_id
        FROM LearningSession
        WHERE learningPlanId = ? AND status = 'active'
        ORDER BY startedAt DESC
        LIMIT 1
        """,
        (learning_plan_id,),
    )
    if session:
        return session

    plan = query_one(
        "SELECT learnerId AS learner_id FROM LearningPlan WHERE learningPlanId = ?",
        (learning_plan_id,),
    )
    if not plan:
        raise ValueError("learning_plan_not_found")

    now = _now()
    session_id = str(uuid.uuid4())
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO LearningSession(
                sessionId, learnerId, learningPlanId, startedAt, endedAt, status, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, plan["learner_id"], learning_plan_id, now, None, "active", now, now),
        )
    return {"session_id": session_id, "learner_id": plan["learner_id"]}


def add_interaction_record(
    learning_plan_id: str,
    mode: str,
    record_payload: dict[str, Any],
) -> dict[str, Any]:
    if mode not in {"learn", "quiz", "review"}:
        raise ValueError("invalid_mode")
    concept_id = record_payload.get("concept_id")
    if not concept_id:
        raise ValueError("missing_concept_id")

    session = get_or_create_active_session(learning_plan_id)
    now = _now()
    record_id = str(uuid.uuid4())
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO LearningRecord(
                learningRecordId, sessionId, conceptId, recordType, result, score, latencyMs,
                difficultyBucket, feedbackType, occurredAt, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                session["session_id"],
                concept_id,
                mode,
                record_payload.get("result"),
                record_payload.get("score"),
                record_payload.get("latency_ms"),
                record_payload.get("difficulty_bucket"),
                record_payload.get("feedback_type"),
                record_payload.get("occurred_at", now),
                now,
                now,
            ),
        )
    return {
        "learning_record_id": record_id,
        "session_id": session["session_id"],
        "learner_id": session["learner_id"],
        "concept_id": concept_id,
        "record_type": mode,
        "occurred_at": record_payload.get("occurred_at", now),
    }
