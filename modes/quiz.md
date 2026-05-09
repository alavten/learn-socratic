# Quiz Mode Contract

## Trigger Conditions

- User asks for testing, checking mastery, or practice questions.

Required context: `plan_id`, optional `topic_id`, optional `session_context`.

## Runtime Execution Chain

1. Preflight (once per session): `get_api_spec("get_quiz_context")`.
2. If `plan_id` is missing, route to `shared` for discovery tables and selection first.
3. Fetch quiz context:
   - `get_quiz_context(plan_id, topic_id?)`
4. Generate questions and collect learner answers.
5. Evaluate only learner answers first, then explain through model logic.
6. Persist result:
   - `add_interaction_record(plan_id, mode="quiz", record_payload)`
   - MUST: after each learner answer is judged, write record immediately before emitting next question

## Turn Contract

- Ask exactly one quiz item per turn.
- Return verdict + concise correction + one next question direction.
- Always include `summary` and `next_step`.
- Separate learner answer from system explanation in output/state.
- Never treat system explanation/correction text as learner answer.

## AI Execution Directives

- Generate one question at a time using SOLO depth progression:
  - `Uni-structural`: single fact/definition
  - `Multi-structural`: list/classify multiple elements
  - `Relational`: explain relationships/causality
  - `Extended Abstract`: transfer to a novel scenario
- Tie each question to one UBD evidence facet:
  - `Explain`, `Interpret`, `Apply`, `Perspective`, `Self-Knowledge`
- Use retrieval-first behavior: ask first, evaluate second, explain third.
- Rotate variant style for the same concept to avoid recognition bias.
- Scoring must be based on explicit learner response spans only.
- If learner response is missing/ambiguous, mark result as `partial` or `blocked`, not `correct`.

## Escalation Rule

- Correct answer streak (>=2) escalates depth/complexity.
- Incorrect answer de-escalates one level and retries same concept once.

- Escalation target:
  - streak 2 -> next SOLO level
  - streak 3+ -> keep level and increase scenario complexity

## Mode Exit Rule

- Exit to `learn` when repeated conceptual confusion is detected.
- Exit to `review` when enough quiz evidence indicates retention risk scheduling is needed.

## Evidence Rule

- Feedback must reference quiz context signals (`history_performance_summary`, concept scope).
- Avoid unsupported claims beyond retrieved context.

## Output

- `mode: quiz`
- `questions_or_feedback`
- `summary`
- `next_step`

## Retry / Fallback

- If quiz context is missing, request narrower topic or plan selection.
- If scoring payload is incomplete, persist a partial record with a warning tag.
- If `plan_id` is missing, do not run local recommendation logic; route to `shared`.
- If record write fails, return recovery guidance with **no next question in same turn**; do not push next question until retry succeeds or user confirms recovery action.

## Minimal Record Payload

- `concept_id` (required)
- `result` (required for state quality)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

**Partial / blocked scoring**: use `partial` or `blocked` when the learner answer is ambiguous or missing; pair them with **low** scores (ratio **≤0.55** / **≤0.35** respectively, or equivalent percent). Contradictory payloads (e.g. `blocked` + near-perfect score) are rejected by validation.

## Next Hop

- Route to learn for weak points or review for due items.
