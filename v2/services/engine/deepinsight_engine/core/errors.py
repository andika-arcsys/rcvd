"""Registri kode error. Setiap error yang tampil ke pengguna punya kode di sini."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    http_status: int
    message_id: str  # pesan Bahasa Indonesia untuk pengguna
    cause: str
    action: str


_SPECS: tuple[ErrorSpec, ...] = (
    ErrorSpec(
        "API-001",
        401,
        "Token engine tidak valid atau tidak ada.",
        "Header X-DeepInsight-Token salah atau hilang.",
        "Mulai ulang aplikasi agar token baru diteruskan ke tampilan.",
    ),
    ErrorSpec(
        "API-002",
        422,
        "Permintaan tidak valid.",
        "Isi permintaan tidak sesuai skema.",
        "Periksa kolom yang ditandai di detail.",
    ),
    ErrorSpec(
        "API-003",
        404,
        "Sumber daya tidak ditemukan.",
        "Alamat atau ID tidak ada.",
        "Periksa ID dan muat ulang layar.",
    ),
    ErrorSpec(
        "SYS-001",
        500,
        "Konfigurasi tidak valid.",
        "Berkas YAML di config/ gagal dibaca atau tidak lolos validasi.",
        "Perbaiki berkas yang disebut pada detail lalu mulai ulang engine.",
    ),
    ErrorSpec(
        "SYS-002",
        500,
        "Kesalahan internal engine.",
        "Terjadi pengecualian yang tidak terduga.",
        "Laporkan kode ini bersama session_id kepada Teknisi program.",
    ),
    ErrorSpec(
        "GPU-001",
        503,
        "GPU NVIDIA tidak terdeteksi.",
        "Driver NVML tidak tersedia atau tidak ada GPU.",
        "Lanjut mode terbatas, atau pasang driver NVIDIA yang sesuai.",
    ),
    ErrorSpec(
        "STO-001",
        507,
        "Ruang penyimpanan tidak cukup.",
        "Ruang kosong di bawah batas minimum.",
        "Kosongkan disk lalu coba lagi.",
    ),
    ErrorSpec(
        "VID-001",
        503,
        "Sinyal video terputus.",
        "Tidak ada frame baru melebihi batas LOST SIGNAL.",
        "Periksa kabel dan kamera ROV; FREEZE dinonaktifkan sementara.",
    ),
)

REGISTRY: dict[str, ErrorSpec] = {spec.code: spec for spec in _SPECS}


class EngineError(Exception):
    """Error terdaftar. Ditangani di batas API menjadi respons JSON berkode."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        if code not in REGISTRY:
            raise KeyError(f"Kode error tidak terdaftar: {code}")
        self.spec = REGISTRY[code]
        self.detail = detail
        super().__init__(f"{code}: {self.spec.message_id}")


def render_error_codes_markdown() -> str:
    """Hasilkan isi docs/ERROR_CODES.md dari registri (satu sumber kebenaran)."""
    lines = [
        "# ERROR_CODES",
        "",
        "Dihasilkan dari `deepinsight_engine/core/errors.py` (`make docs-errors`).",
        "Jangan diubah manual.",
        "",
        "| Kode | HTTP | Pesan pengguna | Kemungkinan sebab | Tindakan |",
        "| --- | --- | --- | --- | --- |",
    ]
    for spec in sorted(REGISTRY.values(), key=lambda s: s.code):
        lines.append(
            f"| {spec.code} | {spec.http_status} | {spec.message_id} "
            f"| {spec.cause} | {spec.action} |"
        )
    return "\n".join(lines) + "\n"
