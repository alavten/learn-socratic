"""Application logger for doc-socratic runtime."""

from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str = "doc_socratic") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **context: Any) -> None:
    pairs = " ".join(f"{k}={v!r}" for k, v in sorted(context.items()))
    logger.info("%s %s", event, pairs)
