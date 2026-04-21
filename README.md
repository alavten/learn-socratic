# Doc Socratic Learning Optimized

Doc-Socratic 是一个以知识图谱与学习闭环为核心的技能运行时，提供：

- 知识图谱入库与查询（concept / relation / evidence）。
- 资料入图与学习闭环（ingest / learn / quiz / review）。
- 编排层统一 API 与 `list_apis/get_api_spec` 自描述能力。

## 目录结构

- `SKILL.md`：技能入口与模式路由规则。
- `modes/`：`ingest` / `learn` / `quiz` / `review` / `shared` 契约。
- `scripts/foundation/`：SQLite 与日志基础设施。
- `scripts/knowledge_graph/`：图谱入库、校验、查询。
- `scripts/learning/`：计划、上下文、记录、状态、任务。
- `scripts/orchestration/`：编排服务与 prompt 模板。
- `tests/`：单元测试与集成测试。

## 双视图导航

### User Journey View（学习者视角）

- 我有资料，先建图：`modes/ingest.md`
- 我想先理解内容：`modes/learn.md`
- 我想测试掌握情况：`modes/quiz.md`
- 我想按到期项复习：`modes/review.md`
- 我不确定下一步：`modes/shared.md`

### System Operator View（系统运维视角）

- 统一命令入口：`python scripts/cli.py <subcommand>`
- API 契约与示例：`docs/api-usage.md`
- 架构与数据设计：`docs/architecture-design.md`、`docs/data-model-design.md`
- 设计覆盖检查：`docs/design-coverage-checklist.md`

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
python3 scripts/cli.py list-apis
```

## 数据库位置

- 默认数据库路径：`data/skill.sqlite3`
- 可通过环境变量覆盖：

```bash
export DOC_SOCRATIC_DB_PATH=/tmp/doc-socratic.sqlite3
```

## 调用示例与命令手册

- 详细 Python/CLI 示例统一维护在：`docs/api-usage.md`
- 模式级调用指引在：`modes/ingest.md`、`modes/learn.md`、`modes/quiz.md`、`modes/review.md`

## 测试

- 运行全部测试：

```bash
python3 -m pytest -q
```

- 仅运行异常路径集成测试：

```bash
python3 -m pytest -q tests/integration/test_error_paths.py
```
