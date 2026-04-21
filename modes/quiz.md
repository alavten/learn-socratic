# Quiz Mode Contract

## Trigger Conditions

- User asks for testing, checking mastery, or practice questions.

## Inputs

- `plan_id`
- Optional `topic_id`
- `session_context`

## Command Invocation

- Recommended executable format:
  - `python scripts/cli.py get-quiz-prompt --plan-id PLAN_ID --topic-id t1`
  - `python scripts/cli.py append-learning-record --plan-id PLAN_ID --mode quiz --concept-id c1 --result correct --score 78 --difficulty-bucket hard`

## Runtime Execution Chain

1. Preflight (once per session): `list_apis()` and `get_api_spec("get_quiz_prompt")`.
2. If `plan_id` missing:
   - `list_knowledge_graphs()`
   - `list_learning_plans()`
   - `create_learning_plan(graph_id, topic_id?)`
3. Fetch quiz context:
   - `get_quiz_prompt(plan_id, topic_id?)`
4. Generate questions and collect learner answers.
5. Score and explain through model logic.
6. Persist result:
   - `append_learning_record(plan_id, mode="quiz", record_payload)`

## Steps

1. Resolve scope and call `get_quiz_prompt(plan_id, topic_id?)`.
2. Generate questions, collect answers, and evaluate outcomes.
3. Write `append_learning_record(..., mode='quiz', ...)`.
4. Return feedback and targeted follow-up suggestions.

## Output

- `mode: quiz`
- `questions_or_feedback`
- `summary`
- `next_step`

## Retry / Fallback

- If quiz context is missing, request narrower topic or plan selection.
- If scoring payload is incomplete, persist a partial record with a warning tag.

## Minimal Record Payload

- `concept_id` (required)
- `result` (required for state quality)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

## Next Hop

- Route to learn for weak points or review for due items.
