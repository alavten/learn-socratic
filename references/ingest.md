# Ingest Mode Contract

## Trigger Conditions

- User asks to import materials, build a graph, or update existing graph knowledge.
- Caller has prepared structured graph payload from documents/LLM extraction.

Required context: `graph_id`, `payload_file` (`structured_payload` JSON object only), optional `session_context`.

## Runtime Execution Chain

1. Preflight (once per session): `get_api_spec("ingest_knowledge_graph")`.
2. Validate payload format and required fields before write.
3. Execute ingestion:
   - `ingest_knowledge_graph(graph_id, structured_payload)`
4. Check `validation_summary`:
   - if `ok=true`: return `graph_id/version/change_summary`
   - if `ok=false`: return errors and correction hints
5. Optional handoff:
   - create plan via `create_learning_plan(graph_id, topic_id?)`
   - continue with `learn` mode prompt retrieval

## Turn Contract

- One ingestion attempt per turn.
- Return one clear status (`success` or `needs_fix`) plus one next action.
- Keep feedback concise and list at most top 5 validation errors at once.

## AI Execution Directives

- Treat ingest as a validation-first mode, not a teaching mode.
- Validate and report before proposing downstream learning actions.
- If payload fails, return field-level fixes and ask for corrected payload.
- If payload succeeds, summarize version/change delta and recommend the next mode.
- Do not invent missing payload fields; request explicit correction inputs.

## Series and chapter graphs (书系拆章)

**《Claude Harness VS Codex Harness》** 在库内已迁移为与 `se-full-20260422` **同构**：单一 `graph_id`（`claude-harness-vs-codex-harness`），章节与节全部挂在 **`topics`**（`chapter` / `section` + `parent_topic_id`），**不要**再为该书包新建 `b2-ch*` 平行子图。

其它书系若仍采用「一书多 `graph_id` + 父图」模式，可沿用下列约定（与 `parent_graph_id` 校验一致）：

1. **先写入父图**（专用 `graph_id` + 最小合法 payload），再逐章 ingest。
2. 每章子图的 `graph` 中设置 **`parent_graph_id`** 指向父图，避免平行根图。
3. **命名**：父图 `graph.graph_name` 用书系稳定标题；各章 `graph_name` 使用同一前缀 + 章后缀（例如 em dash `—`）。
4. 成功入图后确认父链与命名符合约定。

可选：在 payload 中设置 `graph.ingest_policy.require_parent: true`，批处理/CI 下缺少 `parent_graph_id` 会直接校验失败。

## Escalation Rule

- If validation passes: suggest next hop (`learn` or optional `create_learning_plan`).
- If validation fails: de-escalate to payload repair guidance with concrete field-level fixes.

## Mode Exit Rule

- Exit to `learn` only after `validation_summary.ok = true`.
- Stay in `ingest` when payload parse/validation is still failing.

## Evidence Rule

- When rejecting relation data, include validation evidence from `validation_summary.errors`.
- Do not fabricate source evidence; echo payload-level diagnostics only.

## Output

- `mode: ingest`
- `graph_id`
- `version`
- `change_summary`
- `validation_summary`
- `next_step`

## Retry / Fallback

- If payload file cannot be parsed, stop and return parse error.
- If payload file is wrapped as `{ "graph_id": "...", "structured_payload": {...} }`, reject and ask caller to pass only inner `structured_payload`.
- If validation fails, do not write learning records; request payload correction.
- If graph exists with conflict, retry with corrected payload and same `graph_id`.

## Next Hop

- Route to `learn` after successful ingestion when user wants immediate study.
