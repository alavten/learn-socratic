"""Application bootstrap and dependency wiring."""

from __future__ import annotations

import sys
from pathlib import Path

# Support direct execution: `python scripts/app.py`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.foundation.logger import get_logger, log_event
from scripts.foundation.storage import run_migrations
from scripts.orchestration.orchestration_app_service import OrchestrationAppService


def create_app() -> OrchestrationAppService:
    logger = get_logger("doc_socratic.app")
    run_migrations()
    log_event(logger, "migrations_completed")
    return OrchestrationAppService()


if __name__ == "__main__":
    service = create_app()
    print({"apis": service.list_apis()})
