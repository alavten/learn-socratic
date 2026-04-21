"""Public API for learning module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from scripts.foundation.storage import paginate, query_all, query_one, transaction
from scripts.knowledge_graph import api as kg_api
from scripts.learning.session import append_learning_record as append_record_impl
from scripts.learning.state import update_state_from_record
from scripts.learning.tasking import upsert_task_for_state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_default_learner() -> str:
    learner = query_one("SELECT learnerId AS learner_id FROM Learner LIMIT 1")
    if learner:
        return learner["learner_id"]
    learner_id = "default-learner"
    now = _now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO Learner(learnerId, profileId, timezone, locale, status, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (learner_id, "default-profile", "UTC", "zh-CN", "active", now, now),
        )
    return learner_id


def list_learning_plans(limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
    page_limit, offset = paginate(limit, cursor)
    rows = query_all(
        """
        SELECT
            lp.learningPlanId AS plan_id,
            lp.graphId AS graph_id,
            lp.status,
            lp.updatedAt AS updated_at,
            (
                SELECT COUNT(*)
                FROM LearningTask lt
                WHERE lt.learningPlanId = lp.learningPlanId AND lt.status = 'pending'
            ) AS pending_tasks
        FROM LearningPlan lp
        ORDER BY lp.updatedAt DESC
        LIMIT ? OFFSET ?
        """,
        (page_limit + 1, offset),
    )
    has_more = len(rows) > page_limit
    visible = rows[:page_limit]
    for row in visible:
        row["progress"] = {"pending_tasks": row["pending_tasks"]}
        row["focus_topics"] = query_all(
            """
            SELECT topicId AS topic_id
            FROM LearningPlanTopic
            WHERE learningPlanId = ?
            ORDER BY createdAt ASC
            LIMIT 5
            """,
            (row["plan_id"],),
        )
    return {
        "items": visible,
        "has_more": has_more,
        "cursor": str(offset + page_limit) if has_more else None,
    }


def create_learning_plan(graph_id: str, topic_id: str | None = None) -> dict[str, Any]:
    learner_id = _ensure_default_learner()
    now = _now()
    plan_id = str(uuid.uuid4())
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO LearningPlan(
                learningPlanId, learnerId, graphId, planName, goalType, startAt, endAt, status, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                learner_id,
                graph_id,
                f"Plan-{graph_id}",
                "capability_growth",
                now,
                None,
                "active",
                now,
                now,
            ),
        )
        if topic_id:
            conn.execute(
                """
                INSERT INTO LearningPlanTopic(learningPlanTopicId, learningPlanId, topicId, reason, createdAt)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), plan_id, topic_id, "initial_scope", now),
            )
    return {
        "plan_id": plan_id,
        "graph_id": graph_id,
        "initial_scope_summary": {"topic_id": topic_id, "topic_bound": topic_id is not None},
    }


def extend_learning_plan_topics(
    plan_id: str,
    topic_ids: list[str],
    reason: str | None = None,
) -> dict[str, Any]:
    now = _now()
    added_topics: list[str] = []
    skipped_topics: list[str] = []
    with transaction() as conn:
        for topic_id in topic_ids:
            exists = conn.execute(
                "SELECT 1 FROM LearningPlanTopic WHERE learningPlanId = ? AND topicId = ?",
                (plan_id, topic_id),
            ).fetchone()
            if exists:
                skipped_topics.append(topic_id)
                continue
            conn.execute(
                """
                INSERT INTO LearningPlanTopic(learningPlanTopicId, learningPlanId, topicId, reason, createdAt)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), plan_id, topic_id, reason or "progressive_extension", now),
            )
            added_topics.append(topic_id)
        conn.execute("UPDATE LearningPlan SET updatedAt = ? WHERE learningPlanId = ?", (now, plan_id))
    return {
        "plan_id": plan_id,
        "added_topics": added_topics,
        "skipped_topics": skipped_topics,
        "new_scope_summary": {"topic_count": len(added_topics)},
    }


def _resolve_plan_scope(plan_id: str, topic_id: str | None) -> dict[str, Any]:
    if topic_id:
        return {"topic_ids": [topic_id]}
    topics = query_all(
        "SELECT topicId AS topic_id FROM LearningPlanTopic WHERE learningPlanId = ?",
        (plan_id,),
    )
    topic_ids = [t["topic_id"] for t in topics]
    return {"topic_ids": topic_ids} if topic_ids else {}


def get_learning_context(plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
    plan = query_one(
        """
        SELECT learningPlanId AS plan_id, graphId AS graph_id, goalType AS goal_type, status
        FROM LearningPlan WHERE learningPlanId = ?
        """,
        (plan_id,),
    )
    if not plan:
        return {"error": "plan_not_found", "plan_id": plan_id}
    scope = _resolve_plan_scope(plan_id, topic_id)
    concept_pack = kg_api.get_concepts(plan["graph_id"], scope, detail="brief", concept_limit=20)
    relation_pack = kg_api.get_concept_relations(plan["graph_id"], scope, depth=1, relation_limit=30)
    evidence_pack = kg_api.get_concept_evidence(plan["graph_id"], scope, mode="summary", evidence_limit=20)
    state_summary = query_all(
        """
        SELECT masteryLevel AS mastery_level, COUNT(*) AS count
        FROM LearnerConceptState
        WHERE learningPlanId = ?
        GROUP BY masteryLevel
        """,
        (plan_id,),
    )
    task_summary = query_all(
        """
        SELECT taskType AS task_type, COUNT(*) AS count
        FROM LearningTask
        WHERE learningPlanId = ? AND status = 'pending'
        GROUP BY taskType
        """,
        (plan_id,),
    )
    return {
        "goal_summary": {"goal_type": plan["goal_type"], "plan_status": plan["status"]},
        "state_summary": state_summary,
        "task_summary": task_summary,
        "concept_scope": scope,
        "concept_pack_brief": {
            "concepts": concept_pack.get("concept_briefs", []),
            "relations": relation_pack.get("relation_briefs", []),
            "evidence": evidence_pack.get("evidence_summary", []),
            "has_more": concept_pack.get("has_more", False),
        },
    }


def get_quiz_context(plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
    learning_context = get_learning_context(plan_id, topic_id=topic_id)
    performance = query_all(
        """
        SELECT
            lr.recordType AS record_type,
            AVG(COALESCE(lr.score, 0)) AS avg_score,
            COUNT(*) AS count
        FROM LearningRecord lr
        JOIN LearningSession ls ON ls.sessionId = lr.sessionId
        WHERE ls.learningPlanId = ?
        GROUP BY lr.recordType
        """,
        (plan_id,),
    )
    return {
        "quiz_scope": learning_context.get("concept_scope", {}),
        "history_performance_summary": performance,
        "difficulty_hint": "mix easy-medium-hard with focus on weak concepts",
        "constraints": {"max_question_count": 10},
        "detail": {"concept_pack_brief": learning_context.get("concept_pack_brief", {})},
    }


def get_review_context(plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
    del topic_id
    due_items = query_all(
        """
        SELECT
            learningTaskId AS learning_task_id,
            conceptId AS concept_id,
            priorityScore AS priority_score,
            dueAt AS due_at,
            reasonType AS reason_type
        FROM LearningTask
        WHERE learningPlanId = ? AND status = 'pending'
        ORDER BY priorityScore DESC, dueAt ASC
        LIMIT 20
        """,
        (plan_id,),
    )
    risk_summary = query_all(
        """
        SELECT
            AVG(forgettingRisk) AS avg_forgetting_risk,
            AVG(confidence) AS avg_confidence
        FROM LearnerConceptState
        WHERE learningPlanId = ?
        """,
        (plan_id,),
    )
    return {
        "due_items": due_items,
        "forgetting_risk_summary": risk_summary[0] if risk_summary else {},
        "priority_reasons": ["overdue", "weak_point", "upcoming"],
        "constraints": {"max_items": 20},
    }


def append_learning_record(
    plan_id: str,
    mode: str,
    record_payload: dict[str, Any],
) -> dict[str, Any]:
    commit = append_record_impl(plan_id, mode, record_payload)
    state_delta = update_state_from_record(
        learner_id=commit["learner_id"],
        learning_plan_id=plan_id,
        concept_id=commit["concept_id"],
        mode=mode,
        record_payload=record_payload,
    )
    task_delta = upsert_task_for_state(
        learning_plan_id=plan_id,
        concept_id=commit["concept_id"],
        state_summary=state_delta,
    )
    return {
        "commit_result": commit,
        "state_delta_summary": state_delta,
        "task_delta_summary": task_delta,
    }
