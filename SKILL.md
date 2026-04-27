---
name: learn-socratic
description: Socratic learning from documents with graph ingest plus a learn/quiz/review loop, mastery tracking, spaced scheduling, and variant quizzing. Use when users ask to study, teach me, test me, review, memorize, make flashcards, or prep for exams.
---

# Doc Socratic Learning Optimized

## Purpose

This skill supports graph ingestion and concept learning with four interaction modes:

- `ingest`: convert structured payload into a validated knowledge graph revision.
- `learn`: explain and coach new material.
- `quiz`: assess current mastery.
- `review`: reinforce retention and weak points.

## Session Contract

- One primary mode per user turn unless clarifying in `shared`.
- Always return `summary` plus one concrete `next_step` aligned with the active mode contract.
- Detailed steps live in `modes/*.md`; do not duplicate here.

## Global Guardrails

Applies to every session regardless of mode.

- **Session start**: return `mode` and one actionable `next_step`.
- **Session end**: return concise `summary` and `next_step`.
- Per-turn and per-mode fields are defined only in `modes/*.md`.
- Keep responses concise and evidence-grounded.
- Adapt difficulty based on latest learner performance.
- Do not duplicate mode-specific steps here; follow `modes/*.md`.

## Intent Matrix

Map natural language intent to target mode and mode contract file:

| User intent hint                            | Target mode | Contract file     |
| ------------------------------------------- | ----------- | ----------------- |
| import materials, build graph, update graph | `ingest`    | `modes/ingest.md` |
| explain, teach me, learn                    | `learn`     | `modes/learn.md`  |
| test me, quiz, ask questions                | `quiz`      | `modes/quiz.md`   |
| review, recap, due items                    | `review`    | `modes/review.md` |
| ambiguous or conflicting intent             | `shared`    | `modes/shared.md` |

Routing flow rules:

1. If intent is missing, conflicting, or ambiguous, route to `shared` for one clarification turn and then re-route.
2. In-session mode switching must return to this router first, then dispatch to the new target mode.
3. If target mode file is unavailable or dispatch fails, return `summary` with failure reason and `next_step` to continue in `shared`.

## Quick Start

- Detect user intent and route using the table above.
- Load only the selected mode contract file (for example, modes/learn.md) and confirm it is available before execution.
- If mode file loading fails, route to `shared` and return failure reason with next action.
- Return mode output with `summary` and one actionable `next_step`.

## CLI Hints

- Example:
  - `python scripts/cli.py get-learning-prompt --plan-id PLAN_ID --topic-id t1`
- `--mode=ingest|learn|quiz|review`
- `--file=`
- `--graph-id=`
- `--payload-file=`
- `--target=`
- `--timebox=`

## 踩坑经验

（以下由 AI 在实际调用中自动积累，请勿手动删除）

- **ingest-knowledge-graph / graph_type 值约束**：`graph.graph_type` 只能是 `'domain'`、`'module'`、`'view'` 三者之一，`'curriculum'` 等其他值会触发 CHECK 约束错误报错。查阅已有图谱：se-full-20260422 和 claude-code-full 均使用 `graph_type: "domain"`。
- **ingest-knowledge-graph / 引用已存在概念**：若 relations 中的 from_concept_id / to_concept_id 引用了已在图谱中存在但不在当前 payload 中的概念，会报 "not found in payload concepts" 错误。解决方法：把被引用的已存在概念也加到 payload 的 concepts 列表中（至少包含 concept_id + canonical_name + definition 即可，API 会以 upsert 模式处理）。
- **get-knowledge-graph / 返回字段**：`concept_briefs` 中每个对象包含 `concept_id`、`canonical_name`、`short_definition`、`difficulty`（而非 `difficulty_level`）；`topic_concepts` 包含 `topic_concept_id`、`topic_id`、`concept_id`、`role`、`rank`、`canonical_name`、`short_definition`、`difficulty`。

