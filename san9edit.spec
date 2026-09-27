# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH)

DATAS = [
    (str(ROOT / "assets" / "map.geojson"),     "assets"),
    (str(ROOT / "assets" / "characters.json"), "assets"),
    (str(ROOT / "assets" / "roads.geojson"),   "assets"),
    (str(ROOT / "assets" / "water.geojson"),   "assets"),
    (str(ROOT / "assets" / "portrait"),        "assets/portrait"),
    (str(ROOT / "scenarios"),                  "scenarios"),
]

ICON = str(ROOT / "assets" / "icon.ico")
ICON = ICON if Path(ICON).is_file() else None

EXCLUDES = [
    "tools", "tests",
    "matplotlib", "numpy", "scipy", "pandas",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "IPython", "jupyter", "notebook",
]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=["PIL._tkinter_finder"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="暗耻三国志",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=ICON,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False,
    name="暗耻三国志",
    contents_directory=".",
)