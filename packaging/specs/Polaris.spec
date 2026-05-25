# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parents[1]

# 항상 포함되는 코어 데이터
_datas = [
    (str(ROOT / 'ui' / 'dist'),         'ui/dist'),
    (str(ROOT / 'packaging' / 'icons'), 'packaging/icons'),
]

# 옵셔널 plugin 데이터 디렉터리 — 존재할 때만 자동 포함
# plugin 추가 시 여기에 한 줄만 추가하면 됨 (예: ('llm-presets', 'llm-presets'))
for _src, _dest in [
    ('catalog', 'catalog'),
]:
    if (ROOT / _src).is_dir():
        _datas.append((str(ROOT / _src), _dest))

a = Analysis(
    [str(ROOT / 'polaris.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'docx',
        'docx.shared',
        'docx.enum.text',
        'docx.oxml',
        'docx.oxml.ns',
        'kubernetes',
        'webview',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # numpy 는 우리 코드에서 직접 사용 안 함. PyInstaller 가 PIL.Image 의
        # type hint 참조(numpy._typing._array_like 등)때문에 hidden import 로
        # 끌어왔지만 런타임에는 불필요. 제외 시 약 52 MB (numpy 31.8 + OpenBLAS 20) 절감.
        'numpy',
        'numpy.libs',
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
    name='polaris',
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
    icon=str(ROOT / 'packaging' / 'icons' / 'polaris.ico'),
)
