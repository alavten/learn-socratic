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
