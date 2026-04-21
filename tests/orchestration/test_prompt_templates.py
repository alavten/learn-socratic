import pytest

from scripts.orchestration.prompt_templates import build_prompt


def test_build_learn_prompt_contains_goal_and_concept_focus():
    context = {
        "goal_summary": {"goal_type": "capability_growth"},
        "concept_pack_brief": {
            "concepts": [{"canonical_name": f"Concept{i}"} for i in range(10)],
        },
    }
    prompt = build_prompt("learn", context)
    assert "Socratic learning coach" in prompt
    assert "capability_growth" in prompt
    assert "Concept0" in prompt
    assert "Concept7" in prompt
    assert "Concept8" not in prompt
    assert "Feynman loop" in prompt
    assert "Explain, Interpret, Apply" in prompt


def test_build_quiz_prompt_contains_scope_and_history():
    context = {
        "quiz_scope": {"topic_ids": ["t1"]},
        "history_performance_summary": [{"record_type": "quiz", "avg_score": 82}],
    }
    prompt = build_prompt("quiz", context)
    assert "quiz generator and grader" in prompt
    assert "topic_ids" in prompt
    assert "avg_score" in prompt
    assert "retrieval-first" in prompt
    assert "SOLO levels" in prompt
    assert "UBD facet" in prompt


def test_build_review_prompt_contains_due_items_and_risk():
    context = {
        "due_items": [{"concept_id": "c1"}],
        "forgetting_risk_summary": {"avg_forgetting_risk": 0.4},
    }
    prompt = build_prompt("review", context)
    assert "spaced review coach" in prompt
    assert "concept_id" in prompt
    assert "avg_forgetting_risk" in prompt
    assert "spacing-first order" in prompt
    assert "retrieval-first" in prompt


def test_build_prompt_unsupported_mode_raises():
    with pytest.raises(ValueError, match="unsupported_mode"):
        build_prompt("ingest", {})
