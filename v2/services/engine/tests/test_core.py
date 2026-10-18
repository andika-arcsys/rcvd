from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from deepinsight_engine.core import ids
from deepinsight_engine.core.errors import REGISTRY, EngineError, render_error_codes_markdown

DOCS_ERROR_CODES = Path(__file__).resolve().parents[3] / "docs" / "ERROR_CODES.md"


def test_display_id_formats() -> None:
    now = datetime(2026, 10, 17, 16, 5)
    assert ids.session_id(now) == "SES-20261017-1605"
    assert ids.mission_id(now, 3) == "MSN-20261017-03"
    assert ids.snapshot_id("SES-20261017-1605", 12) == "SNP-SES-20261017-1605-0012"
    assert ids.candidate_id("SES-20261017-1605", 1) == "CND-SES-20261017-1605-0001"


def test_uuid7_is_valid_and_time_ordered() -> None:
    first, second = ids.uuid7(), ids.uuid7()
    parsed = uuid.UUID(first)
    assert parsed.version == 7 and parsed.variant == uuid.RFC_4122
    assert first[:8] <= second[:8]


def test_error_codes_are_well_formed() -> None:
    assert REGISTRY
    for code, spec in REGISTRY.items():
        assert re.fullmatch(r"[A-Z]{3,5}-\d{3}", code)
        assert spec.message_id and spec.cause and spec.action


def test_unregistered_code_is_rejected() -> None:
    with pytest.raises(KeyError):
        EngineError("XXX-999")


def test_error_codes_doc_is_in_sync() -> None:
    assert DOCS_ERROR_CODES.read_text(encoding="utf-8") == render_error_codes_markdown(), (
        "Jalankan `make docs-errors` untuk memperbarui docs/ERROR_CODES.md"
    )
