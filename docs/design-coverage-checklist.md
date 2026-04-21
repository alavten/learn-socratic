# Design Coverage Checklist

## Architecture Design Coverage

- [x] L1 entry routing implemented in `SKILL.md`.
- [x] L2 mode contracts implemented in `modes/shared.md`, `modes/learn.md`, `modes/quiz.md`, `modes/review.md`.
- [x] L3 orchestration service implemented in `scripts/orchestration/orchestration_app_service.py`.
- [x] Prompt text packaging implemented in `scripts/orchestration/prompt_templates.py`.
- [x] L4 knowledge graph module implemented in `scripts/knowledge_graph/`.
- [x] L4 learning module implemented in `scripts/learning/`.
- [x] L5 storage and logging implemented in `scripts/foundation/storage.py` and `scripts/foundation/logger.py`.
- [x] App bootstrap and wiring implemented in `scripts/app.py`.

## Data Model Coverage

- [x] Graph entities implemented: `Graph`, `Topic`, `Concept`, `TopicConcept`, `ConceptRelation`, `Evidence`, `RelationEvidence`.
- [x] Learning entities implemented: `Learner`, `LearningPlan`, `LearningSession`, `LearningRecord`, `LearnerConceptState`, `LearningTask`.
- [x] Plan scope extension table implemented: `LearningPlanTopic`.
- [x] Required enums/check constraints implemented in schema.
- [x] Version fields (`dr`, `drtime`) and current-record uniqueness implemented.
- [x] Relation evidence mandatory check enforced at ingest validation.
- [x] `LearnerConceptState` uniqueness and target constraints implemented.
- [x] `createdAt/updatedAt` metadata maintained on learning-side entities.

## API and Flow Coverage

- [x] Orchestration self-description APIs: `list_apis`, `get_api_spec`.
- [x] Knowledge graph APIs: list/get/ingest/get_concepts/get_concept_relations/get_concept_evidence.
- [x] Learning APIs: list/create/extend/get_learning_context/get_quiz_context/get_review_context/append_learning_record.
- [x] Prompt APIs: `get_learning_prompt`, `get_quiz_prompt`, `get_review_prompt`.
- [x] End-to-end flows tested: ingest -> learn -> quiz -> review -> mode switch.

## Quality and Verification

- [x] Unit tests added for knowledge graph, learning, orchestration.
- [x] Integration test added for full loop execution.
- [x] DB path override enabled via `DOC_SOCRATIC_DB_PATH` for isolated tests.
