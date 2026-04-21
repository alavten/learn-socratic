# API Usage Guide

本文档面向调用方，说明 `orchestration_app_service` 的可用 API、典型入参和响应示例。

## 使用方式

```python
from scripts.app import create_app

service = create_app()
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

### `list_knowledge_graphs(limit=20, cursor=None)`

**请求示例**

```json
{
  "limit": 20,
  "cursor": null
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
  "cursor": null
}
```

### `get_knowledge_graph(graph_id, topic_id=None, concept_limit=20, cursor=None)`

**请求示例**

```json
{
  "graph_id": "g1",
  "topic_id": "t1",
  "concept_limit": 20,
  "cursor": null
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
  "cursor": null
}
```

### `ingest_knowledge_graph(graph_id, structured_payload)`

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

### `get_concepts(graph_id, concept_scope, detail='brief', concept_limit=20, cursor=None)`

**请求示例**

```json
{
  "graph_id": "g1",
  "concept_scope": {
    "topic_ids": ["t1"]
  },
  "detail": "brief",
  "concept_limit": 20,
  "cursor": null
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

### `list_learning_plans(limit=20, cursor=None)`

**请求示例**

```json
{
  "limit": 20,
  "cursor": null
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

返回复习上下文（到期项、遗忘风险、优先原因）。

---

## 4) Prompt API

### `get_learning_prompt(plan_id, topic_id=None)`
### `get_quiz_prompt(plan_id, topic_id=None)`
### `get_review_prompt(plan_id, topic_id=None)`

以上 API 响应结构一致：

```json
{
  "prompt_text": "You are a ...",
  "context_summary": {}
}
```

---

## 5) 记录提交 API

### `append_learning_record(plan_id, mode, record_payload)`

`mode` 取值：`learn` / `quiz` / `review`

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
- API 名不存在：`unknown_api: <api_name>`
- 提交非法模式：`invalid_mode`
- 图谱录入校验失败：`validation_summary.ok = false`，错误详见 `validation_summary.errors`

---

## 7) 最小端到端示例

```python
from scripts.app import create_app
from tests.helpers import sample_graph_payload

service = create_app()
service.ingest_knowledge_graph("g1", sample_graph_payload())
plan = service.create_learning_plan("g1", topic_id="t1")

prompt = service.get_learning_prompt(plan["plan_id"], topic_id="t1")
print(prompt["prompt_text"])

result = service.append_learning_record(
    plan["plan_id"],
    "learn",
    {"concept_id": "c1", "result": "ok", "score": 80, "difficulty_bucket": "easy"},
)
print(result["state_delta_summary"])
```
