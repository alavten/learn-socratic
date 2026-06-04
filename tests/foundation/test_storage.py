"""Storage path resolution and schema constraints."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.foundation.storage import (
    SCHEMA_SQL,
    _db_path,
    default_db_path,
    get_connection,
    run_migrations,
    transaction,
)


def test_default_db_path_under_alavten_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DOC_SOCRATIC_DB_PATH", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    if os.name == "nt":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
    expected = tmp_path / ".alavten" / "data" / "knowledge" / "knowledge_v1.sqlite3"
    assert default_db_path() == expected
    assert _db_path() == expected


def test_db_path_honors_doc_socratic_db_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom = tmp_path / "custom.sqlite3"
    monkeypatch.setenv("DOC_SOCRATIC_DB_PATH", str(custom))
    assert _db_path() == custom


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_active_plan(conn: sqlite3.Connection, *, plan_id: str, graph_id: str) -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO Learner(learnerId, profileId, timezone, locale, status, createdAt, updatedAt)
        VALUES ('default-learner', NULL, 'UTC', 'zh-CN', 'active', ?, ?)
        ON CONFLICT(learnerId) DO NOTHING
        """,
        (now, now),
    )
    conn.execute(
        """
        INSERT INTO Graph(
            graphId, parentGraphId, graphType, graphName, purpose, owner,
            schemaVersion, schemaReleasedAt, releaseTag, releasedAt, revision, status
        ) VALUES (?, NULL, 'domain', ?, NULL, NULL, '1.0', NULL, NULL, NULL, 1, 'active')
        ON CONFLICT(graphId) DO NOTHING
        """,
        (graph_id, graph_id),
    )
    conn.execute(
        """
        INSERT INTO LearningPlan(
            learningPlanId, learnerId, graphId, planName, goalType,
            startAt, endAt, status, createdAt, updatedAt
        ) VALUES (?, 'default-learner', ?, ?, 'capability_growth', ?, NULL, 'active', ?, ?)
        """,
        (plan_id, graph_id, f"Plan-{plan_id[:8]}", now, now, now),
    )


@pytest.fixture()
def schema_only_db(monkeypatch: pytest.MonkeyPatch) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.sqlite3")
        old = os.environ.get("DOC_SOCRATIC_DB_PATH")
        monkeypatch.setenv("DOC_SOCRATIC_DB_PATH", db_path)
        with transaction() as conn:
            conn.executescript(SCHEMA_SQL)
        yield db_path
        if old is not None:
            monkeypatch.setenv("DOC_SOCRATIC_DB_PATH", old)


def test_run_migrations_creates_active_plan_unique_index(isolated_db: str) -> None:
    run_migrations()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'index' AND name = 'uq_active_plan_per_learner_graph'
            """
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_unique_index_blocks_second_active_plan(schema_only_db: str) -> None:
    conn = get_connection()
    try:
        graph_id = "g-unique-plan"
        _insert_active_plan(conn, plan_id=str(uuid.uuid4()), graph_id=graph_id)
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            _insert_active_plan(conn, plan_id=str(uuid.uuid4()), graph_id=graph_id)
            conn.commit()
    finally:
        conn.close()
