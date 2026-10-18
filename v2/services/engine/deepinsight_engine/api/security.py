"""Token opsional. Bila diisi, UI mengirimnya di header. Wajib saat env=prod."""

from __future__ import annotations

import secrets

from fastapi import Header, Request

from ..core.errors import EngineError

TOKEN_HEADER = "X-DeepInsight-Token"


def require_token(request: Request, x_deepinsight_token: str | None = Header(default=None)) -> None:
    expected: str | None = request.app.state.token
    if expected is None:
        return
    supplied = x_deepinsight_token or ""
    if not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise EngineError("API-001")
