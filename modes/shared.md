# Shared Mode Contract

## Trigger Conditions

- User intent is unclear or conflicting.
- Required context is missing (`plan_id`, `topic_id`, or target graph).
- A mode workflow cannot continue due to recoverable validation errors.
- User asks to update or correct learning records (掌握记录、学习轨迹、上次评分/结果).

## Steps

1. Run discovery APIs and build a fresh snapshot for this turn (no memory-only fallback):
   - `list_knowledge_graphs()` (paginate until done when `has_more=true`)
   - `list_learning_plans()` (paginate until done when `has_more=true`)
2. Present discovery results as two independent markdown tables before any mode decision:
   - `KnowledgeGraphs`
   - `PendingLearningPlans`
3. Ask one concise clarification question that asks user to choose **plan** or **graph** first (not mode first).
4. After explicit user selection, return control to router (`../SKILL.md` Intent Matrix) for final mode selection.

## Scenarios (small cases)

These scenarios are short clarifiers used only to decide the next hop.

### Chapter/topic scope

When user asks to learn a specific chapter/section/topic (for example, "学第3章", "讲解事务隔离"):

1. Prefer existing `plan_id` if user picks a plan; otherwise pick `graph_id`, then narrow to `topic_id` if needed.
2. If multiple candidates exist, present short options and ask user to choose exactly one.
3. After selection, hand off to `learn` (or `review/quiz` if user explicitly requests).

### Learning record correction

When user asks to fix stored outcomes (scores/results/history), clarify scope then hand off:

- Minimum scope: `plan_id` + target (`concept_id` or `topic_id`) + what to correct (`result` / `score` / `difficulty_bucket` / redo last turn).
- If target is unknown, propose a small candidate list and ask one choice question.
- Hand off to the target practice mode (`learn` / `quiz` / `review`) to perform the write.

### Main-mode failure recovery

When `last_mode` and `last_error` indicate interrupted execution:

- If recoverable (missing context / validation), ask for the single missing key and retry via proper mode handoff.
- If not recoverable, explain the constraint briefly and provide one safe next step.

### Long-tail API or tooling question

If the user asks for a small operation not covered by the main modes, run `list_apis()` + `get_api_spec()` once, then recommend 1 next hop and ask for confirmation.

## Output (minimal)

- Always output `KnowledgeGraphs` and `PendingLearningPlans` tables first.
- Ask exactly one question: choose **plan** or **graph** first (not mode first).
- Required output fields: `mode="shared"`, `clarification_question`, `discovery_snapshot.source="api_discovery"`, `knowledge_graphs_table`, `pending_learning_plans_table`, `summary`, `next_step`.
