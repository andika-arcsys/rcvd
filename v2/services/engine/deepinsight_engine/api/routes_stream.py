"""Aliran tampilan WebSocket: JSON frame_id lalu JPEG biner (ADR-010)."""

from __future__ import annotations

import asyncio
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.logging import get_logger

stream = APIRouter()
_log = get_logger("stream")


@stream.websocket("/video/stream")
async def video_stream(websocket: WebSocket) -> None:
    if not _allowed(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    await _pump(websocket)


def _allowed(websocket: WebSocket) -> bool:
    expected = websocket.app.state.token
    if not expected:
        return True
    supplied = websocket.query_params.get("token") or ""
    return secrets.compare_digest(str(supplied).encode(), str(expected).encode())


@stream.websocket("/video/compare-stream")
async def compare_stream(websocket: WebSocket) -> None:
    if not _allowed(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    await _pump_compare(websocket)


async def _pump(websocket: WebSocket) -> None:
    last = ""
    try:
        while True:
            try:
                payload, jpeg = websocket.app.state.runtime.display_packet()
            except Exception as exc:  # noqa: BLE001 - satu frame buruk tidak menutup aliran
                _skip_frame(exc)
                await asyncio.sleep(0.03)
                continue
            key = f"{payload['state']}:{payload['frame_id']}"
            if key != last and not await _send_frame(websocket, payload, [jpeg] if jpeg else []):
                return
            last = key
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        return


async def _pump_compare(websocket: WebSocket) -> None:
    last = ""
    try:
        while True:
            try:
                payload, parts = websocket.app.state.runtime.compare_packet()
            except Exception as exc:  # noqa: BLE001 - satu frame buruk tidak menutup aliran
                _skip_frame(exc)
                await asyncio.sleep(0.03)
                continue
            key = f"{payload['state']}:{payload['frame_id']}:{len(parts)}"
            if key != last and not await _send_frame(websocket, payload, parts):
                return
            last = key
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        return


def _skip_frame(exc: Exception) -> None:
    _log.warning("frame tampilan dilewati", extra={"code": "SYS-002", "ctx": {"detail": str(exc)}})


async def _send_frame(websocket: WebSocket, payload: dict[str, object], parts: list[bytes]) -> bool:
    try:
        await websocket.send_json(payload)
        for part in parts:
            await websocket.send_bytes(part)
    except WebSocketDisconnect:
        return False
    except Exception as exc:  # noqa: BLE001 - putus aliran tanpa jejak ASGI
        _skip_frame(exc)
        return False
    return True
