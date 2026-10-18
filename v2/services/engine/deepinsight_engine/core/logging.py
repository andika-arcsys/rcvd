"""Log JSON terstruktur, satu berkas per sesi, dirotasi."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOGGER_NAME = "deepinsight"


class JsonFormatter(logging.Formatter):
    def __init__(self, session: str) -> None:
        super().__init__()
        self._session = session

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "session_id": self._session,
            "component": record.name.removeprefix(f"{LOGGER_NAME}."),
            "code": getattr(record, "code", None),
            "msg": record.getMessage(),
            "ctx": getattr(record, "ctx", None),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    session: str, log_dir: Path, level: str, rotate_mb: int, backups: int
) -> logging.Logger:
    """Pasang handler berkas (dirotasi) dan stderr pada logger utama."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    formatter = JsonFormatter(session)
    file_handler = RotatingFileHandler(
        log_dir / "engine.log",
        maxBytes=rotate_mb * 1024 * 1024,
        backupCount=backups,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def get_logger(component: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{component}")
