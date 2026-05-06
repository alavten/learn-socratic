import inspect

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


def test_schema_properties_align_with_public_service_signatures():
    public_methods = {
        name: getattr(OrchestrationAppService, name)
        for name in API_SPECS.keys()
        if hasattr(OrchestrationAppService, name)
    }
    assert set(public_methods.keys()) == set(API_SPECS.keys())

    for api_name, method in public_methods.items():
        schema = API_SPECS[api_name]["input_schema"]
        properties = set((schema.get("properties") or {}).keys())
        required = set(schema.get("required") or [])
        signature = inspect.signature(method)
        parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.name != "self"
        ]
        param_names = {parameter.name for parameter in parameters}
        required_params = {
            parameter.name
            for parameter in parameters
            if parameter.default is inspect.Signature.empty
        }

        assert param_names == properties, f"{api_name} schema/params mismatch: props={properties}, params={param_names}"
        assert required == required_params, f"{api_name} required mismatch: required={required}, params_required={required_params}"
        assert schema.get("additionalProperties") is False
