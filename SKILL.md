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
- **Books and large documents**: use one stable `graph_id` for the whole book; ingest **one chapter per turn** into that same graph (chapters as `topics` with `topic_type: chapter`, sections under `parent_topic_id`). Do not split a single book into parallel root graphs or try to build the full book payload in one shot. See `references/ingest.md` (“书籍与大文档导入”).
- Legacy multi-`graph_id` + `parent_graph_id` is only when the user explicitly wants isolated chapter graphs (see `references/ingest.md` “书系拆章（遗留）”).
- **Learning telemetry is mandatory** for `learn` / `quiz` / `review`.
- **Quiz storage granularity** is always one `add_interaction_record` per judged question, regardless of `quiz_pacing` (`per_concept` vs `per_chapter`); pacing only changes how many questions appear in one user turn.
- After each taught concept or judged learner answer, immediately call `add_interaction_record` with `concept_id` and outcome payload.
- Do not introduce the next concept, emit the next question, advance a review queue, or hand off modes until the previous record write succeeds or recovery is surfaced.
- Keep responses concise and evidence-grounded.
- Adapt difficulty based on latest learner performance.

## Intent Matrix

Map natural language intent to target mode and reference contract file:

| User intent hint                            | Target mode | Contract file          |
| ------------------------------------------- | ----------- | ----------------- |
| import materials, build graph, update graph | `ingest`    | `references/ingest.md` |
| fix chapter order, reorder topics, 章节顺序 | `ingest` or dedicated reorder flow | `references/reorder-topics.md` |
| explain, teach me, learn                    | `learn`     | `references/learn.md`  |
| test me, quiz, ask questions, 一题一题, 批量测验, 一章测验 | `quiz`      | `references/quiz.md`   |
| review, recap, due items                    | `review`    | `references/review.md` |
| weak points, mastery report, chapter performance, 薄弱点, 掌握程度 | `shared` (discovery) then diagnostics CLI | `references/shared.md` |
| ambiguous or conflicting intent             | `shared`    | `references/shared.md` |

Routing flow rules:

1. If intent is missing, conflicting, or ambiguous, route to `shared` for one clarification turn and then re-route.
2. In-session mode switching must return to this router first, then dispatch to the new target mode.
3. If target mode file is unavailable or dispatch fails, return `summary` with failure reason and `next_step` to continue in `shared`.
4. `shared` also handles recoverable execution failures and long-tail capability discovery, then must hand off back to one main mode (`ingest`/`learn`/`quiz`/`review`) when context is ready.

## Mastery / weak-point diagnostics

When the user asks for **weak points**, **mastery by chapter**, or **learning performance analysis** (not an interactive review/quiz turn):

1. If `plan_id` is unknown, run discovery (`list-learning-plans` or `shared` flow) and let the user pick a plan.
2. Call **`get-mastery-diagnostics`** once and read the JSON (`by_topic`, `by_concept`, `ranked_weak_concepts`, `summary`). Do **not** query SQLite or invent table names.
3. Optional scope: `--topic-id` for a chapter subtree, or `--concept-id` for a concept plus all `part_of` sub-concepts.
4. After the report, route to `review` / `learn` / `quiz` with a concrete `next_step`.

**Shell (required prefix on every command):** `cd <skill-repo-root> && python -m scripts.cli.main …`

Examples:

`cd …/learn-socratic && python -m scripts.cli.main get-mastery-diagnostics --plan-id PLAN_ID`

`cd …/learn-socratic && python -m scripts.cli.main get-mastery-diagnostics --plan-id PLAN_ID --topic-id t1`

`cd …/learn-socratic && python -m scripts.cli.main get-mastery-diagnostics --plan-id PLAN_ID --concept-id c1`

**Forbidden for diagnostics:** ad-hoc SQL or `from scripts.knowledge_graph.api import create_app`. Python entry point when needed: `from scripts.app import create_app`.

**`list-learning-plans` semantics:** `progress.pending_tasks` counts **LearningTask** queue rows, not “number of review questions due”.

**`get-mode-context` vs diagnostics:** CLI stdout includes `context_summary` for **session continuation** in learn/quiz/review; for mastery reports use **`get-mastery-diagnostics`** instead.

## CLI Hints

Run commands from the skill repo root (the directory that contains `scripts/`), e.g. `cd …/learn-socratic && python -m scripts.cli.main …`.

**Naming**

| Surface | Style | Example |
| ------- | ----- | ------- |
| CLI subcommands, flags, API discovery `name` (`list-apis`, `get-api-spec --api-name`) | kebab-case | `create-learning-plan`, `--plan-id` |
| JSON request/response fields in API payloads | snake_case | `graph_id`, `plan_id`, `concept_id` |

**Discovery (authoritative)**

1. **`list-apis`** — JSON list of orchestration API `name` values (kebab-case), aligned with CLI subcommands where a dedicated command exists.
2. **`get-api-spec --api-name <kebab-case>`** — input JSON Schema; value must be a `name` from **`list-apis`** (e.g. `create-learning-plan`). Snake_case names (e.g. `create_learning_plan`) are rejected.
3. **`list-knowledge-graphs`** — lists stored graph metadata; use this to obtain valid **`graph_id`** values. It does **not** enumerate shell subcommands (do not confuse with `list-apis`).

**Allowed CLI subcommands only** (must match `scripts/cli/main.py`; do not invent names such as `get-concepts`):

`list-apis`, `get-api-spec`, `list-knowledge-graphs`, `get-knowledge-graph`, `ingest-knowledge-graph`, `reorder-graph-topics`, `remove-knowledge-graph-entities`, `list-learning-plans`, `create-learning-plan`, `extend-learning-plan-topics`, `get-mode-context`, `get-mastery-diagnostics`, `add-interaction-record`

**Notes**

- There is **no** `get-concepts` CLI. To fetch concept briefs from the terminal by graph (and optionally topic), use **`get-knowledge-graph`** with `--graph-id` and optional `--topic-id`, `--concept-limit`, `--offset`.
- `scripts.knowledge_graph.api.get_concepts` is a **Python module** helper, not a method on `OrchestrationAppService` and not exposed as a subcommand.
- Some orchestration APIs (e.g. `get_discovery_context`) have **no** dedicated CLI; call them via `from scripts.app import create_app` in Python (or `call_api` if you use it).

Example:

`python -m scripts.cli.main get-mode-context --mode learn --plan-id PLAN_ID --topic-id t1`
