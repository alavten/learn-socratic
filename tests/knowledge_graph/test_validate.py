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


def test_validate_relation_type_must_be_allowed_value():
    payload = sample_graph_payload()
    payload["relations"][0]["relation_type"] = "constrains"

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "relation[0] invalid relation_type 'constrains'" in " ".join(result["errors"])


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


def test_validate_evidence_requires_quote_text():
    payload = sample_graph_payload()
    payload["evidences"][0].pop("quote_text")

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "evidence[0] missing quote_text" in result["errors"]


def test_validate_topic_concept_requires_topic_concept_id():
    payload = sample_graph_payload()
    payload["topic_concepts"][0].pop("topic_concept_id")

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "topic_concept[0] missing topic_concept_id" in result["errors"]


def test_validate_relation_evidence_requires_relation_evidence_id():
    payload = sample_graph_payload()
    payload["relation_evidences"][0].pop("relation_evidence_id")

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "relation_evidence[0] missing relation_evidence_id" in result["errors"]


def test_validate_rejects_api_envelope_wrapper():
    payload = {
        "graph_id": "g1",
        "structured_payload": sample_graph_payload(),
    }

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "payload appears wrapped with graph_id/structured_payload envelope" in " ".join(result["errors"])


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


def test_validate_topic_requires_topic_type():
    payload = sample_graph_payload()
    payload["topics"][0].pop("topic_type")

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    joined = " ".join(result["errors"])
    assert "topic[0] missing topic_type" in joined
    assert "chapter" in joined and "section" in joined


def test_validate_topic_type_must_be_allowed_value():
    payload = sample_graph_payload()
    payload["topics"][0]["topic_type"] = "Chapter"

    result = validate_structured_payload(payload)

    assert result["ok"] is False
    assert "topic[0] invalid topic_type 'Chapter'" in " ".join(result["errors"])


def test_validate_section_root_topic_emits_warning():
    payload = sample_graph_payload()
    payload["topics"][0]["topic_type"] = "section"
    payload["topics"][0]["parent_topic_id"] = None

    result = validate_structured_payload(payload)

    assert result["ok"] is True
    joined = " ".join(result["warnings"])
    assert "root topic has topic_type='section'" in joined


def test_validate_chapter_under_section_emits_warning():
    payload = sample_graph_payload()
    payload["topics"][0]["topic_type"] = "section"
    payload["topics"][1]["topic_type"] = "chapter"
    payload["topics"][1]["parent_topic_id"] = "t1"

    result = validate_structured_payload(payload)

    assert result["ok"] is True
    joined = " ".join(result["warnings"])
    assert "chapters should not be nested under sections" in joined
