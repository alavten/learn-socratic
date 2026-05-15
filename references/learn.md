# Learn Mode Contract

## Trigger Conditions

- User asks to learn, understand, or be guided through concepts.

Required context: `plan_id`, optional `topic_id`, optional `session_context`.

## Runtime Execution Chain

1. Preflight (once per session): `get_api_spec("get_learn_context")`.
2. If `plan_id` is missing, route to `shared` for discovery tables and selection first.
3. Fetch learn prompt context after explicit user selection:
   - `get_learn_context(plan_id, topic_id?)`
4. Reconcile before a new round: if the prior turn taught a concept or judged a concept check but `add_interaction_record` did not succeed, flush the pending taught concept record or judged answer record now. Do not issue new explanation or a new check until the pending record is written or recovery is surfaced per Retry / Fallback.
5. Run Socratic teaching interaction with returned `prompt_text`.
6. Persist a learning record after each concept is taught:
   - `add_interaction_record(plan_id, mode="learn", record_payload)`
   - minimum: `record_payload={"concept_id": "...", "result": "partial"}`
   - recommended: include a conservative `score` and `difficulty_bucket` so exposure is tracked without treating explanation text as mastery evidence
   - MUST: after each concept is taught, write record immediately before any next concept/question/mode handoff
7. Persist another learning record when its concept check is judged:
   - `add_interaction_record(plan_id, mode="learn", record_payload)`
   - minimum: `record_payload={"concept_id": "...", "result": "ok|partial|blocked"}`
   - recommended: include `score`, `difficulty_bucket`, and `latency_ms` for later quiz/review scheduling
   - MUST: after each concept check answer is received and judged, write record immediately before any next concept/question/mode handoff

## Turn Contract

- Ask at most one core learning check per turn.
- Keep explanation focused to one concept cluster each turn.
- Always return `summary` and one `next_step`.
- Separate learner restatement/check response from tutor explanation text.
- Do not infer learner mastery from system explanation content.
- Enforce concept lock per turn: explanation, check question, and verdict must all target the same `anchor_concept_id`.
- Do not introduce a new assessed concept in the same turn.
- Do not introduce any next concept until the taught concept record and any judged answer record for the current `anchor_concept_id` have succeeded or recovery is surfaced.

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

## Output

- `mode: learn`
- `content`
- `summary`
- `next_step`

## Retry / Fallback

- If `plan_id` is missing, do not run local recommendation logic; route to `shared`.
- If context retrieval fails, ask user for plan/topic confirmation.
- If write fails, do not advance to next concept/question/mode handoff; retry once and return explicit recovery `next_step`.

## Minimal Record Payload

- `concept_id` (required)
- `result` (recommended)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

When `result` is `partial` or `blocked`, prefer an explicit **low** `score` (ratio roughly **≤0.55** for partial, **≤0.35** for blocked, or equivalent percent); omitting `score` still yields low mastery defaults server-side.

Multiple records for the same `concept_id` are valid append-only learning events. Do not collapse taught concept records and judged answer records into one record when both events occurred.

When the learner expands to additional chapters or sections under the same graph, call `extend_learning_plan_topics(plan_id, topic_ids)` so prompt scope and plan metadata stay aligned with the chapters being studied.

## Next Hop

- Continue learn, or route to quiz/review through `SKILL.md`.
