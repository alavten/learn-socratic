# Shared Mode Contract

## Trigger Conditions

- User intent is unclear or conflicting.
- Required context is missing (`plan_id`, `topic_id`, or target graph).
- A mode workflow cannot continue due to recoverable validation errors.

## Inputs

- `user_input`
- `session_context`
- Optional: `last_mode`, `last_error`

## Execution Best Practices

- Use executable command examples in unified format:
  - `python scripts/cli.py list-apis`
  - `python scripts/cli.py get-api-spec --api-name create_learning_plan`
  - `python scripts/cli.py get-api-spec --api-name ingest_knowledge_graph`
  - `python scripts/cli.py list-learning-plans`
- Execute business logic through `OrchestrationAppService` APIs only.
- Do not call internal module scripts directly from shell in normal runtime flow.
- Resolve API contract first via `list_apis()` and `get_api_spec(api_name)` before first write call.

## Parameter Mapping (Command -> Runtime)

- `mode` (caller context) -> target workflow (`ingest` / `learn` / `quiz` / `review`)
- CLI subcommand -> target workflow or management action
- `--topic-id` -> topic scope hint
- `--plan-id` -> explicit plan binding
- `--graph-id` -> plan bootstrap graph
- `--payload-file` -> structured ingestion payload JSON path
- `--concept-id/--result/--score/--difficulty-bucket` -> persistence payload fields

## Steps

1. Ask one concise clarification question to resolve intent or missing context.
2. Normalize context into a mode-ready payload.
3. If `plan_id` is missing: discover graph/plan and create one when needed.
4. Return control to router (`SKILL.md`) for final mode selection.

## Standard Preflight Call Chain

1. `list_apis()`
2. `get_api_spec("ingest_knowledge_graph")`, `get_api_spec("create_learning_plan")`, and `get_api_spec("append_learning_record")`
3. `list_knowledge_graphs()` and `list_learning_plans()`
4. If no usable plan: `create_learning_plan(graph_id, topic_id?)`

## Output

- `mode`: resolved mode or `shared`
- `summary`: concise clarification result
- `next_step`: recommended mode transition

## Retry / Fallback

- Retry once with simplified options.
- If still unresolved, default to safe learning overview and ask user to choose mode.

## Next Hop

- Must exit to router after a single clarification loop.
