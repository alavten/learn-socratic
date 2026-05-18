"""Storage path resolution (cross-platform default DB location)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.foundation.storage import _db_path, default_db_path


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
