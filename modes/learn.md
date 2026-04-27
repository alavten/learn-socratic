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
   - analyze topic options + plan status and provide start recommendations
   - ask user to choose where to start (graph/topic or existing plan)
   - if user confirms, then `create_learning_plan(graph_id, topic_id?)` when needed
3. Fetch learn prompt context after user selection:
   - `get_learning_prompt(plan_id, topic_id?)`
4. Run Socratic teaching interaction with returned `prompt_text`.
5. Persist learning record for this turn:
   - `append_learning_record(plan_id, mode="learn", record_payload)`
   - minimum: `record_payload={"concept_id": "...", "result": "ok|partial|blocked"}`
   - recommended: include `score`, `difficulty_bucket`, and `latency_ms` for later quiz/review scheduling

## Turn Contract

- Ask at most one core learning check per turn.
- Keep explanation focused to one concept cluster each turn.
- Always return `summary` and one `next_step`.
- Separate learner restatement/check response from tutor explanation text.
- Do not infer learner mastery from system explanation content.
- Enforce concept lock per turn: explanation, check question, and verdict must all target the same `anchor_concept_id`.
- Do not introduce a new assessed concept in the same turn.

## AI Execution Directives

- Default to Feynman-style teaching loop:
  1. explain one concept briefly,
  2. ask learner to restate in own words,
  3. diagnose gap,
  4. re-explain with a simpler analogy or example.
- Keep one concept focus per turn; do not branch into multiple new concepts.
- If learner gives a correct restatement twice, recommend moving to `quiz`.
- Mastery diagnosis must use learner restatement/check answer only.
- Use a depth ladder for explanation/check alignment:
  - `L1 Recall`: definition and key terms
  - `L2 Understand`: distinguish/compare related concepts
  - `L3 Apply`: simple scenario application
  - `L4 Transfer`: novel scenario reasoning
- The check question depth must match current explanation depth (or one level lower when learner is blocked).

## Escalation Rule

- If learner answers correctly twice on same concept cluster, suggest moving to `quiz`.
- If learner is blocked, de-escalate with simpler framing and one clarifying example.
- Depth progression:
  - correct streak 2 -> next depth level on same concept
  - incorrect/blocked -> fallback one depth level and retry once

## Mode Exit Rule

- Exit to `quiz` when user asks for assessment or demonstrates stable understanding.
- Exit to `review` when context signals overdue or weak-point reinforcement.
- When exiting to `quiz`, quiz scope should be limited to concept(s) explicitly taught and checked in recent learn turns.

## Evidence Rule

- When correcting misunderstandings, cite concept/relation/evidence summaries from prompt context.
- If context is insufficient, explicitly state uncertainty and ask to narrow scope.

## Metacognitive Check

- Every 3-5 turns, ask one short calibration question:
  - expected confidence (0-100)
  - what was hard
  - what to review next

## Steps

1. If `plan_id` is missing, analyze available knowledge-graph topics and existing learning-plan status.
2. Provide ranked start suggestions and ask user to choose a start point.
3. Resolve scope from user choice, then call `get_learning_prompt(plan_id, topic_id?)`.
4. Select one `anchor_concept_id` from context and set current depth level.
5. Deliver explanation and ask one explicit learner restatement/check for that same anchor concept at matching depth.
6. Diagnose outcome from learner restatement/check answer only.
7. If ready for quiz, output a quiz handoff hint (`anchor_concept_id`, achieved depth, suggested first question style).
8. Write `append_learning_record(..., mode='learn', ...)` using learner-answer-based outcome.
9. Return recommended next step.

## Output

- `mode: learn`
- `content`
- `summary`
- `next_step`

## Retry / Fallback

- If `plan_id` is missing and user does not choose a suggestion, keep recommendation mode and do not auto-create plan.
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
