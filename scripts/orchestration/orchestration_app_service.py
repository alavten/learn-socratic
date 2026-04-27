"""Orchestration application service and API self-description."""

from __future__ import annotations

from typing import Any, Callable

from scripts.foundation.logger import get_logger, log_event
from scripts.foundation.storage import run_migrations
from scripts.knowledge_graph import api as kg_api
from scripts.knowledge_graph.store import collect_topic_ids_with_descendants
from scripts.learning import api as learning_api
from scripts.orchestration.prompt_templates import build_prompt


logger = get_logger("doc_socratic.orchestration")


API_SPECS: dict[str, dict[str, Any]] = {
    "list_apis": {"input_schema": {}, "summary": "List callable APIs", "tags": ["meta"], "stability": "stable"},
    "get_api_spec": {
        "input_schema": {"type": "object", "required": ["api_name"]},
        "summary": "Get API input schema",
        "tags": ["meta"],
        "stability": "stable",
    },
    "list_knowledge_graphs": {"input_schema": {"type": "object"}, "summary": "List graph metadata", "tags": ["kg"], "stability": "stable"},
    "get_knowledge_graph": {
        "input_schema": {"type": "object", "required": ["graph_id"]},
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
                            },
                        },
                        "topics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["topic_id", "topic_name"],
                                "properties": {
                                    "topic_id": {"type": "string"},
                                    "topic_name": {"type": "string"},
                                    "topic_type": {"type": "string"},
                                    "sort_order": {"type": "integer"},
                                },
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
                            },
                        },
                    },
                },
            },
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
                },
                "force_delete": {"type": "boolean", "description": "If true, drop learning refs then hard-delete graph rows"},
            },
        },
        "summary": "Remove graph entities after learning dependency check",
        "tags": ["kg", "write", "learning"],
        "stability": "beta",
    },
    "list_learning_plans": {"input_schema": {"type": "object"}, "summary": "List plans", "tags": ["learning"], "stability": "stable"},
    "create_learning_plan": {
        "input_schema": {"type": "object", "required": ["graph_id"]},
        "summary": "Create a new plan",
        "tags": ["learning", "write"],
        "stability": "stable",
    },
    "extend_learning_plan_topics": {
        "input_schema": {"type": "object", "required": ["plan_id", "topic_ids"]},
        "summary": "Extend plan topics",
        "tags": ["learning", "write"],
        "stability": "stable",
    },
    "get_learning_prompt": {
        "input_schema": {"type": "object", "required": ["plan_id"]},
        "summary": "Build learning prompt from context",
        "tags": ["learning", "prompt"],
        "stability": "stable",
    },
    "get_quiz_prompt": {
        "input_schema": {"type": "object", "required": ["plan_id"]},
        "summary": "Build quiz prompt from context",
        "tags": ["learning", "prompt"],
        "stability": "stable",
    },
    "get_review_prompt": {
        "input_schema": {
            "type": "object",
            "required": ["plan_id"],
            "properties": {
                "session_context": {
                    "type": "object",
                    "description": "Optional review session state with served concepts and last turn result",
                }
            },
        },
        "summary": "Build review prompt from context",
        "tags": ["learning", "prompt"],
        "stability": "stable",
    },
    "append_learning_record": {
        "input_schema": {"type": "object", "required": ["plan_id", "mode", "record_payload"]},
        "summary": "Commit a learning record",
        "tags": ["learning", "write"],
        "stability": "stable",
    },
}


def _validate_required(api_name: str, payload: dict[str, Any]) -> None:
    required = API_SPECS[api_name]["input_schema"].get("required", [])
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"missing_required_fields: {missing}")


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
        return {"name": api_name, "input_schema": API_SPECS[api_name]["input_schema"]}

    def list_knowledge_graphs(self, limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
        log_event(logger, "list_knowledge_graphs", limit=limit, cursor=cursor)
        return kg_api.list_knowledge_graphs(limit=limit, cursor=cursor)

    def get_knowledge_graph(
        self,
        graph_id: str,
        topic_id: str | None = None,
        concept_limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        log_event(logger, "get_knowledge_graph", graph_id=graph_id, topic_id=topic_id)
        return kg_api.get_knowledge_graph(
            graph_id=graph_id,
            topic_id=topic_id,
            concept_limit=concept_limit,
            cursor=cursor,
        )

    def ingest_knowledge_graph(
        self,
        graph_id: str,
        structured_payload: dict[str, Any],
        sync_mode: str = "upsert_only",
        prune_scope: dict[str, Any] | None = None,
        force_delete: bool = False,
    ) -> dict[str, Any]:
        _validate_required("ingest_knowledge_graph", {"graph_id": graph_id, "structured_payload": structured_payload})
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
        _validate_required(
            "remove_knowledge_graph_entities",
            {"graph_id": graph_id, "remove_payload": remove_payload},
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

    def list_learning_plans(self, limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
        return learning_api.list_learning_plans(limit=limit, cursor=cursor)

    def create_learning_plan(self, graph_id: str, topic_id: str | None = None) -> dict[str, Any]:
        _validate_required("create_learning_plan", {"graph_id": graph_id})
        return learning_api.create_learning_plan(graph_id=graph_id, topic_id=topic_id)

    def extend_learning_plan_topics(
        self,
        plan_id: str,
        topic_ids: list[str],
        reason: str | None = None,
    ) -> dict[str, Any]:
        _validate_required("extend_learning_plan_topics", {"plan_id": plan_id, "topic_ids": topic_ids})
        return learning_api.extend_learning_plan_topics(plan_id=plan_id, topic_ids=topic_ids, reason=reason)

    def get_learning_prompt(self, plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
        _validate_required("get_learning_prompt", {"plan_id": plan_id})
        context = learning_api.get_learning_context(plan_id=plan_id, topic_id=topic_id)
        return {"prompt_text": build_prompt("learn", context), "context_summary": context}

    def get_quiz_prompt(self, plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
        _validate_required("get_quiz_prompt", {"plan_id": plan_id})
        context = learning_api.get_quiz_context(plan_id=plan_id, topic_id=topic_id)
        return {"prompt_text": build_prompt("quiz", context), "context_summary": context}

    def get_review_prompt(
        self,
        plan_id: str,
        topic_id: str | None = None,
        session_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _validate_required("get_review_prompt", {"plan_id": plan_id})
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

    def append_learning_record(self, plan_id: str, mode: str, record_payload: dict[str, Any]) -> dict[str, Any]:
        _validate_required("append_learning_record", {"plan_id": plan_id, "mode": mode, "record_payload": record_payload})
        return learning_api.append_learning_record(plan_id=plan_id, mode=mode, record_payload=record_payload)


def call_api(service: OrchestrationAppService, api_name: str, payload: dict[str, Any]) -> Any:
    if api_name not in API_SPECS:
        raise ValueError(f"unknown_api: {api_name}")
    _validate_required(api_name, payload)
    handler: Callable[..., Any] = getattr(service, api_name)
    return handler(**payload)
