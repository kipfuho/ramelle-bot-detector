# -*- mode: python ; coding: utf-8 -*-



a = Analysis(
    ['index.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludeexcludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'notebook',
        'jupyter',
        'IPython',
        'tkinter',
        'PyQt5',
        'PySide2',
        'wx',
        'plotly',
        'bokeh',
        'seaborn',
        'sqlalchemy',
        'flask',
        'django',
        'pytest',
        'setuptools',
    ],
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
    name='monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
