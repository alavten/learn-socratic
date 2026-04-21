import pytest

from scripts.orchestration.orchestration_app_service import (
    OrchestrationAppService,
    call_api,
)
from tests.helpers import sample_graph_payload


def test_ingest_fails_when_relation_has_no_evidence(isolated_db):
    service = OrchestrationAppService()
    payload = sample_graph_payload()
    payload["relation_evidences"] = []

    result = service.ingest_knowledge_graph("g1", payload)

    assert result["validation_summary"]["ok"] is False
    assert "has no evidence link" in " ".join(result["validation_summary"]["errors"])


def test_ingest_fails_when_relation_type_is_not_supported(isolated_db):
    service = OrchestrationAppService()
    payload = sample_graph_payload()
    payload["relations"][0]["relation_type"] = "constrains"

    result = service.ingest_knowledge_graph("g1", payload)

    assert result["validation_summary"]["ok"] is False
    assert "invalid relation_type 'constrains'" in " ".join(result["validation_summary"]["errors"])


def test_get_learning_prompt_with_unknown_plan_returns_error_context(isolated_db):
    service = OrchestrationAppService()

    response = service.get_learning_prompt("missing-plan")

    assert "prompt_text" in response
    assert response["context_summary"]["error"] == "plan_not_found"


def test_call_api_missing_required_field_raises_value_error(isolated_db):
    service = OrchestrationAppService()
    service.ingest_knowledge_graph("g1", sample_graph_payload())

    with pytest.raises(ValueError):
        call_api(service, "create_learning_plan", {})


def test_append_learning_record_invalid_mode_raises_value_error(isolated_db):
    service = OrchestrationAppService()
    service.ingest_knowledge_graph("g1", sample_graph_payload())
    plan = service.create_learning_plan("g1", topic_id="t1")

    with pytest.raises(ValueError):
        service.append_learning_record(
            plan["plan_id"],
            "invalid_mode",
            {"concept_id": "c1", "score": 80},
        )
