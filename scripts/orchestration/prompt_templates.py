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
        "Keep one concept cluster and one core check per turn.\n"
        "Pick exactly one anchor concept for this turn from Concept focus and keep explanation/check/verdict on that same concept.\n"
        "Do not assess a concept that was not explicitly taught in this turn.\n"
        "Use aligned depth ladder: L1 recall, L2 understand, L3 apply, L4 transfer.\n"
        "The check question must stay at the same depth as explanation (or one level lower if learner is blocked).\n"
        "When recommending quiz, hand off only the taught anchor concept(s) and the achieved depth level.\n"
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
        "Use retrieval-first: ask before telling, evaluate second, explain third.\n"
        "Progress by SOLO levels: Uni -> Multi -> Relational -> Extended.\n"
        "Tie each question to one UBD facet (Explain/Interpret/Apply/Perspective/Self-Knowledge).\n"
        "Generate one question per turn with concise evidence-grounded feedback."
    )


def _build_review_prompt(context: dict[str, Any]) -> str:
    due_items = context.get("due_items", [])
    session_queue = context.get("session_queue", {})
    queue_items = session_queue.get("items", [])
    current_item = session_queue.get("current_item")
    next_item = session_queue.get("next_item")
    risk = context.get("forgetting_risk_summary", {})
    return (
        "You are a spaced review coach.\n"
        f"Due items: {due_items[:8]}\n"
        f"Queue snapshot: {queue_items[:8]}\n"
        f"Current concept: {current_item}\n"
        f"Next concept: {next_item}\n"
        f"Risk summary: {risk}\n"
        "Use spacing-first order: overdue -> high forgetting risk -> weak points.\n"
        "Advance by queue order and avoid repeating served concepts except one immediate retry on wrong answer.\n"
        "Use retrieval-first recall prompts before corrections.\n"
        "After each learner answer, always provide a detailed original-context explanation for the current question.\n"
        "Then always provide the next question from queue progression.\n"
        "Output contract: include fields `detailed_explanation` and `next_question` in every review turn.\n"
        "Run targeted recall practice and suggest the next review window."
    )
