from scripts.knowledge_graph.api import ingest_knowledge_graph
from scripts.learning.api import get_learn_context_data
from scripts.orchestration.orchestration_app_service import OrchestrationAppService
from tests.helpers import sample_graph_payload


def test_get_learn_context_data_orders_concepts_by_topic_rank(isolated_db):
    payload = sample_graph_payload()
    payload["concepts"].append(
        {
            "concept_id": "c3",
            "canonical_name": "AAA-first-alphabetically",
            "definition": "Ranked second in topic.",
            "concept_type": "fundamental",
            "difficulty_level": "easy",
        }
    )
    payload["topic_concepts"].append(
        {
            "topic_concept_id": "tc3",
            "topic_id": "t1",
            "concept_id": "c3",
            "role": "core",
            "rank": 2,
        }
    )
    ingest_knowledge_graph("g-learn-order", payload)
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g-learn-order", topic_id="t1")

    data = get_learn_context_data(plan["plan_id"], topic_id="t1")
    ids = [item["concept_id"] for item in data["ordered_concepts"]]
    assert ids == ["c1", "c3"]


def test_sequential_learn_queue_covers_all_graph_concepts(isolated_db):
    ingest_knowledge_graph("g-seq", sample_graph_payload())
    service = OrchestrationAppService()
    plan = service.create_learning_plan("g-seq")
    plan_id = plan["plan_id"]
    served: list[str] = []

    for _ in range(4):
        prompt = service.get_learn_context(
            plan_id,
            session_context={
                "served_concept_ids": served,
                "last_completed_concept_id": served[-1] if served else None,
                "last_result": "ok" if served else None,
            }
            if served
            else None,
        )
        current = prompt["context_summary"]["session_queue"]["current_item"]
        if not current:
            break
        concept_id = current["concept_id"]
        service.add_interaction_record(
            plan_id,
            "learn",
            {"concept_id": concept_id, "result": "ok", "score": 80, "difficulty_bucket": "medium"},
        )
        served.append(concept_id)

    assert set(served) == {"c1", "c2"}
