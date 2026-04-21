"""Prompt template builders for orchestration APIs."""

from __future__ import annotations

from typing import Any


def build_prompt(mode: str, context: dict[str, Any]) -> str:
    if mode == "learn":
        return _build_learn_prompt(context)
    if mode == "quiz":
        return _build_quiz_prompt(context)
    if mode == "review":
        return _build_review_prompt(context)
    raise ValueError(f"unsupported_mode: {mode}")


def _build_learn_prompt(context: dict[str, Any]) -> str:
    goals = context.get("goal_summary", {})
    concept_pack = context.get("concept_pack_brief", {})
    concept_names = [c.get("canonical_name") for c in concept_pack.get("concepts", [])[:8]]
    return (
        "You are a Socratic learning coach.\n"
        f"Goal: {goals}\n"
        f"Concept focus: {concept_names}\n"
        "Explain clearly, ask one diagnostic question, and propose next step."
    )


def _build_quiz_prompt(context: dict[str, Any]) -> str:
    scope = context.get("quiz_scope", {})
    perf = context.get("history_performance_summary", [])
    return (
        "You are a quiz generator and grader.\n"
        f"Scope: {scope}\n"
        f"Historical performance: {perf}\n"
        "Generate tiered questions, evaluate answers, and provide concise feedback."
    )


def _build_review_prompt(context: dict[str, Any]) -> str:
    due_items = context.get("due_items", [])
    risk = context.get("forgetting_risk_summary", {})
    return (
        "You are a spaced review coach.\n"
        f"Due items: {due_items[:8]}\n"
        f"Risk summary: {risk}\n"
        "Run targeted recall practice and suggest the next review window."
    )
