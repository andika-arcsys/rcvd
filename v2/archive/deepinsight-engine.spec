# -*- mode: python ; coding: utf-8 -*-
# Sidecar engine. Model .onnx/.pt tidak ikut. Folder models dipilih di Pengaturan.
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("deepinsight_engine")

a = Analysis(
    ["../services/engine/deepinsight_engine/__main__.py"],
    pathex=["../services/engine"],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "onnxruntime", "tensorboard"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="deepinsight-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
