# Shared Mode Contract

## Trigger Conditions

- User intent is unclear or conflicting.
- Required context is missing (`plan_id`, `topic_id`, or target graph).
- A mode workflow cannot continue due to recoverable validation errors.

## Inputs

- `user_input`
- `session_context`
- Optional: `last_mode`, `last_error`

## Execution Best Practices

- Treat this mode as a short router, not a teaching mode.
- Resolve intent quickly, then hand off to target mode.
- Keep cross-mode API details in `SKILL.md` and target mode files.

## Intent Matrix

| User phrase pattern | Routed mode |
| --- | --- |
| 学习/讲解/不懂 | `learn` |
| 考我/测试/出题 | `quiz` |
| 复习/回顾/到期 | `review` |
| 导入资料/建图/更新图谱 | `ingest` |
| 继续/下一个 | current mode |

## Steps

1. Ask one concise clarification question to resolve intent or missing context.
2. Normalize context into a mode-ready payload.
3. Route by intent matrix and confirm target mode.
4. If `plan_id` is missing (learn/quiz/review): discover graph/plan and create one when needed.
5. Return control to router (`SKILL.md`) for final mode selection.

## AI Execution Directives

- Ask at most one clarification question before rerouting.
- Prefer natural language cues over explicit command words.
- If intent remains ambiguous after one retry, default to `learn` with safe scope.

## Output

- `mode`: keep as `shared` for clarification turn, then hand off to resolved mode
- `clarification_question`: one concise question used for disambiguation
- `resolved_mode`: `ingest`/`learn`/`quiz`/`review` or `null` when still unclear
- `summary`: concise clarification result
- `next_step`: recommended mode transition

## Retry / Fallback

- Retry once with simplified options.
- If still unresolved, default to safe learning overview and ask user to choose mode.

## Next Hop

- Must exit to router after a single clarification loop.
