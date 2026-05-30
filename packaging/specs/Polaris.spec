# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parents[1]

# 항상 포함되는 코어 데이터
_datas = [
    (str(ROOT / 'ui' / 'dist'),         'ui/dist'),
    (str(ROOT / 'packaging' / 'icons'), 'packaging/icons'),
]

# ── 옵셔널 plugin 자동 포함 ──────────────────────────────────────────────────
# 각 plugin 구성:
#   • src/api/<name>.py  — *Mixin (PolarisAPI 에 자동 합성)
#   • src/<name>.py      — 헬퍼 모듈 (선택)
#   • <name>/            — 데이터 디렉터리 (선택)
#
# probe 파일이 존재할 때만 빌드에 포함된다. 따라서 plugin 을 삭제한 변형 빌드
# (예: polaris-free) 도 이 spec 을 "그대로" 사용 가능 → spec 은 모든 브랜치에서
# 동일하게 유지된다. plugin 분리 = 파일 삭제뿐, spec 편집 불필요.
#
# 또한 _discover_optional_mixins() 가 pkgutil.iter_modules 로 mixin 을 동적
# 임포트하므로 PyInstaller 정적 분석이 모듈을 놓칠 수 있다. 이를 hiddenimports
# 로 명시해 frozen EXE 에서도 plugin 이 확실히 번들되도록 한다.
#
# plugin 추가 시 아래 _PLUGINS 에 한 줄만 추가하면 됨.
_PLUGINS = [
    # (존재 확인 파일,        hiddenimports,                       데이터 디렉터리 or None)
    ('src/api/catalog.py',  ['src.api.catalog', 'src.catalog'],  'catalog'),
    ('src/api/infra.py',    ['src.api.infra',
                              'src.infra', 'src.infra.ssh',
                              'src.infra.terminal',
                              'src.infra.recipes', 'src.infra.recipes.base',
                              'src.infra.recipes.preflight',
                              'src.infra.recipes.rke2',
                              'paramiko'],  None),
]

_plugin_hidden = []
for _probe, _mods, _data_dir in _PLUGINS:
    if not (ROOT / _probe).exists():
        continue   # plugin 이 제거된 변형 빌드 — 조용히 건너뜀
    _plugin_hidden.extend(_mods)
    if _data_dir and (ROOT / _data_dir).is_dir():
        _datas.append((str(ROOT / _data_dir), _data_dir))

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
        # 코어 vault (kubeconfig / 스냅샷 암호화 — 모든 빌드에 포함)
        'src.vault', 'src.api.vault',
        'src.paths',   # 데이터 디렉터리 위치 해석 (v1.2.2)
        'cryptography', 'cryptography.hazmat.primitives.ciphers.aead',
    ] + _plugin_hidden,
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
