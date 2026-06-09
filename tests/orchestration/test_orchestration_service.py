import pytest

from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.orchestration.orchestration_app_service import OrchestrationAppService
from tests.helpers import sample_graph_payload


def test_api_self_description(isolated_db):
    service = OrchestrationAppService()
    apis = service.list_apis()
    names = [item["name"] for item in apis]
    assert "get-api-spec" in names
    spec = service.get_api_spec("create-learning-plan")
    assert spec["name"] == "create-learning-plan"
    assert "required" in spec["input_schema"]
    assert "valid_payloads" in spec["examples"]
    get_graph_spec = service.get_api_spec("get-knowledge-graph")
    assert "output_schema" in get_graph_spec
    assert "concept_briefs" in get_graph_spec["output_schema"]["properties"]
    discovery_spec = service.get_api_spec("get-discovery-context")
    assert discovery_spec["name"] == "get-discovery-context"
    assert "get-mastery-diagnostics" in names
    diag_spec = service.get_api_spec("get-mastery-diagnostics")
    assert "plan_id" in diag_spec["input_schema"]["required"]


def test_get_api_spec_rejects_snake_case_with_hint(isolated_db):
    service = OrchestrationAppService()
    with pytest.raises(ValueError, match="unknown_api: create_learning_plan"):
        service.get_api_spec("create_learning_plan")


def test_prompt_generation_and_record_commit(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")
    learn_prompt = service.get_learn_context(plan["plan_id"], topic_id="t1")
    assert "prompt_text" in learn_prompt
    assert learn_prompt["context_summary"]["session_queue"]["current_item"]["concept_id"] == "c1"
    commit = service.add_interaction_record(
        plan["plan_id"],
        "learn",
        {"concept_id": "c1", "result": "ok", "score": 80, "difficulty_bucket": "easy"},
    )
    assert "state_delta_summary" in commit


def test_learn_context_skips_learned_concepts_without_session_context(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")
    service.add_interaction_record(
        plan["plan_id"],
        "learn",
        {"concept_id": "c1", "result": "ok", "score": 80, "difficulty_bucket": "easy"},
    )

    prompt = service.get_learn_context(plan["plan_id"], topic_id="t1")
    current = prompt["context_summary"]["session_queue"]["current_item"]
    assert current is None


def test_learn_context_respects_served_concept_ids_in_session_context(isolated_db):
    from tests.helpers import multi_concept_graph_payload

    ingest_knowledge_graph("g-multi", multi_concept_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g-multi", topic_id="t1")

    first = service.get_learn_context(plan["plan_id"])
    first_concept = first["context_summary"]["session_queue"]["current_item"]["concept_id"]

    second = service.get_learn_context(
        plan["plan_id"],
        session_context={
            "served_concept_ids": [first_concept],
            "last_completed_concept_id": first_concept,
            "last_result": "ok",
        },
    )
    second_current = second["context_summary"]["session_queue"]["current_item"]
    assert second_current is not None
    assert second_current["concept_id"] != first_concept
    assert second_current["topic_id"] == "t1"


def test_learn_context_suggests_extend_when_chapter_queue_exhausted(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")
    service.add_interaction_record(
        plan["plan_id"],
        "learn",
        {"concept_id": "c1", "result": "ok", "score": 85, "difficulty_bucket": "medium"},
    )

    prompt = service.get_learn_context(plan["plan_id"], topic_id="t1")
    summary = prompt["context_summary"]
    assert summary["session_queue"]["current_item"] is None
    assert summary["chapter_progress"]["next_topic_id"] == "t2"
    assert summary["suggested_plan_action"]["action"] == "extend_learning_plan_topics"
    assert summary["suggested_plan_action"]["topic_ids"] == ["t2"]
    assert "extend_learning_plan_topics" in prompt["prompt_text"]


def test_get_mastery_diagnostics_orchestration(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")
    service.add_interaction_record(
        plan["plan_id"],
        "learn",
        {"concept_id": "c1", "result": "ok", "score": 75},
    )
    diag = service.get_mastery_diagnostics(plan["plan_id"], topic_id="t1")
    assert diag["scope"]["kind"] == "topic"
    assert diag["summary"]["concepts_with_state"] >= 1


def test_remove_knowledge_graph_entities_api_listed(isolated_db):
    service = OrchestrationAppService()
    names = {a["name"] for a in service.list_apis()}
    assert "remove-knowledge-graph-entities" in names


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


def test_quiz_context_resolves_pacing_and_next_session_context(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")

    default_quiz = service.get_quiz_context(plan["plan_id"], topic_id="t1")
    summary = default_quiz["context_summary"]
    assert summary["quiz_pacing"] == "per_concept"
    assert summary["suggested_batch_size"] == 1
    assert "next_session_context" in summary
    assert "per_concept" in default_quiz["prompt_text"]

    batch_quiz = service.get_quiz_context(
        plan["plan_id"],
        topic_id="t1",
        session_context={"quiz_pacing": "per_chapter", "batch_size": 4},
    )
    batch_summary = batch_quiz["context_summary"]
    assert batch_summary["quiz_pacing"] == "per_chapter"
    assert batch_summary["suggested_batch_size"] == 4
    assert batch_summary["next_session_context"]["quiz_pacing"] == "per_chapter"
    assert "per_chapter" in batch_quiz["prompt_text"]


def test_review_prompt_builds_session_queue_and_skips_served_concept(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1")
    service.add_interaction_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c1", "result": "incorrect", "score": 25, "difficulty_bucket": "hard"},
    )
    service.add_interaction_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c2", "result": "incorrect", "score": 35, "difficulty_bucket": "hard"},
    )

    first = service.get_review_context(plan["plan_id"])
    queue = first["context_summary"]["session_queue"]["items"]
    assert queue
    first_concept = queue[0]["concept_id"]

    second = service.get_review_context(
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
    service.add_interaction_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c1", "result": "incorrect", "score": 20, "difficulty_bucket": "hard"},
    )
    service.add_interaction_record(
        plan["plan_id"],
        "quiz",
        {"concept_id": "c2", "result": "incorrect", "score": 40, "difficulty_bucket": "hard"},
    )
    service.add_interaction_record(
        plan["plan_id"],
        "review",
        {"concept_id": "c1", "result": "correct", "score": 88, "difficulty_bucket": "medium"},
    )

    prompt = service.get_review_context(plan["plan_id"])
    current = prompt["context_summary"]["session_queue"]["current_item"]
    if current:
        assert current["concept_id"] != "c1"


def test_get_discovery_context_returns_dual_tables_with_topic_content(isolated_db):
    ingest_knowledge_graph("g1", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g1", topic_id="t1")
    service.add_interaction_record(
        plan["plan_id"],
        "learn",
        {"concept_id": "c1", "result": "ok", "score": 80, "difficulty_bucket": "medium"},
    )
    payload = service.get_discovery_context(page_limit=10, max_pages=5)
    assert payload["discovery_snapshot"]["source"] == "api_discovery"
    assert "KnowledgeGraphs" in payload["display_markdown"]
    assert "PendingLearningPlans" in payload["display_markdown"]
    assert "主题内容" in payload["tables"]["knowledge_graphs_table"]
    assert "主题内容" in payload["tables"]["pending_learning_plans_table"]
    assert "已完成任务" in payload["tables"]["pending_learning_plans_table"]
    assert "待完成任务" in payload["tables"]["pending_learning_plans_table"]
