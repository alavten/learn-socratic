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

## Turn Contract

- Ask exactly one quiz item per turn.
- Return verdict + concise correction + one next question direction.
- Always include `summary` and `next_step`.

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

## Metacognitive Check

- Every 5 questions, run one brief self-check:
  - confidence before answer
  - actual outcome
  - likely error type (`concept_gap`, `memory_mixup`, `question_misread`, `unknown`)

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
