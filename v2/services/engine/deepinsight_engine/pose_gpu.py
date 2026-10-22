"""Pose planar marker. SVD homografi berjalan di CUDA bila PyTorch melihat GPU.

Titik gambar dinormalisasi dulu dengan undistortPoints. Empat sudut kertas
cukup untuk homografi. Hasilnya diselaraskan dengan solvePnP OpenCV pada distorsi
nol maupun tidak. Bila CUDA gagal, pose dihitung di CPU dengan rumus yang sama.
"""

from __future__ import annotations

import importlib
from typing import Any, Protocol

import numpy as np

_GPU = "GPU"
_CPU = "CPU"


class _Algebra(Protocol):
    label: str

    def tensor(self, value: np.ndarray) -> Any: ...

    def numpy(self, value: Any) -> np.ndarray: ...

    def svd_vh(self, design: Any) -> Any: ...

    def column(self, matrix: Any, index: int) -> Any: ...

    def norm(self, vector: Any) -> Any: ...

    def cross(self, left: Any, right: Any) -> Any: ...

    def stack(self, columns: list[Any]) -> Any: ...

    def svd_rotation(self, matrix: Any) -> Any: ...

    def scale(self, vector: Any, factor: float) -> Any: ...

    def item(self, value: Any) -> float: ...

    def reshape3(self, row: Any) -> Any: ...


def solve_planar(
    cv2: Any,
    obj_xyz: np.ndarray,
    image_pts: np.ndarray,
    camera_matrix: np.ndarray,
    dist: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, str] | None:
    """rvec 3×1, tvec 3×1, dan label GPU atau CPU."""
    normalized = _normalized(cv2, image_pts, camera_matrix, dist)
    obj = np.asarray(obj_xyz, dtype=np.float64).reshape(-1, 3)[:, :2]
    if normalized is None or len(obj) < 4 or len(obj) != len(normalized):
        return None
    found = _try(cv2, _gpu() or _Cpu(), obj, normalized)
    if found is not None:
        return found
    return _opencv(cv2, obj_xyz, image_pts, camera_matrix, dist)


def _try(
    cv2: Any, backend: _Algebra, obj: np.ndarray, points: np.ndarray
) -> tuple[np.ndarray, np.ndarray, str] | None:
    try:
        posed = _pose(cv2, backend, obj, points)
    except (ValueError, np.linalg.LinAlgError, RuntimeError):
        return None
    return None if posed is None else (posed[0], posed[1], backend.label)


def _pose(
    cv2: Any, backend: _Algebra, obj: np.ndarray, points: np.ndarray
) -> tuple[np.ndarray, np.ndarray] | None:
    homography = backend.reshape3(backend.svd_vh(_design(backend, obj, points))[-1])
    rotation, translation = _frame(backend, homography)
    if rotation is None or translation is None:
        return None
    matrix = np.asarray(backend.numpy(rotation), dtype=np.float64)
    vector = np.asarray(backend.numpy(translation), dtype=np.float64).reshape(3)
    if not np.isfinite(matrix).all() or not np.isfinite(vector).all():
        return None
    rvec, _jacobian = cv2.Rodrigues(matrix)
    return np.asarray(rvec, dtype=np.float64), vector.reshape(3, 1)


def _frame(backend: _Algebra, homography: Any) -> tuple[Any, Any] | tuple[None, None]:
    first = backend.column(homography, 0)
    second = backend.column(homography, 1)
    third = backend.column(homography, 2)
    scale = 2.0 / (backend.item(backend.norm(first)) + backend.item(backend.norm(second)))
    if not np.isfinite(scale) or scale == 0:
        return None, None
    left = backend.scale(first, scale)
    mid = backend.scale(second, scale)
    translation = backend.scale(third, scale)
    if backend.item(translation[2]) < 0:
        left = backend.scale(left, -1)
        mid = backend.scale(mid, -1)
        translation = backend.scale(translation, -1)
    rotation = backend.svd_rotation(backend.stack([left, mid, backend.cross(left, mid)]))
    return rotation, translation


def _design(backend: _Algebra, obj: np.ndarray, points: np.ndarray) -> Any:
    rows: list[list[float]] = []
    for (x_pos, y_pos), (u_pos, v_pos) in zip(obj, points, strict=True):
        rows.append([-x_pos, -y_pos, -1.0, 0.0, 0.0, 0.0, u_pos * x_pos, u_pos * y_pos, u_pos])
        rows.append([0.0, 0.0, 0.0, -x_pos, -y_pos, -1.0, v_pos * x_pos, v_pos * y_pos, v_pos])
    return backend.tensor(np.asarray(rows, dtype=np.float64))


def _normalized(
    cv2: Any, image_pts: np.ndarray, camera_matrix: np.ndarray, dist: np.ndarray
) -> np.ndarray | None:
    try:
        flat = cv2.undistortPoints(
            np.asarray(image_pts, dtype=np.float64).reshape(-1, 1, 2),
            np.asarray(camera_matrix, dtype=np.float64).reshape(3, 3),
            np.asarray(dist, dtype=np.float64).reshape(-1, 1),
        )
    except cv2.error:
        return None
    points = np.asarray(flat, dtype=np.float64).reshape(-1, 2)
    if not np.isfinite(points).all():
        return None
    return points


def _opencv(
    cv2: Any,
    obj_xyz: np.ndarray,
    image_pts: np.ndarray,
    camera_matrix: np.ndarray,
    dist: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, str] | None:
    ok, rvec, tvec = cv2.solvePnP(
        np.asarray(obj_xyz, dtype=np.float32).reshape(-1, 3),
        np.asarray(image_pts, dtype=np.float32).reshape(-1, 2),
        np.asarray(camera_matrix, dtype=np.float64).reshape(3, 3),
        np.asarray(dist, dtype=np.float64).reshape(-1, 1),
    )
    if not ok:
        return None
    return np.asarray(rvec, dtype=np.float64), np.asarray(tvec, dtype=np.float64), _CPU


def _gpu() -> _Algebra | None:
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return None
    cuda = getattr(torch, "cuda", None)
    if cuda is None or not bool(cuda.is_available()):
        return None
    return _Torch(torch)


class _Cpu:
    label = _CPU

    def tensor(self, value: np.ndarray) -> np.ndarray:
        return np.asarray(value, dtype=np.float64)

    def numpy(self, value: Any) -> np.ndarray:
        return np.asarray(value, dtype=np.float64)

    def svd_vh(self, design: Any) -> np.ndarray:
        _u, _s, vh = np.linalg.svd(design)
        return np.asarray(vh, dtype=np.float64)

    def reshape3(self, row: Any) -> np.ndarray:
        return np.asarray(row, dtype=np.float64).reshape(3, 3)

    def column(self, matrix: Any, index: int) -> np.ndarray:
        return np.asarray(matrix, dtype=np.float64)[:, index]

    def norm(self, vector: Any) -> float:
        return float(np.linalg.norm(np.asarray(vector, dtype=np.float64)))

    def cross(self, left: Any, right: Any) -> np.ndarray:
        return np.cross(np.asarray(left), np.asarray(right))

    def stack(self, columns: list[Any]) -> np.ndarray:
        return np.column_stack([np.asarray(column, dtype=np.float64) for column in columns])

    def svd_rotation(self, matrix: Any) -> np.ndarray:
        u_mat, _s, vh = np.linalg.svd(np.asarray(matrix, dtype=np.float64))
        if float(np.linalg.det(u_mat @ vh)) < 0:
            vh = np.array(vh, copy=True)
            vh[2, :] *= -1
        return np.asarray(u_mat @ vh, dtype=np.float64)

    def scale(self, vector: Any, factor: float) -> np.ndarray:
        return np.asarray(vector, dtype=np.float64) * factor

    def item(self, value: Any) -> float:
        return float(np.asarray(value).reshape(-1)[0])


class _Torch:
    label = _GPU

    def __init__(self, torch: Any) -> None:
        self._torch = torch
        self._device = torch.device("cuda")

    def tensor(self, value: np.ndarray) -> Any:
        return self._torch.as_tensor(value, dtype=self._torch.float64, device=self._device)

    def numpy(self, value: Any) -> np.ndarray:
        return np.asarray(value.detach().cpu().numpy(), dtype=np.float64)

    def svd_vh(self, design: Any) -> Any:
        _u, _s, vh = self._torch.linalg.svd(design)
        return vh

    def reshape3(self, row: Any) -> Any:
        return row.reshape(3, 3)

    def column(self, matrix: Any, index: int) -> Any:
        return matrix[:, index]

    def norm(self, vector: Any) -> Any:
        return self._torch.linalg.norm(vector)

    def cross(self, left: Any, right: Any) -> Any:
        return self._torch.linalg.cross(left, right)

    def stack(self, columns: list[Any]) -> Any:
        return self._torch.stack(columns, dim=1)

    def svd_rotation(self, matrix: Any) -> Any:
        u_mat, _s, vh = self._torch.linalg.svd(matrix)
        if float(self._torch.linalg.det(u_mat @ vh).detach().cpu().item()) < 0:
            vh = vh.clone()
            vh[2, :] *= -1
        return u_mat @ vh

    def scale(self, vector: Any, factor: float) -> Any:
        return vector * factor

    def item(self, value: Any) -> float:
        return float(value.detach().cpu().item())
