# Review Mode

## 适用场景

用户要求复习、间隔重复或巩固薄弱点。成功标准：从 `session_queue.current_item` 完成一轮检索式复习，且 `add_interaction_record(mode=review)` 已写入。

## 前置输入

| 项 | required | 说明 |
| --- | --- | --- |
| `plan_id` | yes | 学习计划 ID；缺失时交 `shared` |
| `topic_id` | no | 限定复习范围 |
| `session_context` | no | 上轮 `next_session_context`；含 `served_concept_ids`、`last_completed_concept_id`、`last_result` |

## 执行步骤

1. 会话首次：`get-api-spec --api-name get-review-context`。
2. 缺 `plan_id` → 停止，交 `shared`。
3. `get-mode-context --mode review --plan-id PLAN_ID [--topic-id TOPIC_ID] [--session-context-json JSON]`。
4. 按 `session_queue.current_item` 与 `prompt_text`：检索式提问 → 收答 → 判定 → `add-interaction-record`。
5. record 写入成功后，用 `next_session_context` 推进队列并生成下一题。

## 停止条件

| 场景 | 处理 |
| --- | --- |
| 缺 `plan_id` | 停止，交 `shared` |
| 无 due 项 | 建议轻量 `quiz` 或新 `learn` 任务 |
| record 写入失败 | 不推进队列、不 handoff；重试一次 |

## 下一步调整

- 成功 → 继续 `review` 队列
- 概念缺口（非记忆衰减）→ `learn`
- 用户要挑战验证 → `quiz`
- 失败 / 需澄清 → `shared`
- 每轮返回 `mode: review`、`summary`、`next_step`
