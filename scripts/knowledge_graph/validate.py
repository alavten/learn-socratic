"""Validation logic for structured knowledge graph ingestion."""

from __future__ import annotations

from typing import Any

ALLOWED_RELATION_TYPES = {
    "prerequisite_of",
    "part_of",
    "contrast_with",
    "applied_in",
    "related_to",
}
ALLOWED_GRAPH_TYPES = {"domain", "module", "view"}


def validate_structured_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "errors": ["payload must be an object"],
            "warnings": [],
            "stats": {
                "concept_count": 0,
                "relation_count": 0,
                "evidence_count": 0,
                "relation_evidence_count": 0,
            },
        }

    required_sections = [
        "graph",
        "concepts",
        "relations",
        "evidences",
        "relation_evidences",
    ]
    missing_sections = [section for section in required_sections if section not in payload]
    if missing_sections:
        errors.append(f"payload missing required sections: {missing_sections}")

    # Guard against passing API envelope into payload_file.
    if "structured_payload" in payload and isinstance(payload.get("structured_payload"), dict):
        errors.append(
            "payload appears wrapped with graph_id/structured_payload envelope; "
            "payload_file must contain structured_payload object only"
        )

    graph = payload.get("graph")
    if graph is None or not isinstance(graph, dict):
        errors.append("payload.graph must be an object")
    else:
        for field in ["graph_type", "graph_name", "schema_version", "release_tag"]:
            if not graph.get(field):
                errors.append(f"payload.graph missing {field}")
        graph_type = graph.get("graph_type")
        if graph_type and graph_type not in ALLOWED_GRAPH_TYPES:
            allowed = ", ".join(sorted(ALLOWED_GRAPH_TYPES))
            errors.append(
                f"payload.graph graph_type '{graph_type}' is invalid, allowed: [{allowed}]"
            )

    concepts = payload.get("concepts", [])
    relations = payload.get("relations", [])
    evidences = payload.get("evidences", [])
    relation_evidences = payload.get("relation_evidences", [])
    topics = payload.get("topics", [])
    topic_concepts = payload.get("topic_concepts", [])

    if not isinstance(concepts, list):
        errors.append("payload.concepts must be an array")
        concepts = []
    if not isinstance(relations, list):
        errors.append("payload.relations must be an array")
        relations = []
    if not isinstance(evidences, list):
        errors.append("payload.evidences must be an array")
        evidences = []
    if not isinstance(relation_evidences, list):
        errors.append("payload.relation_evidences must be an array")
        relation_evidences = []
    if not isinstance(topics, list):
        errors.append("payload.topics must be an array")
        topics = []
    if not isinstance(topic_concepts, list):
        errors.append("payload.topic_concepts must be an array")
        topic_concepts = []

    concept_ids = {c.get("concept_id") for c in concepts if c.get("concept_id")}
    relation_ids = {r.get("concept_relation_id") for r in relations if r.get("concept_relation_id")}
    evidence_ids = {e.get("evidence_id") for e in evidences if e.get("evidence_id")}
    topic_ids = {t.get("topic_id") for t in topics if t.get("topic_id")}

    for idx, concept in enumerate(concepts):
        if not isinstance(concept, dict):
            errors.append(f"concept[{idx}] must be an object")
            continue
        if not concept.get("concept_id"):
            errors.append(f"concept[{idx}] missing concept_id")
        if not concept.get("canonical_name"):
            errors.append(f"concept[{idx}] missing canonical_name")
        if not concept.get("definition"):
            errors.append(f"concept[{idx}] missing definition")

    for idx, topic in enumerate(topics):
        if not isinstance(topic, dict):
            errors.append(f"topic[{idx}] must be an object")
            continue
        if not topic.get("topic_id"):
            errors.append(f"topic[{idx}] missing topic_id")
        if not topic.get("topic_name"):
            errors.append(f"topic[{idx}] missing topic_name")

    for idx, relation in enumerate(relations):
        if not isinstance(relation, dict):
            errors.append(f"relation[{idx}] must be an object")
            continue
        from_id = relation.get("from_concept_id")
        to_id = relation.get("to_concept_id")
        relation_type = relation.get("relation_type", "related_to")
        if not relation.get("concept_relation_id"):
            errors.append(f"relation[{idx}] missing concept_relation_id")
        if from_id not in concept_ids:
            errors.append(f"relation[{idx}] from_concept_id not found in payload concepts")
        if to_id not in concept_ids:
            errors.append(f"relation[{idx}] to_concept_id not found in payload concepts")
        if from_id == to_id:
            errors.append(f"relation[{idx}] self-loop is not allowed")
        if relation_type not in ALLOWED_RELATION_TYPES:
            allowed = ", ".join(sorted(ALLOWED_RELATION_TYPES))
            errors.append(
                f"relation[{idx}] invalid relation_type '{relation_type}', allowed: [{allowed}]"
            )

    for idx, evidence in enumerate(evidences):
        if not isinstance(evidence, dict):
            errors.append(f"evidence[{idx}] must be an object")
            continue
        if not evidence.get("evidence_id"):
            errors.append(f"evidence[{idx}] missing evidence_id")
        if not evidence.get("quote_text"):
            errors.append(f"evidence[{idx}] missing quote_text")

    for idx, tc in enumerate(topic_concepts):
        if not isinstance(tc, dict):
            errors.append(f"topic_concept[{idx}] must be an object")
            continue
        if not tc.get("topic_concept_id"):
            errors.append(f"topic_concept[{idx}] missing topic_concept_id")
        if topic_ids and tc.get("topic_id") not in topic_ids:
            errors.append(f"topic_concept[{idx}] topic_id not found in payload topics")
        if tc.get("concept_id") not in concept_ids:
            errors.append(f"topic_concept[{idx}] concept_id not found in payload concepts")

    relation_evidence_map: dict[str, int] = {}
    for idx, re_item in enumerate(relation_evidences):
        if not isinstance(re_item, dict):
            errors.append(f"relation_evidence[{idx}] must be an object")
            continue
        if not re_item.get("relation_evidence_id"):
            errors.append(f"relation_evidence[{idx}] missing relation_evidence_id")
        relation_id = re_item.get("concept_relation_id")
        evidence_id = re_item.get("evidence_id")
        if relation_id not in relation_ids:
            errors.append(f"relation_evidence[{idx}] relation not found in payload relations")
        if evidence_id not in evidence_ids:
            errors.append(f"relation_evidence[{idx}] evidence not found in payload evidences")
        if relation_id:
            relation_evidence_map[relation_id] = relation_evidence_map.get(relation_id, 0) + 1

    # Publish-ready constraint: each relation must have at least one evidence.
    for relation_id in relation_ids:
        if relation_evidence_map.get(relation_id, 0) < 1:
            errors.append(f"relation {relation_id} has no evidence link")

    if not payload.get("topics"):
        warnings.append("payload has no topics; graph is queryable but may not be navigable by topic")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "concept_count": len(concepts),
            "relation_count": len(relations),
            "evidence_count": len(evidences),
            "relation_evidence_count": len(relation_evidences),
        },
    }
