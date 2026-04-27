# Ingest Mode Contract

## Trigger Conditions

- User asks to import materials, build a graph, or update existing graph knowledge.
- Caller has prepared structured graph payload from documents/LLM extraction.

## Inputs

- `graph_id` (required)
- `payload_file` (required, JSON, must be `structured_payload` object only)
- Optional `session_context`

## Command Invocation

- Recommended executable format:
  - `python scripts/cli.py ingest-knowledge-graph --graph-id g1 --payload-file ./payload.json`
  - `python scripts/cli.py ingest-knowledge-graph --graph-id g1 --payload-file ./payload.json --sync-mode upsert_and_prune --prune-topic-ids t1,t2`
  - `python scripts/cli.py remove-knowledge-graph-entities --graph-id g1 --payload-file ./remove.json`
  - `python scripts/cli.py list-knowledge-graphs`
  - `python scripts/cli.py get-knowledge-graph --graph-id g1 --concept-limit 20`

## Runtime Execution Chain

1. Preflight (once per session): `list_apis()` and `get_api_spec("ingest_knowledge_graph")`.
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

## Escalation Rule

- If validation passes: escalate to plan bootstrap suggestion (`create_learning_plan`).
- If validation fails: de-escalate to payload repair guidance with concrete field-level fixes.

## Mode Exit Rule

- Exit to `learn` only after `validation_summary.ok = true`.
- Stay in `ingest` when payload parse/validation is still failing.

## Evidence Rule

- When rejecting relation data, include validation evidence from `validation_summary.errors`.
- Do not fabricate source evidence; echo payload-level diagnostics only.

## Steps

1. Load JSON payload from `payload_file`.
2. Call ingest API and capture validation result.
3. On success, summarize changed entities and revision.
4. On failure, report failed items and next fix action.
5. Offer transition to `learn` mode for immediate study.

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
