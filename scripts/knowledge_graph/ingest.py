"""Ingestion pipeline for structured graph payloads."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from scripts.foundation.storage import transaction
from scripts.knowledge_graph.validate import validate_structured_payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ingest_knowledge_graph(graph_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_structured_payload(payload)
    if not validation["ok"]:
        return {
            "graph_id": graph_id,
            "version": None,
            "change_summary": {},
            "validation_summary": validation,
            "detail": {"failed_items": validation["errors"]},
        }

    now = _now()
    graph = payload.get("graph", {})
    topics = payload.get("topics", [])
    concepts = payload.get("concepts", [])
    topic_concepts = payload.get("topic_concepts", [])
    relations = payload.get("relations", [])
    evidences = payload.get("evidences", [])
    relation_evidences = payload.get("relation_evidences", [])

    try:
        with transaction() as conn:
            existing_graph = conn.execute(
                "SELECT revision FROM Graph WHERE graphId = ?",
                (graph_id,),
            ).fetchone()
            revision = (existing_graph["revision"] + 1) if existing_graph else 1

            conn.execute(
                """
                INSERT INTO Graph(
                    graphId, parentGraphId, graphType, graphName, purpose, owner,
                    schemaVersion, schemaReleasedAt, releaseTag, releasedAt, revision, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(graphId) DO UPDATE SET
                    parentGraphId=excluded.parentGraphId,
                    graphType=excluded.graphType,
                    graphName=excluded.graphName,
                    purpose=excluded.purpose,
                    owner=excluded.owner,
                    schemaVersion=excluded.schemaVersion,
                    schemaReleasedAt=excluded.schemaReleasedAt,
                    releaseTag=excluded.releaseTag,
                    releasedAt=excluded.releasedAt,
                    revision=excluded.revision,
                    status=excluded.status
                """,
                (
                    graph_id,
                    graph.get("parent_graph_id"),
                    graph.get("graph_type", "domain"),
                    graph.get("graph_name", graph_id),
                    graph.get("purpose"),
                    graph.get("owner"),
                    graph.get("schema_version", "1.0.0"),
                    graph.get("schema_released_at", now),
                    graph.get("release_tag", f"r{revision}"),
                    now,
                    revision,
                    graph.get("status", "active"),
                ),
            )

            for topic in topics:
                conn.execute(
                    """
                    INSERT INTO Topic(topicId, graphId, parentTopicId, topicName, topicType, sortOrder, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(topicId) DO UPDATE SET
                        graphId=excluded.graphId,
                        parentTopicId=excluded.parentTopicId,
                        topicName=excluded.topicName,
                        topicType=excluded.topicType,
                        sortOrder=excluded.sortOrder,
                        status=excluded.status
                    """,
                    (
                        topic["topic_id"],
                        graph_id,
                        topic.get("parent_topic_id"),
                        topic["topic_name"],
                        topic.get("topic_type", "section"),
                        topic.get("sort_order", 0),
                        topic.get("status", "active"),
                    ),
                )

            for concept in concepts:
                conn.execute(
                    """
                    INSERT INTO Concept(
                        conceptId, graphId, conceptType, canonicalName, definition, language,
                        difficultyLevel, dr, drtime, status, createdAt, updatedAt
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(conceptId) DO UPDATE SET
                        graphId=excluded.graphId,
                        conceptType=excluded.conceptType,
                        canonicalName=excluded.canonicalName,
                        definition=excluded.definition,
                        language=excluded.language,
                        difficultyLevel=excluded.difficultyLevel,
                        dr=excluded.dr,
                        drtime=excluded.drtime,
                        status=excluded.status,
                        updatedAt=excluded.updatedAt
                    """,
                    (
                        concept["concept_id"],
                        graph_id,
                        concept.get("concept_type", "concept"),
                        concept["canonical_name"],
                        concept["definition"],
                        concept.get("language", "zh-CN"),
                        concept.get("difficulty_level", "medium"),
                        int(concept.get("dr", False)),
                        concept.get("drtime"),
                        concept.get("status", "active"),
                        concept.get("created_at", now),
                        now,
                    ),
                )

            for rel in relations:
                conn.execute(
                    """
                    INSERT INTO ConceptRelation(
                        conceptRelationId, graphId, fromConceptId, toConceptId, relationType,
                        directionality, weight, confidence, dr, drtime, status, createdAt, updatedAt
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(conceptRelationId) DO UPDATE SET
                        graphId=excluded.graphId,
                        fromConceptId=excluded.fromConceptId,
                        toConceptId=excluded.toConceptId,
                        relationType=excluded.relationType,
                        directionality=excluded.directionality,
                        weight=excluded.weight,
                        confidence=excluded.confidence,
                        dr=excluded.dr,
                        drtime=excluded.drtime,
                        status=excluded.status,
                        updatedAt=excluded.updatedAt
                    """,
                    (
                        rel["concept_relation_id"],
                        graph_id,
                        rel["from_concept_id"],
                        rel["to_concept_id"],
                        rel.get("relation_type", "related_to"),
                        rel.get("directionality", "directed"),
                        rel.get("weight", 1.0),
                        rel.get("confidence", 0.7),
                        int(rel.get("dr", False)),
                        rel.get("drtime"),
                        rel.get("status", "active"),
                        rel.get("created_at", now),
                        now,
                    ),
                )

            for evidence in evidences:
                conn.execute(
                    """
                    INSERT INTO Evidence(
                        evidenceId, sourceType, sourceTitle, sourceUri, sourceChecksum,
                        sourceIndexedAt, locator, quoteText, note, capturedAt
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(evidenceId) DO UPDATE SET
                        sourceType=excluded.sourceType,
                        sourceTitle=excluded.sourceTitle,
                        sourceUri=excluded.sourceUri,
                        sourceChecksum=excluded.sourceChecksum,
                        sourceIndexedAt=excluded.sourceIndexedAt,
                        locator=excluded.locator,
                        quoteText=excluded.quoteText,
                        note=excluded.note,
                        capturedAt=excluded.capturedAt
                    """,
                    (
                        evidence["evidence_id"],
                        evidence.get("source_type", "doc"),
                        evidence.get("source_title"),
                        evidence.get("source_uri"),
                        evidence.get("source_checksum"),
                        evidence.get("source_indexed_at", now),
                        evidence.get("locator"),
                        evidence["quote_text"],
                        evidence.get("note"),
                        evidence.get("captured_at", now),
                    ),
                )

            for tc in topic_concepts:
                conn.execute(
                    """
                    INSERT INTO TopicConcept(
                        topicConceptId, topicId, conceptId, role, aliasText, aliasType,
                        aliasLanguage, aliasStatus, rank, validFrom, validTo
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(topicConceptId) DO UPDATE SET
                        topicId=excluded.topicId,
                        conceptId=excluded.conceptId,
                        role=excluded.role,
                        aliasText=excluded.aliasText,
                        aliasType=excluded.aliasType,
                        aliasLanguage=excluded.aliasLanguage,
                        aliasStatus=excluded.aliasStatus,
                        rank=excluded.rank,
                        validFrom=excluded.validFrom,
                        validTo=excluded.validTo
                    """,
                    (
                        tc["topic_concept_id"],
                        tc["topic_id"],
                        tc["concept_id"],
                        tc.get("role", "core"),
                        tc.get("alias_text"),
                        tc.get("alias_type"),
                        tc.get("alias_language"),
                        tc.get("alias_status"),
                        tc.get("rank", 0),
                        tc.get("valid_from"),
                        tc.get("valid_to"),
                    ),
                )

            for rel_evi in relation_evidences:
                conn.execute(
                    """
                    INSERT INTO RelationEvidence(
                        relationEvidenceId, conceptRelationId, evidenceId, supportScore, evidenceRole
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(relationEvidenceId) DO UPDATE SET
                        conceptRelationId=excluded.conceptRelationId,
                        evidenceId=excluded.evidenceId,
                        supportScore=excluded.supportScore,
                        evidenceRole=excluded.evidenceRole
                    """,
                    (
                        rel_evi["relation_evidence_id"],
                        rel_evi["concept_relation_id"],
                        rel_evi["evidence_id"],
                        rel_evi.get("support_score", 0.7),
                        rel_evi.get("evidence_role", "primary"),
                    ),
                )

    except sqlite3.IntegrityError as exc:
        # Keep ingest recoverable for user-driven payload repair loops.
        constraint_error = f"database constraint failed: {exc}"
        return {
            "graph_id": graph_id,
            "version": None,
            "change_summary": {},
            "validation_summary": {
                "ok": False,
                "errors": [constraint_error],
                "warnings": validation.get("warnings", []),
                "stats": validation.get("stats", {}),
            },
            "detail": {"failed_items": [constraint_error]},
        }

    return {
        "graph_id": graph_id,
        "version": revision,
        "change_summary": {
            "topics_upserted": len(topics),
            "concepts_upserted": len(concepts),
            "relations_upserted": len(relations),
            "evidences_upserted": len(evidences),
            "relation_evidence_upserted": len(relation_evidences),
            "topic_concepts_upserted": len(topic_concepts),
        },
        "validation_summary": validation,
    }
