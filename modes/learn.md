# Learn Mode Contract

## Trigger Conditions

- User asks to learn, understand, or be guided through concepts.

## Inputs

- `plan_id`
- Optional `topic_id`
- `session_context`

## Command Invocation

- Recommended executable format:
  - `python scripts/cli.py get-learning-prompt --plan-id PLAN_ID --topic-id t1`
  - `python scripts/cli.py append-learning-record --plan-id PLAN_ID --mode learn --concept-id c1 --result ok --score 85 --difficulty-bucket medium`

## Runtime Execution Chain

1. Preflight (once per session): `list_apis()` and `get_api_spec("get_learning_prompt")`.
2. If `plan_id` missing:
   - `list_knowledge_graphs()`
   - `list_learning_plans()`
   - `create_learning_plan(graph_id, topic_id?)`
3. Fetch learn prompt context:
   - `get_learning_prompt(plan_id, topic_id?)`
4. Run Socratic teaching interaction with returned `prompt_text`.
5. Persist outcome:
   - `append_learning_record(plan_id, mode="learn", record_payload)`

## Steps

1. Resolve scope and call `get_learning_prompt(plan_id, topic_id?)`.
2. Deliver explanation and guided follow-up questions.
3. Collect interaction outcome and write `append_learning_record(..., mode='learn', ...)`.
4. Return recommended next step.

## Output

- `mode: learn`
- `content`
- `summary`
- `next_step`

## Retry / Fallback

- If context retrieval fails, ask user for plan/topic confirmation.
- If write fails, show response and ask for permission to retry record submission.

## Minimal Record Payload

- `concept_id` (required)
- `result` (recommended)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

## Next Hop

- Continue learn, or route to quiz/review through `SKILL.md`.
