# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller：单文件窗口程序 + Flask 静态资源 + 窗口图标 app.ico"""

from pathlib import Path

ROOT = Path(SPEC).resolve().parent
ICO = ROOT / "dist_assets" / "app.ico"
icon_arg = str(ICO) if ICO.is_file() else None

datas = [
    (str(ROOT / "lan_transfer" / "templates"), "lan_transfer/templates"),
    (str(ROOT / "lan_transfer" / "static"), "lan_transfer/static"),
]
if ICO.is_file():
    datas.append((str(ICO), "."))

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name="文件传输助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
