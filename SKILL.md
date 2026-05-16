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
- Keep this file thin: mode-specific fields/steps live only in reference contract files (`references/*.md`).
- Do not use memory-only fallback as primary evidence; run required API discovery first.
- For multi-graph courses or books, do not leave chapter graphs as parallel roots: create a parent `graph_id`, set each chapter’s `graph.parent_graph_id`, and keep a shared `graph.graph_name` prefix (see `references/ingest.md` “书系拆章”) unless the user explicitly wants isolated graphs.
- **Learning telemetry is mandatory** for `learn` / `quiz` / `review`.
- After each taught concept or judged learner answer, immediately call `add_interaction_record` with `concept_id` and outcome payload.
- Do not introduce the next concept, emit the next question, advance a review queue, or hand off modes until the previous record write succeeds or recovery is surfaced.
- Keep responses concise and evidence-grounded.
- Adapt difficulty based on latest learner performance.

## Intent Matrix

Map natural language intent to target mode and reference contract file:

| User intent hint                            | Target mode | Contract file          |
| ------------------------------------------- | ----------- | ----------------- |
| import materials, build graph, update graph | `ingest`    | `references/ingest.md` |
| explain, teach me, learn                    | `learn`     | `references/learn.md`  |
| test me, quiz, ask questions                | `quiz`      | `references/quiz.md`   |
| review, recap, due items                    | `review`    | `references/review.md` |
| ambiguous or conflicting intent             | `shared`    | `references/shared.md` |

Routing flow rules:

1. If intent is missing, conflicting, or ambiguous, route to `shared` for one clarification turn and then re-route.
2. In-session mode switching must return to this router first, then dispatch to the new target mode.
3. If target mode file is unavailable or dispatch fails, return `summary` with failure reason and `next_step` to continue in `shared`.
4. `shared` also handles recoverable execution failures and long-tail capability discovery, then must hand off back to one main mode (`ingest`/`learn`/`quiz`/`review`) when context is ready.

## CLI Hints

Run commands from the skill repo root (the directory that contains `scripts/`), e.g. `cd …/learn-socratic && python -m scripts.cli.main …`.

**Discovery (authoritative)**

1. **`list-apis`** — JSON list of orchestration API `name` values (snake_case), same as `OrchestrationAppService.list_apis()`.
2. **`get-api-spec --api-name <snake_case>`** — input JSON Schema for that API (e.g. `get_knowledge_graph`).
3. **`list-knowledge-graphs`** — lists stored graph metadata; use this to obtain valid **`graph_id`** values. It does **not** enumerate shell subcommands (do not confuse with `list-apis`).

**Allowed CLI subcommands only** (must match `scripts/cli/main.py`; do not invent names such as `get-concepts`):

`list-apis`, `get-api-spec`, `list-knowledge-graphs`, `get-knowledge-graph`, `ingest-knowledge-graph`, `remove-knowledge-graph-entities`, `list-learning-plans`, `create-learning-plan`, `extend-learning-plan-topics`, `get-mode-context`, `add-interaction-record`

**Notes**

- There is **no** `get-concepts` CLI. To fetch concept briefs from the terminal by graph (and optionally topic), use **`get-knowledge-graph`** with `--graph-id` and optional `--topic-id`, `--concept-limit`, `--offset`.
- `scripts.knowledge_graph.api.get_concepts` is a **Python module** helper, not a method on `OrchestrationAppService` and not exposed as a subcommand.
- Some orchestration APIs (e.g. `get_discovery_context`) have **no** dedicated CLI; call them via `create_app()` in Python (or `call_api` if you use it).

Example:

`python -m scripts.cli.main get-mode-context --mode learn --plan-id PLAN_ID --topic-id t1`
