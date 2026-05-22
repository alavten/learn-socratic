# Shared Mode Contract

## Trigger Conditions

- User intent is unclear or conflicting.
- Required context is missing (`plan_id`, `topic_id`, or target graph).
- A mode workflow cannot continue due to recoverable validation errors.
- User asks to update or correct learning records (掌握记录、学习轨迹、上次评分/结果).
- User asks to view or fetch graph chapter/section/topic content (browse/export, not learn/quiz/review).

## Steps

1. Run discovery APIs and build a fresh snapshot for this turn (no memory-only fallback):
   - `list_knowledge_graphs()` (paginate until done when `has_more=true`)
   - `list_learning_plans()` (paginate until done when `has_more=true`)
2. Present discovery results as two independent markdown tables before any mode decision:
   - `KnowledgeGraphs`
   - `PendingLearningPlans`
3. Ask one concise clarification question that asks user to choose **plan** or **graph** first (not mode first).
4. After explicit user selection, return control to router (`../SKILL.md` Intent Matrix) for final mode selection.

## Scenarios

These scenarios are short clarifiers used only to decide the next hop.

### Single file path only

When user provides only one local file path without additional learning intent, skip shared clarification and hand off to `ingest` (`references/ingest.md`).

### Get chapter/topic content (CLI)

When user asks to view or fetch a specific graph chapter/section/topic (e.g. "第3章有哪些概念", "看一下事务隔离这一节") without starting learn/quiz/review:

1. Resolve `graph_id` and `topic_id` via the discovery flow above if missing; if only a chapter/section name is given, run `get-knowledge-graph` once without `--topic-id` and match against `topics`.
2. From the skill repo root, fetch scoped content:

   `python -m scripts.cli.main get-knowledge-graph --graph-id GRAPH_ID --topic-id TOPIC_ID [--concept-limit 20] [--offset OFFSET]`

3. If the response has `has_more=true`, paginate with `--offset` set to `next_offset` until enough for the user or they stop.
4. Return `topics`, `topic_concepts`, and `concept_briefs` from the CLI JSON; stay in `shared` (do not hand off to `learn` unless the user then asks to study).

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
