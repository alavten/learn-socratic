"""Tests for scripts/migrations/merge_b2_into_parent_graph.py."""

from __future__ import annotations

from pathlib import Path

from scripts.migrations.merge_b2_into_parent_graph import _connect, run_merge


def test_dry_run_precheck_on_empty_migrated_db_lists_missing_graphs(isolated_db: str) -> None:
    conn = _connect(Path(isolated_db))
    try:
        out = run_merge(conn, dry_run=True)
    finally:
        conn.close()
    assert out["dry_run"] is True
    missing = out["precheck"]["missing_graphs"]
    assert "claude-harness-vs-codex-harness" in missing
    assert "b2-ch00-reading-map" in missing
