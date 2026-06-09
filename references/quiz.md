# Quiz Mode

## 适用场景

用户要求测验、刷题或检查掌握程度。成功标准：每道已判定题各写一条 `add_interaction_record(mode=quiz)`；`per_chapter` 时 turn 末 `record_summary.written == record_summary.expected`。

## 前置输入

| 项 | required | 说明 |
| --- | --- | --- |
| `plan_id` | yes | 学习计划 ID；缺失时交 `shared` |
| `topic_id` | no | 限定测验范围 |
| `session_context` | no | 可含 `quiz_pacing`、`pacing_hint`、`batch_size`、`pending_items`、`served_concept_ids`；pacing 由脚本解析 |

## 执行步骤

1. 会话首次：`get-api-spec --api-name get-quiz-context`。
2. 缺 `plan_id` → 停止，交 `shared`。
3. 新回合前：若上轮有已判定但未落库的题，先补写 `add-interaction-record`。
4. `get-mode-context --mode quiz --plan-id PLAN_ID [--topic-id TOPIC_ID] [--session-context-json JSON]`；读取 `context_summary.quiz_pacing` 与 `prompt_text`。
5. 按 `prompt_text` 出题 → 收答 → 判定 → 每题 `add-interaction-record`（下一题或切换 mode 前必须写完）。
6. `per_chapter`：回合结束前输出 `record_summary`（`expected`、`written`、`failed`），`written == expected` 方可 handoff。

## 停止条件

| 场景 | 处理 |
| --- | --- |
| 缺 `plan_id` | 停止，交 `shared` |
| quiz context 缺失 | 请用户缩小 topic 或重选 plan |
| record 未齐（`per_chapter`） | 留在 quiz 补写或 recovery，不 handoff |
| record 写入失败 | 同轮不推下一题、不切换 mode |

## 下一步调整

- 成功 → 继续 `quiz`
- 概念缺口 → `learn`（当前 turn record 义务完成后）
- 需巩固 → `review`（record 义务完成后）
- 失败 / 需澄清 → `shared`
- 每轮返回 `mode: quiz`、`quiz_pacing`、`summary`、`next_step`
