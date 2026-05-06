# Shared Mode Contract

## Trigger Conditions

- User intent is unclear or conflicting.
- Required context is missing (`plan_id`, `topic_id`, or target graph).
- A mode workflow cannot continue due to recoverable validation errors.
- User asks to **update or correct learning records** (掌握记录、学习轨迹、上次评分/结果), which must be disambiguated from graph ingest and from normal learn/quiz/review turns.

## Inputs

- `user_input`
- `session_context`
- Optional: `last_mode`, `last_error`
- When updating records: optional `plan_id`, `concept_id`, target mode (`learn` / `quiz` / `review`), and what is being corrected (e.g. `result`, `score`, `difficulty_bucket`).

## Execution Best Practices

- Treat this mode as a short router, not a teaching mode.
- Resolve intent quickly, then hand off to target mode.
- Keep cross-mode API details in `SKILL.md` and target mode files.

## Routing Source of Truth

- Route mapping lives in `../SKILL.md` under **Intent Matrix**.
- `shared` only handles disambiguation, missing context collection, and conflict resolution before handoff.
- For “更新学习记录/修正掌握记录/改上次成绩或结果”, use the **Learning record updates** branch below to clarify first, then hand off.

## Steps

1. If `plan_id` is missing (learn/quiz/review), you MUST call discovery APIs first and build a fresh snapshot for this turn (no memory-only fallback):
   - `list_knowledge_graphs()` (paginate until done when `has_more=true`)
   - `list_learning_plans()` (paginate until done when `has_more=true`)
2. Present discovery results as two independent markdown tables before any mode decision:
   - `KnowledgeGraphs`
   - `PendingLearningPlans`
3. Ask one concise clarification question that asks user to choose **plan** or **graph** first (not mode first).
4. Normalize context into a mode-ready payload after explicit user selection.
5. Route using `../SKILL.md` **Intent Matrix** and confirm target mode.
6. Return control to router (`SKILL.md`) for final mode selection.

## Common Issue Playbooks

Use these playbooks for frequent shared-mode requests before rerouting.

### Chapter/topic scope request

When user asks to learn a specific chapter/section/topic (for example, "学第3章", "讲解事务隔离"):

1. Resolve scope in this order: `plan_id` -> `graph_id` -> `topic_id`.
2. If scope is incomplete, ask one targeted question (for example, chapter belongs to which graph/plan).
3. If multiple matches exist, provide short ranked options and ask user to choose one.
4. After explicit user selection, hand off to `learn` with resolved scope.

### Learning record correction request

When user asks to fix mastery results, scores, history, or last turn outcomes:

1. Confirm this is record correction, not graph-content update.
2. Collect minimum scope: `plan_id`, concept/topic target, and correction field (`result` / `score` / `difficulty_bucket` / redo).
3. If exact concept is unknown, offer a narrowed candidate list and ask one choice question.
4. Hand off to target practice mode (`learn` / `quiz` / `review`) after scope is complete.

### Main-mode failure recovery

When `last_mode` and `last_error` indicate interrupted execution:

1. Classify error as recoverable (missing context, validation, transient API failure) or non-recoverable (contract mismatch, missing capability).
2. For recoverable errors, request one missing key input and retry via proper mode handoff.
3. For non-recoverable errors, explain constraint briefly and provide one safe next action (usually `learn` with narrowed scope or `ingest` fix path).
4. Always output reroute target and the minimal context still needed.

## API Discovery for Long-tail Intents

Use this branch when request is learning-related but not directly covered by the main Intent Matrix.

1. Run capability discovery preflight: `list_apis()`.
2. Select at most 1-2 candidate APIs relevant to current user ask.
3. Validate required input contracts with `get_api_spec(api_name)`.
4. Return one recommended action and ask user to confirm before execution.

Guardrails:

- Do not perform write operations during discovery.
- If capability is unavailable, explain the gap and reroute to the closest supported main mode.
- Avoid broad API probing loops; one discovery pass per turn.

## Re-entry Contract

Every shared turn must produce a deterministic handoff payload:

- `resolved_mode`: `ingest` / `learn` / `quiz` / `review` / `null`
- `handoff_reason`: why this mode is selected
- `required_context`: missing or resolved fields (`plan_id`, `graph_id`, `topic_id`, correction scope)
- `next_step`: one executable next action

Re-entry rules:

1. If required context is complete, hand off immediately to resolved mode.
2. If context is incomplete, remain in `shared` and ask exactly one critical question.
3. Never ask multiple clarification questions in one turn.
4. Prevent oscillation: do not reroute twice in the same turn.

Discovery guardrails:

1. Do not answer discovery turns with phrases like “根据记忆/按记忆” as primary evidence.
2. If `discovery_snapshot` is absent, retry discovery instead of continuing with guesswork.
3. If either table is missing, keep turn in `shared` and request re-selection after re-rendering both tables.

## Learning record updates

Use this branch when the user wants to **change stored learning outcomes**, not when they only mean “update the knowledge graph” (that stays under `ingest`).

1. **Separate from ingest**: If the user is clearly updating concepts/relations/graph content, route to `ingest` and do not treat it as a learning-record-only fix.
2. **Collect scope**: Confirm `plan_id`, affected `concept_id` (or topic scope), and which record dimension they want to fix (`result`, `score`, `difficulty_bucket`, or “redo last turn”).
3. **API contract**: After preflight `list_apis()` / `get_api_spec`, prefer a dedicated **update/patch learning record** operation if the backend exposes one (e.g. `update_learning_record`, `patch_learning_record`). If only append exists, follow the spec for **append with superseding or corrective semantics** (metadata fields, duplicate handling), or append a new record that reflects the corrected outcome per product rules.
4. **Mode handoff**: Route to the mode that matches the user’s redo intent—`learn` / `quiz` / `review`—once scope is clear; execution of `add_interaction_record` / update calls stays in that mode’s contract (`modes/learn.md`, `modes/quiz.md`, `modes/review.md`). Use `shared` only until `plan_id`, concept scope, and update-vs-redo intent are resolved.

## AI Execution Directives

- Ask at most one clarification question before rerouting.
- Prefer natural language cues over explicit command words.
- If intent remains ambiguous after one retry, default to `learn` with safe scope.
- For “update learning record” requests: do not write or assume record mutations until `plan_id` and correction scope are known; default handoff is the relevant practice mode (`learn`/`quiz`/`review`), not `ingest`, unless the user explicitly mixes graph updates into the same ask (then clarify order: graph vs. records).

## Output

- `mode`: keep as `shared` for clarification turn, then hand off to resolved mode
- `clarification_question`: one concise question used for disambiguation
- `resolved_mode`: `ingest`/`learn`/`quiz`/`review` or `null` when still unclear
- `handoff_reason`: reason for selected mode or why it remains `null`
- `required_context`: resolved/missing context needed by target mode
- `discovery_snapshot`: MUST include source `api_discovery` and counts/pages for this turn
- `knowledge_graphs_table`: markdown table for `KnowledgeGraphs` with columns:
  - `序号 | graph_id | 图谱名称 | revision | 主题数 | 概念数 | 主题内容 | 状态`
- `pending_learning_plans_table`: markdown table for `PendingLearningPlans` with columns:
  - `序号 | plan_id | 关联图谱 | 已完成任务 | 待完成任务 | 聚焦主题数 | 主题内容 | 最近更新`
- `summary`: concise clarification result
- `next_step`: recommended mode transition

## Retry / Fallback

- Retry once with simplified options.
- If still unresolved, default to safe learning overview and ask user to choose mode.

## Next Hop

- Must exit to router after a single clarification loop.
