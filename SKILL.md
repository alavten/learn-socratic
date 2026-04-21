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

## Routing Rules

Route user intent before selecting a mode workflow.

1. If intent is importing materials or building/updating graph data, route to `modes/ingest.md`.
2. If intent is learning or explanation, route to `modes/learn.md`.
3. If intent is testing or checking mastery, route to `modes/quiz.md`.
4. If intent is review, spaced practice, or recap, route to `modes/review.md`.
5. If intent is missing, conflicting, or ambiguous, route to `modes/shared.md` for one clarification turn and then re-route.
6. In-session mode switching must return to this router first, then dispatch to the new target mode.

## Boundary

- This file defines behavior and routing only.
- Business data access is provided through orchestration APIs.
- Detailed prompting steps belong to `modes/*.md`.
