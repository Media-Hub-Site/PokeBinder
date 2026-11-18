# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

datas = [('assets/sounds', 'assets/sounds'), ('assets/icons', 'assets/icons'), ('assets/style.qss', 'assets'), ('assets/style_dark.qss', 'assets'), ('PokeDatabase.db', '.')]
binaries = []
hiddenimports = []

tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Incluir DLLs de Microsoft Visual C++ Runtime y OpenGL necesarias para Qt6 en Windows limpios
sys32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
vc_dlls = [
    "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
    "vcruntime140.dll", "vcruntime140_1.dll", "vcomp140.dll",
    "d3dcompiler_47.dll", "opengl32sw.dll"
]
for dll in vc_dlls:
    dll_path = os.path.join(sys32, dll)
    if os.path.exists(dll_path):
        binaries.append((dll_path, '.'))




a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TCG_Inventory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icons\\TCG_Logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TCG_Inventory',
)
