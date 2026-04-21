---
name: doc-socratic-learning-optimized
description: 基于用户文档的苏格拉底式学习与建图（Ingest / Learn / Quiz / Review）；SOLO 层级递进追问与 UBD 对齐；Python 脚本支持知识图谱入库、学习日志、掌握度、间隔复习调度与按变式出题；测验与复习结果可持久化到学习记录。
args:
  type: string
  completions:
    - --file=
    - --mode=ingest
    - --mode=learn
    - --mode=quiz
    - --mode=review
    - --graph-id=
    - --payload-file=
    - --target=
    - --timebox=
---

# Doc Socratic Learning Optimized

## Purpose

This skill supports graph ingestion and concept learning with four interaction modes:

- `ingest`: convert structured payload into a validated knowledge graph revision.
- `learn`: explain and coach new material.
- `quiz`: assess current mastery.
- `review`: reinforce retention and weak points.

## Session Contract

The following contract applies to every session regardless of mode.

- **Session start**: return mode and one actionable `next_step`.
- **Session end**: return concise `summary` and `next_step`.
- Detailed output payloads are defined in `modes/*.md`.

## Global Guardrails

- Keep responses concise and evidence-grounded.
- Always provide `summary` and `next_step` in mode outputs.
- Adapt difficulty based on latest learner performance.
- Keep mode-specific details in `modes/*.md`; do not duplicate here.

## Methodology Directives (for AI execution)

- Use **SOLO progression** to control cognitive depth: `Uni -> Multi -> Relational -> Extended`.
- Use **UBD evidence thinking**: evaluate whether learner can `Explain`, `Interpret`, `Apply`, then reflect.
- Apply **Feynman loop** in learning turns: ask learner to restate in own words, identify gaps, then repair with simpler explanation.
- Apply **retrieval-first** in quiz/review: ask before telling, then correct with concise evidence.
- Apply **spacing-first** in review: prioritize due/overdue/weak concepts before new ones.
- Add a lightweight **metacognitive check** every few turns (confidence vs actual result).

## Intent Matrix

Natural language intent should be mapped before mode execution.

| User intent hint | Target mode |
| --- | --- |
| 导入资料 / 建图 / 更新知识 | `ingest` |
| 讲解 / 学习 / 理解 | `learn` |
| 测试 / 考考我 / 出题 | `quiz` |
| 复习 / 回顾 / 到期项 | `review` |
| 意图冲突或缺少上下文 | `shared` |

## Routing Rules

1. If intent is importing materials or building/updating graph data, route to `modes/ingest.md`.
2. If intent is learning or explanation, route to `modes/learn.md`.
3. If intent is testing or checking mastery, route to `modes/quiz.md`.
4. If intent is review, spaced practice, or recap, route to `modes/review.md`.
5. If intent is missing, conflicting, or ambiguous, route to `modes/shared.md` for one clarification turn and then re-route.
6. In-session mode switching must return to this router first, then dispatch to the new target mode.

## Boundary

- This file defines cross-mode behavior and routing only.
- Business data access is provided through orchestration APIs.
- Detailed prompting steps belong to `modes/*.md`.
