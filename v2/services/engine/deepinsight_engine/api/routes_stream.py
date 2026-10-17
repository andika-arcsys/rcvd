"""Aliran tampilan WebSocket: JSON frame_id lalu JPEG biner (ADR-010)."""

from __future__ import annotations

import asyncio
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

stream = APIRouter()


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


async def _pump(websocket: WebSocket) -> None:
    last = ""
    try:
        while True:
            payload, jpeg = websocket.app.state.runtime.display_packet()
            key = f"{payload['state']}:{payload['frame_id']}"
            if key != last:
                await websocket.send_json(payload)
                if jpeg:
                    await websocket.send_bytes(jpeg)
                last = key
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        return
