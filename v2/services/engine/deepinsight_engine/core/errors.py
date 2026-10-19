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
    ErrorSpec(
        "VID-002",
        410,
        "Frame tidak ada lagi di buffer.",
        "frame_id lebih tua dari ring buffer atau tidak dikenal.",
        "Bekukan frame yang masih tampil.",
    ),
    ErrorSpec(
        "VID-003",
        503,
        "Sumber video tidak dapat dibuka.",
        "Berkas, kamera, atau RTSP tidak tersedia.",
        "Periksa jalur berkas atau sambungan kamera.",
    ),
    ErrorSpec(
        "MDL-001",
        404,
        "Berkas model tidak ditemukan.",
        "model.pt, depth_pro.pt, model.onnx, atau classes.json belum ada di folder models.",
        "Salin berkas ke jalur di config/models.yaml. Bobot besar tidak disimpan di Git.",
    ),
    ErrorSpec(
        "MDL-002",
        500,
        "Model gagal dimuat.",
        "Runtime atau isi berkas model tidak dapat dipakai.",
        "Periksa log engine dan berkas model.",
    ),
    ErrorSpec(
        "MDL-003",
        503,
        "Fitur ini membutuhkan GPU NVIDIA.",
        "Mode terbatas: HydroDetect dan SpatialSight nonaktif tanpa GPU.",
        "Gunakan Optical atau AquaClear, atau jalankan di PC dengan GPU NVIDIA.",
    ),
    ErrorSpec(
        "GPU-002",
        500,
        "VRAM tidak kembali ke garis dasar.",
        "Setelah lepas model, pemakaian VRAM masih di atas toleransi.",
        "Proses pekerja dihentikan paksa.",
    ),
    ErrorSpec(
        "GPU-003",
        503,
        "Performa di bawah ambang.",
        "FPS, VRAM, atau utilisasi GPU melewati batas config.",
        "Matikan fitur atau pilih preset AquaClear ringan.",
    ),
    ErrorSpec(
        "CAL-001",
        422,
        "Jarak referensi nol.",
        "Dua node referensi berimpit atau panjang referensi tidak positif.",
        "Pilih dua node yang berbeda dan isi panjang referensi.",
    ),
    ErrorSpec(
        "AREA-001",
        422,
        "Titik kembar.",
        "Dua titik atau lebih berada di koordinat yang sama.",
        "Klik ulang titik yang berbeda.",
    ),
    ErrorSpec(
        "AREA-002",
        422,
        "Urutan titik bersilangan, klik ulang searah keliling.",
        "Sisi poligon berpotongan sendiri.",
        "Klik ulang titik searah keliling bidang.",
    ),
    ErrorSpec(
        "AREA-003",
        422,
        "Titik segaris, luas nol.",
        "Shoelace bernilai nol.",
        "Pilih titik yang membentuk bidang.",
    ),
    ErrorSpec(
        "AREA-004",
        422,
        "Cek silang Heron tidak cocok dengan shoelace.",
        "Selisih relatif luas 3 titik melewati heron_rel_tol.",
        "Laporkan kasus ini; rumus luas tidak konsisten.",
    ),
    ErrorSpec(
        "AREA-005",
        422,
        "Minimal tiga titik untuk luas.",
        "Poligon punya kurang dari 3 titik.",
        "Tambahkan titik sampai membentuk bidang.",
    ),
    ErrorSpec(
        "SPAN-001",
        422,
        "Segmen tidak punya pasangan freeze yang lolos.",
        "Setiap pasangan freeze pada segmen melebihi selisih maksimum.",
        "Ukur ulang segmen tersebut.",
    ),
    ErrorSpec(
        "SPAN-002",
        422,
        "Diameter atau rentang G tidak dikenal.",
        "Diameter bukan 16 atau 8, atau G kanan berada sebelum G kiri.",
        "Periksa diameter pipa dan urutan segmen.",
    ),
    ErrorSpec(
        "AUTH-001",
        401,
        "Pengguna atau PIN tidak valid.",
        "ID pengguna atau PIN salah.",
        "Periksa ID dan PIN. PIN tidak dicatat di log.",
    ),
    ErrorSpec(
        "AUTH-002",
        423,
        "Akun terkunci sementara.",
        "Percobaan masuk melebihi batas config.",
        "Tunggu sampai kunci berakhir, atau minta administrator membuka akun.",
    ),
    ErrorSpec(
        "LASER-001",
        422,
        "Jarak dua titik laser belum diisi.",
        "config laser.ref_cm masih kosong (D-05).",
        "Isi jarak laser yang diukur tim sebelum uji batang.",
    ),
    ErrorSpec(
        "MIS-001",
        422,
        "Misi belum siap dimulai.",
        "Pre-check, tim, atau rencana masih belum lengkap, atau misi sudah berjalan.",
        "Lengkapi rencana dan semua butir pre-check.",
    ),
    ErrorSpec(
        "TAPE-001",
        422,
        "Panjang tali ukur nol.",
        "Pembagi cek silang tali tidak boleh nol.",
        "Isi panjang tali ukur.",
    ),
    ErrorSpec(
        "EDGE-001",
        422,
        "Titik terlalu dekat tepi objek.",
        "Jarak titik ke tepi Canny di bawah edge_risk_px.",
        "Geser titik menjauh dari tepi, lalu simpan lagi.",
    ),
    ErrorSpec(
        "SNAP-001",
        422,
        "Kalibrasi belum sah untuk disimpan.",
        "Status masih UNCALIBRATED.",
        "Ulangi dua titik laser dan panjang referensi.",
    ),
    ErrorSpec(
        "REV-001",
        422,
        "Ukuran belum terkalibrasi tidak dapat dikonfirmasi.",
        "Status kalibrasi masih UNCALIBRATED.",
        "Perbaiki ukuran di Canvas, lalu konfirmasi lagi.",
    ),
    ErrorSpec(
        "REV-002",
        422,
        "Pemeriksa kedua harus orang lain.",
        "Pemeriksa yang sama mencoba memutuskan temuan kritis dua kali.",
        "Minta pemeriksa lain.",
    ),
    ErrorSpec(
        "REV-003",
        422,
        "Sengketa diputus Ketua tim.",
        "Peran yang memutus bukan Ketua tim.",
        "Masuk sebagai Ketua tim dan tulis alasan.",
    ),
    ErrorSpec(
        "REV-004",
        422,
        "Alasan keputusan wajib diisi.",
        "Alasan kosong, atau ubah kelas tanpa nama kelas.",
        "Isi alasan sebelum menyimpan keputusan.",
    ),
    ErrorSpec(
        "RPT-001",
        422,
        "Satu akun tidak boleh mengisi dua tahap berturut-turut.",
        "Pemeriksa tahap ini sama dengan tahap sebelumnya.",
        "Minta akun lain untuk tahap berikutnya.",
    ),
    ErrorSpec(
        "RPT-002",
        422,
        "Laporan yang disetujui terkunci.",
        "Teks atau tahap diminta pada laporan terkunci.",
        "Buat revisi baru bila isi perlu diubah.",
    ),
    ErrorSpec(
        "SET-001",
        403,
        "Pengaturan hanya dapat diubah Ketua tim atau Teknisi program.",
        "Peran sesi bukan peran yang boleh mengubah pengaturan.",
        "Masuk dengan peran yang diizinkan.",
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
