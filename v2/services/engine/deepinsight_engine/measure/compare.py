"""Pembanding batas inklusif. Toleransi dibaca dari config."""

from __future__ import annotations

# 1 meter = 100 cm, dan 100% = 1. Bukan ambang bisnis.
PER_HUNDRED = 100.0


def _scale(value: float, limit: float) -> float:
    return max(1.0, abs(value), abs(limit))


def leq(value: float, limit: float, tol: float) -> bool:
    return value <= limit + tol * _scale(value, limit)


def geq(value: float, limit: float, tol: float) -> bool:
    return value >= limit - tol * _scale(value, limit)


def rel_delta(left: float, right: float) -> float:
    base = max(abs(left), abs(right))
    if base == 0.0:
        return 0.0
    return abs(left - right) / base


def within_percent(delta: float, whole: float, tolerance_pct: float, tol: float) -> bool:
    return leq(delta / whole, tolerance_pct / PER_HUNDRED, tol)
