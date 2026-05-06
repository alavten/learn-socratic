import pytest

from scripts.orchestration.orchestration_app_service import (
    OrchestrationAppService,
    PayloadValidationError,
    call_api,
)


def test_call_api_unknown_name_raises():
    service = OrchestrationAppService()
    with pytest.raises(ValueError, match="unknown_api"):
        call_api(service, "not_exists", {})


def test_call_api_dispatches_to_bound_method(monkeypatch):
    service = OrchestrationAppService()
    monkeypatch.setattr(service, "list_apis", lambda: [{"name": "patched"}])
    result = call_api(service, "list_apis", {})
    assert result == [{"name": "patched"}]


def test_get_api_spec_unknown_raises():
    service = OrchestrationAppService()
    with pytest.raises(ValueError, match="unknown_api"):
        service.get_api_spec("x_unknown")


@pytest.mark.parametrize(
    ("api_name", "payload", "field_path", "error_code"),
    [
        ("create_learning_plan", {}, "$", "invalid_payload_schema"),
        ("create_learning_plan", {"graph_id": "g1", "extra": True}, "$", "invalid_payload_schema"),
        ("add_interaction_record", {"plan_id": "p1", "mode": "bad", "record_payload": {"concept_id": "c1"}}, "$.mode", "invalid_payload_schema"),
        ("add_interaction_record", {"plan_id": "p1", "mode": "learn", "record_payload": {"concept_id": "c1", "latency_ms": -1}}, "$.record_payload.latency_ms", "invalid_payload_schema"),
        ("remove_knowledge_graph_entities", {"graph_id": "g1", "remove_payload": {"concept_ids": "c1"}}, "$.remove_payload.concept_ids", "invalid_payload_schema"),
        (
            "ingest_knowledge_graph",
            {
                "graph_id": "g1",
                "structured_payload": {
                    "graph": {
                        "graph_type": "curriculum",
                        "graph_name": "x",
                        "schema_version": "1.0.0",
                        "release_tag": "r1",
                    },
                    "concepts": [],
                    "relations": [],
                    "evidences": [],
                    "relation_evidences": [],
                },
            },
            "$.structured_payload.graph.graph_type",
            "invalid_payload_schema",
        ),
    ],
)
def test_call_api_rejects_invalid_payloads(api_name, payload, field_path, error_code):
    service = OrchestrationAppService()
    with pytest.raises(PayloadValidationError) as exc_info:
        call_api(service, api_name, payload)
    details = exc_info.value.details
    assert details["error_code"] == error_code
    assert details["field_path"] == field_path
    assert details["api_name"] == api_name
