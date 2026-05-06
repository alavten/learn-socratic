# Review Mode Contract

## Trigger Conditions

- User asks for review, recap, spaced repetition, or due revisions.

## Inputs

- `plan_id`
- Optional `topic_id`
- `session_context`

## Command Invocation

- Recommended executable format:
  - `python -m scripts.cli.main get-mode-context --mode review --plan-id PLAN_ID --topic-id t1`
  - `python -m scripts.cli.main add-interaction-record --context-id PLAN_ID --mode review --concept-id c1 --result correct --score 90 --difficulty-bucket easy`

## Runtime Execution Chain

1. Preflight (once per session): `get_api_spec("get_review_context")`.
2. If `plan_id` missing:
   - `list_knowledge_graphs()`
   - `list_learning_plans()`
   - provide ranked plan/topic start options and ask user to choose
   - only call `create_learning_plan(graph_id, topic_id?)` after explicit user confirmation
3. Bootstrap review session:
   - `get_review_context(plan_id, topic_id?)`
   - build queue snapshot from candidate scope and ranking policy
4. Execute one concept turn from queue head.
5. Persist review result after each concept automatically:
   - `add_interaction_record(plan_id, mode="review", record_payload)`
6. Advance queue pointer and generate next concept prompt.

## Session Bootstrap

- Build one queue snapshot at session start; do not re-rank by latest item on every turn.
- Resolve scope by `plan_id` + optional `topic_id`; do not cross scope when `topic_id` is provided.
- Seed queue from due tasks, weak-point history, and near-due candidates.

## Candidate Pool

- Include candidate concepts from:
  1. overdue review tasks
  2. high forgetting risk states
  3. recent incorrect concepts (weak points)
  4. upcoming due concepts in short window
- Exclude concepts already served in current session, unless retry is required by escalation rule.

## Ranking Policy

- Compute ranked queue with a weighted score from:
  - overdue pressure
  - forgetting risk
  - weak-point/error streak
  - recency gap
- Tie-break order:
  1. earlier `due_at`
  2. higher forgetting risk
  3. lower recent accuracy
- Never use latest-created/latest-updated as primary selector.

## Turn Contract

- One concept-focused review turn at a time unless user asks for recap.
- Always return `summary` and one actionable `next_step`.
- Return `next_session_context` so the next call can continue the queue safely.

## Turn Execution

## AI Execution Directives

- Process one concept per turn from queue head.
- Keep answer attribution strict:
  - learner answer text is the only source for correctness judgment
  - system correction/explanation is feedback only
- Use short retrieval prompts first; only give full explanation after learner attempt.
- After each turn: append learning record, update queue state, provide detailed source-grounded explanation for this question, and provide direct next question content.
- Always return `summary` and `next_step`.

## Loop Guard

- Maintain `served_concept_ids` for current session and advance queue pointer monotonically.
- Do not reselect same concept in same session unless:
  1. current attempt is incorrect, and
  2. one immediate retry is allowed.
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

## Spacing Policy Hint

- Convert `forgetting_risk` to review urgency:
  - `>= 0.7`: immediate review
  - `0.4 - 0.69`: same session or next short window
  - `< 0.4`: normal cadence

## Steps

1. Resolve scope and call `get_review_context(plan_id, topic_id?)`.
2. Build queue snapshot from candidate pool and ranking policy.
3. Select queue head and ask one retrieval question.
4. Capture explicit learner attempt and judge from learner answer only.
5. Provide detailed original-context explanation for this question after judgment.
6. Automatically write `add_interaction_record(..., mode='review', ...)`.
7. Update session queue (`served_concept_ids`, pointer advance, retry flags).
8. Automatically provide next concept question and recommended next review window.

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
- If auto-next fetch fails, provide a manual `next_step` fallback prompt for the nearest due concept.
- If queue construction is incomplete, degrade to overdue-first scan instead of latest-item fallback.
- If `plan_id` is missing and user does not choose an option, stay in recommendation mode and do not auto-create plan.

## Minimal Record Payload

- `concept_id` (required)
- `result` (required for state quality)
- `score` (recommended)
- `difficulty_bucket` (`easy|medium|hard`, recommended)
- `latency_ms` (optional)

## Next Hop

- Continue review queue, or route to learn/quiz through `SKILL.md`.
