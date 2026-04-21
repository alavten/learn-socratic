from scripts.orchestration.orchestration_app_service import OrchestrationAppService
from tests.helpers import sample_graph_payload


def test_full_loop_ingest_learn_quiz_review_switch(isolated_db):
    service = OrchestrationAppService()

    ingest = service.ingest_knowledge_graph("g1", sample_graph_payload())
    assert ingest["validation_summary"]["ok"] is True

    plan = service.create_learning_plan("g1", topic_id="t1")
    plan_id = plan["plan_id"]

    learn_prompt = service.get_learning_prompt(plan_id, topic_id="t1")
    assert "Socratic" in learn_prompt["prompt_text"]
    learn_commit = service.append_learning_record(
        plan_id,
        "learn",
        {"concept_id": "c1", "result": "ok", "score": 78, "difficulty_bucket": "easy"},
    )
    assert learn_commit["commit_result"]["record_type"] == "learn"

    quiz_prompt = service.get_quiz_prompt(plan_id, topic_id="t1")
    assert "quiz" in quiz_prompt["prompt_text"].lower()
    quiz_commit = service.append_learning_record(
        plan_id,
        "quiz",
        {"concept_id": "c1", "result": "correct", "score": 88, "difficulty_bucket": "medium"},
    )
    assert quiz_commit["commit_result"]["record_type"] == "quiz"

    review_prompt = service.get_review_prompt(plan_id)
    assert "review" in review_prompt["prompt_text"].lower()
    review_commit = service.append_learning_record(
        plan_id,
        "review",
        {"concept_id": "c1", "result": "correct", "score": 90, "difficulty_bucket": "hard"},
    )
    assert review_commit["commit_result"]["record_type"] == "review"
