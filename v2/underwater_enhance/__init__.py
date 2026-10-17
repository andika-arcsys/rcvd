"""Underwater video enhancement toolkit.

Pipeline OpenCV untuk restorasi video inspeksi bawah air yang keruh:
UDCP dehazing, restorasi warna gaya FUnIE-GAN/Water-Net, frequency
decomposition + multi-scale unsharp masking, CLAHE, dan stabilisasi temporal
anti-flicker.
"""

from underwater_enhance.pipeline import PRESETS, PipelineConfig, UnderwaterEnhancer

__version__ = "0.1.0"

__all__ = ["PRESETS", "PipelineConfig", "UnderwaterEnhancer", "__version__"]
