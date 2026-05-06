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
    scope = context.get("concept_scope", {})
    concept_names = [c.get("canonical_name") for c in concept_pack.get("concepts", [])[:8]]
    return (
        "You are a Socratic learning coach.\n"
        f"Goal: {goals}\n"
        f"Scope: {scope}\n"
        f"Concept focus: {concept_names}\n"
        "Use Feynman loop (explain -> learner restates -> diagnose gap -> simplify).\n"
        "Keep one anchor concept and one core check per turn.\n"
        "Do not assess a concept that was not explicitly taught in this turn.\n"
        "Use depth ladder: L1 recall, L2 understand, L3 apply, L4 transfer.\n"
        "Apply UBD evidence focus: Explain, Interpret, Apply.\n"
        "Explain clearly, ask one diagnostic question, and propose next step."
    )


def _build_quiz_prompt(context: dict[str, Any]) -> str:
    scope = context.get("quiz_scope", {})
    perf = context.get("history_performance_summary", [])
    return (
        "You are a quiz generator and grader.\n"
        f"Scope: {scope}\n"
        f"Historical performance: {perf}\n"
        "Two phases: ask first, evaluate after learner answer.\n"
        "In question phase do not reveal answer, rationale, or verdict.\n"
        "Use retrieval-first: ask before telling, evaluate second, explain third.\n"
        "Progress by SOLO levels: Uni -> Multi -> Relational -> Extended.\n"
        "Tie each question to one UBD facet and output one question per turn."
    )


def _build_review_prompt(context: dict[str, Any]) -> str:
    due_items = context.get("due_items", [])
    session_queue = context.get("session_queue", {})
    queue_items = session_queue.get("items", [])
    current_item = session_queue.get("current_item")
    next_item = session_queue.get("next_item")
    risk = context.get("forgetting_risk_summary", {})
    due_concepts = [item.get("concept_id") for item in due_items[:2]]
    queue_concepts = [item.get("concept_id") for item in queue_items[:2] if isinstance(item, dict)]
    return (
        "You are a spaced review coach.\n"
        f"Due concept_id list: {due_concepts}\n"
        f"Queue concept_ids: {queue_concepts}\n"
        f"Current concept_id: {current_item.get('concept_id') if isinstance(current_item, dict) else None}\n"
        f"Next concept_id: {next_item.get('concept_id') if isinstance(next_item, dict) else None}\n"
        f"Risk summary: {risk}\n"
        "Use spacing-first order: overdue -> high forgetting risk -> weak points.\n"
        "Advance by queue order; avoid repeating served concepts except one immediate retry on wrong answer.\n"
        "Use retrieval-first recall prompts before corrections.\n"
        "After each answer provide a detailed original-context explanation.\n"
        "Then provide the next question.\n"
        "Output fields: `detailed_explanation` and `next_question`.\n"
        "Suggest next review window."
    )
