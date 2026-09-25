# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for a single-file PyCalculator executable.

Build it with::

    pyinstaller calculator.spec

The result is ``dist/PyCalculator.exe`` on Windows and ``dist/PyCalculator``
elsewhere. Nothing outside the standard library is bundled, so the binary only
carries CPython, Tcl/Tk and this package.
"""

import os

APP_NAME = "PyCalculator"
ENTRY_POINT = os.path.join("src", "calculator", "__main__.py")
SOURCE_ROOT = os.path.join(os.getcwd(), "src")

# Set ICON_FILE to something like os.path.join("docs", "images", "app.ico")
# once you add an icon; PyInstaller uses the default icon while it is None.
ICON_FILE = None

analysis = Analysis(
    [ENTRY_POINT],
    pathex=[SOURCE_ROOT],
    binaries=[],
    datas=[],
    hiddenimports=["tkinter", "tkinter.ttk", "tkinter.messagebox"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim large optional packages that a stdlib-only calculator never touches.
    excludes=[
        "numpy",
        "pandas",
        "matplotlib",
        "PIL",
        "pytest",
        "setuptools",
        "unittest",
    ],
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data)

# Passing the binaries, zipfiles and datas straight to EXE produces the
# one-file build; a COLLECT step would produce a one-folder build instead.
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name=APP_NAME,
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
    icon=ICON_FILE,
)
