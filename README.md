# Doc Socratic Learning Optimized

Doc-Socratic 是一个以知识图谱与学习闭环为核心的技能运行时，提供：

- 知识图谱入库与查询（concept / relation / evidence）。
- 学习计划与学习记录闭环（learn / quiz / review）。
- 编排层统一 API 与 `list_apis/get_api_spec` 自描述能力。

## 目录结构

- `SKILL.md`：技能入口与模式路由规则。
- `modes/`：`learn` / `quiz` / `review` / `shared` 契约。
- `scripts/foundation/`：SQLite 与日志基础设施。
- `scripts/knowledge_graph/`：图谱入库、校验、查询。
- `scripts/learning/`：计划、上下文、记录、状态、任务。
- `scripts/orchestration/`：编排服务与 prompt 模板。
- `tests/`：单元测试与集成测试。

## 环境要求

- Python 3.10+
- `pytest`（用于测试）

## 快速开始

1. 进入目录：

```bash
cd .workbuddy/skills/doc-socratic-learning-optimized
```

2. （可选）创建虚拟环境并安装测试依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
```

3. 初始化并查看可用 API：

```bash
python3 scripts/app.py
```

## 数据库位置

- 默认数据库路径：`data/skill.sqlite3`
- 可通过环境变量覆盖：

```bash
export DOC_SOCRATIC_DB_PATH=/tmp/doc-socratic.sqlite3
```

## 典型调用示例（Python）

```python
from scripts.app import create_app

service = create_app()
print(service.list_apis())
```

```python
from scripts.app import create_app
from tests.helpers import sample_graph_payload

service = create_app()
service.ingest_knowledge_graph("g1", sample_graph_payload())
plan = service.create_learning_plan("g1", topic_id="t1")
prompt = service.get_learning_prompt(plan["plan_id"], topic_id="t1")
commit = service.append_learning_record(
    plan["plan_id"],
    "learn",
    {"concept_id": "c1", "result": "ok", "score": 82, "difficulty_bucket": "easy"},
)
print(prompt["prompt_text"])
print(commit["state_delta_summary"])
```

## 测试

- 运行全部测试：

```bash
python3 -m pytest -q
```

- 仅运行异常路径集成测试：

```bash
python3 -m pytest -q tests/integration/test_error_paths.py
```
