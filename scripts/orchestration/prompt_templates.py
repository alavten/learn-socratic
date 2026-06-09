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
    scope = context.get("concept_scope", {})
    session_queue = context.get("session_queue", {})
    current_item = session_queue.get("current_item")
    next_item = session_queue.get("next_item")
    chapter_progress = context.get("chapter_progress", {})
    next_session_context = context.get("next_session_context", {})
    suggested_plan_action = context.get("suggested_plan_action")
    depth_level = context.get("depth_level")
    anchor_id = current_item.get("concept_id") if isinstance(current_item, dict) else None
    anchor_name = current_item.get("canonical_name") if isinstance(current_item, dict) else None
    next_id = next_item.get("concept_id") if isinstance(next_item, dict) else None
    queue_ids = [
        item.get("concept_id")
        for item in (session_queue.get("items") or [])
        if isinstance(item, dict) and item.get("concept_id")
    ][:5]
    lines = [
        "You are a Socratic learning coach.",
        f"Goal: {goals}",
        f"Scope: {scope}",
        f"Chapter progress: {chapter_progress}",
        f"Anchor concept_id (MUST teach this turn): {anchor_id}",
        f"Anchor canonical_name: {anchor_name}",
        f"Next concept_id (after current completes): {next_id}",
        f"Queue concept_ids (book order): {queue_ids}",
        f"Depth level: {depth_level}",
        f"next_session_context (return to caller after each turn): {next_session_context}",
        "Use Feynman loop (explain -> learner restates -> diagnose gap -> simplify).",
        "Keep one anchor concept and one core check per turn.",
        "Do NOT pick a different concept from scope; only teach anchor concept_id.",
        "Do not assess a concept that was not explicitly taught in this turn.",
        "Use depth ladder: L1 recall, L2 understand, L3 apply, L4 transfer.",
        "Apply UBD evidence focus: Explain, Interpret, Apply.",
        "After add_interaction_record succeeds, advance using session_queue order only.",
        "Explain clearly, ask one diagnostic question, and propose next step.",
    ]
    if suggested_plan_action:
        lines.append(
            f"Chapter complete: call {suggested_plan_action.get('action')} "
            f"with topic_ids={suggested_plan_action.get('topic_ids')} before continuing."
        )
    return "\n".join(lines) + "\n"


def _build_quiz_prompt(context: dict[str, Any]) -> str:
    scope = context.get("quiz_scope", {})
    perf = context.get("history_performance_summary", [])
    pacing = context.get("quiz_pacing", "per_concept")
    max_q = (context.get("constraints") or {}).get("max_question_count", 10)
    suggested = context.get("suggested_batch_size", 1)
    common = (
        "You are a quiz generator and grader.\n"
        f"Scope: {scope}\n"
        f"Historical performance: {perf}\n"
        f"Quiz pacing: {pacing} (max_question_count={max_q}, suggested_batch_size={suggested}).\n"
        "Two phases: ask first, evaluate after learner answer.\n"
        "In question phase do not reveal answer, rationale, or verdict.\n"
        "Use retrieval-first: ask before telling, evaluate second, explain third.\n"
        "Progress by SOLO levels: Uni -> Multi -> Relational -> Extended.\n"
        "Tie each question to one UBD facet.\n"
        "Each judged answer MUST be persisted with add_interaction_record(mode=quiz) before the next question or mode handoff.\n"
        "Output record_summary {expected, written, failed} whenever any answer is judged.\n"
    )
    if pacing == "per_chapter":
        return (
            common
            + "per_chapter: emit a numbered item list (item_id, concept_id, question text) up to suggested_batch_size.\n"
            + "After answers, judge in order and write one record per item; written must equal expected before handoff.\n"
            + "Complex concepts may have 2-3 items; simple concepts 1 item; total items <= max_question_count.\n"
        )
    return (
        common
        + "per_concept: one anchor concept_id per turn; default one question; up to 3 for complex concepts.\n"
        + "Write a record after each judged answer before the next question on the same turn.\n"
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
