import pytest

from scripts.orchestration.orchestration_app_service import (
    OrchestrationAppService,
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
