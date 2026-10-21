"""Pita ketidakpastian garis 3D, rasio gradasi, dan koreksi siluet diameter.

Pita = 2 × rel × panjang, dan 5% tetap batas bawah. Garis yang kliknya
lebih kasar dari 5% tetap memakai pita klik itu.
rel_cal adalah simpangan baku relatif skala dari dua klik pada garis kalibrasi,
bukan pita 2σ yang sudah ditampilkan di angka 2D.

Skor kedalaman membuka rasio model terhadap kedalaman kalibrasi:

    z' = z_kal × (z / z_kal) ** 1.5

Depth Anything 3 merapatkan jauh-bagi-dekat pada permukaan yang menjauh.
Pada frame pipa, piksel menyusut kira-kira 3 kali sementara kedalaman model
hanya naik kira-kira 2 kali. Pangkat 1.5 membuka selisih itu. Garis yang
kedalamannya sama dengan kalibrasi tidak berubah. Peta seragam tidak berubah.
Warna termal tetap rentang persentil 2–98, bukan bobot meter.

Kedalaman siluet silinder, bila peta membaca permukaan depan:

    z_sil = z_depan + R × z_depan / (z_depan + R)

Menambah R penuh menaruh kedalaman di sumbu dan memanjangkan diameter.
Skala bergantung pada z_sil, jadi skala dihitung ulang 3 kali dengan redaman
setengah. Tanpa redaman, tiga langkah berosilasi dan tidak mendekati titik tetap.
Koreksi siluet tetap pada kedalaman mentah model, sebelum pangkat gradasi.
"""

from __future__ import annotations

import math

FLOOR_REL = 0.05
GRADIENT_GAIN = 1.5
FACING_STEPS = 3


def uncertainty_m(
    distance_m: float,
    click_sigma_px: float,
    cal_px: float,
    line_px: float,
    sigma_z: float,
    depth_z: float,
    sigma_cal: float,
    depth_cal: float,
) -> float:
    rel_cal = math.sqrt(2.0) * click_sigma_px / max(cal_px, 1.0)
    click = math.sqrt(2.0) * click_sigma_px / max(line_px, 1.0)
    rel_z = sigma_z / max(abs(depth_z), 1e-6)
    rel_c = sigma_cal / max(abs(depth_cal), 1e-6)
    rel = math.sqrt(rel_cal**2 + click**2 + rel_z**2 + rel_c**2)
    return max(2.0 * rel, FLOOR_REL) * distance_m


def scored_depth(depth: float, cal_depth: float, gain: float = GRADIENT_GAIN) -> float:
    """Kedalaman untuk centimeter. Mentah bila kalibrasi belum punya kedalaman."""
    if depth <= 0 or cal_depth <= 0 or gain == 1.0:
        return depth
    return float(cal_depth * (depth / cal_depth) ** gain)


def gradient_note() -> str:
    return (
        f"Rasio gradasi {GRADIENT_GAIN:.2f} terhadap kedalaman kalibrasi. "
        "Warna termal tetap persentil, bukan meter."
    )


def silhouette_depth(z_front_m: float, radius_m: float) -> float:
    if z_front_m <= 0 or radius_m <= 0:
        return z_front_m
    return z_front_m + (radius_m * z_front_m) / (z_front_m + radius_m)


def facing_scale(
    z_rel: float,
    gain: float,
    known_m: float,
    radius_m: float,
    base_scale: float,
) -> float:
    """Tiga iterasi teredam. gain adalah tali 3D pada kedalaman 1."""
    scale = base_scale
    for _ in range(FACING_STEPS):
        z_sil = silhouette_depth(z_rel * scale, radius_m)
        raw = z_sil * gain
        if raw <= 1e-9:
            return scale
        scale = 0.5 * (scale + known_m / raw)
    return scale
