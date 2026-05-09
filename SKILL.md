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

## Session Guardrails

Applies to every session regardless of mode.

- **Session start**: return `mode` and one actionable `next_step`.
- **Session end**: return concise `summary` and one actionable `next_step`.
- One primary mode per user turn; use `shared` only for clarification/recovery.
- Follow exactly one active mode contract (`shared`/`ingest`/`learn`/`quiz`/`review`) per turn; never mix per-mode rules.
- Keep this file thin: mode-specific fields/steps live only in mode contract files.
- Do not use memory-only fallback as primary evidence; run required API discovery first.
- **Learning telemetry is mandatory** for `learn` / `quiz` / `review`.
- After each taught concept or judged learner answer, immediately call `add_interaction_record` with `concept_id` and outcome payload.
- Do not introduce the next concept, emit the next question, advance a review queue, or hand off modes until the previous record write succeeds or recovery is surfaced.
- Keep responses concise and evidence-grounded.
- Adapt difficulty based on latest learner performance.

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
4. `shared` also handles recoverable execution failures and long-tail capability discovery, then must hand off back to one main mode (`ingest`/`learn`/`quiz`/`review`) when context is ready.

## CLI Hints

- Example:
  - `python -m scripts.cli.main get-mode-context --mode learn --plan-id PLAN_ID --topic-id t1`
- `--mode=ingest|learn|quiz|review`
- `--file=`
- `--graph-id=`
- `--payload-file=`
- `--target=`
- `--timebox=`
