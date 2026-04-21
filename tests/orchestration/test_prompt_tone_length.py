from scripts.orchestration.prompt_templates import build_prompt


def test_prompt_length_guardrails():
    contexts = {
        "learn": {
            "goal_summary": {"goal_type": "capability_growth"},
            "concept_pack_brief": {"concepts": [{"canonical_name": f"C{i}"} for i in range(20)]},
        },
        "quiz": {
            "quiz_scope": {"topic_ids": ["t1"]},
            "history_performance_summary": [{"record_type": "quiz", "avg_score": 88}],
        },
        "review": {
            "due_items": [{"concept_id": f"c{i}"} for i in range(20)],
            "forgetting_risk_summary": {"avg_forgetting_risk": 0.4},
        },
    }
    for mode, context in contexts.items():
        prompt = build_prompt(mode, context)
        assert len(prompt) <= 600


def test_learn_prompt_single_core_question_instruction():
    prompt = build_prompt(
        "learn",
        {
            "goal_summary": {"goal_type": "capability_growth"},
            "concept_pack_brief": {"concepts": [{"canonical_name": "A"}]},
        },
    )
    assert "ask one diagnostic question" in prompt
