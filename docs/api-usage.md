# API Usage Guide

本文档面向调用方，说明 `orchestration_app_service` 的可用 API、典型入参和响应示例。

## 双视图入口

### User Journey View（按目标选择）

1. 资料入图：`ingest-knowledge-graph`
2. 建立学习计划：`create-learning-plan`
3. 学习讲解：`get-mode-context --mode learn`
4. 测验评估：`get-mode-context --mode quiz`
5. 复习强化：`get-mode-context --mode review`
6. 结果回写：`add-interaction-record`

### System Operator View（按运维操作）

- API 发现：`list-apis`、`get-api-spec`
- 图谱运维：`list-knowledge-graphs`、`get-knowledge-graph`、`ingest-knowledge-graph`、`remove-knowledge-graph-entities`
- 学习运维：`list-learning-plans`、`create-learning-plan`、`extend-learning-plan-topics`
- 交互运行：`get-mode-context --mode learn` / `get-mode-context --mode quiz` / `get-mode-context --mode review`
- 记录提交：`add-interaction-record`

补充说明：
- 学习路径导航（用户视角）在 `README.md`。
- 本文档作为系统调用细节的单一维护源。

## 文档分工说明

- `modes/*.md` 负责交互契约（如何问、如何反馈、输出字段要求）。
- `docs/architecture-design.md` 与本文档负责编排执行链（API 调用顺序、上下文组装、状态推进）。
- 当两者出现流程细节冲突时，以编排文档（`architecture-design.md` + 本文档）为准；模式文档不重复维护 API 调用顺序。

## 使用方式

```python
from scripts.app import create_app

service = create_app()
```

```bash
python -m scripts.cli.main list-apis
```

---

## 1) 元信息 API

### `list_apis()`

返回可调用 API 列表。

**请求**

```json
{}
```

**响应示例**

```json
[
  {
    "name": "create_learning_plan",
    "version": "v1",
    "summary": "Create a new plan",
    "tags": ["learning", "write"],
    "stability": "stable"
  }
]
```

### `get_api_spec(api_name)`

返回指定 API 入参规范。

**请求示例**

```json
{
  "api_name": "create_learning_plan"
}
```

**响应示例**

```json
{
  "name": "create_learning_plan",
  "input_schema": {
    "type": "object",
    "required": ["graph_id"]
  }
}
```

---

## 2) 知识图谱 API

### `list_knowledge_graphs(limit=20, offset=None)`

**请求示例**

```json
{
  "limit": 20,
  "offset": null
}
```

**响应示例**

```json
{
  "items": [
    {
      "graph_id": "g1",
      "name": "Python Basics",
      "revision": 1,
      "status": "active",
      "topic_count": 2,
      "concept_count": 2,
      "updated_at": "2026-04-21T10:00:00+00:00"
    }
  ],
  "has_more": false,
  "next_offset": null
}
```

### `get_knowledge_graph(graph_id, topic_id=None, concept_limit=20, offset=None)`

**请求示例**

```json
{
  "graph_id": "g1",
  "topic_id": "t1",
  "concept_limit": 20,
  "offset": null
}
```

**响应示例**

```json
{
  "graph": {
    "graph_id": "g1",
    "name": "Python Basics",
    "graph_type": "domain",
    "schema_version": "1.0.0",
    "release_tag": "r1",
    "revision": 1,
    "status": "active"
  },
  "topics": [],
  "topic_concepts": [],
  "concept_briefs": [],
  "has_more": false,
  "next_offset": null
}
```

### `ingest_knowledge_graph(graph_id, structured_payload)`

CLI `--payload-file` 约定：
- 仅传 `structured_payload` 对象本体（`graph/concepts/relations/...`）。
- 不要传 API 包装体 `{ "graph_id": "...", "structured_payload": {...} }`，`graph_id` 通过 CLI 参数单独提供。

**请求示例**

```json
{
  "graph_id": "g1",
  "structured_payload": {
    "graph": {
      "graph_type": "domain",
      "graph_name": "Python Basics",
      "schema_version": "1.0.0",
      "release_tag": "r1"
    },
    "topics": [
      {
        "topic_id": "t1",
        "topic_name": "Syntax",
        "topic_type": "chapter",
        "sort_order": 1
      }
    ],
    "concepts": [
      {
        "concept_id": "c1",
        "canonical_name": "Variable",
        "definition": "A named storage location.",
        "concept_type": "fundamental",
        "difficulty_level": "easy"
      }
    ],
    "relations": [],
    "evidences": [],
    "relation_evidences": []
  }
}
```

**成功响应示例**

```json
{
  "graph_id": "g1",
  "version": 1,
  "change_summary": {
    "topics_upserted": 1,
    "concepts_upserted": 1,
    "relations_upserted": 0,
    "evidences_upserted": 0,
    "relation_evidence_upserted": 0,
    "topic_concepts_upserted": 0
  },
  "validation_summary": {
    "ok": true,
    "errors": [],
    "warnings": []
  }
}
```

**失败响应示例（关系无证据）**

```json
{
  "graph_id": "g1",
  "version": null,
  "change_summary": {},
  "validation_summary": {
    "ok": false,
    "errors": ["relation r1 has no evidence link"],
    "warnings": []
  },
  "detail": {
    "failed_items": ["relation r1 has no evidence link"]
  }
}
```

**常见字段映射错误（需避免）**

- `relations` 必填：`concept_relation_id / from_concept_id / to_concept_id / relation_type`
  - 错误示例：`relation_id / from / to / type`
- `evidences` 必填：`evidence_id / quote_text`
  - 错误示例：`concept_id / evidence_text`
- `relation_evidences` 必填：`relation_evidence_id / concept_relation_id / evidence_id`
- `topic_concepts` 必填：`topic_concept_id / topic_id / concept_id`
  - **一致性**：`topic_concepts` 非空时，`topics` 也必须非空；每条 `topic_id` 必须出现在 `topics` 中（否则会在校验阶段失败，而不会拖到 SQLite 外键）。
- `concepts` 必填：`concept_id / canonical_name / definition`
  - 错误示例：`name` 代替 `canonical_name`
- `topics` 必填：`topic_id / topic_name / topic_type`
  - `topic_type` 仅允许 `chapter` | `section`；缺失或非枚举值会被校验拒收（不会再被静默降级为 `section`）。
  - 顶层（`parent_topic_id` 为空）建议用 `chapter`；`section` 应挂在 `chapter` 之下，校验器会对违例情况发出 warning。

#### 可选：`sync_mode` / `prune_scope` / `force_delete`

- `sync_mode`：`upsert_only`（默认）或 `upsert_and_prune`。后者在**成功写入**当前 payload 后，在 `prune_scope` 限定的概念集合内，将**库中存在但本次 payload 未出现**的概念与相关关系做**硬删除**。
- `prune_scope`：至少提供 `topic_ids` 和/或非空 `concept_id_prefix`，避免误删整图。
- `force_delete`：剪枝时若学习计划仍引用待删概念，默认阻断；为 `true` 时先清理学习域引用（任务、状态、记录、计划-主题行）再删图谱。

CLI 示例：

```bash
python -m scripts.cli.main ingest-knowledge-graph --graph-id g1 --payload-file ./payload.json \
  --sync-mode upsert_and_prune --prune-topic-ids t1,t2 --force-delete
```

#### 历史修复示例：补齐曾缺失的 Concept（如 `cc-ch2-*`）

若 `topic_concepts` 引用了尚未写入 `Concept` 表的 `concept_id`，入库会因 `TopicConcept → Concept` 外键失败且整笔事务回滚。处理方式：

1. 在权威 payload 的 `concepts` 数组中增加对应节点（或使用仓库内示例片段 [`tests/fixtures/cc_ch2_supplement_concepts.json`](../tests/fixtures/cc_ch2_supplement_concepts.json) 合并进你的 JSON）。
2. 重新执行 `ingest_knowledge_graph`（与学习计划所用 `graph_id` 一致）。
3. 若还需补学习遥测，在图谱已对齐后对每条概念照常使用通用 CLI `add-interaction-record`（见本文第 5 节及文中示例），不要使用单独的专用修补子命令。

### `remove_knowledge_graph_entities(graph_id, remove_payload, force_delete=False)`

编排层**先**调用学习域 `check_plan_dependencies`，存在依赖且 `force_delete=false` 时返回 `dependency_conflict`；通过或强制删除时再调用图谱域硬删除。

**`remove_payload` 示例**（`--payload-file` 文件内容）

```json
{
  "concept_ids": ["c1"],
  "relation_ids": ["r1"],
  "topic_ids": ["t1"]
}
```

至少一个数组非空。

**CLI**

```bash
python -m scripts.cli.main remove-knowledge-graph-entities --graph-id g1 --payload-file ./remove.json --force-delete
```

**依赖冲突响应（节选）**

```json
{
  "error": "dependency_conflict",
  "graph_id": "g1",
  "forced": false,
  "blocking_dependencies": [
    { "plan_id": "...", "dep_type": "learning_task", "entity_id": "c1" }
  ]
}
```

### `get_concepts(graph_id, concept_scope, detail='brief', concept_limit=20, offset=None)`

**请求示例**

```json
{
  "graph_id": "g1",
  "concept_scope": {
    "topic_ids": ["t1"]
  },
  "detail": "brief",
  "concept_limit": 20,
  "offset": null
}
```

### `get_concept_relations(graph_id, concept_scope, depth=1, relation_limit=50)`

**请求示例**

```json
{
  "graph_id": "g1",
  "concept_scope": {
    "concept_ids": ["c1"]
  },
  "depth": 1,
  "relation_limit": 50
}
```

### `get_concept_evidence(graph_id, concept_scope, mode='summary', evidence_limit=20)`

**请求示例**

```json
{
  "graph_id": "g1",
  "concept_scope": {
    "concept_ids": ["c1"]
  },
  "mode": "summary",
  "evidence_limit": 20
}
```

---

## 3) 学习计划与上下文 API

### `list_learning_plans(limit=20, offset=None)`

**进度语义**：每条计划里的 `progress.completed_tasks` / `progress.pending_tasks` 统计 **LearningTask** 队列状态（不是「已学完章节数」）。同一字段中还包含：

- `progress.concepts_touched`：该计划下已有掌握状态行的 **distinct 概念数**；
- `progress.records_by_mode`：`LearningRecord` 按 `learn` / `quiz` / `review` 的条数汇总。

**请求示例**

```json
{
  "limit": 20,
  "offset": null
}
```

### `create_learning_plan(graph_id, topic_id=None)`

**请求示例**

```json
{
  "graph_id": "g1",
  "topic_id": "t1"
}
```

**响应示例**

```json
{
  "plan_id": "7a8d3be0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "graph_id": "g1",
  "initial_scope_summary": {
    "topic_id": "t1",
    "topic_bound": true
  }
}
```

### `extend_learning_plan_topics(plan_id, topic_ids, reason=None)`

**请求示例**

```json
{
  "plan_id": "7a8d3be0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "topic_ids": ["t2", "t3"],
  "reason": "progressive_extension"
}
```

### `get_learning_context(plan_id, topic_id=None)`

返回学习上下文（目标、状态、任务、概念包摘要）。

### `get_quiz_context(plan_id, topic_id=None)`

返回测验上下文（范围、历史表现、难度提示、约束）。

### `get_review_context(plan_id, topic_id=None)`

返回复习上下文（到期项、遗忘风险、优先原因、候选队列评分输入）。

默认返回字段（兼容 + 新增）：
- `due_items`：待复习任务（兼容字段）
- `forgetting_risk_summary`
- `priority_reasons`
- `candidate_items`：按综合评分排序的候选概念（含 `review_score`）
- `review_score_factors`：每个概念的评分因子（`overdue_score/forgetting_risk_score/weakness_score/recency_gap_score`）
- `queue_policy`：评分权重与 tie-break 策略
- `scope`：实际生效范围（包含 plan/topic 解析结果）

---

## 4) Prompt API

### `get_learn_context(plan_id, topic_id=None)`
### `get_quiz_context(plan_id, topic_id=None)`
### `get_review_context(plan_id, topic_id=None, session_context=None)`

以上 API 响应结构一致：

```json
{
  "prompt_text": "You are a ...",
  "context_summary": {}
}
```

`get_review_context` 支持会话级队列推进输入：

```json
{
  "plan_id": "7a8d3be0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "topic_id": "t1",
  "session_context": {
    "served_concept_ids": ["c1"],
    "last_completed_concept_id": "c1",
    "last_result": "correct"
  }
}
```

`context_summary` 里新增：
- `session_queue.items/current_item/next_item`
- `next_session_context`（用于下一轮继续调用）
- `candidate_items/review_score_factors/queue_policy`（复习队列综合评分输入）

推荐 CLI（带会话推进上下文）：

```bash
python -m scripts.cli.main get-mode-context --mode review \
  --plan-id PLAN_ID \
  --topic-id t1 \
  --session-context-json '{"served_concept_ids":["c1"],"last_completed_concept_id":"c1","last_result":"correct"}'
```

---

## 5) 记录提交 API

### `add_interaction_record(plan_id, mode, record_payload)`

`mode` 取值：`learn` / `quiz` / `review`

**入参校验（领域层）**：写入前会校验 `plan_id` 存在、`mode` 合法、`concept_id` 必填且 **`concept_id` 必须已存在于该计划对应知识图谱的 `Concept` 表中（当前版本 `dr = 0`）**，`result`（若提供）在白名单、`score` 在合法区间且不与 `partial`/`blocked` 矛盾、`difficulty_bucket`/`latency_ms` 合法。失败抛出 `LearningPayloadError`（`code` + `message`）；编排层经 JSON Schema 校验的请求也应与之对齐。

此前若因缺失概念导致 SQLite 外键失败，事务会整体回滚（通常不会在库里留下半条 `LearningRecord`）。图谱补齐后，新的交互可正常写入；**更早的交互明细**仅在仍保留会话日志等离线副本时可手工补录同一 API（注意时间与幂等）。

**分数**：`score` 可为 **0–100（百分制）** 或 **0–1（比例）**。省略时按 `result` 推断默认（例如 `ok`/`correct`/`pass` 偏高，`partial`/`blocked` 偏低）。

当 `mode=review` 时，调用方应在用户作答后输出：
- `detailed_explanation`：本题的详细原文依据解释（定义/关系/证据）
- `next_question`：队列推进后的下一题题目

**请求示例**

```json
{
  "plan_id": "7a8d3be0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "mode": "quiz",
  "record_payload": {
    "concept_id": "c1",
    "result": "correct",
    "score": 88,
    "difficulty_bucket": "medium",
    "latency_ms": 1200
  }
}
```

**响应示例**

```json
{
  "commit_result": {
    "learning_record_id": "f6a3...d9",
    "session_id": "a44...b2",
    "learner_id": "default-learner",
    "concept_id": "c1",
    "record_type": "quiz"
  },
  "state_delta_summary": {
    "state_action": "updated",
    "mastery_score": 0.76,
    "mastery_level": "Proficient",
    "forgetting_risk": 0.24,
    "next_review_at": "2026-04-24T09:00:00+00:00"
  },
  "task_delta_summary": {
    "task_action": "updated",
    "learning_task_id": "2c1...e8",
    "task_type": "review",
    "priority_score": 0.42,
    "due_at": "2026-04-22T09:00:00+00:00"
  }
}
```

---

## 6) 常见错误

- 缺少必填参数：抛出 `ValueError`，例如 `missing_required_fields: ['graph_id']`
- **学习记录**：`plan_not_found`、`invalid_mode`、`missing_concept_id`、`concept_not_in_plan_graph`（概念不在该计划的图中或非当前 `dr=0`）、`invalid_result`、`score_out_of_range`、`score_result_mismatch`（`blocked`/`partial` 与过高分数）、`invalid_difficulty_bucket`、`invalid_latency_ms`（见 `scripts.learning.validation.LearningPayloadError`）
- API 名不存在：`unknown_api: <api_name>`
- 提交非法模式：`invalid_mode`
- 图谱录入校验失败：`validation_summary.ok = false`，错误详见 `validation_summary.errors`
- 图谱移除被学习计划阻断：`remove_knowledge_graph_entities` 返回 `error: dependency_conflict`，或 `ingest` 剪枝阶段 `prune_result.blocked = true` 且 `validation_summary.ok = false`

---

## 7) 图谱硬删除、剪枝与备份回滚

- **硬删除**：`remove_knowledge_graph_entities` 与 `upsert_and_prune` 剪枝均为物理删除 SQLite 行；不提供应用层 `restore`。
- **备份**：执行 `--force-delete` 或大批量剪枝前，建议复制环境变量 `DOC_SOCRATIC_DB_PATH` 指向的库文件（或整库目录）作为快照，以便故障时恢复。
- **灰度**：先在副本库上跑 `remove` / `upsert_and_prune`，校验 `dependency_check` 与 `delete_summary` 后再对生产库操作。

---

## 8) 最小端到端示例

```python
from scripts.app import create_app
from tests.helpers import sample_graph_payload

service = create_app()
service.ingest_knowledge_graph("g1", sample_graph_payload())
plan = service.create_learning_plan("g1", topic_id="t1")

prompt = service.get_learn_context(plan["plan_id"], topic_id="t1")
print(prompt["prompt_text"])

result = service.add_interaction_record(
    plan["plan_id"],
    "learn",
    {"concept_id": "c1", "result": "ok", "score": 80, "difficulty_bucket": "easy"},
)
print(result["state_delta_summary"])
```
