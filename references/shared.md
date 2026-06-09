# Shared Mode（语义澄清）

## 适用场景

- 用户意图冲突或无法映射到单一 mode
- 缺 `plan_id`、`graph_id` 或目标图谱
- 主 mode 因可恢复错误中断（缺上下文、校验失败）
- 浏览章节/概念内容（非 learn/quiz/review 交互）
- 薄弱点/掌握程度报告（非交互式复习）
- 修正或补写学习 record
- 用户仅提供本地文件路径且无其他学习意图 → 直接 handoff `ingest`

## 前置输入

| 项 | required | 说明 |
| --- | --- | --- |
| `file_path` | no | 仅路径时走 ingest |
| `plan_id` / `graph_id` | no | 专项分支所需 |
| `last_mode` / `last_error` | no | 失败恢复 |

## 执行步骤

### 1. API 发现（exec 前必做）

```bash
cd <技能根目录> && python -m scripts.cli.main list-apis
cd <技能根目录> && python -m scripts.cli.main get-api-spec --api-name <method>
```

### 2. 缺上下文时

- `list-knowledge-graphs`（`has_more` 时分页）
- `list-learning-plans`（`has_more` 时分页）
- 展示 **KnowledgeGraphs** 与 **PendingLearningPlans** 两张表
- 用 `[单选]` 请用户先选 **plan** 或 **graph**

### 3. 选择 Mode

向用户展示下表，**MUST** 用 `[单选]` 选择一项：

| Mode | 说明 | 文档 |
| ---- | ---- | ---- |
| `ingest` | 导入/更新知识图谱、修正章节顺序 | [ingest.md](./ingest.md) |
| `learn` | 讲解与带学 | [learn.md](./learn.md) |
| `quiz` | 测验与刷题 | [quiz.md](./quiz.md) |
| `review` | 间隔复习与巩固 | [review.md](./review.md) |

用户选定后，**MUST** 进入对应文档第一步继续执行。

### 4. 专项分支

- **浏览章节**：`get-knowledge-graph --graph-id GRAPH_ID [--topic-id TOPIC_ID]`；`has_more` 时用 `next_offset` 分页
- **薄弱点报告**：`get-mastery-diagnostics --plan-id PLAN_ID [--topic-id TOPIC_ID | --concept-id CONCEPT_ID]`；shell 示例见 `SKILL.md`
- **record 修正**：handoff 至 `quiz` / `learn` / `review`，逐条 `add-interaction-record`，禁止在 shared 批量写 record

## 停止条件

| 场景 | 处理 |
| --- | --- |
| discovery 为空 | 说明无可用图谱/plan，请用户先 ingest |
| 用户未选择 plan/graph 或 mode | 停留 shared，再问一题 |
| 主 mode 不可恢复失败 | 简述约束，给一条安全 `next_step` |

## 下一步调整

- 澄清完成 → 进入所选 mode 文档第一步
- 薄弱点报告后 → `review`（due/薄弱）、`learn`（概念缺口）、`quiz`（验证）
- 每轮返回 `mode: shared`、`summary`、`next_step`
