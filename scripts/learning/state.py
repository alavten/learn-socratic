"""State aggregation logic for learner concept mastery."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from scripts.foundation.storage import query_one, transaction


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mastery_level(score: float) -> str:
    if score >= 0.9:
        return "Mastered"
    if score >= 0.7:
        return "Proficient"
    if score >= 0.4:
        return "Learning"
    return "New"


def _normalize_score(score_input: Any) -> float:
    """Normalize score from either 0~1 or 0~100 into 0~1."""
    if score_input is None:
        return 0.6
    raw = float(score_input)
    # Backward-compatible: allow callers to send percentage (0~100) or ratio (0~1).
    normalized = raw / 100.0 if raw > 1.0 else raw
    return max(0.0, min(1.0, normalized))


def update_state_from_record(
    learner_id: str,
    learning_plan_id: str,
    concept_id: str,
    mode: str,
    record_payload: dict[str, Any],
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    now = _now()
    if conn is not None:
        fetched = conn.execute(
            """
            SELECT *
            FROM LearnerConceptState
            WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
            """,
            (learner_id, learning_plan_id, concept_id),
        ).fetchone()
        row = dict(fetched) if fetched else None
    else:
        row = query_one(
            """
            SELECT *
            FROM LearnerConceptState
            WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
            """,
            (learner_id, learning_plan_id, concept_id),
        )

    score_input = record_payload.get("score")
    normalized_score = _normalize_score(score_input)
    result = (record_payload.get("result") or "").lower()

    if row:
        prev_mastery = float(row["masteryScore"])
        mastery = max(0.0, min(1.0, prev_mastery * 0.7 + normalized_score * 0.3))
        correct_inc = 1 if result in {"correct", "pass", "ok"} else 0
        wrong_inc = 1 if result in {"wrong", "fail", "incorrect"} else 0
        learn_inc = 1 if mode == "learn" else 0
        quiz_inc = 1 if mode == "quiz" else 0
        review_inc = 1 if mode == "review" else 0
        bucket = record_payload.get("difficulty_bucket")
        easy_inc = 1 if bucket == "easy" else 0
        medium_inc = 1 if bucket == "medium" else 0
        hard_inc = 1 if bucket == "hard" else 0
        confidence = max(0.0, min(1.0, float(row["confidence"]) * 0.7 + mastery * 0.3))
        forgetting_risk = max(0.0, min(1.0, 1.0 - mastery))
        next_review_at = now + timedelta(days=max(1, int((1.0 - forgetting_risk) * 7)))

        if conn is not None:
            conn.execute(
                """
                UPDATE LearnerConceptState
                SET masteryLevel = ?, masteryScore = ?, learnCount = learnCount + ?,
                    quizCount = quizCount + ?, reviewCount = reviewCount + ?,
                    easyCount = easyCount + ?, mediumCount = mediumCount + ?, hardCount = hardCount + ?,
                    correctCount = correctCount + ?, wrongCount = wrongCount + ?,
                    confidence = ?, forgettingRisk = ?, lastInteractionAt = ?, nextReviewAt = ?,
                    updatedAt = ?
                WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
                """,
                (
                    _mastery_level(mastery),
                    mastery,
                    learn_inc,
                    quiz_inc,
                    review_inc,
                    easy_inc,
                    medium_inc,
                    hard_inc,
                    correct_inc,
                    wrong_inc,
                    confidence,
                    forgetting_risk,
                    now.isoformat(),
                    next_review_at.isoformat(),
                    now.isoformat(),
                    learner_id,
                    learning_plan_id,
                    concept_id,
                ),
            )
        else:
            with transaction() as tx:
                tx.execute(
                    """
                    UPDATE LearnerConceptState
                    SET masteryLevel = ?, masteryScore = ?, learnCount = learnCount + ?,
                        quizCount = quizCount + ?, reviewCount = reviewCount + ?,
                        easyCount = easyCount + ?, mediumCount = mediumCount + ?, hardCount = hardCount + ?,
                        correctCount = correctCount + ?, wrongCount = wrongCount + ?,
                        confidence = ?, forgettingRisk = ?, lastInteractionAt = ?, nextReviewAt = ?,
                        updatedAt = ?
                    WHERE learnerId = ? AND learningPlanId = ? AND conceptId = ?
                    """,
                    (
                        _mastery_level(mastery),
                        mastery,
                        learn_inc,
                        quiz_inc,
                        review_inc,
                        easy_inc,
                        medium_inc,
                        hard_inc,
                        correct_inc,
                        wrong_inc,
                        confidence,
                        forgetting_risk,
                        now.isoformat(),
                        next_review_at.isoformat(),
                        now.isoformat(),
                        learner_id,
                        learning_plan_id,
                        concept_id,
                    ),
                )
        return {
            "state_action": "updated",
            "mastery_score": mastery,
            "mastery_level": _mastery_level(mastery),
            "forgetting_risk": forgetting_risk,
            "next_review_at": next_review_at.isoformat(),
        }

    mastery = normalized_score
    confidence = mastery
    forgetting_risk = max(0.0, min(1.0, 1.0 - mastery))
    next_review_at = now + timedelta(days=max(1, int((1.0 - forgetting_risk) * 7)))
    state_id = str(uuid.uuid4())
    learn_count = 1 if mode == "learn" else 0
    quiz_count = 1 if mode == "quiz" else 0
    review_count = 1 if mode == "review" else 0
    bucket = record_payload.get("difficulty_bucket")
    easy_count = 1 if bucket == "easy" else 0
    medium_count = 1 if bucket == "medium" else 0
    hard_count = 1 if bucket == "hard" else 0
    correct_count = 1 if result in {"correct", "pass", "ok"} else 0
    wrong_count = 1 if result in {"wrong", "fail", "incorrect"} else 0

    if conn is not None:
        conn.execute(
            """
            INSERT INTO LearnerConceptState(
                learnerConceptStateId, learnerId, learningPlanId, conceptId,
                targetLevel, targetScore, masteryLevel, masteryScore,
                learnCount, quizCount, reviewCount,
                easyCount, mediumCount, hardCount,
                correctCount, wrongCount,
                confidence, forgettingRisk, lastInteractionAt, nextReviewAt, createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state_id,
                learner_id,
                learning_plan_id,
                concept_id,
                "Proficient",
                0.8,
                _mastery_level(mastery),
                mastery,
                learn_count,
                quiz_count,
                review_count,
                easy_count,
                medium_count,
                hard_count,
                correct_count,
                wrong_count,
                confidence,
                forgetting_risk,
                now.isoformat(),
                next_review_at.isoformat(),
                now.isoformat(),
                now.isoformat(),
            ),
        )
    else:
        with transaction() as tx:
            tx.execute(
                """
                INSERT INTO LearnerConceptState(
                    learnerConceptStateId, learnerId, learningPlanId, conceptId,
                    targetLevel, targetScore, masteryLevel, masteryScore,
                    learnCount, quizCount, reviewCount,
                    easyCount, mediumCount, hardCount,
                    correctCount, wrongCount,
                    confidence, forgettingRisk, lastInteractionAt, nextReviewAt, createdAt, updatedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    learner_id,
                    learning_plan_id,
                    concept_id,
                    "Proficient",
                    0.8,
                    _mastery_level(mastery),
                    mastery,
                    learn_count,
                    quiz_count,
                    review_count,
                    easy_count,
                    medium_count,
                    hard_count,
                    correct_count,
                    wrong_count,
                    confidence,
                    forgetting_risk,
                    now.isoformat(),
                    next_review_at.isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
    return {
        "state_action": "created",
        "mastery_score": mastery,
        "mastery_level": _mastery_level(mastery),
        "forgetting_risk": forgetting_risk,
        "next_review_at": next_review_at.isoformat(),
    }
