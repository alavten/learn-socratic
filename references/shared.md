# Shared Mode Contract

## Trigger Conditions

- User intent is unclear or conflicting.
- Required context is missing (`plan_id`, `topic_id`, or target graph).
- A mode workflow cannot continue due to recoverable validation errors.
- User asks to update or correct learning records (掌握记录、学习轨迹、上次评分/结果) — route to the originating mode (`quiz` / `learn` / `review`) for per-item writes; do not batch-write records inside `shared`.
- User asks to view or fetch graph chapter/section/topic content (browse/export, not learn/quiz/review).
- User asks for a **mastery / weak-point report** (薄弱点、掌握程度、章节表现) without starting an interactive learn/quiz/review turn.
- User asks for a **mastery / weak-point report** (薄弱点、掌握程度、章节答题表现) — not an interactive review turn.

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

### Record correction

When the user wants to fix or backfill mastery / quiz / learn records:

1. Run discovery if `plan_id` is missing (steps 1–2 above).
2. Identify the target mode (`quiz` for test outcomes, `learn` for teaching/check outcomes, `review` for review outcomes).
3. Hand off to that mode contract; write **one record per judged item** via `add_interaction_record` (CLI loop), not conversation-only updates.
4. Verify with `list-learning-plans` and confirm `progress.records_by_mode` counts match expectations.
5. Return `summary` + `next_step` to continue in the target mode or router.

### Mastery / weak-point report

When the user wants diagnostics (weak concepts, chapter-level performance, mastery summary) rather than starting learn/quiz/review:

1. Run discovery if `plan_id` is missing (steps 1–2 above); have the user confirm the target **plan**.
2. Optional narrowing: user names a chapter → resolve `topic_id`; names a concept → resolve `concept_id` (diagnostics expands `part_of` sub-concepts automatically).
3. Invoke **`get-mastery-diagnostics`** from the skill repo root (exact shell in `../SKILL.md`); read `by_topic`, `by_concept`, `ranked_weak_concepts`, and `summary`.
4. Present a concise human-readable report; set `next_step` to `review` (due/weak queue), `learn` (conceptual gaps), or `quiz` (verification), with `plan_id` and optional scope ids.

Do not query SQLite or guess schema/table names in this scenario.

### Mastery / weak-point report

When the user wants diagnostics (not a live review/quiz session):

1. Run discovery if `plan_id` is missing (steps 1–2 above); have the user confirm the target **plan**.
2. If they name a chapter or concept, note `topic_id` or `concept_id` for scope (concept scope includes all `part_of` sub-concepts under that anchor).
3. Invoke **`get-mastery-diagnostics`** from the skill repo root (exact shell in `../SKILL.md`); read `by_topic`, `by_concept`, `ranked_weak_concepts`, and `summary`.
4. Present a concise human-readable report from that JSON only; do not query SQLite or guess schema.
5. Return `mode="shared"`, `summary`, and `next_step` pointing to `review` (due/weak queue), `learn` (concept gaps), or `quiz` (verification), as appropriate.

### Long-tail API or tooling question

If the user asks for a small operation not covered by the main modes, run `list_apis()` + `get_api_spec()` once, then recommend 1 next hop and ask for confirmation.

## Output (minimal)

- Always output `KnowledgeGraphs` and `PendingLearningPlans` tables first.
- Ask exactly one question: choose **plan** or **graph** first (not mode first).
- Required output fields: `mode="shared"`, `clarification_question`, `discovery_snapshot.source="api_discovery"`, `knowledge_graphs_table`, `pending_learning_plans_table`, `summary`, `next_step`.
