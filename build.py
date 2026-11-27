#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polaris 빌드 스크립트.

변경사항이 반드시 .exe 에 반영되도록 다음을 강제한다:
  1. polaris.py 의 VERSION 상수와 CHANGELOG.md 의 최신 ## vX.Y.Z 헤더가
     일치하지 않으면 빌드를 중단한다.
  2. dist/polaris.exe, build/, __pycache__/ 를 모두 삭제한 뒤 빌드한다.
  3. 빌드 후 산출물의 timestamp 와 VERSION 을 표시한다.

사용법:
  python build.py            # 가드 통과 시 빌드
  python build.py --force    # 가드 무시 (권장하지 않음)
  python build.py --check    # 가드만 검사하고 빌드는 안 함
"""
import os
import re
import sys
import shutil
import subprocess
import importlib.util
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY     = ROOT / 'polaris.py'
CHLOG  = ROOT / 'CHANGELOG.md'
README = ROOT / 'README.md'
SPEC   = ROOT / 'packaging' / 'specs' / 'Polaris.spec'
# onedir 빌드 (v1.2.4~): 산출물은 dist/polaris/ 폴더 (launcher + _internal/).
# 단일 exe 자가압축(onefile)이 AV 오탐(Wacatac/Sabsik!ml) 주범이라 폴더형으로 전환,
# 배포는 zip 으로 묶는다. (옛 단일 polaris.exe 는 v1.2.3 이전 태그에서 접근)
DIST     = ROOT / 'dist'
APPDIR   = DIST / 'polaris'              # PyInstaller COLLECT 출력 폴더
EXE      = APPDIR / 'polaris.exe'        # onedir 런처
ZIP      = DIST / 'polaris-win64.zip'    # 설치 exe payload (빌드 중간물 — 배포·커밋 안 함, v1.2.20~)
LEGACY_EXE = DIST / 'polaris.exe'        # 구 onefile 산출물 (정리 대상)

# 설치 마법사 (v1.2.9~): Tauri(Rust + WebView2) 단일 self-contained exe.
# (~v1.2.8 은 Inno Setup) MSVC 빌드로 WebView2Loader 정적 링크 → 사이드카 DLL 불필요.
# onedir 앱(zip)을 payload 로 임베드해 선택 폴더에 설치.
SETUP_TAURI = ROOT / 'packaging' / 'setup-tauri'
SETUP  = DIST / 'polaris-setup-win64.exe'  # 배포 산출물 (v1.2.25~ 패키지 레지스트리 업로드 — git 커밋 안 함)

REQUIRED_RUNTIME_IMPORTS = [
    ('kubernetes', 'kubernetes'),
    ('webview', 'pywebview'),
    ('docx', 'python-docx'),
    ('PyInstaller', 'pyinstaller'),
    ('pystray', 'pystray'),
    ('PIL', 'Pillow'),
    ('cryptography', 'cryptography'),
    ('mcp', 'mcp'),
]


def fail(msg):
    print(f'\n[FAIL] {msg}\n', file=sys.stderr)
    sys.exit(1)


def info(msg):
    print(f'[INFO] {msg}')


def ok(msg):
    print(f'[ OK ] {msg}')


def warn(msg):
    print(f'[WARN] {msg}')


def read_py_version():
    """polaris.py 에서 VERSION = 'X.Y.Z' 추출."""
    if not PY.exists():
        fail(f'{PY} 없음')
    txt = PY.read_text(encoding='utf-8')
    m = re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)['\"]", txt, re.MULTILINE)
    if not m:
        fail(f'{PY} 에서 VERSION = "X.Y.Z" 라인을 찾지 못함')
    return m.group(1)


def read_changelog_version():
    """CHANGELOG.md 의 최상단 ## vX.Y.Z[-suffix] 헤더 추출.

    X.Y.Z 숫자 버전 외에 보안 패치 suffix(-s1, -s2, ...)나
    RC(-rc1) 등 하이픈 접미사도 허용합니다.
    """
    if not CHLOG.exists():
        fail(f'{CHLOG} 없음')
    txt = CHLOG.read_text(encoding='utf-8')
    # X.Y.Z 뒤에 -접미사(영숫자) 허용
    m = re.search(r'^##\s+v(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)', txt, re.MULTILINE)
    if not m:
        fail(f'{CHLOG} 에서 ## vX.Y.Z 헤더를 찾지 못함')
    return m.group(1)


def check_versions(force=False):
    py_v = read_py_version()
    cl_v = read_changelog_version()
    info(f'polaris.py     VERSION = {py_v}')
    info(f'CHANGELOG.md   latest  = v{cl_v}')
    if py_v != cl_v:
        msg = (
            f'버전 불일치!\n'
            f'  polaris.py: {py_v}\n'
            f'  CHANGELOG : v{cl_v}\n\n'
            f'해결 방법:\n'
            f'  - 둘 중 하나를 다른 값에 맞춰 수정\n'
            f'  - 새 패치를 만든다면: polaris.py 의 VERSION 을 올리고\n'
            f'    CHANGELOG.md 최상단에 ## vX.Y.Z 항목 추가\n\n'
            f'(가드를 무시하려면 --force 사용. 권장하지 않음)'
        )
        if force:
            print(f'[WARN] {msg}\n[WARN] --force 지정으로 강행')
            return py_v
        fail(msg)
    ok(f'버전 동기화 확인: v{py_v}')
    return py_v


def sync_readme_version(version):
    """README 다운로드 표의 '최신' 행 버전을 VERSION 과 자동 동기화 (best-effort).

    CHANGELOG↔VERSION 가드처럼 릴리스마다 README 버전 깜빡임을 방지한다. master 의
    `| **최신** |` 행에 든 vX.Y.Z[-suffix] 토큰(라벨·raw URL·release URL)만 교체.
    github 이중언어 README 는 행 형식이 달라 자동으로 건너뛴다(매칭 안 됨)."""
    if not README.exists():
        return
    raw = README.read_bytes()
    eol = '\r\n' if b'\r\n' in raw else '\n'
    lines = raw.decode('utf-8').split(eol)
    changed = False
    for i, ln in enumerate(lines):
        if ln.startswith('| **최신** |'):
            new = re.sub(r'v\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?', f'v{version}', ln)
            if new != ln:
                lines[i] = new
                changed = True
            break
    if changed:
        README.write_bytes(eol.join(lines).encode('utf-8'))
        info(f'README 최신 다운로드 버전 동기화 → v{version}')
    else:
        ok(f'README 최신 다운로드 버전 확인: v{version}')


def _missing_runtime_imports(find_spec=importlib.util.find_spec):
    return [
        (module, package)
        for module, package in REQUIRED_RUNTIME_IMPORTS
        if find_spec(module) is None
    ]


def check_runtime_imports():
    missing = _missing_runtime_imports()
    if missing:
        lines = '\n'.join(
            f'  - {module} (pip install {package})'
            for module, package in missing
        )
        fail(
            'PyInstaller 빌드에 필요한 Python 패키지가 현재 런타임에 없습니다.\n'
            f'{lines}\n\n'
            '해결 방법:\n'
            '  python -m pip install -r requirements.txt\n\n'
            '패키지가 빠진 상태로 빌드하면 실행되지 않는 작은 EXE가 생성될 수 있습니다.'
        )
    ok('필수 Python 런타임 패키지 확인 완료')


def check_spec_file():
    if not SPEC.exists():
        fail(f'{SPEC} 없음 — packaging/specs/Polaris.spec 이 필요합니다')
    ok(f'PyInstaller spec 확인: {SPEC.relative_to(ROOT)}')


#: 줄바꿈을 보는 곳 — 소스를 「\n」 정규식으로 읽는 테스트가 있어 CR 이 섞이면 코드와 무관하게 깨진다
_EOL_DIRS = ('src', 'ui/src', 'tests', 'scripts', 'packaging/specs')
_EOL_FILES = ('build.py', 'polaris.py', 'CHANGELOG.md', 'README.md')
_EOL_EXT = {'.py', '.js', '.jsx', '.mjs', '.css', '.json', '.md', '.toml', '.spec', '.txt'}

#: 그동안 실제로 사고가 났던 것들의 재발 방지 테스트 — 빌드마다 돈다
GUARD_TESTS = (
    # plugin 을 spec 에 안 넣어 설치판에서 기능이 통째로 빠짐
    'tests.test_plugin_spec_sync',
    # 설정 키 화이트리스트 누락 — 저장이 조용히 실패
    'tests.test_settings_sync_v1560',
    # 보고서마다 따로 색 · 서식을 넣어 양식이 어긋남
    'tests.test_report_rules_all_v1561',
    # 이 판에 없는 기능의 코드 · 낱말이 다시 들어옴
    'tests.test_free_scope',
)


def _eol_targets(root=None):
    root = Path(root or ROOT)
    for rel in _EOL_FILES:
        if (root / rel).is_file():
            yield root / rel
    for d in _EOL_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in base.rglob('*'):
            if p.suffix in _EOL_EXT and p.is_file() and 'node_modules' not in p.parts \
                    and '__pycache__' not in p.parts:
                yield p


def find_cr_files(root=None):
    """CR 이 든 파일 → [(경로, 'crlf'|'cr')]. 'cr' 은 줄 끝이 아닌 CR(히어독이 \\r 을 진짜 CR 로 바꾼 것 등)."""
    out = []
    for p in _eol_targets(root):
        b = p.read_bytes()
        if b'\r' not in b:
            continue
        out.append((p, 'cr' if b.replace(b'\r\n', b'').count(b'\r') else 'crlf'))
    return out


def clean_preview_dirs(root=None):
    """ui/__preview* — 미리보기 확인용으로 만든 폴더. 남아 있으면 빌드에 섞인다."""
    gone = []
    for p in (Path(root or ROOT) / 'ui').glob('__preview*'):
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        gone.append(p.name)
    return gone


def check_source_hygiene(fix_eol=False):
    gone = clean_preview_dirs()
    if gone:
        info(f'미리보기 폴더 지움: {", ".join(gone)}')
    bad = find_cr_files()
    if bad and fix_eol:
        for p, kind in bad:
            if kind == 'crlf':
                p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n'))
        fixed = [p for p, k in bad if k == 'crlf']
        if fixed:
            info(f'CRLF → LF {len(fixed)}개')
        bad = [(p, k) for p, k in bad if k == 'cr']
    if bad:
        for p, kind in bad[:20]:
            warn(f'  {kind.upper():4} {p.relative_to(ROOT)}')
        fail(f'CR 이 든 소스 {len(bad)}개 — CRLF 는 `python build.py --fix-eol` 로 고칩니다. '
             '줄 중간의 CR 은 히어독이 \\r 을 진짜 CR 로 바꾼 것일 수 있으니 직접 보고 고치세요.')
    ok('소스 줄바꿈 LF · 미리보기 폴더 없음')


def run_guard_tests():
    r = subprocess.run([sys.executable, '-m', 'unittest', '-q', *GUARD_TESTS],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'})
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-6000:])
        fail('재발 방지 테스트 실패 — 예전에 사고가 났던 누락입니다. 위 메시지대로 고친 뒤 다시 빌드하세요.')
    ok(f'재발 방지 테스트 {len(GUARD_TESTS)}종 통과')




def clean():
    targets = [
        ROOT / 'build',
        ROOT / '__pycache__',
        APPDIR,                          # onedir 폴더
        ZIP, ZIP.with_name(ZIP.name + '.sha256'), ZIP.with_name(ZIP.name + '.sha512'),
        SETUP, SETUP.with_name(SETUP.name + '.sha256'), SETUP.with_name(SETUP.name + '.sha512'),
        SETUP.with_name(SETUP.name + '.sig'),
        LEGACY_EXE,                      # 구 onefile 산출물 + 체크섬 정리
        LEGACY_EXE.with_name('polaris.exe.sha256'),
        LEGACY_EXE.with_name('polaris.exe.sha512'),
    ]
    for t in targets:
        if t.exists():
            if t.is_dir():
                shutil.rmtree(t, ignore_errors=True)
            else:
                t.unlink()
            info(f'삭제: {t.relative_to(ROOT)}')


def _resolve_command_path(cmd, which=shutil.which):
    if not cmd:
        return cmd
    resolved = which(cmd[0])
    return [resolved or cmd[0], *cmd[1:]]


def _command_works(cmd):
    try:
        r = subprocess.run(
            _resolve_command_path(cmd) + ['--version'],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


def _resolve_npm_command():
    for cmd in (['npm'], ['corepack', 'npm']):
        if _command_works(cmd):
            return cmd
    fail('npm 실행 파일을 찾을 수 없습니다. Node.js/npm 또는 corepack npm을 확인하세요.')


def _normalize_text_file(path):
    text = Path(path).read_text(encoding='utf-8')
    Path(path).write_text(text, encoding='utf-8', newline='\n')


def _node_module_path(ui_dir, package_name):
    return Path(ui_dir) / 'node_modules' / Path(*package_name.split('/'))


def _missing_node_modules_dependencies(ui_dir):
    package_file = Path(ui_dir) / 'package.json'
    if not package_file.exists():
        return []
    pkg = json.loads(package_file.read_text(encoding='utf-8'))
    deps = {}
    deps.update(pkg.get('dependencies') or {})
    deps.update(pkg.get('devDependencies') or {})
    return [
        name for name in sorted(deps)
        if not _node_module_path(ui_dir, name).exists()
    ]


def run_npm_build():
    """React UI 빌드 (ui/dist 생성)."""
    ui_dir = ROOT / 'ui'
    if not ui_dir.exists():
        fail(f'UI 디렉터리 없음: {ui_dir}')

    npm = _resolve_command_path(_resolve_npm_command())
    install_cmd = ['ci'] if (ui_dir / 'package-lock.json').exists() else ['install']

    missing_deps = _missing_node_modules_dependencies(ui_dir)
    # node_modules가 없거나 package.json의 직접 의존성이 누락되면 npm install 먼저
    if not (ui_dir / 'node_modules').exists() or missing_deps:
        if missing_deps:
            info(f'누락된 npm 의존성 감지: {", ".join(missing_deps)}')
        info(f'{" ".join(npm + install_cmd)} 실행 중...')
        r = subprocess.run(npm + install_cmd, cwd=str(ui_dir))
        if r.returncode != 0:
            fail(f'{" ".join(npm + install_cmd)} 실패 (종료 코드: {r.returncode})')
        ok(f'{" ".join(npm + install_cmd)} 완료')

    info(f'{" ".join(npm + ["run", "build"])} 실행 중...')
    r = subprocess.run(npm + ['run', 'build'], cwd=str(ui_dir))
    if r.returncode != 0:
        fail(f'{" ".join(npm + ["run", "build"])} 실패 (종료 코드: {r.returncode})')

    dist = ui_dir / 'dist' / 'index.html'
    if not dist.exists():
        fail(f'빌드 산출물 없음: {dist}')
    _normalize_text_file(dist)
    ok(f'React UI 빌드 완료: {dist.relative_to(ROOT)}')


def run_pyinstaller():
    info('PyInstaller 실행 (1~3분 소요)...')
    r = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', '--noconfirm', str(SPEC)],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        fail(f'PyInstaller 종료 코드: {r.returncode}')


def write_third_party_notices(version):
    """오픈소스 고지(THIRD_PARTY_NOTICES.txt)를 polaris.exe 옆에 — 실제로 번들된 것만 (v1.4.19).

    LGPL 라이브러리(pystray)가 실행 파일 밖에 일반 .py 로 있는지도 여기서 확인한다
    (spec 의 module_collection_mode 가 빠지면 PYZ 안으로 들어가 사용자가 바꿔 끼울 수 없다).
    """
    sys.path.insert(0, str(ROOT / 'packaging'))
    try:
        import third_party_notices as tpn
    finally:
        sys.path.pop(0)
    for name in tpn.LGPL_REPLACEABLE:
        init = APPDIR / '_internal' / name / '__init__.py'
        if not init.is_file():
            fail(f'LGPL 라이브러리 {name} 가 일반 파일로 없습니다({init}) — Polaris.spec 의 '
                 'module_collection_mode 를 확인하세요.')
    out, comps = tpn.write(ROOT, APPDIR, f'v{version}')
    missing = tpn.missing_texts(comps)
    if missing:
        fail('라이선스 전문을 찾지 못한 구성 요소가 있습니다 — 고지 파일을 완성할 수 없습니다:\n  '
             + '\n  '.join(missing))
    ok(f'오픈소스 고지: {out.relative_to(ROOT)} ({len(comps)}개 구성 요소, '
       f'{out.stat().st_size // 1024} KB) · LGPL {", ".join(tpn.LGPL_REPLACEABLE)} 일반 파일 확인')


def _dir_size_mb(path):
    total = 0
    for p in Path(path).rglob('*'):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total / (1024 * 1024)


def verify_exe(version):
    if not EXE.exists():
        fail(f'빌드 산출물 없음: {EXE}')
    mtime = datetime.fromtimestamp(EXE.stat().st_mtime)
    ok(f'산출물: {APPDIR.relative_to(ROOT)}/ (onedir)')
    ok(f'  런처: {EXE.name} ({EXE.stat().st_size / (1024*1024):.1f} MB)')
    ok(f'  폴더: {_dir_size_mb(APPDIR):.1f} MB')
    ok(f'  생성: {mtime.strftime("%Y-%m-%d %H:%M:%S")}')
    ok(f'  버전: v{version}')
    # onedir 런처가 실제로 기동되는지 + 버전 일치 확인 (headless --selfcheck)
    try:
        out = subprocess.run([str(EXE), '--selfcheck'], capture_output=True,
                             text=True, timeout=60).stdout
        rep = json.loads(out)
        if rep.get('version') != version:
            fail(f'selfcheck 버전 불일치: EXE={rep.get("version")} vs {version}')
        # v1.3.73 — kubernetes 를 처음 쓸 때 불러오게 바꿨다. 빌드가 빠뜨리면 여기서 멈춘다
        if not (rep.get('k8s_lib') or {}).get('loaded'):
            fail(f'selfcheck: kubernetes 라이브러리를 불러오지 못함 — {(rep.get("k8s_lib") or {}).get("error")}')
        # v1.4.19 — LGPL 라이브러리는 실행 파일 밖의 .py 에서 불러와야 한다(사용자가 바꿔 끼울 수 있게)
        bad = {k: v for k, v in (rep.get('lgpl_libs') or {}).items() if v is not True}
        if bad or not rep.get('lgpl_libs'):
            fail(f'selfcheck: LGPL 라이브러리를 일반 파일에서 불러오지 않음 — {bad or "보고 없음"}')
        ok(f'  selfcheck: OK (frozen={rep.get("frozen")}, '
           f'features={rep.get("enabled_features")})')
    except Exception as e:
        fail(f'selfcheck 실패 — onedir 런처 기동 불가: {e}')


def make_zip():
    """dist/polaris/ → dist/polaris-win64.zip (설치 exe 임베드용 payload — 배포 안 함)."""
    if ZIP.exists():
        ZIP.unlink()
    # base_dir='polaris' → 압축 풀면 polaris/ 폴더가 생기고 그 안에서 polaris.exe 실행
    shutil.make_archive(str(ZIP.with_suffix('')), 'zip',
                        root_dir=str(DIST), base_dir='polaris')
    ok(f'zip: {ZIP.relative_to(ROOT)} ({ZIP.stat().st_size / (1024*1024):.1f} MB)')


def _find_vcvars():
    """vcvars64.bat 경로 탐색 (vswhere 우선 → 표준 설치 경로). 없으면 None."""
    pf86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    vswhere = Path(pf86) / 'Microsoft Visual Studio' / 'Installer' / 'vswhere.exe'
    if vswhere.is_file():
        try:
            out = subprocess.run(
                [str(vswhere), '-latest', '-products', '*',
                 '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
                 '-property', 'installationPath'],
                capture_output=True, text=True, timeout=30,
            ).stdout.strip()
            if out:
                vc = Path(out) / 'VC' / 'Auxiliary' / 'Build' / 'vcvars64.bat'
                if vc.is_file():
                    return vc
        except Exception:
            pass
    for base in (r'C:\Program Files\Microsoft Visual Studio\2022',
                 r'C:\Program Files (x86)\Microsoft Visual Studio\2022'):
        for ed in ('BuildTools', 'Community', 'Professional', 'Enterprise'):
            vc = Path(base) / ed / 'VC' / 'Auxiliary' / 'Build' / 'vcvars64.bat'
            if vc.is_file():
                return vc
    return None


def _sync_tauri_source(src, dst):
    """setup-tauri 소스를 ASCII 빌드 폴더로 복사 (node_modules/target/dist/payload/.git 제외).

    한글 경로에서 MinGW/일부 빌드 도구가 실패하므로 ASCII 경로에서 빌드하기 위함.
    기존 node_modules / target 은 보존(재설치·재컴파일 회피)."""
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    skip = {'node_modules', 'target', 'dist', 'payload', '.git'}
    for item in src.rglob('*'):
        rel = item.relative_to(src)
        if any(part in skip for part in rel.parts):
            continue
        out = dst / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)


def _sync_tauri_version(version):
    """setup-tauri 소스 버전을 VERSION 과 동기화.

    설치 마법사 창(App.jsx)에 표시되는 버전이 여기 빠져 있어 v1.2.8 에서 계속 고정된 채
    v1.2.89 까지 갱신 안 되고 있었다(사용자가 "설치파일 버전이 옛 버전"이라고 신고) — App.jsx/
    package.json 을 추가해 재발 방지.
    """
    # \d+\.\d+\.\d+ 뒤의 -rN 등 접미사까지([^"]*) 통째로 교체 — 안 그러면 버전이 누적됨
    targets = [
        (SETUP_TAURI / 'src-tauri' / 'tauri.conf.json',
         r'("version"\s*:\s*")\d+\.\d+\.\d+[^"]*'),
        (SETUP_TAURI / 'src-tauri' / 'Cargo.toml',
         r'(?m)^(version\s*=\s*")\d+\.\d+\.\d+[^"]*'),
        (SETUP_TAURI / 'src-tauri' / 'src' / 'main.rs',
         r'(const VERSION:\s*&str\s*=\s*")\d+\.\d+\.\d+[^"]*'),
        (SETUP_TAURI / 'src' / 'App.jsx',
         r"(const VERSION\s*=\s*'v)\d+\.\d+\.\d+[^']*"),
        (SETUP_TAURI / 'package.json',
         r'("version"\s*:\s*")\d+\.\d+\.\d+[^"]*'),
    ]
    for path, pat in targets:
        if not path.exists():
            continue
        txt = path.read_text(encoding='utf-8')
        new = re.sub(pat, lambda m: m.group(1) + version, txt, count=1)
        if new != txt:
            path.write_text(new, encoding='utf-8', newline='\n')
            info(f'Tauri 버전 동기화: {path.relative_to(ROOT)} → v{version}')


def make_installer_tauri(version):
    """packaging/setup-tauri (Tauri) → dist/polaris-setup-win64.exe (단일 self-contained exe).

    payload = dist/polaris-win64.zip (앞서 make_zip 산출). MSVC 빌드로 WebView2Loader 를
    정적 링크해 사이드카 DLL 없는 단일 exe 생성. 한글 경로 빌드 실패 방지를 위해 ASCII 경로에서 빌드.
    v1.2.20~: 설치 exe 가 유일한 배포 산출물 → 호출자(main)는 False 면 빌드를 중단한다.
    반환: 설치 파일 생성 여부(False = setup-tauri 소스/MSVC/cargo 미발견)."""
    if not SETUP_TAURI.exists():
        warn(f'{SETUP_TAURI.relative_to(ROOT)} 없음 — 설치 exe 를 만들 수 없습니다.')
        return False
    if not ZIP.exists():
        warn('payload(dist/polaris-win64.zip) 없음 — 설치 파일 생략')
        return False
    vcvars = _find_vcvars()
    if not vcvars:
        warn('MSVC(VC.Tools x64) 미발견 — 설치 exe 를 만들 수 없습니다. '
             'VS Build Tools(C++ 데스크톱 워크로드) 설치 후 다시 빌드하세요.')
        return False
    if not (shutil.which('cargo') or (Path.home() / '.cargo' / 'bin' / 'cargo.exe').exists()):
        warn('cargo(Rust msvc 툴체인) 미발견 — 설치 파일 생략. rustup 으로 Rust 설치 필요.')
        return False

    _sync_tauri_version(version)

    build_dir = Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'polaris-setup-build'
    info(f'Tauri 설치기 빌드 (ASCII 경로): {build_dir}')
    _sync_tauri_source(SETUP_TAURI, build_dir)
    payload = build_dir / 'src-tauri' / 'payload' / 'polaris-win64.zip'
    payload.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ZIP, payload)

    out_exe = (build_dir / 'src-tauri' / 'target' / 'x86_64-pc-windows-msvc'
               / 'release' / 'polaris-setup.exe')
    if out_exe.exists():
        out_exe.unlink()

    bat = build_dir / 'polaris-build-installer.bat'
    bat.write_text(
        '@echo off\r\n'
        f'cd /d "{build_dir}"\r\n'
        'set "PATH=C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer;'
        'C:\\Program Files\\Microsoft Visual Studio\\Installer;'
        '%USERPROFILE%\\.cargo\\bin;%PATH%"\r\n'
        f'call "{vcvars}"\r\n'
        'set "RUSTUP_TOOLCHAIN=stable-x86_64-pc-windows-msvc"\r\n'
        'if not exist node_modules call npm install\r\n'
        'call npm run tauri -- build --target x86_64-pc-windows-msvc\r\n'
        'echo TAURI_INSTALLER_EXIT=%ERRORLEVEL%\r\n',
        encoding='ascii',
    )
    info('Tauri 빌드 시작 (의존성 캐시 시 수 분)...')
    r = subprocess.run(['cmd', '/c', str(bat)], cwd=str(build_dir),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if not out_exe.exists() or 'TAURI_INSTALLER_EXIT=0' not in (r.stdout or ''):
        tail = (r.stdout or '')[-1500:] + '\n--- stderr ---\n' + (r.stderr or '')[-500:]
        fail(f'Tauri 설치기 빌드 실패:\n{tail}')
    if SETUP.exists():
        SETUP.unlink()
    shutil.copy2(out_exe, SETUP)
    ok(f'설치 파일: {SETUP.relative_to(ROOT)} '
       f'({SETUP.stat().st_size / (1024*1024):.1f} MB · Tauri 단일 exe)')
    return True


def write_checksums(exe=EXE):
    """EXE 의 SHA-256/512 체크섬 파일을 LF 로 생성한다.

    `sha256sum -c polaris.exe.sha256` (배포물 다운로드 후 사용자 검증)이 반드시
    동작하도록 두 가지를 강제한다:
      - 형식 : '<hex>  polaris.exe'  (해시 + 공백 2개 + 파일명만, 경로 없음)
      - 줄끝 : LF 강제. CRLF 로 생기면 파일명이 'polaris.exe\\r' 로 파싱돼
               검증이 'No such file or directory' 로 실패한다. (실배포 사고 방지)
    체크섬 파일은 build.py 와 scripts/publish_github.py 가 공유한다(단일 진실원).
    반환: 생성된 체크섬 파일 경로 리스트.
    """
    import hashlib
    exe = Path(exe)
    if not exe.exists():
        fail(f'체크섬 대상 없음: {exe}')
    data = exe.read_bytes()
    out = []
    for algo in ('sha256', 'sha512'):
        digest = hashlib.new(algo, data).hexdigest()
        line = f'{digest}  {exe.name}\n'              # LF + 파일명만
        dst = exe.with_name(exe.name + '.' + algo)
        dst.write_bytes(line.encode('ascii'))         # write_bytes → 줄끝 변환 없음(LF 보장)
        out.append(dst)
    return out


def main():
    # 콘솔 출력 인코딩 에러 방지 (cp949 환경 등)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    args = sys.argv[1:]
    force = '--force' in args
    check_only = '--check' in args

    print('=' * 56)
    print(f'  Polaris 빌드 스크립트')
    print('=' * 56)

    version = check_versions(force=force)
    check_source_hygiene(fix_eol='--fix-eol' in args)
    run_guard_tests()
    check_runtime_imports()
    check_spec_file()

    if check_only:
        ok('--check 모드: 가드만 검사 완료. 빌드는 건너뜀.')
        return

    print()
    sync_readme_version(version)   # README 다운로드 표 '최신' 버전 자동 동기화

    print()
    info('이전 빌드 산출물 정리...')
    clean()


    print()
    info('React UI 빌드...')
    run_npm_build()


    print()
    run_pyinstaller()

    print()
    write_third_party_notices(version)

    print()
    verify_exe(version)

    print()
    info('설치기 payload(zip) 생성...')
    make_zip()   # dist/polaris-win64.zip — 설치 exe 에 임베드할 중간물(배포·커밋 안 함)

    print()
    info('설치 파일 패키징 (Tauri 단일 exe · 사용자 공간 설치)...')
    # v1.2.20~: 배포 산출물은 설치 exe 하나뿐 → 빌드 못 하면 하드 실패(zip fallback 없음).
    if not make_installer_tauri(version):
        fail('설치 exe 빌드 실패/생략 — exe 가 유일한 배포 산출물이므로 빌드를 중단합니다. '
             '(설치기 빌드에 setup-tauri 소스 + MSVC + cargo 필요)')

    print()
    info('체크섬 생성 (LF, `sha256sum -c` 호환)...')
    for p in write_checksums(SETUP):
        ok(f'체크섬: {p.relative_to(ROOT)}')

    # payload zip 은 설치 exe 에 임베드됐으므로 배포물에서 제거 — dist 에는 설치 exe 만 남긴다.
    for z in (ZIP, ZIP.with_name(ZIP.name + '.sha256'), ZIP.with_name(ZIP.name + '.sha512')):
        if z.exists():
            z.unlink()
    info('payload zip 정리 완료 — 배포 산출물은 설치 exe 만')

    print()
    print('=' * 56)
    print(f'  Build complete - Polaris v{version}')
    print('=' * 56)


if __name__ == '__main__':
    main()
