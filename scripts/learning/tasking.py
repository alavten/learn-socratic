"""Learning task scheduling and reprioritization."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from scripts.foundation.storage import query_one, transaction


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_task_for_state(
    learning_plan_id: str,
    concept_id: str,
    state_summary: dict[str, Any],
    reason_type: str = "weak_point",
    last_result: str | None = None,
) -> dict[str, Any]:
    now = _now()
    mastery = float(state_summary.get("mastery_score", 0.0))
    forgetting = float(state_summary.get("forgetting_risk", 1.0))
    normalized_result = (last_result or "").lower()
    is_correct = normalized_result in {"correct", "ok", "pass"}
    task_type = "review" if forgetting > 0.35 else "learn"
    priority = max(0.1, min(1.0, 0.6 * forgetting + 0.4 * (1.0 - mastery)))
    # Dequeue-friendly policy (plan A): after a correct review, lower priority and push due later.
    if is_correct:
        priority = max(0.1, priority * 0.55)
        due_at = now + timedelta(hours=max(24, int((1.0 - priority) * 36)))
    else:
        due_at = now + timedelta(hours=max(4, int((1.0 - priority) * 24)))

    task = query_one(
        """
        SELECT learningTaskId AS task_id
        FROM LearningTask
        WHERE learningPlanId = ? AND conceptId = ? AND status = 'pending'
        ORDER BY generatedAt DESC
        LIMIT 1
        """,
        (learning_plan_id, concept_id),
    )

    if task:
        with transaction() as conn:
            conn.execute(
                """
                UPDATE LearningTask
                SET taskType = ?, reasonType = ?, strategy = ?, priorityScore = ?, dueAt = ?, updatedAt = ?
                WHERE learningTaskId = ?
                """,
                (
                    task_type,
                    reason_type,
                    "state_gap_and_forgetting_risk",
                    priority,
                    due_at.isoformat(),
                    now.isoformat(),
                    task["task_id"],
                ),
            )
        return {
            "task_action": "updated",
            "learning_task_id": task["task_id"],
            "task_type": task_type,
            "priority_score": priority,
            "due_at": due_at.isoformat(),
        }

    task_id = str(uuid.uuid4())
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO LearningTask(
                learningTaskId, learningPlanId, conceptId, taskType, reasonType, strategy,
                priorityScore, dueAt, generatedAt, batchId, status, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                learning_plan_id,
                concept_id,
                task_type,
                reason_type,
                "state_gap_and_forgetting_risk",
                priority,
                due_at.isoformat(),
                now.isoformat(),
                now.strftime("%Y%m%d%H"),
                "pending",
                now.isoformat(),
                now.isoformat(),
            ),
        )
    return {
        "task_action": "created",
        "learning_task_id": task_id,
        "task_type": task_type,
        "priority_score": priority,
        "due_at": due_at.isoformat(),
    }
