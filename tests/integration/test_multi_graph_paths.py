from scripts.orchestration.orchestration_app_service import OrchestrationAppService
from tests.helpers import sample_graph_payload


def _payload_with_suffix(suffix: str) -> dict:
    payload = sample_graph_payload()
    payload["graph"]["graph_name"] = f"Python Basics {suffix}"
    payload["graph"]["release_tag"] = f"r1-{suffix}"

    for topic in payload["topics"]:
        topic["topic_id"] = f"{topic['topic_id']}-{suffix}"
        topic["topic_name"] = f"{topic['topic_name']}-{suffix}"

    for concept in payload["concepts"]:
        concept["concept_id"] = f"{concept['concept_id']}-{suffix}"
        concept["canonical_name"] = f"{concept['canonical_name']}-{suffix}"

    payload["topic_concepts"] = [
        {
            "topic_concept_id": f"tc1-{suffix}",
            "topic_id": f"t1-{suffix}",
            "concept_id": f"c1-{suffix}",
            "role": "core",
            "rank": 1,
        },
        {
            "topic_concept_id": f"tc2-{suffix}",
            "topic_id": f"t2-{suffix}",
            "concept_id": f"c2-{suffix}",
            "role": "core",
            "rank": 1,
        },
    ]
    payload["relations"] = [
        {
            "concept_relation_id": f"r1-{suffix}",
            "from_concept_id": f"c1-{suffix}",
            "to_concept_id": f"c2-{suffix}",
            "relation_type": "prerequisite_of",
        }
    ]
    payload["evidences"] = [
        {
            "evidence_id": f"e1-{suffix}",
            "source_type": "doc",
            "source_title": "Guide",
            "quote_text": "Variables are used before function logic.",
        }
    ]
    payload["relation_evidences"] = [
        {
            "relation_evidence_id": f"re1-{suffix}",
            "concept_relation_id": f"r1-{suffix}",
            "evidence_id": f"e1-{suffix}",
            "support_score": 0.9,
        }
    ]
    return payload


def test_multi_graph_listing_with_pagination(isolated_db):
    service = OrchestrationAppService()
    service.ingest_knowledge_graph("g-a", _payload_with_suffix("a"))
    service.ingest_knowledge_graph("g-b", _payload_with_suffix("b"))
    service.ingest_knowledge_graph("g-c", _payload_with_suffix("c"))

    first = service.list_knowledge_graphs(limit=2)
    assert len(first["items"]) == 2
    assert first["has_more"] is True
    assert first["cursor"] == "2"

    second = service.list_knowledge_graphs(limit=2, cursor=first["cursor"])
    assert len(second["items"]) == 1
    assert second["has_more"] is False
    assert second["cursor"] is None


def test_plan_and_prompt_stay_with_selected_graph_scope(isolated_db):
    service = OrchestrationAppService()
    service.ingest_knowledge_graph("g-a", _payload_with_suffix("a"))
    service.ingest_knowledge_graph("g-b", _payload_with_suffix("b"))

    plan_a = service.create_learning_plan("g-a", topic_id="t1-a")
    plan_b = service.create_learning_plan("g-b", topic_id="t1-b")

    prompt_a = service.get_learning_prompt(plan_a["plan_id"], topic_id="t1-a")
    prompt_b = service.get_learning_prompt(plan_b["plan_id"], topic_id="t1-b")

    text_a = prompt_a["prompt_text"]
    text_b = prompt_b["prompt_text"]
    assert "Variable-a" in text_a
    assert "Variable-b" not in text_a
    assert "Variable-b" in text_b
    assert "Variable-a" not in text_b


def test_reingest_same_graph_increments_revision(isolated_db):
    service = OrchestrationAppService()
    first = service.ingest_knowledge_graph("g-a", _payload_with_suffix("a"))
    second_payload = _payload_with_suffix("a2")
    second_payload["graph"]["release_tag"] = "r2-a"
    second = service.ingest_knowledge_graph("g-a", second_payload)

    assert first["version"] == 1
    assert second["version"] == 2
