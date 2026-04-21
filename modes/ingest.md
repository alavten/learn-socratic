# Ingest Mode Contract

## Trigger Conditions

- User asks to import materials, build a graph, or update existing graph knowledge.
- Caller has prepared structured graph payload from documents/LLM extraction.

## Inputs

- `graph_id` (required)
- `payload_file` (required, JSON)
- Optional `session_context`

## Command Invocation

- Recommended executable format:
  - `python scripts/cli.py ingest-knowledge-graph --graph-id g1 --payload-file ./payload.json`
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
- If validation fails, do not write learning records; request payload correction.
- If graph exists with conflict, retry with corrected payload and same `graph_id`.

## Next Hop

- Route to `learn` after successful ingestion when user wants immediate study.
