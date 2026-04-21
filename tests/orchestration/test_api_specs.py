from scripts.orchestration.orchestration_app_service import API_SPECS, OrchestrationAppService


def test_list_apis_and_specs_are_consistent(isolated_db):
    service = OrchestrationAppService()
    listed = service.list_apis()
    listed_names = {item["name"] for item in listed}
    spec_names = set(API_SPECS.keys())
    assert listed_names == spec_names

    for name in spec_names:
        spec = service.get_api_spec(name)
        assert spec["name"] == name
        assert "input_schema" in spec
