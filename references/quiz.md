# Quiz Mode Contract

## Trigger Conditions

- User asks for testing, checking mastery, or practice questions.

Required context: `plan_id`, optional `topic_id`, optional `session_context`.

## Quiz Pacing

`quiz_pacing` controls how many questions appear in one user turn, not how records are stored. **Every judged answer still produces exactly one `add_interaction_record(mode="quiz")`.**

| Value | When to use | Question count |
| ----- | ----------- | -------------- |
| `per_concept` | Recent `learn` was one concept per turn, or user asks for one-at-a-time / 一题一题 | One anchor `concept_id` per turn; simple concepts 1 question; complex concepts 2–3 questions in the same turn (each judged answer → one record) |
| `per_chapter` | Recent `learn` covered a whole chapter or many concepts at once, or user asks for batch / 批量 / 一章测验 | Question list for scope concepts; simple concept 1 question, complex concept 2–3; total ≤ `constraints.max_question_count` from `get_quiz_context` |

**Default selection** (user may override explicitly):

1. If user says 一题一题 / 逐题 → `per_concept`.
2. If user says 批量 / N 题 / 一章测验 → `per_chapter` (honor N when given).
3. Else infer from recent `learn` granularity: single-concept learn → `per_concept`; multi-concept or chapter learn → `per_chapter`.
4. If still ambiguous → `per_concept`.

Pass `quiz_pacing` and optional `batch_size` in `session_context` when calling `get_quiz_context`; persist `next_session_context` from the API response for the next quiz turn.

## Runtime Execution Chain

1. Preflight (once per session): `get_api_spec("get_quiz_context")`.
2. If `plan_id` is missing, route to `shared` for discovery tables and selection first.
3. **Reconcile** before a new quiz round: if the prior turn judged any answer but `add_interaction_record` did not succeed for that item, flush pending records now. Do not emit new questions until pending writes succeed or recovery is surfaced per Retry / Fallback.
4. Fetch quiz context:
   - `get_quiz_context(plan_id, topic_id?, session_context?)`
5. Select `quiz_pacing` per **Quiz Pacing** (use `context_summary.quiz_pacing` when API already resolved it).
6. Generate questions and collect learner answers per active turn contract below.
7. Evaluate only learner answers first, then explain through model logic.
8. Persist results:
   - `add_interaction_record(plan_id, mode="quiz", record_payload)`
   - MUST: after each learner answer is judged, write record immediately before emitting the next question in the same turn or handing off modes
9. End-of-turn check (`per_chapter` or multi-question `per_concept`): `record_summary.written` must equal `record_summary.expected` before mode handoff.

## Turn Contract

Shared rules (both pacings):

- Always return `summary`, `next_step`, and `quiz_pacing`.
- Separate learner answer from system explanation in output/state.
- Never treat system explanation/correction text as learner answer.
- Do not hand off to `learn` / `review` / next chapter until required records for the current turn are written or recovery is surfaced.
- Multiple records for the same `concept_id` are valid append-only learning events.

### `per_concept`

- Focus one anchor `concept_id` per turn unless the user explicitly continues the same concept.
- Ask 1 question by default; for complex concepts (rich relations/evidence in context), up to 3 questions on the same `concept_id` in one turn.
- Return verdict + concise correction after each answer; optional brief pointer to the next question within the same concept.
- MUST: after each judged answer, write record before the next question on the same turn or any mode handoff.

### `per_chapter`

- Emit a numbered question list: each item has `item_id`, `concept_id`, and the question text (question phase: no answers/verdicts).
- Collect learner answers (one message or several); align each answer to `item_id` / `concept_id` before judging.
- Judge and `add_interaction_record` in item order; do not skip items.
- Before turn end, output `record_summary` with `expected`, `written`, and `failed` (items that could not be written).
- MUST: `written == expected` before handoff; if not, stay in quiz recovery (no `learn` / `review` / next chapter).

## AI Execution Directives

- Use SOLO depth progression for all questions:
  - `Uni-structural`: single fact/definition
  - `Multi-structural`: list/classify multiple elements
  - `Relational`: explain relationships/causality
  - `Extended Abstract`: transfer to a novel scenario
- Tie each question to one UBD evidence facet: `Explain`, `Interpret`, `Apply`, `Perspective`, `Self-Knowledge`
- Use retrieval-first behavior: ask first, evaluate second, explain third.
- Rotate variant style for the same concept to avoid recognition bias.
- Scoring must be based on explicit learner response spans only.
- If learner response is missing/ambiguous, mark result as `partial` or `blocked`, not `correct`.
- **`per_concept`**: pace like a tutor—one anchor concept, sequential micro-questions when complexity warrants.
- **`per_chapter`**: plan the full item list up front; complexity drives `items_per_concept` (1–3); cap total items at `max_question_count`.

## Escalation Rule

- Correct answer streak (>=2) escalates depth/complexity.
- Incorrect answer de-escalates one level and retries same concept once.

- Escalation target:
  - streak 2 -> next SOLO level
  - streak 3+ -> keep level and increase scenario complexity

## Mode Exit Rule

- Exit to `learn` when repeated conceptual confusion is detected, only after current turn record obligations are met.
- Exit to `review` when enough quiz evidence indicates retention risk scheduling is needed, only after current turn record obligations are met.

## Evidence Rule

- Feedback must reference quiz context signals (`history_performance_summary`, concept scope).
- Avoid unsupported claims beyond retrieved context.

## Output

- `mode: quiz`
- `quiz_pacing`: `per_concept` | `per_chapter`
- `questions_or_feedback`
- `record_summary`: `{ expected, written, failed: [{ concept_id, item_id? }] }` (required whenever any answer was judged in the turn)
- `items` (required for `per_chapter` after question phase): `[{ item_id, concept_id, record_write?: ok|failed }]`
- `summary`
- `next_step`

## Retry / Fallback

- If quiz context is missing, request narrower topic or plan selection.
- If scoring payload is incomplete, persist a partial record with a warning tag.
- If `plan_id` is missing, do not run local recommendation logic; route to `shared`.
- If record write fails, return recovery guidance with **no next question or mode handoff in same turn**; do not push next question until retry succeeds or user confirms recovery action.
- **`per_chapter`**: if any item in `record_summary.failed` is non-empty, do not hand off modes; retry failed items or surface recovery.

## Minimal Record Payload

- `concept_id` (required)
- `result` (required for state quality)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

**Partial / blocked scoring**: use `partial` or `blocked` when the learner answer is ambiguous or missing; pair them with **low** scores (ratio **≤0.55** / **≤0.35** respectively, or equivalent percent). Contradictory payloads (e.g. `blocked` + near-perfect score) are rejected by validation.

## Next Hop

- Route to learn for weak points or review for due items only after all judged answers in the current turn have successful record writes (or explicit recovery).
