# Ingest Mode

## 适用场景

用户要求导入资料、建图或更新图谱。一书一图、按章增量 ingest 见 `SKILL.md` Session Guardrails。成功标准：`validation_summary.ok=true`，返回 `graph_id`、`version`、`change_summary`。

## 前置输入

| 项 | required | 说明 |
| --- | --- | --- |
| `graph_id` | yes | 全书稳定 slug，各章复用同一 ID |
| `payload_file` | yes | 仅内层 `structured_payload` JSON；禁止 `{graph_id, structured_payload}` 包装 |
| `session_context` | no | 多章进度标记（已 ingest 章次等） |

## 执行步骤

1. 会话首次：`get-api-spec --api-name ingest-knowledge-graph`。
2. `ingest-knowledge-graph --graph-id GRAPH_ID --payload-file PATH`（每轮一章增量）。
3. 读 `validation_summary`：`ok=true` 时回报 `version`、`change_summary`；`ok=false` 时列出最多 5 条字段级错误。
4. 可选：`create-learning-plan --graph-id GRAPH_ID [--topic-id TOPIC_ID]`。
5. **书序修正**（章节顺序与目录不符时）：
   - `get-knowledge-graph --graph-id GRAPH_ID`
   - 由 LLM 产出某一兄弟组完整 `topic_ids` 有序列表
   - `reorder-graph-topics --graph-id GRAPH_ID --payload-file PATH`（每个 `parent_topic_id` 单独一次；payload 形状见 `get-api-spec --api-name reorder-graph-topics`）

## 停止条件

| 场景 | 处理 |
| --- | --- |
| payload 无法解析 | 停止，返回 parse 错误 |
| validation `ok=false` | 不建 plan、不写 learning record；请求修正 payload |
| reorder 缺/重复 `topic_id` | 对照 `get-knowledge-graph` 修正列表后重试 |

## 下一步调整

- 成功、尚有未导入章 → 继续 `ingest` 下一章
- 成功且用户要学 → `learn`（全书完成前默认不切 learn，除非用户明确要求边导边学）
- validation 失败 → 留在 `ingest` 修 payload
- 书序已修正 → `learn` / `quiz` / `review`
- 每轮返回 `mode: ingest`、`summary`、`next_step`
