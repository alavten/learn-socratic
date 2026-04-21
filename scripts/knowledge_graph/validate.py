"""Validation logic for structured knowledge graph ingestion."""

from __future__ import annotations

from typing import Any


def validate_structured_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    concepts = payload.get("concepts", [])
    relations = payload.get("relations", [])
    evidences = payload.get("evidences", [])
    relation_evidences = payload.get("relation_evidences", [])

    concept_ids = {c.get("concept_id") for c in concepts if c.get("concept_id")}
    relation_ids = {r.get("concept_relation_id") for r in relations if r.get("concept_relation_id")}
    evidence_ids = {e.get("evidence_id") for e in evidences if e.get("evidence_id")}

    for idx, concept in enumerate(concepts):
        if not concept.get("concept_id"):
            errors.append(f"concept[{idx}] missing concept_id")
        if not concept.get("canonical_name"):
            errors.append(f"concept[{idx}] missing canonical_name")
        if not concept.get("definition"):
            errors.append(f"concept[{idx}] missing definition")

    for idx, relation in enumerate(relations):
        from_id = relation.get("from_concept_id")
        to_id = relation.get("to_concept_id")
        if not relation.get("concept_relation_id"):
            errors.append(f"relation[{idx}] missing concept_relation_id")
        if from_id not in concept_ids:
            errors.append(f"relation[{idx}] from_concept_id not found in payload concepts")
        if to_id not in concept_ids:
            errors.append(f"relation[{idx}] to_concept_id not found in payload concepts")
        if from_id == to_id:
            errors.append(f"relation[{idx}] self-loop is not allowed")

    relation_evidence_map: dict[str, int] = {}
    for idx, re_item in enumerate(relation_evidences):
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
