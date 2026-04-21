---
name: doc-socratic-learning
description: 双模式文档学习技能 - 学习模式 (讲解为主) 和测验模式 (SOLO×UBD 追问)。Use when user wants "追问式学习/费曼学习/learn this doc". Quiz mode maintains mastery dashboard with spaced repetition.
args:
  type: string
  completions:
    - --file=
    - --mode=learn
    - --mode=quiz
    - --target=
    - --timebox=
    - --language=
---

# Doc Socratic Learning (双模式版本)

## Purpose
提供两种学习模式，帮助用户高效掌握文档内容：
- **学习模式 (Learn Mode)**: 通过讲解、示例、对话帮助理解
- **测验模式 (Quiz Mode)**: 基于 SOLO×UBD 框架的追问式测验

The skill maintains a persistent mastery dashboard for continuity, with spaced repetition based on the Ebbinghaus forgetting curve.

**Key Features**:
1. **双模式切换**: 用户可随时在学习模式和测验模式间切换
2. **学习模式**: 文档导览 → 概念讲解 → 示例说明 → 即时问答
3. **测验模式**: SOLO 递进提问 → 文档依据反馈 → 掌握度追踪 → 间隔复习
4. **自然对话交互**: 通过对话上下文识别用户意图，无需命令语法
5. **知识依赖检查**: 前置知识薄弱时自动降维讲解

---

## Inputs (collect in one message, then proceed)
- Document path in workspace (preferred) or pasted text
- Mode (default: learn for new documents, quiz for review)
- Learning target (default：能够用自己的话解释并举例应用)
- Timebox (default: 30 minutes)
- Output language (default: user language)

---

## Modes Overview

### Mode 1: Learn Mode (学习模式)

**Purpose**: 帮助用户初次理解文档内容，建立知识框架

**Workflow**:
1. **文档导览**: 展示文档结构、核心概念地图、学习目标建议
2. **概念讲解**: 逐节讲解，每个概念包含：定义 + 示例 + 与其他概念的关系
3. **即时问答**: 每个概念后用 1-2 个简单问题检查理解（不计入掌握度）
4. **用户提问**: 随时回答用户问题，基于文档内容
5. **阶段总结**: 每完成一节，总结关键要点

**Style**:
- 讲解为主，测验为辅
- 不显示复杂的掌握度表格
- 允许用户控制节奏（"跳过"、"详细讲"、"举个例子"）
- 错误时直接给出正确答案和解释

---

### Mode 2: Quiz Mode (测验模式)

**Purpose**: 通过 SOLO 递进式提问检验和巩固学习成果

**Core Framework**:
- **SOLO progression**: Uni-structural → Multi-structural → Relational → Extended Abstract
- **UBD facets**: Explain → Interpret → Apply → Perspective → Empathy → Self-Knowledge
- **Ebbinghaus spacing**: 基于掌握度的间隔复习提醒

**Workflow**:
1. **Session 概览**: 显示"已掌握 vs 需复习"状态（仅限有学习记录的文档）
2. **单题循环**: Question → Answer → Feedback → Dashboard Update → Next Question
3. **动态难度**: 根据正确率自动调整 SOLO 级别
4. **变式练习**: 5 种变式题型轮询（V1→V2→V3→V4→V5）
5. **元认知检查**: 每 10 题或会话结束时进行

**Style**:
- 一题一题问，不一次给多题
- 反馈基于文档依据（带引用）
- 严格更新掌握度表格

---

## Mode Detection and Switching

**Mode selection at session start**:
| User Input Pattern | Detected Mode | Action |
|-------------------|---------------|--------|
| "学习模式", "learn mode", "我不熟悉", "第一次看" | Learn Mode | 启动学习模式 |
| "测验模式", "quiz mode", "考考我", "测试" | Quiz Mode | 启动测验模式 |
| "复习", "review", "再看看" | Quiz Mode | 启动测验模式，优先复习 |
| No pattern detected + no learning history | Learn Mode | 默认学习模式 |
| No pattern detected + has learning history | Quiz Mode | 默认测验模式 |

**In-session switching**:
| User Input | Action |
|-----------|--------|
| "切换到学习模式", "我想先学一下", "这题我不会，讲讲吧" | Switch to Learn Mode for current topic |
| "切换到测验模式", "考考我", "出题吧" | Switch to Quiz Mode |
| "显示状态", "学得怎么样" | Show mastery dashboard summary |
| "跳过", "下一个", "继续" | Continue current mode, skip current item |

---

## Files (required)

After the first user answer in **Quiz Mode**, create or update a learning log file in the SAME directory as the source document:
- Path: `<source-dir>/<source-basename>-learning.md`
  - Example: `ReferenceLibrary/SoftwareEngineering/Chapter7-SoftwareEngineering-learning.md`

**Note**: In Learn Mode, no file is created unless user explicitly requests quiz/assessment.

---

## Learn Mode Workflow (学习模式流程)

### Step L1 — Document Overview (文档导览)

**Purpose**: 帮助用户建立整体知识框架

**Actions**:
1. 读取文档，识别主要章节和核心概念
2. 生成**概念地图**展示各概念之间的关系
3. 建议学习目标（基于文档内容）
4. 询问用户想从哪里开始，或建议从第一节开始

**Output Format**:
```
┌─────────────────────────────────────────────────────────────┐
│                    文档导览                                  │
├─────────────────────────────────────────────────────────────┤
│  文档：[文档名称]                                            │
│  章节数：[X] 个核心主题                                       │
├─────────────────────────────────────────────────────────────┤
│  核心概念地图：                                              │
│  [概念 A] → [概念 B] → [概念 C]                              │
│     ↓                       ↑                                │
│  [概念 D] → [概念 E]                                      │
├─────────────────────────────────────────────────────────────┤
│  建议学习路径：                                              │
│  1. [基础概念] → 2. [核心方法] → 3. [应用场景]                │
├─────────────────────────────────────────────────────────────┤
│  你想从哪里开始？                                            │
│  A) 按顺序学习第 1 节                                          │
│  B) 指定章节（告诉我章节号）                                  │
│  C) 先了解某个具体概念                                        │
└─────────────────────────────────────────────────────────────┘
```

---

### Step L2 — Concept Explanation (概念讲解)

**Purpose**: 逐节讲解，每个概念包含以下要素

**Format** (for each concept):
1. **定义** (Definition): 文档中的核心定义，带引用
2. **作用/目的** (Purpose): 为什么需要这个概念
3. **示例** (Example): 具体应用场景或例子
4. **与其他概念的关系** (Relationships): 前置概念、后续概念、相关概念
5. **常见误区** (Misconceptions): 容易混淆的点（如有）

**Style**:
- 用通俗易懂的语言解释
- 必要时用生活中的类比
- 允许用户随时打断提问

---

### Step L3 — Instant Check (即时检查)

**Purpose**: 每个概念后用 1-2 个简单问题检查理解（不计入掌握度）

**Question Types**:
- 确认性问题："刚才讲的 [概念]，你能用自己的话复述一下吗？"
- 简单应用："如果 [某场景]，应该用 [概念 A] 还是 [概念 B]？"

**Feedback**:
- 正确：简短确认，继续下一个概念
- 错误/不会：直接给出正确答案和解释，不记录错题

---

### Step L4 — User Questions (用户提问)

**Purpose**: 回答用户任何问题

**Rules**:
- 基于文档内容回答，带引用
- 如果文档没有相关内容，说明"文档中没有提到这个"
- 可以补充外部知识，但要标注"这不是文档内容"

---

### Step L5 — Section Summary (阶段总结)

**Purpose**: 每完成一节，总结关键要点

**Format**:
```
┌─────────────────────────────────────────────────────────────┐
│  第 X 节总结                                                  │
├─────────────────────────────────────────────────────────────┤
│  核心要点：                                                  │
│  ● [要点 1]                                                   │
│  ● [要点 2]                                                   │
│  ● [要点 3]                                                   │
├─────────────────────────────────────────────────────────────┤
│  下一步：                                                    │
│  A) 继续第 X+1 节                                             │
│  B) 复习本节（再讲讲）                                       │
│  C) 切换到测验模式考考我                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Quiz Mode Workflow (测验模式流程)

### Mastery Dashboard (测验模式专用)

**Note**: The following dashboard and calculations apply to **Quiz Mode only**. Learn Mode does not create or update the dashboard.

Maintain ONE markdown table aggregated by **knowledge point** (not per-turn transcript). Each user answer updates exactly one row.

| Knowledge point | Section | Mastery | Correct | Incorrect | Last result | Last attempted (ISO) | Key correction (doc-grounded) | Citation (heading/lines) | Next prompt | Next review date (ISO) | SOLO level | UBD facets | Streak | Variant cycle |
|----------------|---------|---------|---------|-----------|-------------|----------------------|-------------------------------|--------------------------|------------|------------------------|------------|------------|--------|---------------|

**Rules** (abbreviated - see original for full details):
- **Mastery**: `New` / `Learning` / `Proficient` / `Mastered`
- **SOLO level**: `Uni-structural` / `Multi-structural` / `Relational` / `Extended Abstract`
- **UBD facets**: `Explain`, `Interpret`, `Apply`, `Perspective`, `Empathy`, `Self-Knowledge`
- **Next review date**: Based on Ebbinghaus forgetting curve intervals

---

### Step Q0 — Session Start: Overview + Knowledge Dependency Check

**MANDATORY: At the start of EACH session, display the following overview BEFORE asking any questions:**

```
┌─────────────────────────────────────────────────────────────┐
│                    学习会话概览                              │
├─────────────────────────────────────────────────────────────┤
│  文档：[文档名称]                                            │
│  时间：[当前时间]                                            │
├─────────────────────────────────────────────────────────────┤
│  掌握状态汇总：                                              │
│  ● Mastered: [X] 个 (已掌握，自动跳过)                        │
│  ● Proficient: [X] 个 (已熟练，自动跳过)                      │
│  ● Learning: [X] 个 (需复习)                                 │
│  ● New: [X] 个 (新学习)                                      │
├─────────────────────────────────────────────────────────────┤
│  今日优先复习（过期/即将过期）：                               │
│  - [知识点 A]: 过期 [X] 天，掌握度 [XX%]                       │
│  - [知识点 B]: 今天到期，掌握度 [XX%]                          │
├─────────────────────────────────────────────────────────────┤
│  知识依赖检查：                                              │
│  - [前置知识 C] 尚未掌握 → 先复习 [前置知识 C]                  │
└─────────────────────────────────────────────────────────────┘

💡 提示：你可以随时说"显示状态"查看进度，说"我来问"切换为提问模式，说"跳过"跳过当前知识点。
```

**Session Start Rules:**
1. Read the existing `<document-name>-learning.md` file
2. Categorize knowledge points by Mastery level
3. **Auto-skip**: Do NOT ask questions about Proficient/Mastered knowledge points UNLESS:
   - User explicitly requests review (e.g., "复习 XXX", "再看看 XXX")
   - It's a prerequisite for a Learning-level concept
4. **Prioritize**: Overdue reviews first (Next review date in the past)
5. **Knowledge Dependency Check**: Before asking about a concept, verify prerequisites are at least Learning level
6. **Intent Detection**: Check user's latest message for natural language intent patterns (see "Natural Conversation Intent Detection" section)

**Knowledge Dependency Graph Enforcement:**
```
Example dependency rules:
- 【支持过程】 ← 前提：【基本过程】(至少 Learning 级别)
- 【螺旋模型】 ← 前提：【瀑布模型】+ 【风险分析】(至少 Learning 级别)
- 【CMMI 成熟度】 ← 前提：【过程管理概念】(至少 Learning 级别)
- 【XP 十二实践】 ← 前提：【敏捷宣言】+ 【XP 价值观】(至少 Learning 级别)
```

If a prerequisite is New or has incorrect last result:
1. Inform user: "要理解 [当前概念]，需要先掌握 [前置知识]"
2. Ask a prerequisite question first
3. After prerequisite is answered correctly, return to original concept

---

### Step 1 — Single-question loop (strict)

Ask **exactly ONE** question at a time, progressing through SOLO taxonomy levels while ensuring UBD understanding facets.

**Mode Selection (Natural Conversation Detection):**

Detect user intent from conversation context at session start:

| Pattern | Intent | Action |
|---------|--------|--------|
| User asks "状态/进度/学得怎么样" | Status request | Display session overview, then resume quiz |
| User says "我来问/我想问/能给我讲讲/我不太理解" | User-led request | Switch to user-led: answer their question, then ask ONE follow-up quiz |
| User says "跳过/下一个/这个知道了" | Skip request | Move to next knowledge point |
| User says "复习/再看看/关于 XXX" | Review request | Force review specific knowledge point |
| User says "提示/给点提示" | Hint request | Provide scaffolding at lower SOLO level |
| No pattern detected | Default | Continue quiz-led mode (AI asks questions) |

**Important**: After handling user intent, return to quiz-led mode unless user explicitly continues asking questions.

**Question progression (mandatory, SOLO-based):**

| SOLO Level | UBD Facet | Question Type | Example |
|-----------|----------|--------------|---------|
| **1. Uni-structural** (单点) | Explain (解释) | **Structure/Definition**: Identify one element | "在 GB/T 8566-2022 的支持过程（9 个）列表中，`审核过程`之后是哪一个过程？" |
| **2. Multi-structural** (多点) | Explain (解释) | **List/Classify**: Recall multiple elements | "列出 CMMI 五个成熟度等级的名称" |
| **3. Relational** (关联) | Interpret (阐释) + Perspective (洞察) | **Compare/Mechanism**: Understand relationships | "解释 CMMI L2 已管理级与 L3 已定义级的本质区别是什么？" |
| **4. Extended Abstract** (抽象扩展) | Apply (应用) | **Transfer/Design**: Apply to novel contexts | "某团队需求不明确、技术风险高，应选择哪种开发模型？说明理由。" |
| **4+. Extended Abstract** (抽象扩展) | Empathy (移情) | **Emotional Conflict**: Navigate stakeholder feelings | See Empathy Template below |

**Empathy Question Template (mandatory structure for true Empathy facet):**

Empathy questions MUST include ALL three elements:
1. **Specific situation descriptor** (时间、地点、约束条件)
2. **Emotional/feeling vocabulary** (担忧，焦虑，困惑，抗拒，沮丧，欣慰，着急，无奈)
3. **Genuine perspective conflict** with empathy for ALL parties involved

**Example format:**
```
某团队正在开发医疗系统，已加班到晚上 9 点。
- 产品经理焦虑地说："客户刚又提了新需求，这周必须上线！"
- 开发者沮丧地说："代码还没重构，现在加功能会积累技术债！"
- 客户担忧地说："我担心功能不完整影响医院使用..."

作为架构师，你如何回应每个角色的关切？从他们的角度描述各自的担忧，然后提出一个能平衡各方需求的方案。
```

**Non-example (DO NOT do this):**
"从管理者和开发者两个角度看，[某方法论] 的价值有什么不同？"
→ This is Perspective, not Empathy (lacks emotion/situation descriptors)

**SOLO level distribution (target ratios per session):**
- Uni-structural: 20%
- Multi-structural: 20%
- Relational: 30%
- Extended Abstract: 30%

---

### Structured Metacognitive Check (every 10 questions)

**UBD self-knowledge check (mandatory, every 10 questions or session end):**
Ask exactly ONE metacognitive question using the **Structured Metacognitive Check** format below.

Choose ONE of the following four types each time:

1. **Prediction-Actual Comparison**:
   ```
   刚才那道题，你答题前的把握是百分之多少 (0-100%)？实际结果如何？
   如果把握高但答错了，是什么原因？(A. 概念不清 B. 记忆混淆 C. 审题错误 D. 知识盲区)
   ```

2. **Error Type Identification** (after incorrect answers):
   ```
   你的错误是因为：
   A) 概念不清（不理解核心定义）
   B) 记忆混淆（与其他概念记混了）
   C) 审题错误（没看清题目问什么）
   D) 知识盲区（完全没学过这个点）

   针对你的错误类型，你打算如何复习？
   ```

3. **Transfer Ability Self-Rating**:
   ```
   如果向一个没学过 [核心概念] 的人解释它，你能做到：
   A) 复述原文定义
   B) 举一个具体例子说明
   C) 用一个生活中的比喻让他理解

   你现在处于哪个 level？想达到 C level 需要什么？
   ```

4. **Knowledge Dependency Check**:
   ```
   要理解 [当前概念]，你需要先掌握什么前置知识？
   例如：要理解"螺旋模型"，需要先理解"瀑布模型"和"风险分析"的概念。

   你的前置知识掌握了吗？如果卡住了，是哪里卡住了？
   ```

---

### Question Clarity + Dependency Rules

**Question clarity (mandatory):**
- Include **document/standard/topic context** (e.g., "在 GB/T 8566-2022 软件生存周期过程中…")
- When referring to a subsection, name the parent (e.g., "软件生存周期过程中的**支持过程（9 个）**里…")
- Optionally add one short "考查点" line

**Knowledge Dependency Enforcement (mandatory):**
Before asking a question:
1. Check if the concept has prerequisites in the knowledge dependency graph
2. Verify prerequisite concepts are at least `Learning` level
3. If prerequisites are `New` or have incorrect last result → ask prerequisite question first
4. When user struggles with a dependent concept, trace back to check root cause

**Question sequencing rule**: Follow the knowledge dependency graph order.

---

### Step 2 — Evaluate answers (doc-grounded)

When the user answers:
1. Split the user answer into **atomic claims** (1 sentence per claim)
2. For each claim, classify:
   - Correct (in doc)
   - Incorrect (per doc)
   - Unverifiable (not in doc)
3. Produce a brief correction using this structure:
   - Verdict (1 line)
   - What's correct (bullets, optional)
   - Corrections (doc says …) (bullets with citations)
   - Missing-but-important (from doc) (1–3 bullets)
   - Beyond doc (if any)

**If the overall verdict is Incorrect (per doc):**
1. Provide the correct answer with doc citations
2. Offer choice: "要不要开始学习模式？你可以反过来问我：你哪里卡住/想从哪一行表开始理解？"
3. If user chooses learning mode: answer their questions doc-grounded, then propose ONE follow-up quiz question

**SOLO Level Judgment (mandatory):**
Analyze the user's answer structure to determine SOLO level achieved:
- Single element recalled → Uni-structural
- Multiple elements listed without relationships → Multi-structural
- Relationships explained with causal connectors → Relational
- Novel context transfer or synthesis → Extended Abstract

---

### Step 3 — Update mastery dashboard (mandatory)

After giving feedback, update `<document-name>-learning.md`:

1. Pick exactly ONE **knowledge point** for the question
2. Determine the **SOLO level** based on user answer structure (see rubric above)
3. Determine which **UBD facets** the user demonstrated
4. Create the row if missing; otherwise update it:
   - Increment `Correct` or `Incorrect` depending on overall verdict
   - Set `Last result`, `Last attempted`, `Key correction`, `Citation`
   - Update `SOLO level` to the highest achieved
   - Update `UBD facets` by adding any newly demonstrated facets
   - Update `Streak` (increment on correct, reset on incorrect)
   - Recalculate `Mastery Score` and `Mastery` level
   - Set `Next prompt` based on Step 4 rules
   - Set `Next review date` using Ebbinghaus intervals
   - Update `Variant cycle` (increment, wrap around at 5)

---

### Formative vs Summative Assessment (mandatory distinction)

**Formative Assessment (每 5 题，low-stakes):**
- Purpose: 提供学习反馈，不更新掌握度
- Format: "过去 5 道题，你做对了 X 道。我们来看看错题能学到什么。"
- Action: Analyze error patterns, identify knowledge gaps, adjust next questions
- **Do NOT update mastery counters** — this is for learning only

**Summative Assessment (每 20 题，high-stakes):**
- Purpose: 评估整体掌握水平
- Format: "已经完成 20 道题，现在做一个综合性问题来评估你的整体理解。"
- Action: Ask a Relational or Extended Abstract level question synthesizing multiple concepts
- **DO update mastery counters** and recalculate mastery level

**Implementation rule**: Track question count in session. At question 5, 10, 15... do formative check. At question 20, 40, 60... do summative assessment.

---

### Step 4 — Adaptive difficulty (SOLO-based progression)

**SOLO progression rules:**

| Current State | Last Result | Next Action |
|--------------|-------------|-------------|
| Any | Incorrect (per doc) | Stay at current SOLO level or drop one level + provide scaffolding |
| Any | Unverifiable (not in doc) | Bridge to nearest doc-grounded concept, or beyond-doc with one minimal external query |
| New/Learning | Correct | Advance within current SOLO level (different variant type) OR move up one SOLO level if 2+ consecutive correct |
| Proficient | Correct | Move to Relational or Extended Abstract level |
| Mastered | Correct | Focus on Extended Abstract + UBD self-knowledge |

**Minimum SOLO level per mastery level (enforced):**

| Mastery Level | Minimum SOLO Level | Minimum UBD Facets |
|---------------|-------------------|-------------------|
| New | Uni-structural | Explain |
| Learning | Multi-structural | Explain + Interpret |
| Proficient | Relational | Explain + Interpret + Perspective |
| Mastered | Extended Abstract | Explain + Interpret + Apply + Perspective + Self-Knowledge |

**Repetition rule (strict):**
- If a question is incorrect, the NEXT question must re-test the same knowledge point once (simpler), after providing the correct answer

---

### Step 5 — Continue until timebox or user stops

Run loops of: **Question → user answer → feedback → dashboard update → next question**

**Session End Checklist:**
1. Update all knowledge point rows with Next review date
2. Display session summary:
   ```
   ┌─────────────────────────────────────────┐
   │          本次会话总结                    │
   ├─────────────────────────────────────────┤
   │  总题数：[X]                             │
   │  正确率：[XX%]                           │
   │  新掌握：[X] 个知识点                     │
   │  需复习：[X] 个知识点 (下次复习日期)        │
   └─────────────────────────────────────────┘
   ```
3. Remind user of next scheduled review session

---

## Reverse Questioning (user-initiated)

If the user asks a question to learn (instead of answering yours):

1. Treat it as **learning mode** for the closest knowledge point
2. Answer using the document as primary source (with citations). If not in doc: label `Not in doc` and propose one minimal external query
3. Update the mastery dashboard row for that knowledge point:
   - Do NOT change Correct/Incorrect counters (user is asking, not being tested)
   - Update `Last attempted`, `Key correction` (if any), `Citation`
   - Set `Next prompt` to `repeat-easy` (to test understanding next)
4. Ask exactly ONE follow-up quiz question (structural first) to check their understanding

**Natural language cues that indicate user-led mode:**
- "我来问问...", "我想了解...", "能给我讲讲...", "我不太理解...", "这里为什么...", "XXX 是什么意思"

---

## Natural Conversation Intent Detection

**Mode switching and commands are detected from natural conversation context:**

| User Intent | Natural Language Patterns | System Response |
|-------------|--------------------------|-----------------|
| **Show status** | "状态", "进度", "学得怎么样", "还有多少", "看看掌握了多少", "现在什么水平" | Display session overview (mastery summary + due reviews) |
| **Switch to user-led** | "我来问", "我想问", "能给我讲讲", "我不太理解", "这里不太懂", "解释一下", "为什么" | Switch to user-led mode: answer user's questions doc-grounded, then follow up with ONE quiz question |
| **Skip current topic** | "跳过", "下一个", "这个知道了", "已经会了", "没问题了", "继续", "下一题" | Skip current knowledge point, move to next priority topic |
| **Review specific topic** | "复习", "再看看", "回到", "关于 XXX", "我想问 XXX", "XXX 是什么" | Force review specific knowledge point immediately |
| **Request hint** | "提示", "给点提示", "不知道", "没思路" | Provide scaffolding hint at lower SOLO level |
| **Learning mode after incorrect** | "没听懂", "为什么", "怎么来的" | Switch to learning mode: explain with citations, then ask ONE follow-up |

**Detection Rules:**
1. Check user message for pattern matches at session start
2. If multiple patterns detected, prioritize: Review > Status > User-led > Skip
3. Default mode is quiz-led (AI asks questions)
4. After handling user intent, return to quiz-led mode unless user explicitly wants to continue asking

---

## Style constraints

- Questions must be **short**, **single-focus**, and **clear in context**
- Always go **easy to hard**
- Prefer the document over assumptions: **以文档为准**
- Never create any extra markdown files besides the required `*-learning.md` log
- Never present multiple questions in one turn. One question only.
- **CRITICAL**: Auto-skip Proficient/Mastered knowledge points unless user explicitly requests review

---

## Example (complete flow)

**Session Start Overview:**
```
┌─────────────────────────────────────────────────────────────┐
│                    学习会话概览                              │
├─────────────────────────────────────────────────────────────┤
│  文档：第七章 软件工程                                       │
│  时间：2026-03-19 14:00                                    │
├─────────────────────────────────────────────────────────────┤
│  掌握状态汇总：                                              │
│  ● Mastered: 0 个                                            │
│  ● Proficient: 5 个 (已熟练，自动跳过)                        │
│  ● Learning: 10 个 (需复习)                                   │
│  ● New: 20 个 (新学习)                                        │
├─────────────────────────────────────────────────────────────┤
│  今日优先复习：无过期                                         │
└─────────────────────────────────────────────────────────────┘

💡 提示：你可以随时说"显示状态"查看进度，说"我来问"切换为提问模式，说"跳过"跳过当前知识点。
```

**Question progression example:**

1) **Uni-structural + Explain (V1 Forward 识别)**:
   "在 GB/T 8566-2022 软件生存周期过程中，**支持过程（9 个）**的列表里，`审核过程`之后是什么？"

2) **Multi-structural + Explain (V2 Reverse 识别)**:
   "具有'记录、分析、解决问题并闭环跟踪'特征的是哪个支持过程？"

3) **Relational + Interpret (V3 Boundary 区分)**:
   "`验证过程`与`确认过程`的本质区别是什么？考查点：理解两者的检查对象不同。"

4) **Relational + Perspective (V3 Boundary 区分)**:
   "从需方和供方两个角度看，`获取过程`与`供应过程`各有什么关注重点？"

5) **Extended Abstract + Apply (V4 Scenario 应用)**:
   "某项目需求不明确、技术风险高、安全性要求高。应选择哪种开发模型？说明理由。"

6) **Extended Abstract + Empathy**:
   ```
   某团队正在开发金融系统，已加班两周。
   - 产品经理焦虑地说："监管要求下周必须上线合规功能！"
   - 开发者抗拒地说："代码没时间重构，现在加功能会出 bug！"
   - 客户担忧地说："我担心功能不完整影响业务..."

   作为架构师，你如何回应每个角色的关切？提出一个能平衡各方需求的方案。
   ```

7) **Structured Self-Knowledge Check**:
   "刚才那道题，你答题前的把握是百分之多少？实际结果如何？如果把握高但答错了，是什么原因？"

---

**If incorrect:** give doc-grounded correction, then drop one SOLO level for scaffolding:
"先用一句话分别说明：验证过程检查什么对象？确认过程检查什么对象？"
