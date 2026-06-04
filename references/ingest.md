# Ingest Mode Contract

## Trigger Conditions

- User asks to import materials, build a graph, or update existing graph knowledge.
- Caller has prepared structured graph payload from documents/LLM extraction.

Required context: `graph_id`, `payload_file` (`structured_payload` JSON object only), optional `session_context`.

## Runtime Execution Chain

1. Preflight (once per session): `get_api_spec("ingest-knowledge-graph")`.
2. Validate payload format and required fields before write.
3. Execute ingestion:
   - `ingest_knowledge_graph(graph_id, structured_payload)`
4. Check `validation_summary`:
   - if `ok=true`: return `graph_id/version/change_summary`
   - if `ok=false`: return errors and correction hints
5. Optional handoff:
   - create plan via `create_learning_plan(graph_id, topic_id?)`
   - continue with `learn` mode prompt retrieval

## Turn Contract

- One ingestion attempt per turn.
- Return one clear status (`success` or `needs_fix`) plus one next action.
- Keep feedback concise and list at most top 5 validation errors at once.

## AI Execution Directives

- Treat ingest as a validation-first mode, not a teaching mode.
- Validate and report before proposing downstream learning actions.
- If payload fails, return field-level fixes and ask for corrected payload.
- If payload succeeds, summarize version/change delta and recommend the next mode.
- Do not invent missing payload fields; request explicit correction inputs.

## 书籍与大文档导入

**默认模型（一书一图、按章累加）**：整本书对应**一个** `graph_id`；章节与节用 `topics` 表达（`chapter` / `section` + `parent_topic_id`），与 `se-full-20260422`、`claude-harness-vs-codex-harness` 同构。**不要**为同一本书按章新建多个平行 `graph_id`（例如 `b2-ch*`）。

**大文档必须拆章、逐次 ingest**（同一 `graph_id`）：

1. **选定全书 `graph_id`**（稳定 slug，全书复用）；首轮可用最小 `graph` 元数据 + 第 1 章 `topics`/concepts，或先建空壳再补章。
2. **按章节边界切分源文件**（目录、标题 `#`、PDF 书签等）；**每轮只处理一章**（必要时再拆为 `section` 子节点），从原文抽取 `structured_payload`。
3. **每章一次 `ingest_knowledge_graph`**，CLI/API 的 `graph_id` **始终相同**；payload 只含**本章增量**（新/更新的 `topic_id`、`concept_id` 等），由存储层合并进同一图谱 revision。
4. **ID 稳定**：`topic_id` / `concept_id` 带书系前缀且章内唯一，避免跨章覆盖；章间关系用 `relations` + `evidences` 挂到已有 `concept_id`。
5. **进度**：每轮回报 `version` / `change_summary` 与「下一章」`next_step`；全书完成前不要切换到 `learn`，除非用户明确要求边导边学。

**禁止**：单次把整本书塞进一个超大 payload；为每章新建独立根 `graph_id`（除非用户明确要求隔离图，见下节遗留模式）。

### 同层 sort_order 与存储层行为

- **书序由 payload 表达**：运行时不会为任何 `graph_id` / `topic_id` 做特殊排序；同批 `topics` 在写入前按 `(sort_order, topic_id)` 在本批兄弟节点内重排为连续 1…N。
- **按章增量 ingest**：新的 `topic_id`（库中尚不存在）若与同父已有兄弟冲突（常见为每章都写 `sort_order: 1`），存储层会 **追加到同父末尾**（当前同父最大 `sort_order + 1`）。若需插入中间位置，须在 payload 中写 **大于当前同父 max** 的目标序号。
- **每次 ingest 结束**：对全图每个 `parent_topic_id` 分组，将兄弟节点 **归一化** 为连续 1…N（稳定排序：`sort_order` 升序，同序时 `topic_id` 升序）。`change_summary.topics_sort_normalized` 为被改写的行数。
- **查询顺序**：`get_knowledge_graph` / 学习计划 focus topics 按 `sort_order` 升序、同序时按 `topic_id` 升序。
- **历史脏数据 / 书序修正**：若多章已写成相同 `sort_order`，ingest 归一化只保证连续序号，**不**自动修正书序。由 Agent 调用 `get-knowledge-graph`，经大模型产出完整 `topic_ids` 后执行 `reorder-graph-topics`（契约见 [`reorder-topics.md`](reorder-topics.md)）。不要在技能仓库内维护书单 JSON 或运维迁移脚本。

## 书系拆章（遗留：多 graph_id + 父图）

仅当用户**明确要求**章节彼此隔离、或维护历史「一书多 `graph_id`」资产时使用（与 `parent_graph_id` 校验一致）：

1. **先写入父图**（专用 `graph_id` + 最小合法 payload），再逐章 ingest。
2. 每章子图的 `graph` 中设置 **`parent_graph_id`** 指向父图，避免平行根图。
3. **命名**：父图 `graph.graph_name` 用书系稳定标题；各章 `graph_name` 使用同一前缀 + 章后缀（例如 em dash `—`）。

可选：`graph.ingest_policy.require_parent: true` — 批处理/CI 下缺少 `parent_graph_id` 会直接校验失败。

**已迁移示例**：《Claude Harness VS Codex Harness》现为单一 `graph_id`，章节在 `topics` 下；**不要**再为该书包新建 `b2-ch*` 平行子图。

## Escalation Rule

- If validation passes: suggest next hop (`learn` or optional `create_learning_plan`).
- If validation fails: de-escalate to payload repair guidance with concrete field-level fixes.

## Mode Exit Rule

- Exit to `learn` only after `validation_summary.ok = true`.
- Stay in `ingest` when payload parse/validation is still failing.

## Evidence Rule

- When rejecting relation data, include validation evidence from `validation_summary.errors`.
- Do not fabricate source evidence; echo payload-level diagnostics only.

## Output

- `mode: ingest`
- `graph_id`
- `version`
- `change_summary`
- `validation_summary`
- `next_step`

## Retry / Fallback

- If payload file cannot be parsed, stop and return parse error.
- If payload file is wrapped as `{ "graph_id": "...", "structured_payload": {...} }`, reject and ask caller to pass only inner `structured_payload`.
- If validation fails, do not write learning records; request payload correction.
- If graph exists with conflict, retry with corrected payload and same `graph_id`.

## Next Hop

- Route to `learn` after successful ingestion when user wants immediate study.
