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
PY    = ROOT / 'polaris.py'
CHLOG = ROOT / 'CHANGELOG.md'
SPEC  = ROOT / 'packaging' / 'specs' / 'Polaris.spec'
EXE   = ROOT / 'dist' / 'polaris.exe'

REQUIRED_RUNTIME_IMPORTS = [
    ('kubernetes', 'kubernetes'),
    ('webview', 'pywebview'),
    ('docx', 'python-docx'),
    ('PyInstaller', 'pyinstaller'),
    ('pystray', 'pystray'),
    ('PIL', 'Pillow'),
    ('cryptography', 'cryptography'),
    ('paramiko', 'paramiko'),
]


def fail(msg):
    print(f'\n[FAIL] {msg}\n', file=sys.stderr)
    sys.exit(1)


def info(msg):
    print(f'[INFO] {msg}')


def ok(msg):
    print(f'[ OK ] {msg}')


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


def clean():
    targets = [
        ROOT / 'build',
        ROOT / '__pycache__',
        EXE,
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


def verify_exe(version):
    if not EXE.exists():
        fail(f'빌드 산출물 없음: {EXE}')
    size_mb = EXE.stat().st_size / (1024 * 1024)
    mtime = datetime.fromtimestamp(EXE.stat().st_mtime)
    ok(f'산출물: {EXE}')
    ok(f'  크기: {size_mb:.1f} MB')
    ok(f'  생성: {mtime.strftime("%Y-%m-%d %H:%M:%S")}')
    ok(f'  버전: v{version}')


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
    check_runtime_imports()
    check_spec_file()

    if check_only:
        ok('--check 모드: 가드만 검사 완료. 빌드는 건너뜀.')
        return

    print()
    info('이전 빌드 산출물 정리...')
    clean()

    print()
    info('React UI 빌드...')
    run_npm_build()

    print()
    run_pyinstaller()

    print()
    verify_exe(version)
    # 버전별 사본은 만들지 않음 — 옛 버전은 GitLab 태그 (raw/v1.0.X/dist/polaris.exe) 로 접근 가능
    # 저장공간 절약을 위해 dist/ 에는 항상 polaris.exe 하나만 유지

    print()
    print('=' * 56)
    print(f'  Build complete - Polaris v{version}')
    print('=' * 56)


if __name__ == '__main__':
    main()
