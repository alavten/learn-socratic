"""SQLite storage adapter and schema migration."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _db_path() -> Path:
    from_env = os.getenv("DOC_SOCRATIC_DB_PATH")
    if from_env:
        return Path(from_env)
    return _root_dir() / "data" / "skill.sqlite3"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    _ensure_parent(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_all(sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def execute(sql: str, params: Sequence[Any] = ()) -> int:
    with transaction() as conn:
        result = conn.execute(sql, params)
        return result.rowcount


def execute_many(sql: str, params_list: Sequence[Sequence[Any]]) -> None:
    with transaction() as conn:
        conn.executemany(sql, params_list)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS Graph (
    graphId TEXT PRIMARY KEY,
    parentGraphId TEXT REFERENCES Graph(graphId),
    graphType TEXT NOT NULL CHECK (graphType IN ('domain', 'module', 'view')),
    graphName TEXT NOT NULL,
    purpose TEXT,
    owner TEXT,
    schemaVersion TEXT NOT NULL,
    schemaReleasedAt TEXT,
    releaseTag TEXT,
    releasedAt TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS Topic (
    topicId TEXT PRIMARY KEY,
    graphId TEXT NOT NULL REFERENCES Graph(graphId) ON DELETE CASCADE,
    parentTopicId TEXT REFERENCES Topic(topicId),
    topicName TEXT NOT NULL,
    topicType TEXT NOT NULL,
    sortOrder INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS Concept (
    conceptId TEXT PRIMARY KEY,
    graphId TEXT NOT NULL REFERENCES Graph(graphId) ON DELETE CASCADE,
    conceptType TEXT NOT NULL,
    canonicalName TEXT NOT NULL,
    definition TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'zh-CN',
    difficultyLevel TEXT NOT NULL DEFAULT 'medium',
    dr INTEGER NOT NULL DEFAULT 0 CHECK (dr IN (0, 1)),
    drtime TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_concept_current
ON Concept(graphId, canonicalName, language, conceptType, dr);

CREATE TABLE IF NOT EXISTS TopicConcept (
    topicConceptId TEXT PRIMARY KEY,
    topicId TEXT NOT NULL REFERENCES Topic(topicId) ON DELETE CASCADE,
    conceptId TEXT NOT NULL REFERENCES Concept(conceptId) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'core',
    aliasText TEXT,
    aliasType TEXT,
    aliasLanguage TEXT,
    aliasStatus TEXT,
    rank INTEGER NOT NULL DEFAULT 0,
    validFrom TEXT,
    validTo TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_topic_concept ON TopicConcept(topicId, conceptId, role);

CREATE TABLE IF NOT EXISTS ConceptRelation (
    conceptRelationId TEXT PRIMARY KEY,
    graphId TEXT NOT NULL REFERENCES Graph(graphId) ON DELETE CASCADE,
    fromConceptId TEXT NOT NULL REFERENCES Concept(conceptId),
    toConceptId TEXT NOT NULL REFERENCES Concept(conceptId),
    relationType TEXT NOT NULL CHECK (
        relationType IN ('prerequisite_of', 'part_of', 'contrast_with', 'applied_in', 'related_to')
    ),
    directionality TEXT NOT NULL DEFAULT 'directed',
    weight REAL NOT NULL DEFAULT 1.0,
    confidence REAL NOT NULL DEFAULT 0.7,
    dr INTEGER NOT NULL DEFAULT 0 CHECK (dr IN (0, 1)),
    drtime TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL,
    CHECK (fromConceptId != toConceptId)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_relation_current
ON ConceptRelation(graphId, fromConceptId, toConceptId, relationType, dr);

CREATE TABLE IF NOT EXISTS Evidence (
    evidenceId TEXT PRIMARY KEY,
    sourceType TEXT NOT NULL,
    sourceTitle TEXT,
    sourceUri TEXT,
    sourceChecksum TEXT,
    sourceIndexedAt TEXT,
    locator TEXT,
    quoteText TEXT NOT NULL,
    note TEXT,
    capturedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS RelationEvidence (
    relationEvidenceId TEXT PRIMARY KEY,
    conceptRelationId TEXT NOT NULL REFERENCES ConceptRelation(conceptRelationId) ON DELETE CASCADE,
    evidenceId TEXT NOT NULL REFERENCES Evidence(evidenceId) ON DELETE CASCADE,
    supportScore REAL NOT NULL DEFAULT 0.7,
    evidenceRole TEXT NOT NULL DEFAULT 'primary'
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_relation_evidence
ON RelationEvidence(conceptRelationId, evidenceId);

CREATE TABLE IF NOT EXISTS Learner (
    learnerId TEXT PRIMARY KEY,
    profileId TEXT,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    locale TEXT NOT NULL DEFAULT 'zh-CN',
    status TEXT NOT NULL DEFAULT 'active',
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS LearningPlan (
    learningPlanId TEXT PRIMARY KEY,
    learnerId TEXT NOT NULL REFERENCES Learner(learnerId) ON DELETE CASCADE,
    graphId TEXT NOT NULL REFERENCES Graph(graphId),
    planName TEXT NOT NULL,
    goalType TEXT NOT NULL,
    startAt TEXT,
    endAt TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS LearningPlanTopic (
    learningPlanTopicId TEXT PRIMARY KEY,
    learningPlanId TEXT NOT NULL REFERENCES LearningPlan(learningPlanId) ON DELETE CASCADE,
    topicId TEXT NOT NULL REFERENCES Topic(topicId),
    reason TEXT,
    createdAt TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_plan_topic ON LearningPlanTopic(learningPlanId, topicId);

CREATE TABLE IF NOT EXISTS LearningSession (
    sessionId TEXT PRIMARY KEY,
    learnerId TEXT NOT NULL REFERENCES Learner(learnerId),
    learningPlanId TEXT NOT NULL REFERENCES LearningPlan(learningPlanId) ON DELETE CASCADE,
    startedAt TEXT NOT NULL,
    endedAt TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS LearningRecord (
    learningRecordId TEXT PRIMARY KEY,
    sessionId TEXT NOT NULL REFERENCES LearningSession(sessionId) ON DELETE CASCADE,
    conceptId TEXT NOT NULL REFERENCES Concept(conceptId),
    recordType TEXT NOT NULL CHECK (recordType IN ('learn', 'quiz', 'review')),
    result TEXT,
    score REAL,
    latencyMs INTEGER,
    difficultyBucket TEXT CHECK (difficultyBucket IN ('easy', 'medium', 'hard')),
    feedbackType TEXT,
    occurredAt TEXT NOT NULL,
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS LearnerConceptState (
    learnerConceptStateId TEXT PRIMARY KEY,
    learnerId TEXT NOT NULL REFERENCES Learner(learnerId),
    learningPlanId TEXT NOT NULL REFERENCES LearningPlan(learningPlanId) ON DELETE CASCADE,
    conceptId TEXT NOT NULL REFERENCES Concept(conceptId),
    targetLevel TEXT,
    targetScore REAL,
    masteryLevel TEXT NOT NULL DEFAULT 'New',
    masteryScore REAL NOT NULL DEFAULT 0.0,
    learnCount INTEGER NOT NULL DEFAULT 0 CHECK (learnCount >= 0),
    quizCount INTEGER NOT NULL DEFAULT 0 CHECK (quizCount >= 0),
    reviewCount INTEGER NOT NULL DEFAULT 0 CHECK (reviewCount >= 0),
    easyCount INTEGER NOT NULL DEFAULT 0 CHECK (easyCount >= 0),
    mediumCount INTEGER NOT NULL DEFAULT 0 CHECK (mediumCount >= 0),
    hardCount INTEGER NOT NULL DEFAULT 0 CHECK (hardCount >= 0),
    correctCount INTEGER NOT NULL DEFAULT 0 CHECK (correctCount >= 0),
    wrongCount INTEGER NOT NULL DEFAULT 0 CHECK (wrongCount >= 0),
    confidence REAL NOT NULL DEFAULT 0.0,
    forgettingRisk REAL NOT NULL DEFAULT 1.0,
    lastInteractionAt TEXT,
    nextReviewAt TEXT,
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL,
    CHECK (targetLevel IS NOT NULL OR targetScore IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_learner_plan_concept
ON LearnerConceptState(learnerId, learningPlanId, conceptId);

CREATE TABLE IF NOT EXISTS LearningTask (
    learningTaskId TEXT PRIMARY KEY,
    learningPlanId TEXT NOT NULL REFERENCES LearningPlan(learningPlanId) ON DELETE CASCADE,
    conceptId TEXT NOT NULL REFERENCES Concept(conceptId),
    taskType TEXT NOT NULL CHECK (taskType IN ('learn', 'review')),
    reasonType TEXT NOT NULL CHECK (reasonType IN ('overdue', 'upcoming', 'weak_point', 'manual')),
    strategy TEXT,
    priorityScore REAL NOT NULL DEFAULT 0.5,
    dueAt TEXT,
    generatedAt TEXT NOT NULL,
    batchId TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL
);
"""


def run_migrations() -> None:
    with transaction() as conn:
        conn.executescript(SCHEMA_SQL)


def paginate(limit: int, offset: str | None) -> tuple[int, int]:
    safe_limit = max(1, min(limit, 200))
    safe_offset = int(offset or "0")
    if safe_offset < 0:
        safe_offset = 0
    return safe_limit, safe_offset
