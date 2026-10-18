"""Cache LRU berbatas ukuran. Bukti tidak pernah masuk ke sini."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

from ..core.errors import EngineError

_KEY = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,120}$")


class CacheManager:
    def __init__(self, root: Path, max_mb: int) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._max_bytes = max_mb * 1024 * 1024
        self._order: OrderedDict[str, int] = OrderedDict()

    def put(self, key: str, data: bytes) -> None:
        self._check_key(key)
        if len(data) > self._max_bytes:
            raise EngineError("STO-001", key)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self._order[key] = len(data)
        self._order.move_to_end(key)
        self._evict()

    def get(self, key: str) -> bytes | None:
        self._check_key(key)
        path = self._path(key)
        if key not in self._order or not path.is_file():
            return None
        self._order.move_to_end(key)
        return path.read_bytes()

    def clear(self) -> None:
        for path in self.root.rglob("*"):
            if path.is_file():
                path.unlink()
        self._order.clear()

    def used_mb(self) -> float:
        return sum(self._order.values()) / 1024**2

    def _evict(self) -> None:
        while self._order and sum(self._order.values()) > self._max_bytes:
            key, _size = self._order.popitem(last=False)
            path = self._path(key)
            if path.is_file():
                path.unlink()

    def _path(self, key: str) -> Path:
        return self.root / key

    def _check_key(self, key: str) -> None:
        if key.startswith("evidence") or not _KEY.match(key):
            raise EngineError("API-002", "kunci cache tidak diizinkan")
