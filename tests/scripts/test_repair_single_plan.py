from pathlib import Path

from scripts.foundation.storage import query_all, transaction
from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.api import create_learning_plan
from scripts.repair_single_plan import repair_single_plan
from tests.helpers import sample_graph_payload


def test_repair_single_plan_preview_and_apply(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    main = create_learning_plan("g1", topic_id="t1")

    # Manually craft a duplicate plan row to emulate historical dirty data.
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO LearningPlan(
                learningPlanId, learnerId, graphId, planName, goalType, startAt, endAt, status, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("dup-plan", "default-learner", "g1", "dup", "capability_growth", "2026-01-01", None, "active", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            """
            INSERT INTO LearningPlanTopic(learningPlanTopicId, learningPlanId, topicId, reason, createdAt)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("dup-topic", "dup-plan", "t2", "manual", "2026-01-01"),
        )
        conn.execute(
            """
            INSERT INTO LearningSession(sessionId, learnerId, learningPlanId, startedAt, endedAt, status, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("dup-session", "default-learner", "dup-plan", "2026-01-01", None, "active", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            """
            INSERT INTO LearningRecord(
                learningRecordId, sessionId, conceptId, recordType, result, score, latencyMs,
                difficultyBucket, feedbackType, occurredAt, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "dup-record",
                "dup-session",
                "c2",
                "learn",
                "ok",
                80,
                1000,
                "medium",
                None,
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.execute(
            """
            INSERT INTO LearningTask(
                learningTaskId, learningPlanId, conceptId, taskType, reasonType, strategy,
                priorityScore, dueAt, generatedAt, batchId, status, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "dup-task",
                "dup-plan",
                "c2",
                "learn",
                "manual",
                "test",
                0.8,
                "2026-01-02",
                "2026-01-01",
                "20260101",
                "pending",
                "2026-01-01",
                "2026-01-01",
            ),
        )
        conn.execute(
            """
            INSERT INTO LearnerConceptState(
                learnerConceptStateId, learnerId, learningPlanId, conceptId, targetLevel, targetScore,
                masteryLevel, masteryScore, learnCount, quizCount, reviewCount, easyCount, mediumCount, hardCount,
                correctCount, wrongCount, confidence, forgettingRisk, lastInteractionAt, nextReviewAt, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "dup-state",
                "default-learner",
                "dup-plan",
                "c2",
                "Proficient",
                None,
                "Proficient",
                0.6,
                1,
                0,
                0,
                1,
                0,
                0,
                1,
                0,
                0.7,
                0.3,
                "2026-01-01",
                "2026-01-02",
                "2026-01-01",
                "2026-01-01",
            ),
        )

    preview = repair_single_plan(Path(isolated_db), graph_id="g1", main_plan_id=main["plan_id"], apply_changes=False)
    assert preview["duplicate_plan_count"] == 1
    assert preview["topics_to_merge"] == ["t2"]
    assert preview["applied"] is False

    applied = repair_single_plan(Path(isolated_db), graph_id="g1", main_plan_id=main["plan_id"], apply_changes=True)
    assert applied["applied"] is True
    assert applied["duplicate_plan_count"] == 0
    assert applied["runtime_merge_summary"]["sessions_moved"] == 1
    assert applied["runtime_merge_summary"]["records_moved_via_sessions"] == 1
    assert applied["runtime_merge_summary"]["tasks_moved"] == 1
    assert applied["runtime_merge_summary"]["states_moved"] == 1

    plans = query_all("SELECT learningPlanId FROM LearningPlan WHERE graphId = ?", ("g1",))
    assert len(plans) == 1
    topics = query_all("SELECT topicId FROM LearningPlanTopic WHERE learningPlanId = ?", (main["plan_id"],))
    assert {row["topicId"] for row in topics} == {"t1", "t2"}
    sessions = query_all("SELECT sessionId FROM LearningSession WHERE learningPlanId = ?", (main["plan_id"],))
    assert {row["sessionId"] for row in sessions} == {"dup-session"}

