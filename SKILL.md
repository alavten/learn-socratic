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

## Global Guardrails

Applies to every session regardless of mode.

- **Session start**: return `mode` and one actionable `next_step`.
- **Session end**: return concise `summary` and `next_step`.
- Per-turn and per-mode fields are defined only in `modes/*.md`.
- Keep responses concise and evidence-grounded.
- Adapt difficulty based on latest learner performance.
- Do not duplicate mode-specific steps here; follow `modes/*.md`.

## Intent Routing

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
