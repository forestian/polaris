"""외부 CLI 탐색 + subprocess 헬퍼.

폴라리스가 사용하는 외부 도구(kubectl, helm, k9s, Windows Terminal) 의 경로 탐색,
실행 명령 구성, 백그라운드 실행 시 CMD 창 깜빡임 방지 플래그 등을 모았습니다.

이 모듈은 kubernetes Python 라이브러리에 의존하지 않습니다 — 순수 subprocess 계층.
"""
import os
import re
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
# kubectl 이 없을 때 안내 — 폐쇄망에서는 자동 받기(dl.k8s.io)가 실패하니 직접 둘 곳을 알려 준다(v1.4.24)
KUBECTL_MISSING = ('kubectl 을 찾을 수 없습니다 — 인터넷이 되면 클러스터에 연결할 때 자동으로 받습니다. '
                   '폐쇄망이면 클러스터와 버전이 맞는 kubectl.exe 를 ' + _KUBECTL_LOCAL + ' 에 두거나 PATH 에 넣으세요.')
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


# ── 클러스터 판에 맞는 kubectl 고르기 (v1.5.74) ────────────────────────────────
# 예전엔 PATH 의 kubectl 하나만 썼다. 사용자 PC 는 PATH 맨 앞이 Docker Desktop 의 1.32 라 1.37 클러스터와
# 판 차이(±1 보장)를 크게 넘었다(경고 · 새 필드 오해 가능). 이 PC 에 있는 kubectl 을 모두 찾아,
# 연결한 클러스터마다 판 차이가 가장 적은 것을 쓴다 — 새 클러스터에 맞추느라 옛 클러스터가 깨지지 않게.
_SERVER_MINOR: dict[str, int] = {}                 # kubeconfig 경로 → 서버 마이너 판(연결할 때 적어 둠)
_CLIENT_MINOR: dict[str, tuple] = {}               # kubectl 경로 → (수정 시각, 마이너 판 | None)
_KUBECTL_FOR: dict[str, str] = {}                  # kubeconfig 경로 → 고른 kubectl


def _kc_key(kubeconfig: str) -> str:
    return os.path.normcase(os.path.abspath(kubeconfig)) if kubeconfig else ''


def _minor_of(version: str) -> int | None:
    """'v1.37.2+k3s1' · '1.36' · '36+' 같은 판에서 마이너 숫자"""
    s = str(version or '').strip()
    m = re.match(r'^v?\d+\.(\d+)', s) or re.match(r'^(\d+)\+?$', s)
    return int(m.group(1)) if m else None


def note_server_version(kubeconfig: str, git_version: str) -> None:
    """클러스터에 연결할 때 그 kubeconfig 의 서버 판을 적어 둔다(src/k8s.py connect)."""
    key, minor = _kc_key(kubeconfig), _minor_of(git_version)
    if key and minor is not None:
        if _SERVER_MINOR.get(key) != minor:
            _KUBECTL_FOR.pop(key, None)
        _SERVER_MINOR[key] = minor


def pick_kubectl(candidates: list, server_minor: int | None) -> str | None:
    """[(경로, 마이너)] 중 서버 판과 차이가 가장 적은 것. 차이가 같으면 새 판(클라이언트가 한 판 위인 것은 공식 지원).
    서버 판을 모르거나 판을 읽은 후보가 없으면 None — 부르는 쪽이 예전 순서로 고른다."""
    known = [(p, m) for p, m in candidates if m is not None]
    if server_minor is None or not known:
        return None
    return min(known, key=lambda pm: (abs(pm[1] - server_minor), -pm[1]))[0]


def _kubectl_candidates() -> list:
    """이 PC 의 kubectl 실행 파일들(실제 경로, 중복 없이) — PATH 의 모든 것 + 알려진 자리."""
    exe = 'kubectl.exe' if sys.platform == 'win32' else 'kubectl'
    seen, out = set(), []
    paths = [os.path.join(d.strip('"'), exe) for d in os.environ.get('PATH', '').split(os.pathsep) if d.strip()]
    local = os.environ.get('LOCALAPPDATA', '')
    paths += [_KUBECTL_LOCAL,
              r'C:\Program Files\kubectl\kubectl.exe',
              r'C:\Program Files\Rancher Desktop\resources\resources\win32\bin\kubectl.exe',
              os.path.join(local, 'Programs', 'Rancher Desktop', 'resources', 'resources', 'win32', 'bin', 'kubectl.exe')
              if local else '']
    for p in paths:
        if not p or not os.path.isfile(p):
            continue
        key = os.path.normcase(os.path.realpath(p))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _client_minor(path: str) -> int | None:
    """kubectl 의 클라이언트 마이너 판(파일이 바뀌지 않으면 한 번만 실행)."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    hit = _CLIENT_MINOR.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    minor = None
    try:
        r = subprocess.run([path, 'version', '--client', '-o', 'json'], capture_output=True, text=True,
                           timeout=5, encoding='utf-8', errors='replace', creationflags=_NO_WINDOW)
        txt = r.stdout or ''
        start = txt.find('{')                 # Rancher 래퍼 등이 앞에 진행 줄을 찍을 수 있다
        if start >= 0:
            minor = _minor_of((json.loads(txt[start:]).get('clientVersion') or {}).get('minor', ''))
    except Exception:
        minor = None
    _CLIENT_MINOR[path] = (mtime, minor)
    return minor


def _find_kubectl(kubeconfig: str | None = None) -> str | None:
    """kubeconfig 를 주면 그 클러스터 판에 가장 가까운 kubectl, 아니면(또는 판을 모르면) 예전 순서의 첫 kubectl."""
    key = _kc_key(kubeconfig) if kubeconfig else ''
    if key and key in _SERVER_MINOR:
        chosen = _KUBECTL_FOR.get(key)
        if chosen and os.path.isfile(chosen):
            return chosen
        chosen = pick_kubectl([(p, _client_minor(p)) for p in _kubectl_candidates()], _SERVER_MINOR[key])
        if chosen:
            _KUBECTL_FOR[key] = chosen
            return chosen
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


def kubectl_choice(kubeconfig: str | None) -> dict:
    """화면 · 진단용 — 이 클러스터에 쓰는 kubectl 과 판"""
    path = _find_kubectl(kubeconfig)
    full = path if (path and os.path.isfile(path)) else None
    return {'path': path, 'client_minor': _client_minor(full) if full else None,
            'server_minor': _SERVER_MINOR.get(_kc_key(kubeconfig)) if kubeconfig else None}


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

_CMD_META = set('&|<>^%"')     # 괄호는 C:\Program Files (x86) 경로에 흔하고 단일 명령에선 무해하다


def _cmd_safe_or_raise(args) -> None:
    """cmd.exe /k 로 넘길 인자에 cmd 특수문자가 있으면 거부한다(v1.5.28 검토).

    Windows Terminal 이 없을 때의 대체 경로는 인자를 cmd.exe 가 다시 해석한다 — 경로나 이름에 & | 가
    있으면 그 뒤가 별도 명령으로 실행된다. 그런 경우는 실행하지 않고 알린다."""
    for a in args:
        if any(ch in _CMD_META for ch in str(a)):
            raise ValueError('명령 창(cmd)으로 열 수 없는 문자(& | < > ^ % ")가 경로 · 이름에 있습니다 — '
                             'Windows Terminal 을 설치하면 열 수 있습니다.')


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
    _cmd_safe_or_raise(k9s_args)
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

    _cmd_safe_or_raise([title] + kubectl_cmd)
    return (
        ['cmd.exe', '/c', 'start', title, 'cmd.exe', '/k'] + kubectl_cmd,
        'CMD',
    )


# ─────────────────────────────────────────────────────────────────────────────
# kubectl 실행 + 명령어 파싱
# ─────────────────────────────────────────────────────────────────────────────

# RKE2/Rancher 의 kubectl wrapper(versioner.go) 가 클러스터 버전에 맞는 kubectl 을
# 처음 호출할 때 출력에 섞는 다운로드 진행 로그 패턴. 실제 명령 출력이 아니므로 제거한다.
_VERSIONER_NOISE_RE = re.compile(
    r'''(?xim)
    ^.*(?:
        versioner\.go:\d+          |  # I0529 ... versioner.go:115] ...
        Right\ kubectl\ missing    |
        Downloading\b              |
        ^\s*kubectl[\w.+-]*\.exe\s+\d+%   # kubectl1.32.13+rke2r1.exe 5% |...|
    ).*$
    '''
)


def _strip_versioner_noise(text: str) -> str:
    """kubectl wrapper(versioner) 의 다운로드 진행 로그 라인을 제거.

    versioner 는 진행률을 carriage-return(\\r) 으로 갱신하기도 하므로 \\r 분해 후
    노이즈 라인을 걸러낸다. 일반 kubectl 출력에는 영향 없음.
    """
    if not text or ('versioner' not in text and 'Downloading' not in text
                    and '.exe ' not in text):
        return text
    # \r 로 갱신되는 진행률 조각 제거
    text = text.replace('\r', '\n')
    kept = [ln for ln in text.split('\n') if not _VERSIONER_NOISE_RE.match(ln)]
    # 노이즈 제거 후 앞쪽 빈 줄 정리
    return '\n'.join(kept).lstrip('\n')


def _run_kubectl(kubeconfig: str, args: list, timeout: int = 30,
                 stdin_input: str | None = None):
    """kubectl 명령 실행. (stdout, stderr) 반환.

    stdin_input 이 주어지면 표준입력으로 전달한다 (예: `kubectl apply -f -`).
    임시 파일을 디스크에 쓰지 않으므로 민감한 매니페스트도 안전하게 적용 가능.

    RKE2/Rancher kubectl wrapper 의 버전 다운로드 진행 로그는 자동으로 제거된다.
    """
    kubectl = _find_kubectl(kubeconfig)
    if not kubectl:
        return '', KUBECTL_MISSING
    cmd = [kubectl, '--kubeconfig', kubeconfig] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           input=stdin_input,
                           timeout=timeout, encoding='utf-8', errors='replace',
                           creationflags=_NO_WINDOW)
        return _strip_versioner_noise(r.stdout), _strip_versioner_noise(r.stderr)
    except subprocess.TimeoutExpired:
        return '', f'타임아웃 ({timeout}s)'
    except Exception as e:
        return '', str(e)


def _run_kubectl_rc(kubeconfig: str, args: list, timeout: int = 30,
                    stdin_input: str | None = None):
    """`_run_kubectl` 과 같지만 **종료코드까지** 반환. (rc, stdout, stderr).

    별도 함수로 둔 이유 — `_run_kubectl` 은 호출부가 많아 반환 형태를 바꿀 수 없다.

    이게 필요한 곳은 `kubectl diff` 다. diff 는 종료코드로 결과를 알린다:
        0 = 차이 없음 / 1 = **차이 있음(정상)** / ≥2 = 실행 실패
    종료코드 없이 stdout·stderr 만 보면 "차이 있음"과 "실패"를 구분할 수 없어
    멀쩡한 diff 를 오류로 신고하게 된다.

    실행 자체가 불가능한 경우(kubectl 없음/타임아웃/예외) rc 는 -1.
    """
    kubectl = _find_kubectl(kubeconfig)
    if not kubectl:
        return -1, '', KUBECTL_MISSING
    cmd = [kubectl, '--kubeconfig', kubeconfig] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           input=stdin_input,
                           timeout=timeout, encoding='utf-8', errors='replace',
                           creationflags=_NO_WINDOW)
        return (r.returncode,
                _strip_versioner_noise(r.stdout),
                _strip_versioner_noise(r.stderr))
    except subprocess.TimeoutExpired:
        return -1, '', f'타임아웃 ({timeout}s)'
    except Exception as e:
        return -1, '', str(e)


def _parse_kubectl_command(cmd: str) -> list[str]:
    """사용자 입력 kubectl 명령을 argv 로 분해. 'kubectl' 접두사는 제거."""
    text = (cmd or '').strip()
    if not text:
        return []
    if '\\' in text:
        # Windows 경로(-f C:\work\a.yaml) — POSIX 분해는 역슬래시를 지워 C:worka.yaml 이 됐다(v1.5.28 검토)
        args = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in '"\'' else a
                for a in shlex.split(text, posix=False)]
    else:
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
    if cmd in ('port-forward', 'watch', 'proxy', 'attach'):
        return True

    def _flag(short, long_):
        # -f · --follow · --follow=true · 묶음 짧은 플래그(-fp) 까지 (v1.5.28 검토 — 예전엔 60초 동안 멈췄다)
        for a in tail:
            a = str(a)
            if a == long_ or (a.startswith(long_ + '=') and a.split('=', 1)[1].lower() not in ('false', '0')):
                return True
            # 묶음은 값 없는 짧은 플래그로만 된 것(-fp · -Aw) — -owide 같은 값 붙은 플래그를 잘못 잡지 않게
            if (short and a.startswith('-') and not a.startswith('--') and len(a) > 1
                    and short in a[1:] and set(a[1:]) <= set('fpwA')):
                return True
        return False
    if cmd == 'logs' and _flag('f', '--follow'):
        return True
    if cmd in ('get', 'events') and (_flag('w', '--watch') or _flag('', '--watch-only')):
        return True
    return False


# kubectl 내장 서브커맨드 — 그 밖의 이름은 kubectl 이 PATH 의 `kubectl-<이름>` 플러그인 실행 파일을 찾아 돌린다.
# 터미널 입력 한 줄이 아무 실행 파일이나 띄우지 못하게 내장 명령만 받는다(v1.5.28 검토)
KUBECTL_BUILTIN_SUBCMDS = frozenset('''
annotate api-resources api-versions apply attach auth autoscale certificate cluster-info completion config
cordon cp create debug delete describe diff drain edit events exec explain expose get kustomize label logs
patch port-forward proxy replace rollout run scale set taint top uncordon version wait help
'''.split())
