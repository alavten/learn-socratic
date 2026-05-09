"""Public API for learning module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from scripts.foundation.storage import paginate, query_all, query_one, transaction
from scripts.knowledge_graph import api as kg_api
from scripts.learning.session import add_interaction_record as append_record_impl
from scripts.learning.state import update_state_from_record
from scripts.learning.tasking import sync_task_status_from_result, upsert_task_for_state


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


def list_learning_plans(limit: int = 20, offset: str | None = None) -> dict[str, Any]:
    page_limit, offset_value = paginate(limit, offset)
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
            ,
            (
                SELECT COUNT(*)
                FROM LearningTask lt
                WHERE lt.learningPlanId = lp.learningPlanId AND lt.status IN ('completed', 'done')
            ) AS completed_tasks
        FROM LearningPlan lp
        ORDER BY lp.updatedAt DESC
        LIMIT ? OFFSET ?
        """,
        (page_limit + 1, offset_value),
    )
    has_more = len(rows) > page_limit
    visible = rows[:page_limit]
    for row in visible:
        row["progress"] = {
            "completed_tasks": row["completed_tasks"],
            "pending_tasks": row["pending_tasks"],
        }
        row["focus_topics"] = query_all(
            """
            SELECT t.topicId AS topic_id, t.topicName AS topic_name
            FROM LearningPlanTopic
            JOIN Topic t ON t.topicId = LearningPlanTopic.topicId
            WHERE learningPlanId = ?
            ORDER BY t.sortOrder ASC, t.topicId ASC, LearningPlanTopic.createdAt ASC
            """,
            (row["plan_id"],),
        )
        topic_names = [item["topic_name"] for item in row["focus_topics"][:3] if item.get("topic_name")]
        row["topic_content"] = "；".join(topic_names) if topic_names else "（暂无主题摘要）"
    return {
        "items": visible,
        "has_more": has_more,
        "next_offset": str(offset_value + page_limit) if has_more else None,
    }


def create_learning_plan(graph_id: str, topic_id: str | None = None) -> dict[str, Any]:
    learner_id = _ensure_default_learner()
    now = _now()
    with transaction() as conn:
        existing = conn.execute(
            """
            SELECT learningPlanId AS plan_id
            FROM LearningPlan
            WHERE learnerId = ? AND graphId = ? AND status = 'active'
            ORDER BY updatedAt DESC, createdAt DESC
            LIMIT 1
            """,
            (learner_id, graph_id),
        ).fetchone()
        plan_reused = existing is not None
        plan_id = existing["plan_id"] if existing else str(uuid.uuid4())
        if not existing:
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
            topic_exists = conn.execute(
                "SELECT 1 FROM LearningPlanTopic WHERE learningPlanId = ? AND topicId = ?",
                (plan_id, topic_id),
            ).fetchone()
            if not topic_exists:
                conn.execute(
                    """
                    INSERT INTO LearningPlanTopic(learningPlanTopicId, learningPlanId, topicId, reason, createdAt)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), plan_id, topic_id, "initial_scope", now),
                )
        conn.execute("UPDATE LearningPlan SET updatedAt = ? WHERE learningPlanId = ?", (now, plan_id))
    return {
        "plan_id": plan_id,
        "graph_id": graph_id,
        "plan_reused": plan_reused,
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


def _parse_iso_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def get_review_context(plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
    plan = query_one(
        """
        SELECT learningPlanId AS plan_id, graphId AS graph_id
        FROM LearningPlan
        WHERE learningPlanId = ?
        """,
        (plan_id,),
    )
    if not plan:
        return {"error": "plan_not_found", "plan_id": plan_id}

    scope = _resolve_plan_scope(plan_id, topic_id)
    scoped_concepts_pack = kg_api.get_concepts(
        plan["graph_id"],
        scope,
        detail="brief",
        concept_limit=200,
    )
    scoped_concept_ids = {
        concept.get("concept_id")
        for concept in scoped_concepts_pack.get("concept_briefs", [])
        if concept.get("concept_id")
    }

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
    if scoped_concept_ids:
        due_items = [item for item in due_items if item.get("concept_id") in scoped_concept_ids]

    perf_rows = query_all(
        """
        SELECT
            lr.conceptId AS concept_id,
            COUNT(*) AS attempt_count,
            SUM(CASE WHEN LOWER(COALESCE(lr.result, '')) IN ('wrong', 'incorrect', 'fail') THEN 1 ELSE 0 END) AS wrong_count,
            SUM(CASE WHEN LOWER(COALESCE(lr.result, '')) IN ('correct', 'ok', 'pass') THEN 1 ELSE 0 END) AS correct_count,
            MAX(lr.occurredAt) AS last_occurred_at
        FROM LearningRecord lr
        JOIN LearningSession ls ON ls.sessionId = lr.sessionId
        WHERE ls.learningPlanId = ?
        GROUP BY lr.conceptId
        """,
        (plan_id,),
    )
    perf_by_concept = {row["concept_id"]: row for row in perf_rows if row.get("concept_id")}

    state_rows = query_all(
        """
        SELECT
            conceptId AS concept_id,
            forgettingRisk AS forgetting_risk,
            nextReviewAt AS next_review_at
        FROM LearnerConceptState
        WHERE learningPlanId = ?
        """,
        (plan_id,),
    )
    state_by_concept = {row["concept_id"]: row for row in state_rows if row.get("concept_id")}

    now = datetime.now(timezone.utc)
    candidate_ids: set[str] = {item["concept_id"] for item in due_items if item.get("concept_id")}
    for concept_id, state in state_by_concept.items():
        if scoped_concept_ids and concept_id not in scoped_concept_ids:
            continue
        next_review_at = _parse_iso_ts(state.get("next_review_at"))
        forgetting_risk = float(state.get("forgetting_risk") or 0.0)
        if forgetting_risk >= 0.7:
            candidate_ids.add(concept_id)
            continue
        if next_review_at and next_review_at <= now:
            candidate_ids.add(concept_id)

    review_score_factors: dict[str, dict[str, float]] = {}
    candidate_items: list[dict[str, Any]] = []
    due_by_concept = {item["concept_id"]: item for item in due_items if item.get("concept_id")}
    for concept_id in sorted(candidate_ids):
        due_item = due_by_concept.get(concept_id, {})
        state = state_by_concept.get(concept_id, {})
        perf = perf_by_concept.get(concept_id, {})

        due_at = _parse_iso_ts(due_item.get("due_at"))
        overdue_seconds = max(0.0, (now - due_at).total_seconds()) if due_at else 0.0
        overdue_score = _clamp01(overdue_seconds / 86400.0)
        risk_score = _clamp01(float(state.get("forgetting_risk") or 0.0))

        attempt_count = int(perf.get("attempt_count") or 0)
        wrong_count = int(perf.get("wrong_count") or 0)
        accuracy = (
            float(perf.get("correct_count") or 0) / attempt_count
            if attempt_count > 0
            else 0.5
        )
        weakness_score = _clamp01((wrong_count / max(1, attempt_count)) if attempt_count else 0.5)

        last_occurred = _parse_iso_ts(perf.get("last_occurred_at"))
        recency_days = max(0.0, (now - last_occurred).total_seconds() / 86400.0) if last_occurred else 3.0
        recency_gap_score = _clamp01(recency_days / 7.0)

        review_score = _clamp01(
            0.35 * overdue_score
            + 0.30 * risk_score
            + 0.20 * weakness_score
            + 0.15 * recency_gap_score
        )
        review_score_factors[concept_id] = {
            "overdue_score": overdue_score,
            "forgetting_risk_score": risk_score,
            "weakness_score": weakness_score,
            "recency_gap_score": recency_gap_score,
            "review_score": review_score,
        }
        candidate_items.append(
            {
                "concept_id": concept_id,
                "review_score": review_score,
                "due_at": due_item.get("due_at"),
                "priority_score": due_item.get("priority_score"),
                "reason_type": due_item.get("reason_type"),
                "forgetting_risk": state.get("forgetting_risk"),
                "recent_accuracy": accuracy,
                "attempt_count": attempt_count,
                "wrong_count": wrong_count,
            }
        )

    candidate_items.sort(
        key=lambda item: (
            -(item.get("review_score") or 0.0),
            item.get("due_at") or "",
            -(item.get("forgetting_risk") or 0.0),
            item.get("recent_accuracy") if item.get("recent_accuracy") is not None else 1.0,
        )
    )
    candidate_items = candidate_items[:20]

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
    recent_review_rows = query_all(
        """
        SELECT lr.conceptId AS concept_id
        FROM LearningRecord lr
        JOIN LearningSession ls ON ls.sessionId = lr.sessionId
        WHERE ls.learningPlanId = ? AND lr.recordType = 'review'
        ORDER BY lr.occurredAt DESC, lr.createdAt DESC
        LIMIT 5
        """,
        (plan_id,),
    )
    recent_review_concepts = [row["concept_id"] for row in recent_review_rows if row.get("concept_id")]
    return {
        "due_items": due_items,
        "forgetting_risk_summary": risk_summary[0] if risk_summary else {},
        "priority_reasons": ["overdue", "weak_point", "upcoming"],
        "candidate_items": candidate_items,
        "review_score_factors": review_score_factors,
        "queue_policy": {
            "weights": {
                "overdue_score": 0.35,
                "forgetting_risk_score": 0.30,
                "weakness_score": 0.20,
                "recency_gap_score": 0.15,
            },
            "tie_break": ["due_at_earlier", "higher_forgetting_risk", "lower_recent_accuracy"],
        },
        "scope": scope,
        "recent_review_concepts": recent_review_concepts,
        "constraints": {"max_items": 20},
    }


def check_plan_dependencies(
    graph_id: str,
    concept_ids: list[str] | None = None,
    topic_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return learning-plan references that block graph entity removal."""
    cids = [c for c in (concept_ids or []) if c]
    tids = [t for t in (topic_ids or []) if t]
    blocking: list[dict[str, Any]] = []

    if tids:
        placeholders = ",".join("?" for _ in tids)
        rows = query_all(
            f"""
            SELECT DISTINCT
                lp.learningPlanId AS plan_id,
                'learning_plan_topic' AS dep_type,
                lpt.topicId AS entity_id
            FROM LearningPlanTopic lpt
            JOIN LearningPlan lp ON lp.learningPlanId = lpt.learningPlanId
            WHERE lp.graphId = ? AND lpt.topicId IN ({placeholders})
            """,
            (graph_id, *tids),
        )
        blocking.extend(dict(r) for r in rows)

    if cids:
        ph = ",".join("?" for _ in cids)
        tasks = query_all(
            f"""
            SELECT DISTINCT
                lp.learningPlanId AS plan_id,
                'learning_task' AS dep_type,
                lt.conceptId AS entity_id
            FROM LearningTask lt
            JOIN LearningPlan lp ON lp.learningPlanId = lt.learningPlanId
            WHERE lp.graphId = ? AND lt.conceptId IN ({ph})
            """,
            (graph_id, *cids),
        )
        blocking.extend(dict(r) for r in tasks)

        states = query_all(
            f"""
            SELECT DISTINCT
                lp.learningPlanId AS plan_id,
                'learner_concept_state' AS dep_type,
                lcs.conceptId AS entity_id
            FROM LearnerConceptState lcs
            JOIN LearningPlan lp ON lp.learningPlanId = lcs.learningPlanId
            WHERE lp.graphId = ? AND lcs.conceptId IN ({ph})
            """,
            (graph_id, *cids),
        )
        blocking.extend(dict(r) for r in states)

        records = query_all(
            f"""
            SELECT DISTINCT
                lp.learningPlanId AS plan_id,
                'learning_record' AS dep_type,
                lr.conceptId AS entity_id
            FROM LearningRecord lr
            JOIN LearningSession ls ON ls.sessionId = lr.sessionId
            JOIN LearningPlan lp ON lp.learningPlanId = ls.learningPlanId
            WHERE lp.graphId = ? AND lr.conceptId IN ({ph})
            """,
            (graph_id, *cids),
        )
        blocking.extend(dict(r) for r in records)

    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in blocking:
        key = (item["plan_id"], item["dep_type"], item["entity_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return {
        "graph_id": graph_id,
        "has_blocking": len(deduped) > 0,
        "blocking_dependencies": deduped,
    }


def cleanup_learning_refs_for_graph_entity_removal(
    graph_id: str,
    concept_ids: list[str] | None = None,
    topic_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Remove learning-domain rows that reference concepts/topics on the given graph (hard delete)."""
    cids = [c for c in (concept_ids or []) if c]
    tids = [t for t in (topic_ids or []) if t]
    summary: dict[str, int] = {
        "learning_tasks_deleted": 0,
        "learner_concept_states_deleted": 0,
        "learning_records_deleted": 0,
        "learning_plan_topics_deleted": 0,
    }
    if not cids and not tids:
        return summary

    with transaction() as conn:
        if cids:
            ph = ",".join("?" for _ in cids)
            cur = conn.execute(
                f"""
                DELETE FROM LearningTask
                WHERE learningPlanId IN (SELECT learningPlanId FROM LearningPlan WHERE graphId = ?)
                  AND conceptId IN ({ph})
                """,
                (graph_id, *cids),
            )
            summary["learning_tasks_deleted"] = cur.rowcount or 0

            cur = conn.execute(
                f"""
                DELETE FROM LearnerConceptState
                WHERE learningPlanId IN (SELECT learningPlanId FROM LearningPlan WHERE graphId = ?)
                  AND conceptId IN ({ph})
                """,
                (graph_id, *cids),
            )
            summary["learner_concept_states_deleted"] = cur.rowcount or 0

            cur = conn.execute(
                f"""
                DELETE FROM LearningRecord
                WHERE learningRecordId IN (
                    SELECT lr.learningRecordId
                    FROM LearningRecord lr
                    JOIN LearningSession ls ON ls.sessionId = lr.sessionId
                    JOIN LearningPlan lp ON lp.learningPlanId = ls.learningPlanId
                    WHERE lp.graphId = ? AND lr.conceptId IN ({ph})
                )
                """,
                (graph_id, *cids),
            )
            summary["learning_records_deleted"] = cur.rowcount or 0

        if tids:
            ph_t = ",".join("?" for _ in tids)
            cur = conn.execute(
                f"""
                DELETE FROM LearningPlanTopic
                WHERE learningPlanId IN (SELECT learningPlanId FROM LearningPlan WHERE graphId = ?)
                  AND topicId IN ({ph_t})
                """,
                (graph_id, *tids),
            )
            summary["learning_plan_topics_deleted"] = cur.rowcount or 0

    return summary


def add_interaction_record(
    plan_id: str,
    mode: str,
    record_payload: dict[str, Any],
) -> dict[str, Any]:
    with transaction() as conn:
        commit = append_record_impl(plan_id, mode, record_payload, conn=conn)
        state_delta = update_state_from_record(
            learner_id=commit["learner_id"],
            learning_plan_id=plan_id,
            concept_id=commit["concept_id"],
            mode=mode,
            record_payload=record_payload,
            conn=conn,
        )
        task_delta = upsert_task_for_state(
            learning_plan_id=plan_id,
            concept_id=commit["concept_id"],
            state_summary=state_delta,
            last_result=record_payload.get("result"),
            conn=conn,
        )
        task_status_delta = sync_task_status_from_result(
            learning_plan_id=plan_id,
            concept_id=commit["concept_id"],
            state_summary=state_delta,
            last_result=record_payload.get("result"),
            conn=conn,
        )
        plan_updated_at = _now()
        conn.execute(
            "UPDATE LearningPlan SET updatedAt = ? WHERE learningPlanId = ?",
            (plan_updated_at, plan_id),
        )
    return {
        "commit_result": commit,
        "state_delta_summary": state_delta,
        "task_delta_summary": task_delta,
        "task_status_delta_summary": task_status_delta,
        "plan_delta_summary": {
            "plan_id": plan_id,
            "plan_updated_at": plan_updated_at,
            "plan_touched": True,
        },
    }
