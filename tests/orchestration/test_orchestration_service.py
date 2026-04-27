from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.orchestration.orchestration_app_service import OrchestrationAppService
from tests.helpers import sample_graph_payload


def test_api_self_description(isolated_db):
    service = OrchestrationAppService()
    apis = service.list_apis()
    names = [item["name"] for item in apis]
    assert "get_api_spec" in names
    spec = service.get_api_spec("create_learning_plan")
    assert "required" in spec["input_schema"]


def test_prompt_generation_and_record_commit(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")
    learn_prompt = service.get_learning_prompt(plan["plan_id"], topic_id="t1")
    assert "prompt_text" in learn_prompt
    commit = service.append_learning_record(
        plan["plan_id"],
        "learn",
        {"concept_id": "c1", "result": "ok", "score": 80, "difficulty_bucket": "easy"},
    )
    assert "state_delta_summary" in commit


def test_remove_knowledge_graph_entities_api_listed(isolated_db):
    service = OrchestrationAppService()
    names = {a["name"] for a in service.list_apis()}
    assert "remove_knowledge_graph_entities" in names


def test_ingest_with_prune_scope_optional(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    same = sample_graph_payload()
    out = service.ingest_knowledge_graph(
        "g1",
        same,
        sync_mode="upsert_only",
        prune_scope={"topic_ids": ["t1"]},
        force_delete=False,
    )
    assert out["validation_summary"]["ok"] is True
    assert "prune_result" not in out


def test_review_prompt_builds_session_queue_and_skips_served_concept(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1")
    service.append_learning_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c1", "result": "incorrect", "score": 25, "difficulty_bucket": "hard"},
    )
    service.append_learning_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c2", "result": "incorrect", "score": 35, "difficulty_bucket": "hard"},
    )

    first = service.get_review_prompt(plan["plan_id"])
    queue = first["context_summary"]["session_queue"]["items"]
    assert queue
    first_concept = queue[0]["concept_id"]

    second = service.get_review_prompt(
        plan["plan_id"],
        session_context={"served_concept_ids": [first_concept]},
    )
    second_current = second["context_summary"]["session_queue"]["current_item"]
    assert second_current is not None
    assert second_current["concept_id"] != first_concept


def test_review_prompt_without_session_context_skips_most_recent_reviewed_concept(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1")
    service.append_learning_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c1", "result": "incorrect", "score": 20, "difficulty_bucket": "hard"},
    )
    service.append_learning_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c2", "result": "incorrect", "score": 40, "difficulty_bucket": "hard"},
    )
    service.append_learning_record(
        plan["plan_id"],
        "review",
        {"concept_id": "c1", "result": "correct", "score": 88, "difficulty_bucket": "medium"},
    )

    prompt = service.get_review_prompt(plan["plan_id"])
    current = prompt["context_summary"]["session_queue"]["current_item"]
    if current:
        assert current["concept_id"] != "c1"
