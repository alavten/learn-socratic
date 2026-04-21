import pytest

from scripts.knowledge_graph.validate import validate_structured_payload
from tests.helpers import sample_graph_payload


def test_validate_success_payload():
    payload = sample_graph_payload()
    result = validate_structured_payload(payload)
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["stats"]["concept_count"] == 2


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (
            lambda p: p["concepts"].__setitem__(
                0, {k: v for k, v in p["concepts"][0].items() if k != "concept_id"}
            ),
            "concept[0] missing concept_id",
        ),
        (
            lambda p: p["concepts"].__setitem__(
                0, {k: v for k, v in p["concepts"][0].items() if k != "canonical_name"}
            ),
            "concept[0] missing canonical_name",
        ),
        (
            lambda p: p["concepts"].__setitem__(
                0, {k: v for k, v in p["concepts"][0].items() if k != "definition"}
            ),
            "concept[0] missing definition",
        ),
    ],
)
def test_validate_concept_required_fields(mutator, expected_error):
    payload = sample_graph_payload()
    mutator(payload)
    result = validate_structured_payload(payload)
    assert result["ok"] is False
    assert expected_error in result["errors"]


def test_validate_relation_self_loop():
    payload = sample_graph_payload()
    payload["relations"][0]["from_concept_id"] = "c1"
    payload["relations"][0]["to_concept_id"] = "c1"

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "relation[0] self-loop is not allowed" in result["errors"]


def test_validate_relation_missing_references():
    payload = sample_graph_payload()
    payload["relations"][0]["from_concept_id"] = "missing"
    payload["relations"][0]["to_concept_id"] = "missing2"

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "relation[0] from_concept_id not found in payload concepts" in result["errors"]
    assert "relation[0] to_concept_id not found in payload concepts" in result["errors"]


def test_validate_relation_evidence_missing_relation():
    payload = sample_graph_payload()
    payload["relation_evidences"][0]["concept_relation_id"] = "r-missing"

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "relation_evidence[0] relation not found in payload relations" in result["errors"]


def test_validate_relation_evidence_missing_evidence():
    payload = sample_graph_payload()
    payload["relation_evidences"][0]["evidence_id"] = "e-missing"

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "relation_evidence[0] evidence not found in payload evidences" in result["errors"]


def test_validate_warns_when_topics_missing():
    payload = sample_graph_payload()
    payload["topics"] = []

    result = validate_structured_payload(payload)

    assert result["ok"] is True
    assert result["warnings"] == [
        "payload has no topics; graph is queryable but may not be navigable by topic"
    ]


def test_validate_relation_requires_at_least_one_evidence_link():
    payload = sample_graph_payload()
    payload["relation_evidences"] = []

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "relation r1 has no evidence link" in result["errors"]
