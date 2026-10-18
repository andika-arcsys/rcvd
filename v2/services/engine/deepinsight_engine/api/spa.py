"""Menyajikan build React dari folder dist pada port yang sama dengan API.

Jalur `/gallery`, `/dashboard`, dan `/pims` sudah dipakai API. Layar React memakai
HashRouter (`/#/gallery`) supaya unduhan JSON tidak tertukar dengan dokumen HTML.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response


def ui_dist(config_dir: Path, override: Path | None) -> Path | None:
    dist = override if override is not None else config_dir.parent / "apps" / "desktop" / "dist"
    if (dist / "index.html").is_file():
        return dist
    return None


def mount_ui(app: FastAPI, dist: Path | None) -> None:
    if dist is None:
        return
    root = dist.resolve()

    async def _pages(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in {"GET", "HEAD"}:
            asset = _static_file(root, request.url.path)
            if asset is not None:
                return FileResponse(asset)
        response = await call_next(request)
        if response.status_code == 404 and _wants_document(request):
            return FileResponse(root / "index.html")
        return response

    app.middleware("http")(_pages)


def _wants_document(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def _static_file(dist: Path, url_path: str) -> Path | None:
    if url_path in {"", "/"}:
        return dist / "index.html"
    relative = url_path.lstrip("/")
    if not relative or "\\" in relative:
        return None
    candidate = (dist / relative).resolve()
    try:
        candidate.relative_to(dist)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None
