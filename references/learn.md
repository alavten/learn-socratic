# Learn Mode

## 适用场景

用户要求讲解、理解或带学新概念。成功标准：本轮完成 `context_summary.session_queue.current_item.concept_id` 的讲授与可选检查，且相关 `add_interaction_record` 已写入。

## 前置输入

| 项 | required | 说明 |
| --- | --- | --- |
| `plan_id` | yes | 学习计划 ID；缺失时交 `shared` 发现 |
| `topic_id` | no | 章节/主题范围；用户点名章节但未给 ID 时，先用 `get-knowledge-graph` 匹配 |
| `session_context` | no | 上轮 `next_session_context` 回传；含 `served_concept_ids`、`last_completed_concept_id`、`last_result` 等 |

## 执行步骤

1. 会话首次：`get-api-spec --api-name get-learn-context`。
2. 缺 `plan_id` → 停止，交 `shared`。
3. `get-mode-context --mode learn --plan-id PLAN_ID [--topic-id TOPIC_ID] [--session-context-json JSON]`。
4. 只讲授 `context_summary.session_queue.current_item.concept_id`；按返回的 `prompt_text` 交互。
5. 每讲完一概念、每判定一次学习者回答 → `add-interaction-record`（字段约束见 `get-api-spec --api-name add-interaction-record`）。
6. record 写入成功后，将 `context_summary.next_session_context`（判定后附加 `last_completed_concept_id`、`last_result`）传入下一轮 `get-mode-context`。
7. 若 `context_summary.suggested_plan_action.action` 为 `extend_learning_plan_topics`，先执行该 API 再继续 learn。

## 停止条件

| 场景 | 处理 |
| --- | --- |
| 缺 `plan_id` | 停止，交 `shared` 发现并选定 plan |
| context 获取失败 | 请用户确认 plan/topic |
| record 写入失败 | 不推进下一概念或切换 mode；重试一次并给出 recovery `next_step` |

## 下一步调整

- 成功 → 继续 `learn`，或用户要求时切 `quiz` / `review`
- 章节学完且 `suggested_plan_action` 出现 → `extend-learning-plan-topics` 后继续 learn
- 失败 / 需澄清 → `shared`
- 每轮返回 `mode: learn`、`summary`、`next_step`
