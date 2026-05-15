# Review Mode Contract

## Trigger Conditions

- User asks for review, recap, spaced repetition, or due revisions.

Required context: `plan_id`, optional `topic_id`, optional `session_context`.

## Runtime Execution Chain

1. Preflight (once per session): `get_api_spec("get_review_context")`.
2. If `plan_id` is missing, route to `shared` for discovery tables and selection first.
3. Bootstrap review session:
   - `get_review_context(plan_id, topic_id?)`
   - build queue snapshot from candidate scope and ranking policy
4. Execute one concept turn from queue head.
5. Persist review result after each concept automatically:
   - `add_interaction_record(plan_id, mode="review", record_payload)`
   - MUST: after each learner answer is judged, write record immediately before queue advance, `next_question`, or mode handoff
6. After successful record write, advance queue pointer and generate next concept prompt.

## Queue Policy

- Build one queue snapshot at session start; do not re-rank by latest item on every turn.
- Resolve scope by `plan_id` + optional `topic_id`; do not cross scope when `topic_id` is provided.
- Candidate sources: overdue tasks, high forgetting-risk states, recent incorrect concepts, short-window upcoming items.
- Exclude concepts already served in current session unless one immediate retry is required.
- Rank by weighted signal (overdue pressure, forgetting risk, weak-point streak, recency gap); tie-break by earlier `due_at`, then higher risk, then lower recent accuracy.
- Never use latest-created/latest-updated as primary selector.

## Turn Contract

- One concept-focused review turn at a time unless user asks for recap.
- Always return `summary` and one actionable `next_step`.
- Return `next_session_context` so the next call can continue the queue safely.

## AI Execution Directives

- Process one concept per turn from queue head.
- Keep answer attribution strict:
  - learner answer text is the only source for correctness judgment
  - system correction/explanation is feedback only
- Use short retrieval prompts first; only give full explanation after learner attempt.
- After each turn: append learning record, update queue state after successful record write, provide detailed source-grounded explanation for this question, and provide direct next question content only after the write succeeds.
- Always return `summary` and `next_step`.

## Loop Guard

- Maintain `served_concept_ids` for current session and advance queue pointer monotonically.
- Do not reselect same concept in same session unless current attempt is incorrect and one immediate retry is allowed.
- After one retry, force move to next queue item.

## Escalation Rule

- If recall is consistently correct, widen interval suggestion and move to next due item.
- If recall is incorrect, narrow scope and re-test same concept once with simpler prompt.

- Interval suggestion policy:
  - high confidence + correct -> widen
  - uncertain + correct -> keep
  - incorrect -> shorten

## Mode Exit Rule

- Exit to `learn` when the issue is conceptual gap, not memory decay.
- Exit to `quiz` when user requests challenge-level verification.

## Evidence Rule

- Prioritize due-item evidence (`priority_reasons`, risk summary) in explanations.
- Keep correction anchored to context materials; do not overgeneralize outside scope.
- The explanation must include detailed original-context grounding (key definition/relationship/evidence quotes or close paraphrase).
- Never skip explanation even when learner answer is correct.

## Output

- `mode: review`
- `review_items_or_feedback`
- `detailed_explanation`
- `next_question`
- `summary`
- `next_step`

## Retry / Fallback

- If due items are empty, suggest a light quiz or new learning task.
- If persistence fails, retain user-visible feedback and retry commit once.
- Advance queue, emit the next question, or hand off to `learn` / `quiz` only after successful record write.
- If auto-next fetch fails, provide a manual `next_step` fallback prompt for the nearest due concept.
- If queue construction is incomplete, degrade to overdue-first scan instead of latest-item fallback.
- If `plan_id` is missing, do not run local recommendation logic; route to `shared`.
- If record write still fails after one retry, do not continue to next concept in current turn.

## Minimal Record Payload

- `concept_id` (required)
- `result` (required for state quality)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

## Next Hop

- Continue review queue, or route to learn/quiz through `SKILL.md`, only after the current review result record write succeeds.
