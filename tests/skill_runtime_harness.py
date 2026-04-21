"""SKILL.md-aligned runtime harness used by integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.orchestration.orchestration_app_service import OrchestrationAppService


@dataclass
class RuntimeContext:
    mode: str | None = None
    graph_id: str | None = None
    plan_id: str | None = None
    topic_id: str | None = None


class SkillRuntime:
    """Test-side runtime facade that executes SKILL.md mode contracts."""

    def __init__(self, service: OrchestrationAppService | None = None) -> None:
        self.service = service or OrchestrationAppService()

    def route_mode(self, user_input: str, last_mode: str | None = None) -> str:
        text = user_input.strip().lower()
        if any(k in text for k in ["导入", "建图", "更新图谱", "ingest", "import"]):
            return "ingest"
        if any(k in text for k in ["学习", "讲解", "理解", "learn", "explain"]):
            return "learn"
        if any(k in text for k in ["考我", "测试", "出题", "quiz", "test"]):
            return "quiz"
        if any(k in text for k in ["复习", "回顾", "到期", "review"]):
            return "review"
        if any(k in text for k in ["继续", "下一个", "continue", "next"]) and last_mode:
            return last_mode
        return "shared"

    def session_start(self, mode: str) -> dict[str, Any]:
        return {
            "mode": mode,
            "next_step": f"execute_{mode}_turn",
            "summary": f"session routed to {mode}",
        }

    def run_ingest(self, graph_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.service.ingest_knowledge_graph(graph_id=graph_id, structured_payload=payload)
        ok = bool(result["validation_summary"]["ok"])
        status = "success" if ok else "needs_fix"
        return {
            "mode": "ingest",
            "status": status,
            "graph_id": result["graph_id"],
            "version": result["version"],
            "change_summary": result.get("change_summary", {}),
            "validation_summary": result["validation_summary"],
            "summary": "ingest succeeded" if ok else "ingest requires payload fixes",
            "next_step": "create_learning_plan" if ok else "fix_payload_and_retry",
        }

    def ensure_plan(self, graph_id: str, topic_id: str | None = None, plan_id: str | None = None) -> str:
        if plan_id:
            return plan_id
        plans = self.service.list_learning_plans(limit=50).get("items", [])
        for item in plans:
            if item.get("graph_id") == graph_id:
                return item["plan_id"]
        created = self.service.create_learning_plan(graph_id=graph_id, topic_id=topic_id)
        return created["plan_id"]

    def run_learn(self, plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
        response = self.service.get_learning_prompt(plan_id=plan_id, topic_id=topic_id)
        return {
            "mode": "learn",
            "content": response["prompt_text"],
            "summary": "one concept explained with one diagnostic check",
            "next_step": "ask_learner_to_restate_then_record",
        }

    def run_quiz(self, plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
        response = self.service.get_quiz_prompt(plan_id=plan_id, topic_id=topic_id)
        return {
            "mode": "quiz",
            "questions_or_feedback": response["prompt_text"],
            "summary": "single retrieval-first quiz item prepared",
            "next_step": "collect_answer_then_append_record",
        }

    def run_review(self, plan_id: str, topic_id: str | None = None) -> dict[str, Any]:
        response = self.service.get_review_prompt(plan_id=plan_id, topic_id=topic_id)
        return {
            "mode": "review",
            "review_items_or_feedback": response["prompt_text"],
            "summary": "due-item focused review prompt prepared",
            "next_step": "run_recall_then_append_record",
        }

    def run_shared(self, user_input: str, last_mode: str | None = None) -> dict[str, Any]:
        resolved = self.route_mode(user_input=user_input, last_mode=last_mode)
        if resolved == "shared":
            return {
                "mode": "shared",
                "summary": "intent unclear, one clarification needed",
                "next_step": "ask_user_to_choose_ingest_learn_quiz_review",
            }
        return {
            "mode": resolved,
            "summary": f"intent resolved to {resolved}",
            "next_step": f"route_to_{resolved}",
        }
