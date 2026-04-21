# Review Mode Contract

## Trigger Conditions

- User asks for review, recap, spaced repetition, or due revisions.

## Inputs

- `plan_id`
- Optional `topic_id`
- `session_context`

## Command Invocation

- Recommended executable format:
  - `python scripts/cli.py get-review-prompt --plan-id PLAN_ID --topic-id t1`
  - `python scripts/cli.py append-learning-record --plan-id PLAN_ID --mode review --concept-id c1 --result correct --score 90 --difficulty-bucket easy`

## Runtime Execution Chain

1. Preflight (once per session): `list_apis()` and `get_api_spec("get_review_prompt")`.
2. If `plan_id` missing:
   - `list_knowledge_graphs()`
   - `list_learning_plans()`
   - `create_learning_plan(graph_id, topic_id?)`
3. Fetch review context:
   - `get_review_prompt(plan_id, topic_id?)`
4. Execute recall/correction loop.
5. Persist review result:
   - `append_learning_record(plan_id, mode="review", record_payload)`

## Steps

1. Resolve scope and call `get_review_prompt(plan_id, topic_id?)`.
2. Run review interactions and corrective prompts.
3. Write `append_learning_record(..., mode='review', ...)`.
4. Return recommended next review window and next action.

## Output

- `mode: review`
- `review_items_or_feedback`
- `summary`
- `next_step`

## Retry / Fallback

- If due items are empty, suggest a light quiz or new learning task.
- If persistence fails, retain user-visible feedback and retry commit once.

## Minimal Record Payload

- `concept_id` (required)
- `result` (required for state quality)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

## Next Hop

- Continue review queue, or route to learn/quiz through `SKILL.md`.
