"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from scripts.foundation.storage import run_migrations


@pytest.fixture()
def isolated_db() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.sqlite3")
        old = os.environ.get("DOC_SOCRATIC_DB_PATH")
        os.environ["DOC_SOCRATIC_DB_PATH"] = db_path
        run_migrations()
        yield db_path
        if old is None:
            os.environ.pop("DOC_SOCRATIC_DB_PATH", None)
        else:
            os.environ["DOC_SOCRATIC_DB_PATH"] = old
