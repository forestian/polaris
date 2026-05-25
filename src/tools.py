"""외부 CLI 탐색 + subprocess 헬퍼.

폴라리스가 사용하는 외부 도구(kubectl, helm, k9s, Windows Terminal) 의 경로 탐색,
실행 명령 구성, 백그라운드 실행 시 CMD 창 깜빡임 방지 플래그 등을 모았습니다.

이 모듈은 kubernetes Python 라이브러리에 의존하지 않습니다 — 순수 subprocess 계층.
"""
import os
import sys
import json
import shlex
import subprocess
from pathlib import Path

# ── subprocess CREATE_NO_WINDOW (CMD 창 깜빡임 방지) ───────────────────────────
# Windows 에서만 의미가 있고, 다른 OS 에서는 0 (no-op) 으로 동작.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

# ── 실행파일 경로 (사용자 ~/.kube 디렉터리) ───────────────────────────────────
_KUBECTL_LOCAL = os.path.join(os.path.expanduser('~'), '.kube', 'kubectl.exe')
_HELM_LOCAL    = os.path.join(os.path.expanduser('~'), '.kube', 'helm.exe')
_K9S_LOCAL     = os.path.join(os.path.expanduser('~'), '.kube', 'k9s.exe')

# ── 탐색 캐시 (반복 호출 시 비용 절감) ────────────────────────────────────────
_kubectl_cached: str | None = None
_helm_cached:    str | None = None
_k9s_cached:     str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# 실행파일 탐색
# ─────────────────────────────────────────────────────────────────────────────

def _probe(path: str) -> bool:
    """실행파일이 실제로 동작하는지 확인."""
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        r = subprocess.run([path, 'version', '--client'],
                           capture_output=True, timeout=3,
                           creationflags=flags)
        return r.returncode in (0, 1)
    except Exception:
        return False


def _find_kubectl() -> str | None:
    global _kubectl_cached
    if _kubectl_cached:
        ok = os.path.isfile(_kubectl_cached) if _kubectl_cached != 'kubectl' else True
        if ok:
            return _kubectl_cached
        _kubectl_cached = None
    for c in ['kubectl', _KUBECTL_LOCAL,
              r'C:\Program Files\kubectl\kubectl.exe',
              r'C:\Program Files\Rancher Desktop\resources\resources\win32\bin\kubectl.exe']:
        if _probe(c):
            _kubectl_cached = c
            return c
    return None


def _find_k9s() -> str | None:
    global _k9s_cached
    if _k9s_cached:
        ok = os.path.isfile(_k9s_cached) if _k9s_cached != 'k9s' else True
        if ok:
            return _k9s_cached
        _k9s_cached = None
    if os.path.isfile(_K9S_LOCAL):
        _k9s_cached = _K9S_LOCAL
        return _K9S_LOCAL
    import shutil
    found = shutil.which('k9s')
    if found:
        _k9s_cached = found
        return found
    for c in [r'C:\Program Files\k9s\k9s.exe']:
        if os.path.isfile(c):
            _k9s_cached = c
            return c
    return None


def _find_helm() -> str | None:
    global _helm_cached
    if _helm_cached:
        ok = os.path.isfile(_helm_cached) if _helm_cached != 'helm' else True
        if ok:
            return _helm_cached
        _helm_cached = None
    if os.path.isfile(_HELM_LOCAL):
        _helm_cached = _HELM_LOCAL
        return _HELM_LOCAL
    import shutil
    found = shutil.which('helm')
    if found:
        _helm_cached = found
        return found
    for c in [r'C:\Program Files\helm\helm.exe']:
        if os.path.isfile(c):
            _helm_cached = c
            return c
    return None


def _find_windows_terminal() -> str | None:
    """wt.exe 경로 탐색. 없으면 None."""
    import shutil
    found = shutil.which('wt') or shutil.which('wt.exe')
    if found:
        return found
    candidate = os.path.join(
        os.environ.get('LOCALAPPDATA', ''),
        'Microsoft', 'WindowsApps', 'wt.exe',
    )
    return candidate if os.path.isfile(candidate) else None


# ─────────────────────────────────────────────────────────────────────────────
# Windows Terminal Polaris 컬러 스킴 주입
# ─────────────────────────────────────────────────────────────────────────────

_WT_SCHEME_NAME = 'Polaris'
_WT_POLARIS_SCHEME = {
    'name':                _WT_SCHEME_NAME,
    'background':          '#060914',   # --bg-0
    'foreground':          '#c8c4dc',   # --text
    'cursorColor':         '#f3c969',   # --nimbus / polestar gold
    'selectionBackground': '#1c2046',   # --bg-3
    # ANSI 16색
    'black':         '#060e1c',
    'brightBlack':   '#1f3152',
    'red':           '#f87171',   # --red
    'brightRed':     '#f87171',
    'green':         '#34d399',   # --nimbus / --green
    'brightGreen':   '#34d399',
    'yellow':        '#fbbf24',   # --yellow
    'brightYellow':  '#fbbf24',
    'blue':          '#60a5fa',   # --blue
    'brightBlue':    '#60a5fa',
    'purple':        '#c084fc',
    'brightPurple':  '#c084fc',
    'cyan':          '#22d3ee',
    'brightCyan':    '#22d3ee',
    'white':         '#c4d4e8',   # --text
    'brightWhite':   '#e0efff',   # --text-bright
}


def _find_wt_settings() -> Path | None:
    """Windows Terminal settings.json 경로 탐색."""
    local = os.environ.get('LOCALAPPDATA', '')
    candidates = [
        Path(local) / 'Packages' / 'Microsoft.WindowsTerminal_8wekyb3d8bbwe' / 'LocalState' / 'settings.json',
        Path(local) / 'Packages' / 'Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe' / 'LocalState' / 'settings.json',
        Path(local) / 'Microsoft' / 'WindowsTerminal' / 'settings.json',
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _inject_wt_polaris_scheme() -> bool:
    """Windows Terminal settings.json에 Polaris 컬러 스킴 주입. 성공 여부 반환."""
    try:
        settings_path = _find_wt_settings()
        if not settings_path:
            return False
        text = settings_path.read_text(encoding='utf-8')
        settings = json.loads(text)
        schemes = settings.setdefault('schemes', [])
        settings['schemes'] = [s for s in schemes if s.get('name') != _WT_SCHEME_NAME]
        settings['schemes'].append(_WT_POLARIS_SCHEME)
        tmp = settings_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(settings, indent=4, ensure_ascii=False), encoding='utf-8')
        tmp.replace(settings_path)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 외부 터미널 실행 (k9s / 파드 셸)
# ─────────────────────────────────────────────────────────────────────────────

def _build_k9s_launch_command(k9s_path: str, kubeconfig: str = '') -> tuple[list[str], str]:
    """k9s 실행 커맨드 반환. (args, terminal_name)"""
    k9s_args = [k9s_path]
    if kubeconfig:
        k9s_args.extend(['--kubeconfig', kubeconfig])

    wt = _find_windows_terminal()
    if wt:
        scheme_ok = _inject_wt_polaris_scheme()
        cmd = [wt, 'new-tab', '--title', 'Polaris — k9s', '--tabColor', '#060914']
        if scheme_ok:
            cmd.extend(['--colorScheme', _WT_SCHEME_NAME])
        cmd.extend(['--'] + k9s_args)
        return cmd, 'Windows Terminal'

    # fallback: CMD 창
    return (
        ['cmd.exe', '/c', 'start', 'Polaris k9s', 'cmd.exe', '/k'] + k9s_args,
        'CMD',
    )


def _build_pod_shell_command(kubectl: str, exec_args: list[str], kubeconfig: str,
                             ns: str, name: str) -> tuple[list[str], str]:
    """파드 exec 터미널 커맨드. (cmd, terminal_name)"""
    kube_flag = ['--kubeconfig', kubeconfig] if kubeconfig else []
    kubectl_cmd = [kubectl] + kube_flag + exec_args
    title = f'Polaris — {ns}/{name}'

    wt = _find_windows_terminal()
    if wt:
        scheme_ok = _inject_wt_polaris_scheme()
        cmd = [wt, 'new-tab', '--title', title, '--tabColor', '#060914']
        if scheme_ok:
            cmd.extend(['--colorScheme', _WT_SCHEME_NAME])
        cmd.extend(['--'] + kubectl_cmd)
        return cmd, 'Windows Terminal'

    return (
        ['cmd.exe', '/c', 'start', title, 'cmd.exe', '/k'] + kubectl_cmd,
        'CMD',
    )


# ─────────────────────────────────────────────────────────────────────────────
# kubectl 실행 + 명령어 파싱
# ─────────────────────────────────────────────────────────────────────────────

def _run_kubectl(kubeconfig: str, args: list, timeout: int = 30):
    """kubectl 명령 실행. (stdout, stderr) 반환."""
    kubectl = _find_kubectl()
    if not kubectl:
        return '', 'kubectl을 찾을 수 없습니다.'
    cmd = [kubectl, '--kubeconfig', kubeconfig] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, encoding='utf-8', errors='replace',
                           creationflags=_NO_WINDOW)
        return r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return '', f'타임아웃 ({timeout}s)'
    except Exception as e:
        return '', str(e)


def _parse_kubectl_command(cmd: str) -> list[str]:
    """사용자 입력 kubectl 명령을 argv 로 분해. 'kubectl' 접두사는 제거."""
    text = (cmd or '').strip()
    if not text:
        return []
    args = shlex.split(text)
    if args and Path(args[0]).name.lower() in ('kubectl', 'kubectl.exe'):
        args = args[1:]
    return args


def _extract_host_port(msg: str) -> str:
    """에러 메시지에서 host:port 추출. 실패 시 '서버' 반환."""
    import re
    m = re.search(r"host='([^']+)',\s*port=(\d+)", msg)
    if m:
        return f'{m.group(1)}:{m.group(2)}'
    m = re.search(r'([\w.-]+):(\d{2,5})', msg)
    if m:
        return f'{m.group(1)}:{m.group(2)}'
    return '서버'


# ─────────────────────────────────────────────────────────────────────────────
# kubectl 글로벌 플래그 + 스트리밍 명령 감지
# ─────────────────────────────────────────────────────────────────────────────

_KUBECTL_GLOBAL_FLAGS_WITH_VALUE = {
    '--as',
    '--as-group',
    '--as-uid',
    '--cache-dir',
    '--certificate-authority',
    '--client-certificate',
    '--client-key',
    '--cluster',
    '--context',
    '--kubeconfig',
    '--log-backtrace-at',
    '--log-dir',
    '--log-file',
    '--log-file-max-size',
    '--log-flush-frequency',
    '--namespace',
    '--password',
    '--profile',
    '--profile-output',
    '--request-timeout',
    '--server',
    '--stderrthreshold',
    '--tls-server-name',
    '--token',
    '--user',
    '--username',
    '--v',
    '--vmodule',
    '-n',
}

_KUBECTL_GLOBAL_FLAGS_NO_VALUE = {
    '--alsologtostderr',
    '--disable-compression',
    '--insecure-skip-tls-verify',
    '--logtostderr',
    '--match-server-version',
    '--skip-headers',
    '--skip-log-headers',
}


def _kubectl_subcommand_index(args: list[str]) -> int:
    """argv 에서 실제 서브커맨드(get / logs / port-forward ...) 위치 찾기."""
    idx = 0
    args = list(args or [])
    while idx < len(args):
        arg = str(args[idx] or '')
        if arg == '--':
            return idx + 1
        if arg in _KUBECTL_GLOBAL_FLAGS_WITH_VALUE:
            idx += 2
            continue
        if any(arg.startswith(flag + '=') for flag in _KUBECTL_GLOBAL_FLAGS_WITH_VALUE):
            idx += 1
            continue
        if arg in _KUBECTL_GLOBAL_FLAGS_NO_VALUE:
            idx += 1
            continue
        if arg.startswith('-') and len(arg) > 1:
            idx += 1
            continue
        return idx
    return len(args)


def _is_kubectl_streaming_args(args: list[str]) -> bool:
    """kubectl 명령이 지속 실행되는 스트리밍 형태인지 (port-forward / watch / logs -f).
    터미널에서 별도 처리(타임아웃 안 적용) 가 필요한지 판단."""
    args = list(args or [])
    idx = _kubectl_subcommand_index(args)
    if idx >= len(args):
        return False
    cmd = args[idx]
    tail = args[idx + 1:]
    if cmd in ('port-forward', 'watch'):
        return True
    if cmd == 'logs' and ('-f' in tail or '--follow' in tail):
        return True
    if cmd == 'get' and ('-w' in tail or '--watch' in tail):
        return True
    return False
