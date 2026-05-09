"""Validate learning API payloads (domain layer; mirrors orchestration JSON Schema)."""

from __future__ import annotations

from typing import Any, Mapping

from scripts.foundation.storage import query_one

LEARNING_MODES = frozenset({"learn", "quiz", "review"})
ALLOWED_RESULTS = frozenset(
    {
        "ok",
        "partial",
        "blocked",
        "correct",
        "wrong",
        "pass",
        "fail",
        "incorrect",
    }
)
ALLOWED_DIFFICULTY = frozenset({"easy", "medium", "hard"})


class LearningPayloadError(ValueError):
    """Invalid arguments for learning write APIs."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _normalized_score(raw: float) -> float:
    return raw / 100.0 if raw > 1.0 else raw


def validate_record_payload_for_interaction(record_payload: Mapping[str, Any]) -> None:
    """Validate ``record_payload`` for ``add_interaction_record`` (concept-centric writes)."""
    if not isinstance(record_payload, Mapping):
        raise LearningPayloadError("invalid_record_payload", "record_payload must be an object")
    concept_id = record_payload.get("concept_id")
    if not concept_id or not str(concept_id).strip():
        raise LearningPayloadError("missing_concept_id", "record_payload.concept_id is required")

    raw_result = record_payload.get("result")
    if raw_result is not None and raw_result != "":
        result = str(raw_result).strip().lower()
        if result not in ALLOWED_RESULTS:
            raise LearningPayloadError(
                "invalid_result",
                f"record_payload.result must be one of {sorted(ALLOWED_RESULTS)}, got {raw_result!r}",
            )
    else:
        result = ""

    score_raw = record_payload.get("score")
    if score_raw is not None:
        try:
            s = float(score_raw)
        except (TypeError, ValueError) as exc:
            raise LearningPayloadError("invalid_score", "record_payload.score must be a number") from exc
        norm = _normalized_score(s)
        if norm < 0.0 or norm > 1.0:
            raise LearningPayloadError("score_out_of_range", "record_payload.score must be within 0~1 or 0~100")
        if result == "blocked" and norm > 0.35:
            raise LearningPayloadError(
                "score_result_mismatch",
                "blocked outcomes expect score ≤ 35 (percent) or ≤ 0.35 (ratio)",
            )
        if result == "partial" and norm > 0.55:
            raise LearningPayloadError(
                "score_result_mismatch",
                "partial outcomes expect score ≤ 55 (percent) or ≤ 0.55 (ratio)",
            )

    bucket = record_payload.get("difficulty_bucket")
    if bucket is not None and bucket != "":
        if str(bucket).lower() not in ALLOWED_DIFFICULTY:
            raise LearningPayloadError(
                "invalid_difficulty_bucket",
                f"difficulty_bucket must be one of {sorted(ALLOWED_DIFFICULTY)}",
            )

    latency = record_payload.get("latency_ms")
    if latency is not None:
        try:
            li = int(latency)
        except (TypeError, ValueError) as exc:
            raise LearningPayloadError("invalid_latency_ms", "latency_ms must be an integer") from exc
        if li < 0:
            raise LearningPayloadError("invalid_latency_ms", "latency_ms must be >= 0")


def validate_add_interaction_record(plan_id: str, mode: str, record_payload: Mapping[str, Any]) -> None:
    """Full validation before ``add_interaction_record`` mutates storage."""
    if not plan_id or not str(plan_id).strip():
        raise LearningPayloadError("missing_plan_id", "plan_id is required")
    if mode not in LEARNING_MODES:
        raise LearningPayloadError(
            "invalid_mode",
            f"mode must be one of {sorted(LEARNING_MODES)}, got {mode!r}",
        )
    exists = query_one(
        "SELECT learningPlanId AS id FROM LearningPlan WHERE learningPlanId = ?",
        (plan_id,),
    )
    if not exists:
        raise LearningPayloadError("plan_not_found", f"learning plan not found: {plan_id}")
    validate_record_payload_for_interaction(record_payload)
