from scripts.orchestration.session_state import (
    infer_learn_granularity,
    prepare_quiz_session_state,
    resolve_quiz_pacing,
)


def test_resolve_quiz_pacing_explicit_value():
    assert resolve_quiz_pacing({"quiz_pacing": "per_chapter"}) == "per_chapter"


def test_resolve_quiz_pacing_hint_per_concept():
    assert resolve_quiz_pacing({"pacing_hint": "一题一题来"}) == "per_concept"
    assert resolve_quiz_pacing({"pacing_hint": "one at a time please"}) == "per_concept"


def test_resolve_quiz_pacing_hint_per_chapter():
    assert resolve_quiz_pacing({"pacing_hint": "批量测验"}) == "per_chapter"
    assert resolve_quiz_pacing({"pacing_hint": "chapter quiz batch"}) == "per_chapter"


def test_resolve_quiz_pacing_from_recent_learn_granularity():
    assert resolve_quiz_pacing({}, recent_learn_granularity="single") == "per_concept"
    assert resolve_quiz_pacing({}, recent_learn_granularity="multi") == "per_chapter"
    assert resolve_quiz_pacing({}, recent_learn_granularity="chapter") == "per_chapter"


def test_resolve_quiz_pacing_defaults_to_per_concept():
    assert resolve_quiz_pacing({}) == "per_concept"
    assert resolve_quiz_pacing({"served_concept_ids": ["c1"]}) == "per_concept"
    assert resolve_quiz_pacing({"served_concept_ids": ["c1", "c2"]}) == "per_chapter"


def test_infer_learn_granularity():
    assert infer_learn_granularity([]) is None
    assert infer_learn_granularity(["c1"]) == "single"
    assert infer_learn_granularity(["c1", "c2"]) == "multi"
    assert infer_learn_granularity(["c1", "c2", "c3"]) == "chapter"


def test_prepare_quiz_session_state_uses_recent_learn_concepts():
    context = {
        "constraints": {"max_question_count": 10},
        "recent_learn_concepts": ["c1", "c2", "c3"],
        "detail": {"concept_pack_brief": {"concepts": [{"concept_id": "c1"}]}},
    }
    state = prepare_quiz_session_state(context, {})
    assert state["quiz_pacing"] == "per_chapter"
    assert state["suggested_batch_size"] >= 1
