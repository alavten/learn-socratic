# learn-socratic

面向「文档 → 知识图谱 → 新学 / 测验 / 复习」的苏格拉底式学习技能。由 Agent 按 `SKILL.md` 路由，并在各模式的契约文件（`modes/*.md`）下执行。主模式四字：**ingest / learn / quiz / review**（另有 **shared** 用于澄清与恢复）。

## 适用场景

适合说法例如：教我、讲解、做题、考我、复习、遗忘曲线、备考、抽背等。技能会把学习与图谱内容对齐，并在可能时引用证据与概念关系，而不是仅凭对话记忆编造。

## 你将经历的一次会话

- **每次用户发言原则上只跑一种主模式**（`ingest` / `learn` / `quiz` / `review`）；意图不清或缺参数时用 `shared` 做一轮澄清再切回主模式。
- **会话开始**：应能看到当前 `mode` 和一条可执行的 `next_step`。
- **会话中**：回复宜包含 **`summary`（本轮小结）** 和 **`next_step`（下一步建议）**，并保持简洁、有据可依。
- **难度**：会参考你最近的表现调整；不要指望助手在没有拉取上下文的情况下「凭空」引用图谱细节——需要先完成约定的上下文获取流程。
- **写入类操作**：涉及修改图谱、写入学习记录等，应在你有明确确认后再执行（技能契约要求）。

## 五种模式怎么选

用你的说法对照目标模式（详细规则见对应 `modes/*.md`）：

| 你想做的事 | 模式 | 契约文件 |
| --- | --- | --- |
| 导入材料、建图、更新图谱 | `ingest` | `modes/ingest.md` |
| 讲解、带我理解 | `learn` | `modes/learn.md` |
| 测验、考我、出题 | `quiz` | `modes/quiz.md` |
| 复习、背诵、到期巩固 | `review` | `modes/review.md` |
| 意图模糊、说不清跟哪份图谱/资料学、或要从失败里恢复 | `shared` | `modes/shared.md` |

路由习惯：

1. 说不清想学什么、或和其他意图冲突 → 先到 **`shared`** 澄清。
2. 中途换目标（例如从讲解改成测验）→ 先回到 **`SKILL.md` 的意图表**，再进入新模式。
3. 若目标模式的契约无法执行 → `summary` 说明原因，`next_step` 引导回到 **`shared`** 或其它可行模式。

## 各模式：你能做什么、大致会怎样

### `ingest`（把资料变成图谱）

- **适合**：手里有笔记、讲义或 **Markdown 文档**，希望 **导入并解析成知识图谱**，以后按概念关系学习与测验。
- **你怎么配合**：提供要导入的文件或路径；若有多套资料，说明想挂在哪一份「学习资料库」下或是否新建。助手会完成解析与校验，必要时请你按提示改一改格式或补全内容。
- **你会得到**：成功时告知更新摘要与版本信息；有问题则给出能照着改的说明。完成后通常可以 **新建或绑定学习计划**，再进入下面的讲解或做题。

### `learn`（新学）

- **适合**：针对 **知识图谱** 里的概念与证据做苏格拉底式学习——按步骤弄懂、被追问和纠正；学习与图谱内容对齐，而不是脱离资料的泛泛讲解。
- **你怎么配合**：说清楚想基于哪份图谱或哪个主题来学；若要专攻某一章某一节，直接说范围。同一轮会话里可以接着往下聊。
- **学习计划**：进度与记录落在「学习计划」这一层；**若还没有对应的学习计划**，流程会在选定图谱（及可选主题范围）后 **创建学习计划**，再进入讲解与记录。
- **资料或意图仍不清楚**：可到 **`shared`**，先从可选的资料库与计划中选好再继续。
- **节奏**：一轮围绕一小块内容、通常一道核心检查题；判分与进度会记下来，失败时会先补上记录再继续，避免跳步。细则见 `modes/learn.md`。

### `quiz`（测验）

- **适合**：已经在某套学习计划里学过一阵，想 **做题摸底**。
- **你怎么配合**：同样基于一份学习计划；可选指定章节或主题缩小范围。
- **节奏**：一次一题，先判对错再讲清楚；记录写好再推下一题（若暂时写不进去，同一轮不会硬塞下一题）。详见 `modes/quiz.md`。

### `review`（复习）

- **适合**：巩固 **快忘的、到期的、错题相关的** 内容。
- **你怎么配合**：基于学习计划进行；可以说想复习哪一块主题；接着上课时助手会接着上次的复习队列往下走。
- **节奏**：按队列逐个概念过；每次判定后落笔再前进，下一轮接着排。详见 `modes/review.md`。

### `shared`（澄清与恢复）

- **适合**：还没选定学哪套资料、意图含糊、想 **改一改上次评分或记录**，或上一轮中途卡住需要重来。
- **典型流程**：列出可选的知识资料库与学习计划，请你 **先选「跟哪份资料 / 哪个计划」**，再决定是导入、讲解、测验还是复习。
- **章节/主题**：你说要学第几章、哪个知识点时，会先帮你收窄选项，再进入 **`learn`**（或你要的 **`quiz` / `review`**）。

## 发布与 CI（monorepo）

本技能的源码路径为 **`skills/learn-socratic/`**。父 monorepo 根目录下提供一键脚本与 GitHub Actions；请将 **父仓库** 绑定到你的 GitHub remote（本地若仍存在 **`skills/learn-socratic/.git`**，与「仅以父仓为远程」的目标冲突时，迁移时请移除嵌套仓库或改为 submodule）。

- **GitHub Actions（父仓根）**：[**`.github/workflows/learn-socratic-validate.yml`**](../../.github/workflows/learn-socratic-validate.yml)（变更 `skills/learn-socratic/**` 等路径时跑测试 + `gh skill publish --dry-run`）；[**`.github/workflows/learn-socratic-release.yml`**](../../.github/workflows/learn-socratic-release.yml)（手动 **`workflow_dispatch`**，传入 **`version`**，例如 **`v1.2.3`**）。首次发布若 CLI 提示为仓库添加 **`agent-skills`** topic 等，可按 GitHub / [`gh skill publish`](https://cli.github.com/manual/gh_skill_publish) 文档操作。
- **本地一键**：在 monorepo **父目录根**执行 `./scripts/release-learn-socratic.sh vX.Y.Z`，或使用 `make release-learn-socratic VERSION=vX.Y.Z`。依赖：**GitHub CLI**（需支持 `gh skill publish`）、Python（运行 **`pip install -r skills/learn-socratic/requirements-dev.txt`** 与 pytest）；若使用 **`--verify-skills-sh`**，还需 **Node.js**（`npx skills`）。
- **skills.sh 校验**：脚本支持 **`--verify-skills-sh`**（对 `origin` 解析出的 **`owner/repo`** 运行 **`npx skills add owner/repo --list`**，并检查 **`SKILL.md`** 里的 **`name:`**）。可选 **`--skills-sh-search-wait N`** 轮询 **`https://skills.sh/api/search`**（站点收录与排序依赖 CLI 安装匿名统计，可能长时间为空；可用 **`--require-skills-sh-search`** 在必填收录场景下失败退出）。仅做校验时可 **`--target none`**（仍需传入占位 tag，例如 **`v0.0.0`**）。
- **环境变量**

  | 变量 | 作用 |
  |------|------|
  | `LEARN_SOCRATIC_REPO` | 指向 skill 根目录（含 `SKILL.md`）；不设则用 `$MONOREPO_ROOT/skills/learn-socratic`。 |
  | `SKILLS_SH_GITHUB_REPO` | `owner/repo`，覆盖从 **`git remote`** 推断的仓库 slug（用于 **`--verify-skills-sh`**）。 |
  | `SKIP_TESTS=1` | 跳过 pytest |
  | `SKIP_DIRTY_CHECK=1` | 允许在有未提交改动时继续 |
  | `SKIP_PUSH_BRANCH=1` | 不向 `origin` 推送当前分支 |
  | `DRY_RUN_ONLY=1` | 只做校验（含 `--dry-run`），不写 Release |
  | `ENABLE_SKR=1` | 在发布后若存在 **`skr`** 命令且 **`${SKILL_ROOT}/.skr.yaml`**，则执行 **`skr validate`**（需自备 registry；可参考 **[`.skr.yaml.example`](.skr.yaml.example)**）。 |

- **skills.sh（被动分发）**：[skills.sh](https://skills.sh/) 没有单独的「登记搜索」接口；官网检索与排行榜依赖 **`skills` CLI** 的安装匿名统计（见 [文档](https://skills.sh/docs)）。能保证的是：**`npx skills add <父仓>`** 能列出本技能（CI 已自动检查）；能否在首页搜到取决于索引与用量，可用脚本可选轮询搜索 API 观测延迟。
  安装示例：
  `npx skills add <owner>/<monorepo-repo>/tree/<branch>/skills/learn-socratic`
  （将 `<owner>/<monorepo-repo>` 换成父仓 slug）。亦可保留 standalone **`learn-socratic`** 仓库时直接使用 **`npx skills add <owner>/learn-socratic`**。
  [![skills.sh](https://skills.sh/b/alavten/learn-socratic)](https://skills.sh/alavten/learn-socratic)

## SKILL 下载与使用说明

如果你只想拿到技能说明文件（`SKILL.md`）做阅读或二次集成，可用以下方式：

- 下载单文件（raw）：

```bash
curl -L "https://raw.githubusercontent.com/alavten/learn-socratic/main/SKILL.md" -o SKILL.md
```

- 克隆完整仓库（推荐，包含 `modes/*.md` 与脚本）：

```bash
git clone https://github.com/alavten/learn-socratic.git
```

- 通过 skills CLI 直接安装到当前代理环境：

```bash
npx skills add alavten/learn-socratic
```

在 monorepo 场景下，建议仍通过上面的 release/CI 流程维护版本；本节命令更适合快速试用或拉取文档。

## 本地命令行（可选）

在技能目录下可用 CLI 拉取某模式的编排上下文（便于自检或脚本对接），例如：

```bash
python -m scripts.cli.main get-mode-context --mode learn --plan-id PLAN_ID --topic-id TOPIC_ID
```

常用参数提示：`--mode` 取 `ingest|learn|quiz|review`；`ingest` 场景还需 `--graph-id`、`--payload-file` 等（与 `SKILL.md` 中 CLI Hints 一致）。

## 进一步阅读

- 总路由与意图表：**`SKILL.md`**
- 各模式字段、顺序约束与异常处理：**`modes/*.md`**
