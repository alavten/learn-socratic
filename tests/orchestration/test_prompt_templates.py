import pytest

from scripts.orchestration.prompt_templates import build_prompt


def test_build_learn_prompt_contains_goal_and_session_queue():
    context = {
        "goal_summary": {"goal_type": "capability_growth"},
        "concept_scope": {"topic_ids": ["t1"]},
        "session_queue": {
            "items": [
                {"concept_id": "c1", "canonical_name": "Variable"},
                {"concept_id": "c2", "canonical_name": "Function"},
            ],
            "current_item": {"concept_id": "c1", "canonical_name": "Variable"},
            "next_item": {"concept_id": "c2", "canonical_name": "Function"},
        },
        "chapter_progress": {
            "current_topic_id": "t1",
            "concepts_total": 2,
            "concepts_served": 0,
            "next_topic_id": None,
        },
        "next_session_context": {"served_concept_ids": [], "queue_length": 2},
    }
    prompt = build_prompt("learn", context)
    assert "Socratic learning coach" in prompt
    assert "capability_growth" in prompt
    assert "Anchor concept_id (MUST teach this turn): c1" in prompt
    assert "Next concept_id (after current completes): c2" in prompt
    assert "Feynman loop" in prompt
    assert "Explain, Interpret, Apply" in prompt
    assert "Do NOT pick a different concept from scope" in prompt
    assert "Do not assess a concept that was not explicitly taught" in prompt
    assert "L1 recall" in prompt
    assert "Scope" in prompt


def test_build_quiz_prompt_per_concept_pacing():
    context = {
        "quiz_scope": {"topic_ids": ["t1"]},
        "history_performance_summary": [{"record_type": "quiz", "avg_score": 82}],
        "quiz_pacing": "per_concept",
        "suggested_batch_size": 1,
        "constraints": {"max_question_count": 10},
    }
    prompt = build_prompt("quiz", context)
    assert "quiz generator and grader" in prompt
    assert "per_concept" in prompt
    assert "one anchor concept_id" in prompt
    assert "add_interaction_record" in prompt
    assert "record_summary" in prompt


def test_build_quiz_prompt_per_chapter_pacing():
    context = {
        "quiz_scope": {"topic_ids": ["t1"]},
        "history_performance_summary": [],
        "quiz_pacing": "per_chapter",
        "suggested_batch_size": 5,
        "constraints": {"max_question_count": 10},
    }
    prompt = build_prompt("quiz", context)
    assert "per_chapter" in prompt
    assert "numbered item list" in prompt
    assert "written must equal expected" in prompt


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
    assert "detailed original-context explanation" in prompt
    assert "provide the next question" in prompt
    assert "`detailed_explanation`" in prompt
    assert "`next_question`" in prompt


def test_build_prompt_unsupported_mode_raises():
    with pytest.raises(ValueError, match="unsupported_mode"):
        build_prompt("ingest", {})
