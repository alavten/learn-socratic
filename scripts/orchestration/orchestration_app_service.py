"""Orchestration application service and API self-description."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from jsonschema import Draft7Validator

from scripts.foundation.logger import get_logger, log_event
from scripts.foundation.storage import run_migrations
from scripts.knowledge_graph import api as kg_api
from scripts.knowledge_graph.store import collect_topic_ids_with_descendants
from scripts.learning import api as learning_api
from scripts.orchestration.prompt_templates import build_prompt


logger = get_logger("doc_socratic.orchestration")


class PayloadValidationError(ValueError):
    """Structured payload validation error for API dispatch."""

    def __init__(self, details: dict[str, Any]) -> None:
        self.details = details
        super().__init__(details.get("message", "invalid_payload"))


API_SPECS: dict[str, dict[str, Any]] = {
    "list_apis": {
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "summary": "List callable APIs",
        "tags": ["meta"],
        "stability": "stable",
    },
    "get_api_spec": {
        "input_schema": {
            "type": "object",
            "required": ["api_name"],
            "properties": {"api_name": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        },
        "summary": "Get API input schema",
        "tags": ["meta"],
        "stability": "stable",
    },
    "list_knowledge_graphs": {
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1},
                "offset": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "summary": "List graph metadata",
        "tags": ["kg"],
        "stability": "stable",
    },
    "get_knowledge_graph": {
        "input_schema": {
            "type": "object",
            "required": ["graph_id"],
            "properties": {
                "graph_id": {"type": "string", "minLength": 1},
                "topic_id": {"type": "string"},
                "concept_limit": {"type": "integer", "minimum": 1},
                "offset": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "required": ["graph", "topics", "topic_concepts", "concept_briefs", "has_more", "next_offset"],
            "properties": {
                "graph": {"type": "object"},
                "topics": {"type": "array", "items": {"type": "object"}},
                "topic_concepts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "topic_concept_id",
                            "topic_id",
                            "concept_id",
                            "role",
                            "rank",
                            "canonical_name",
                            "short_definition",
                            "difficulty",
                        ],
                        "properties": {
                            "topic_concept_id": {"type": "string"},
                            "topic_id": {"type": "string"},
                            "concept_id": {"type": "string"},
                            "role": {"type": "string"},
                            "rank": {"type": "integer"},
                            "canonical_name": {"type": "string"},
                            "short_definition": {"type": "string"},
                            "difficulty": {"type": "string"},
                        },
                        "additionalProperties": True,
                    },
                },
                "concept_briefs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["concept_id", "canonical_name", "short_definition", "difficulty"],
                        "properties": {
                            "concept_id": {"type": "string"},
                            "canonical_name": {"type": "string"},
                            "short_definition": {"type": "string"},
                            "difficulty": {"type": "string"},
                        },
                        "additionalProperties": True,
                    },
                },
                "has_more": {"type": "boolean"},
                "next_offset": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
        "summary": "Get graph structure and concept briefs",
        "tags": ["kg"],
        "stability": "stable",
    },
    "ingest_knowledge_graph": {
        "input_schema": {
            "type": "object",
            "required": ["graph_id", "structured_payload"],
            "properties": {
                "sync_mode": {
                    "type": "string",
                    "enum": ["upsert_only", "upsert_and_prune"],
                    "description": "upsert_and_prune removes concepts/relations missing from payload within prune_scope",
                },
                "prune_scope": {
                    "type": "object",
                    "properties": {
                        "topic_ids": {"type": "array", "items": {"type": "string"}},
                        "concept_id_prefix": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "force_delete": {
                    "type": "boolean",
                    "description": "When pruning, drop learning refs blocking removal",
                },
                "graph_id": {
                    "type": "string",
                    "description": "Knowledge graph identifier",
                    "examples": ["g-software-engineering"],
                },
                "structured_payload": {
                    "type": "object",
                    "required": ["graph", "concepts", "relations", "evidences", "relation_evidences"],
                    "properties": {
                        "graph": {
                            "type": "object",
                            "required": ["graph_type", "graph_name", "schema_version", "release_tag"],
                            "properties": {
                                "graph_type": {"type": "string", "enum": ["domain", "module", "view"]},
                                "graph_name": {"type": "string"},
                                "schema_version": {"type": "string"},
                                "release_tag": {"type": "string"},
                            },
                            "additionalProperties": False,
                            "examples": [
                                {
                                    "graph_type": "domain",
                                    "graph_name": "Software Engineering Exam Knowledge",
                                    "schema_version": "1.0.0",
                                    "release_tag": "se-r1",
                                }
                            ],
                        },
                        "concepts": {
                            "type": "array",
                            "description": "Concept entries to upsert into graph",
                            "items": {
                                "type": "object",
                                "required": ["concept_id", "canonical_name", "definition"],
                                "properties": {
                                    "concept_id": {
                                        "type": "string",
                                        "description": "Use a namespaced id to avoid collisions across books",
                                        "examples": [
                                            "sebook-ch04-data-communication-basics",
                                            "sebook-ch07-requirement-design-test-tradeoff",
                                        ],
                                    },
                                    "canonical_name": {
                                        "type": "string",
                                        "examples": ["数据通信基础"],
                                    },
                                    "definition": {
                                        "type": "string",
                                        "examples": ["奈奎斯特定理与香农定理等通信基础。"],
                                    },
                                    "concept_type": {
                                        "type": "string",
                                        "examples": ["exam_knowledge"],
                                    },
                                    "difficulty_level": {
                                        "type": "string",
                                        "examples": ["medium"],
                                    },
                                },
                            },
                            "additionalProperties": False,
                        },
                        "relations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": [
                                    "concept_relation_id",
                                    "from_concept_id",
                                    "to_concept_id",
                                    "relation_type",
                                ],
                                "properties": {
                                    "concept_relation_id": {"type": "string"},
                                    "from_concept_id": {"type": "string"},
                                    "to_concept_id": {"type": "string"},
                                    "relation_type": {
                                        "type": "string",
                                        "enum": [
                                            "prerequisite_of",
                                            "part_of",
                                            "contrast_with",
                                            "applied_in",
                                            "related_to",
                                        ],
                                    },
                                },
                                "additionalProperties": False,
                            },
                        },
                        "evidences": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["evidence_id", "quote_text"],
                                "properties": {
                                    "evidence_id": {"type": "string"},
                                    "source_type": {"type": "string"},
                                    "source_title": {"type": "string"},
                                    "source_uri": {"type": "string"},
                                    "locator": {"type": "string"},
                                    "quote_text": {"type": "string"},
                                },
                                "additionalProperties": False,
                            },
                        },
                        "relation_evidences": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": [
                                    "relation_evidence_id",
                                    "concept_relation_id",
                                    "evidence_id",
                                ],
                                "properties": {
                                    "relation_evidence_id": {"type": "string"},
                                    "concept_relation_id": {"type": "string"},
                                    "evidence_id": {"type": "string"},
                                    "support_score": {"type": "number"},
                                    "evidence_role": {"type": "string"},
                                },
                                "additionalProperties": False,
                            },
                        },
                        "topics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["topic_id", "topic_name", "topic_type"],
                                "properties": {
                                    "topic_id": {"type": "string"},
                                    "topic_name": {"type": "string"},
                                    "parent_topic_id": {"type": ["string", "null"]},
                                    "topic_type": {
                                        "type": "string",
                                        "enum": ["chapter", "section"],
                                    },
                                    "sort_order": {"type": "integer"},
                                },
                                "additionalProperties": False,
                            },
                        },
                        "topic_concepts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["topic_concept_id", "topic_id", "concept_id"],
                                "properties": {
                                    "topic_concept_id": {"type": "string"},
                                    "topic_id": {"type": "string"},
                                    "concept_id": {"type": "string"},
                                    "role": {"type": "string"},
                                    "rank": {"type": "integer"},
                                },
                                "additionalProperties": False,
                            },
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
        },
        "summary": "Ingest structured graph payload",
        "tags": ["kg", "write"],
        "stability": "beta",
    },
    "remove_knowledge_graph_entities": {
        "input_schema": {
            "type": "object",
            "required": ["graph_id", "remove_payload"],
            "properties": {
                "graph_id": {"type": "string"},
                "remove_payload": {
                    "type": "object",
                    "properties": {
                        "concept_ids": {"type": "array", "items": {"type": "string"}},
                        "relation_ids": {"type": "array", "items": {"type": "string"}},
                        "topic_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": False,
                },
                "force_delete": {"type": "boolean", "description": "If true, drop learning refs then hard-delete graph rows"},
            },
            "additionalProperties": False,
        },
        "summary": "Remove graph entities after learning dependency check",
        "tags": ["kg", "write", "learning"],
        "stability": "beta",
    },
    "list_learning_plans": {
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1},
                "offset": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "summary": "List plans",
        "tags": ["learning"],
        "stability": "stable",
    },
    "get_discovery_context": {
        "input_schema": {
            "type": "object",
            "properties": {
                "page_limit": {"type": "integer", "minimum": 1},
                "max_pages": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
        "summary": "Build discovery snapshot and dual-table markdown",
        "tags": ["meta", "kg", "learning"],
        "stability": "stable",
    },
    "create_learning_plan": {
        "input_schema": {
            "type": "object",
            "required": ["graph_id"],
            "properties": {
                "graph_id": {"type": "string", "minLength": 1},
                "topic_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "summary": "Create a new plan",
        "tags": ["learning", "write"],
        "stability": "stable",
        "examples": {"valid_payloads": [{"graph_id": "g-software-engineering"}, {"graph_id": "g-software-engineering", "topic_id": "t1"}]},
    },
    "extend_learning_plan_topics": {
        "input_schema": {
            "type": "object",
            "required": ["plan_id", "topic_ids"],
            "properties": {
                "plan_id": {"type": "string", "minLength": 1},
                "topic_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "reason": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "summary": "Extend plan topics",
        "tags": ["learning", "write"],
        "stability": "stable",
    },
    "get_learn_context": {
        "input_schema": {
            "type": "object",
            "required": ["plan_id"],
            "properties": {
                "plan_id": {"type": "string", "minLength": 1},
                "topic_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "summary": "Build learning prompt from context",
        "tags": ["learning", "prompt"],
        "stability": "stable",
        "examples": {"valid_payloads": [{"plan_id": "plan-1"}, {"plan_id": "plan-1", "topic_id": "t1"}]},
    },
    "get_quiz_context": {
        "input_schema": {
            "type": "object",
            "required": ["plan_id"],
            "properties": {
                "plan_id": {"type": "string", "minLength": 1},
                "topic_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "summary": "Build quiz prompt from context",
        "tags": ["learning", "prompt"],
        "stability": "stable",
        "examples": {"valid_payloads": [{"plan_id": "plan-1"}, {"plan_id": "plan-1", "topic_id": "t1"}]},
    },
    "get_review_context": {
        "input_schema": {
            "type": "object",
            "required": ["plan_id"],
            "properties": {
                "plan_id": {"type": "string", "minLength": 1},
                "topic_id": {"type": "string"},
                "session_context": {
                    "type": "object",
                    "description": "Optional review session state with served concepts and last turn result",
                }
            },
            "additionalProperties": False,
        },
        "summary": "Build review prompt from context",
        "tags": ["learning", "prompt"],
        "stability": "stable",
        "examples": {
            "valid_payloads": [
                {"plan_id": "plan-1"},
                {
                    "plan_id": "plan-1",
                    "topic_id": "t1",
                    "session_context": {"served_concept_ids": ["c1"], "last_result": "correct"},
                },
            ]
        },
    },
    "add_interaction_record": {
        "input_schema": {
            "type": "object",
            "required": ["plan_id", "mode", "record_payload"],
            "properties": {
                "plan_id": {"type": "string", "minLength": 1},
                "mode": {"type": "string", "enum": ["learn", "quiz", "review"]},
                "record_payload": {
                    "type": "object",
                    "required": ["concept_id"],
                    "properties": {
                        "concept_id": {"type": "string", "minLength": 1},
                        "result": {"type": "string"},
                        "score": {"type": "number"},
                        "difficulty_bucket": {"type": "string", "enum": ["easy", "medium", "hard"]},
                        "latency_ms": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
        },
        "summary": "Commit a learning record",
        "tags": ["learning", "write"],
        "stability": "stable",
        "examples": {
            "valid_payloads": [
                {
                    "plan_id": "plan-1",
                    "mode": "learn",
                    "record_payload": {"concept_id": "c1", "result": "ok", "score": 80},
                }
            ]
        },
    },
}


def _format_validation_error(api_name: str, payload: Any, *, code: str, message: str, error: Any | None = None) -> PayloadValidationError:
    field_path = "$"
    expected = None
    received = payload
    if error is not None:
        parts = [str(part) for part in list(error.path)]
        field_path = "$" if not parts else "$." + ".".join(parts)
        expected = error.validator_value
        received = error.instance
    return PayloadValidationError(
        {
            "error_code": code,
            "api_name": api_name,
            "field_path": field_path,
            "expected": expected,
            "received": received,
            "message": message,
        }
    )


def _validate_payload(api_name: str, payload: dict[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        err = _format_validation_error(
            api_name,
            payload,
            code="invalid_payload_type",
            message="payload must be an object",
        )
        log_event(
            logger,
            "api_payload_validation_failed",
            api_name=api_name,
            validation_failed=True,
            error_code=err.details["error_code"],
            field_path=err.details["field_path"],
        )
        raise err
    schema = API_SPECS[api_name]["input_schema"]
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(dict(payload)), key=lambda item: item.json_path)
    if errors:
        first = errors[0]
        err = _format_validation_error(
            api_name,
            payload,
            code="invalid_payload_schema",
            message=first.message,
            error=first,
        )
        log_event(
            logger,
            "api_payload_validation_failed",
            api_name=api_name,
            validation_failed=True,
            error_code=err.details["error_code"],
            field_path=err.details["field_path"],
        )
        raise err


def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _is_incorrect_result(result: Any) -> bool:
    return str(result or "").lower() in {"wrong", "incorrect", "fail", "blocked"}


def _prepare_review_session_state(
    context: dict[str, Any],
    session_context: dict[str, Any] | None,
) -> dict[str, Any]:
    incoming = dict(session_context or {})
    served = set(incoming.get("served_concept_ids") or [])
    if not incoming.get("served_concept_ids"):
        # Server-side fallback: avoid immediately repeating the most recent reviewed concept
        # when caller does not persist/return session_context.
        recent_review_concepts = context.get("recent_review_concepts") or []
        if recent_review_concepts:
            served.add(recent_review_concepts[0])
    retry_state = dict(incoming.get("retry_state") or {})
    last_completed = incoming.get("last_completed_concept_id")
    last_result = incoming.get("last_result")

    if last_completed:
        if _is_incorrect_result(last_result):
            retries = int(retry_state.get(last_completed, 0))
            if retries < 1:
                retry_state[last_completed] = retries + 1
            else:
                served.add(last_completed)
                retry_state.pop(last_completed, None)
        else:
            served.add(last_completed)
            retry_state.pop(last_completed, None)

    candidate_items = context.get("candidate_items") or context.get("due_items") or []
    queue_items: list[dict[str, Any]] = []
    for item in candidate_items:
        concept_id = item.get("concept_id")
        if not concept_id:
            continue
        if concept_id in served and retry_state.get(concept_id, 0) == 0:
            continue
        queue_items.append(item)

    return {
        "queue_snapshot": queue_items[:20],
        "current_item": queue_items[0] if queue_items else None,
        "next_item": queue_items[1] if len(queue_items) > 1 else None,
        "served_concept_ids": sorted(served),
        "next_session_context": {
            "served_concept_ids": sorted(served),
            "retry_state": retry_state,
            "queue_length": len(queue_items),
        },
    }


def _format_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        empty = "| " + " | ".join(headers) + " |\n"
        sep = "| " + " | ".join(["---"] * len(headers)) + " |\n"
        return empty + sep + "| " + " | ".join(["-"] * len(headers)) + " |"
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    row_lines = []
    for row in rows:
        normalized = [str(cell) if cell is not None else "" for cell in row]
        row_lines.append("| " + " | ".join(normalized) + " |")
    return "\n".join([header_line, sep_line, *row_lines])


def _build_discovery_tables(
    knowledge_graphs: list[dict[str, Any]],
    pending_learning_plans: list[dict[str, Any]],
) -> dict[str, str]:
    graph_headers = ["序号", "graph_id", "图谱名称", "revision", "主题数", "概念数", "主题内容", "状态"]
    graph_rows = [
        [
            idx + 1,
            item.get("graph_id", ""),
            item.get("name", ""),
            item.get("revision", 0),
            item.get("topic_count", 0),
            item.get("concept_count", 0),
            item.get("topic_content") or "（暂无主题摘要）",
            item.get("status", ""),
        ]
        for idx, item in enumerate(knowledge_graphs)
    ]
    plan_headers = [
        "序号",
        "plan_id",
        "关联图谱",
        "已完成任务",
        "待完成任务",
        "聚焦主题数",
        "主题内容",
        "最近更新",
    ]
    plan_rows = [
        [
            idx + 1,
            item.get("plan_id", ""),
            item.get("graph_id", ""),
            item.get("completed_tasks", 0),
            item.get("pending_tasks", 0),
            len(item.get("focus_topics") or []),
            item.get("topic_content") or "（暂无主题摘要）",
            item.get("updated_at", ""),
        ]
        for idx, item in enumerate(pending_learning_plans)
    ]
    return {
        "knowledge_graphs_table": _format_markdown_table(graph_headers, graph_rows),
        "pending_learning_plans_table": _format_markdown_table(plan_headers, plan_rows),
    }


class OrchestrationAppService:
    def __init__(self) -> None:
        # Ensure schema exists even when callers bypass create_app().
        run_migrations()

    def list_apis(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "version": "v1",
                "summary": spec["summary"],
                "tags": spec["tags"],
                "stability": spec["stability"],
            }
            for name, spec in sorted(API_SPECS.items())
        ]

    def get_api_spec(self, api_name: str) -> dict[str, Any]:
        if api_name not in API_SPECS:
            raise ValueError(f"unknown_api: {api_name}")
        spec = API_SPECS[api_name]
        return {
            "name": api_name,
            "input_schema": spec["input_schema"],
            "output_schema": spec.get("output_schema", {}),
            "examples": spec.get("examples", {}),
        }

    def list_knowledge_graphs(self, limit: int = 20, offset: str | None = None) -> dict[str, Any]:
        log_event(logger, "list_knowledge_graphs", limit=limit, offset=offset)
        return kg_api.list_knowledge_graphs(limit=limit, offset=offset)

    def get_knowledge_graph(
        self,
        graph_id: str,
        topic_id: str | None = None,
        concept_limit: int = 20,
        offset: str | None = None,
    ) -> dict[str, Any]:
        log_event(logger, "get_knowledge_graph", graph_id=graph_id, topic_id=topic_id)
        return kg_api.get_knowledge_graph(
            graph_id=graph_id,
            topic_id=topic_id,
            concept_limit=concept_limit,
            offset=offset,
        )

    def ingest_knowledge_graph(
        self,
        graph_id: str,
        structured_payload: dict[str, Any],
        sync_mode: str = "upsert_only",
        prune_scope: dict[str, Any] | None = None,
        force_delete: bool = False,
    ) -> dict[str, Any]:
        _validate_payload(
            "ingest_knowledge_graph",
            _compact_payload(
                {
                    "graph_id": graph_id,
                    "structured_payload": structured_payload,
                    "sync_mode": sync_mode,
                    "prune_scope": prune_scope,
                    "force_delete": force_delete,
                }
            ),
        )
        log_event(logger, "ingest_knowledge_graph", graph_id=graph_id, sync_mode=sync_mode)
        return kg_api.ingest_knowledge_graph(
            graph_id,
            structured_payload,
            sync_mode=sync_mode,
            prune_scope=prune_scope,
            force_delete=force_delete,
        )

    def remove_knowledge_graph_entities(
        self,
        graph_id: str,
        remove_payload: dict[str, Any],
        force_delete: bool = False,
    ) -> dict[str, Any]:
        _validate_payload(
            "remove_knowledge_graph_entities",
            _compact_payload(
                {
                    "graph_id": graph_id,
                    "remove_payload": remove_payload,
                    "force_delete": force_delete,
                }
            ),
        )
        log_event(logger, "remove_knowledge_graph_entities", graph_id=graph_id, force_delete=force_delete)
        concept_ids = [str(x) for x in (remove_payload.get("concept_ids") or []) if x]
        relation_ids = [str(x) for x in (remove_payload.get("relation_ids") or []) if x]
        topic_ids = [str(x) for x in (remove_payload.get("topic_ids") or []) if x]
        if not concept_ids and not relation_ids and not topic_ids:
            return {
                "error": "empty_remove_payload",
                "message": "Provide concept_ids, relation_ids, and/or topic_ids",
                "graph_id": graph_id,
            }

        expanded_topics = collect_topic_ids_with_descendants(graph_id, topic_ids) if topic_ids else []
        topic_ids_for_check = expanded_topics if expanded_topics else topic_ids
        dep = learning_api.check_plan_dependencies(
            graph_id,
            concept_ids=concept_ids,
            topic_ids=topic_ids_for_check,
        )
        if dep["has_blocking"] and not force_delete:
            return {
                "error": "dependency_conflict",
                "graph_id": graph_id,
                "forced": False,
                "dependency_check": dep,
                "blocking_dependencies": dep["blocking_dependencies"],
            }

        cleanup_summary: dict[str, Any] | None = None
        if dep["has_blocking"] and force_delete:
            cleanup_summary = learning_api.cleanup_learning_refs_for_graph_entity_removal(
                graph_id,
                concept_ids=concept_ids,
                topic_ids=topic_ids_for_check,
            )

        delete_summary = kg_api.remove_knowledge_graph_entities(graph_id, remove_payload)
        if delete_summary.get("error"):
            return delete_summary

        return {
            "graph_id": graph_id,
            "forced": bool(force_delete and dep["has_blocking"]),
            "dependency_check": dep,
            "cleanup_summary": cleanup_summary,
            "delete_summary": delete_summary,
        }

    def list_learning_plans(self, limit: int = 20, offset: str | None = None) -> dict[str, Any]:
        return learning_api.list_learning_plans(limit=limit, offset=offset)

    def get_discovery_context(self, page_limit: int = 20, max_pages: int = 10) -> dict[str, Any]:
        graph_items: list[dict[str, Any]] = []
        graph_offset: str | None = None
        graph_pages = 0
        while graph_pages < max_pages:
            page = self.list_knowledge_graphs(limit=page_limit, offset=graph_offset)
            graph_pages += 1
            graph_items.extend(page.get("items", []))
            graph_offset = page.get("next_offset")
            if not page.get("has_more") or not graph_offset:
                break

        plan_items: list[dict[str, Any]] = []
        plan_offset: str | None = None
        plan_pages = 0
        while plan_pages < max_pages:
            page = self.list_learning_plans(limit=page_limit, offset=plan_offset)
            plan_pages += 1
            plan_items.extend(page.get("items", []))
            plan_offset = page.get("next_offset")
            if not page.get("has_more") or not plan_offset:
                break

        tables = _build_discovery_tables(graph_items, plan_items)
        return {
            "knowledge_graphs": graph_items,
            "pending_learning_plans": plan_items,
            "tables": tables,
            "display_markdown": (
                "## 可用知识图谱（KnowledgeGraphs）\n\n"
                + tables["knowledge_graphs_table"]
                + "\n\n## 待完成学习计划（PendingLearningPlans）\n\n"
                + tables["pending_learning_plans_table"]
            ),
            "discovery_snapshot": {
                "source": "api_discovery",
                "page_limit": page_limit,
                "max_pages": max_pages,
                "knowledge_graph_pages_fetched": graph_pages,
                "learning_plan_pages_fetched": plan_pages,
                "knowledge_graph_count": len(graph_items),
                "pending_learning_plan_count": len(plan_items),
            },
        }

    def create_learning_plan(self, graph_id: str, topic_id: str | None = None) -> dict[str, Any]:
        _validate_payload("create_learning_plan", _compact_payload({"graph_id": graph_id, "topic_id": topic_id}))
        return learning_api.create_learning_plan(graph_id=graph_id, topic_id=topic_id)

    def extend_learning_plan_topics(
        self,
        plan_id: str,
        topic_ids: list[str],
        reason: str | None = None,
    ) -> dict[str, Any]:
        _validate_payload(
            "extend_learning_plan_topics",
            _compact_payload({"plan_id": plan_id, "topic_ids": topic_ids, "reason": reason}),
        )
        return learning_api.extend_learning_plan_topics(plan_id=plan_id, topic_ids=topic_ids, reason=reason)

    def get_learn_context(self, plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
        _validate_payload("get_learn_context", _compact_payload({"plan_id": plan_id, "topic_id": topic_id}))
        context = learning_api.get_learning_context(plan_id=plan_id, topic_id=topic_id)
        return {"prompt_text": build_prompt("learn", context), "context_summary": context}

    def get_quiz_context(self, plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
        _validate_payload("get_quiz_context", _compact_payload({"plan_id": plan_id, "topic_id": topic_id}))
        context = learning_api.get_quiz_context(plan_id=plan_id, topic_id=topic_id)
        return {"prompt_text": build_prompt("quiz", context), "context_summary": context}

    def get_review_context(
        self,
        plan_id: str,
        topic_id: str | None = None,
        session_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _validate_payload(
            "get_review_context",
            _compact_payload(
                {
                    "plan_id": plan_id,
                    "topic_id": topic_id,
                    "session_context": session_context,
                }
            ),
        )
        context = learning_api.get_review_context(plan_id=plan_id, topic_id=topic_id)
        session_state = _prepare_review_session_state(context, session_context)
        context = {
            **context,
            "session_queue": {
                "items": session_state["queue_snapshot"],
                "current_item": session_state["current_item"],
                "next_item": session_state["next_item"],
                "served_concept_ids": session_state["served_concept_ids"],
            },
            "next_session_context": session_state["next_session_context"],
        }
        return {"prompt_text": build_prompt("review", context), "context_summary": context}

    def add_interaction_record(self, plan_id: str, mode: str, record_payload: dict[str, Any]) -> dict[str, Any]:
        _validate_payload(
            "add_interaction_record",
            {"plan_id": plan_id, "mode": mode, "record_payload": record_payload},
        )
        return learning_api.add_interaction_record(plan_id=plan_id, mode=mode, record_payload=record_payload)


def call_api(service: OrchestrationAppService, api_name: str, payload: dict[str, Any]) -> Any:
    if api_name not in API_SPECS:
        raise ValueError(f"unknown_api: {api_name}")
    try:
        _validate_payload(api_name, payload)
        handler: Callable[..., Any] = getattr(service, api_name)
        return handler(**payload)
    except TypeError as exc:
        err = PayloadValidationError(
            {
                "error_code": "invalid_payload_signature",
                "api_name": api_name,
                "field_path": "$",
                "expected": "payload keys must match API signature",
                "received": sorted(payload.keys()),
                "message": str(exc),
            }
        )
        log_event(
            logger,
            "api_payload_validation_failed",
            api_name=api_name,
            validation_failed=True,
            error_code=err.details["error_code"],
            field_path=err.details["field_path"],
        )
        raise err from exc
