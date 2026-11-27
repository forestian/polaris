# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]

# ── MCP(stdio) 서버 — 쿠버네티스 조회 전용 ────────────────────────────────────
# polaris.exe --mcp 는 src.mcp_server 를 함수 안에서 임포트하고, 그 안에서 다시
# mcp SDK 를 임포트한다. mcp 는 pydantic 모델을 서브모듈 전반에 걸쳐 쓰므로
# 정적 분석만으로는 일부가 누락될 수 있어 서브모듈을 통째로 수집한다.
try:
    _mcp_hidden = collect_submodules('mcp') + ['anyio', 'src.mcp_server']
except Exception:
    _mcp_hidden = ['src.mcp_server']

# 항상 포함되는 코어 데이터
_datas = [
    (str(ROOT / 'ui' / 'dist'),         'ui/dist'),
    (str(ROOT / 'packaging' / 'icons'), 'packaging/icons'),
]

# ── 옵셔널 plugin ────────────────────────────────────────────────────────────
# _discover_optional_mixins() 가 pkgutil.iter_modules 로 mixin 을 동적 임포트하므로
# PyInstaller 정적 분석이 놓칠 수 있다 — hiddenimports 로 명시한다.
# (_PLUGINS 는 테스트가 literal_eval 로 읽으므로 리터럴로 둔다)
_PLUGINS = [
    # (존재 확인 파일,             hiddenimports,                                   데이터 디렉터리 or None)
    ('src/api/notifications.py', ['src.api.notifications', 'src.notifications'], None),
    ('src/api/yamllab.py',       ['src.api.yamllab', 'src.yamllab'],             None),
]

_plugin_hidden = []
for _probe, _mods, _data_dir in _PLUGINS:
    if not (ROOT / _probe).exists():
        continue
    _plugin_hidden.extend(_mods)
    if _data_dir and (ROOT / _data_dir).is_dir():
        _datas.append((str(ROOT / _data_dir), _data_dir))

# ── EXE 버전 리소스 (정품 메타데이터 — AV 오탐 완화) ─────────────────────────
# 미서명 + 메타데이터 없는 PyInstaller 실행 파일은 Defender ML 오탐을 더 잘 유발한다.
import re as _re, os as _os
_ver_txt  = (ROOT / 'polaris.py').read_text(encoding='utf-8')
_m        = _re.search(r"VERSION\s*=\s*'([^']+)'", _ver_txt)
_VERSION  = _m.group(1) if _m else '0.0.0'
_nums     = (_re.findall(r'\d+', _VERSION.split('-')[0]) + ['0', '0', '0'])[:3]
_filevers = tuple(int(x) for x in _nums) + (0,)
_ver_info = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={_filevers}, prodvers={_filevers}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Polaris'),
      StringStruct('FileDescription', 'Polaris - Kubernetes Cluster Manager'),
      StringStruct('FileVersion', '{_VERSION}'),
      StringStruct('InternalName', 'polaris'),
      StringStruct('OriginalFilename', 'polaris.exe'),
      StringStruct('ProductName', 'Polaris'),
      StringStruct('ProductVersion', '{_VERSION}'),
      StringStruct('LegalCopyright', 'Copyright (c) Polaris contributors')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)"""
_os.makedirs(ROOT / 'build', exist_ok=True)
_version_file = str(ROOT / 'build' / 'polaris_version_info.txt')
with open(_version_file, 'w', encoding='utf-8') as _vf:
    _vf.write(_ver_info)

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
        # 코어 vault (kubeconfig / 스냅샷 암호화)
        'src.vault', 'src.api.vault',
        'src.paths',      # 데이터 디렉터리 위치 해석
        'src.navguard',   # 창이 앱 화면 밖으로 이동하는 것을 막는다
        'src.k8s_http',   # kubernetes 호출 기본 타임아웃·재시도
        'src.k8s_fast',   # 큰 목록을 모델 변환 없이 읽기
        'cryptography', 'cryptography.hazmat.primitives.ciphers.aead',
    ] + _plugin_hidden + _mcp_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # numpy 는 직접 쓰지 않는다 — PIL.Image 의 type hint 참조로 끌려온다(약 52 MB).
        'numpy',
        'numpy.libs',
        # 이 판에 없는 기능의 라이브러리 — 개발 PC 에 깔려 있어도 묶이지 않게
        'paramiko', 'comtypes', 'winpty', 'winrm', 'requests_ntlm', 'spnego', 'sspilib', 'xmltodict',
    ],
    noarchive=False,
    optimize=0,
    # LGPL 라이브러리는 실행 파일(PYZ)에 묶지 않고 _internal\<이름>\ 에 일반 .py 로 둔다 —
    # LGPL 은 받은 사람이 그 라이브러리를 고친 버전으로 바꿔 끼울 수 있어야 한다.
    # 목록은 packaging/third_party_notices.py 의 LGPL_REPLACEABLE 과 같아야 한다(build.py 가 확인).
    module_collection_mode={'pystray': 'py'},
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir — 바이너리/데이터는 COLLECT 로 분리 (자가압축 제거)
    name='polaris',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # AV 오탐 완화 — UPX 압축은 오탐 트리거
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'packaging' / 'icons' / 'polaris.ico'),
    version=_version_file,
)

# onedir: 산출물은 dist/polaris/ 폴더 (polaris.exe + _internal/). 배포는 설치 파일.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='polaris',
)
