"""TerminalMixin — kubectl 터미널 / k9s 런처 / 파드 셸.
"""
import os
import sys
import shutil
import subprocess
import threading
from pathlib import Path

from src.tools import (
    _find_kubectl, _find_k9s, _NO_WINDOW,
    _build_k9s_launch_command, _build_pod_shell_command,
    _parse_kubectl_command, _is_kubectl_streaming_args,
    _kubectl_subcommand_index, KUBECTL_BUILTIN_SUBCMDS,
)
from src.k8s import _build_pod_exec_args
from src._state import _kubectl_stream_procs


class TerminalMixin:
    _STREAMING_SUBCMDS = frozenset(['port-forward', 'watch'])


    def run_kubectl(self, cmd: str):
        if not self.k8s.kubeconfig:
            return {'output': '', 'error': '클러스터에 연결되지 않았습니다.'}
        kubectl = _find_kubectl(self.k8s.kubeconfig)
        if not kubectl:
            return {'output': '', 'error': _tools_missing()}
        try:
            args = _parse_kubectl_command(cmd)
        except ValueError as e:
            return {'output': '', 'error': f'kubectl 명령 파싱 실패: {e}'}
        if not args:
            return {'output': '', 'error': 'kubectl 명령을 입력하세요.'}
        # 내장 명령만 · 연결된 클러스터만 (v1.5.28 검토)
        _sub_i = _kubectl_subcommand_index(args)
        _sub = args[_sub_i] if _sub_i < len(args) else ''
        if _sub and _sub not in KUBECTL_BUILTIN_SUBCMDS:
            return {'output': '', 'error': f'「{_sub}」 는 kubectl 내장 명령이 아닙니다 — 플러그인(kubectl-{_sub})은 이 터미널에서 실행하지 않습니다.'}
        if _sub == 'plugin' or any(str(a) == '--kubeconfig' or str(a).startswith('--kubeconfig=') for a in args):
            return {'output': '', 'error': '이 터미널은 연결된 클러스터에만 명령합니다 — --kubeconfig 는 쓸 수 없습니다.'}

        # --kubeconfig 플래그 대신 KUBECONFIG 환경변수 사용
        env = {**os.environ, 'KUBECONFIG': self.k8s.kubeconfig}

        # ── 스트리밍 명령 감지 (port-forward / watch / logs --follow 등) ──────
        # logs -f / --follow 도 스트리밍으로 처리
        is_streaming = _is_kubectl_streaming_args(args)

        if is_streaming:
            # Popen으로 백그라운드 실행 → 3초 대기 후 초기 출력 반환
            import threading as _th
            try:
                proc = subprocess.Popen(
                    [kubectl] + args,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace',
                    env=env, creationflags=_NO_WINDOW,
                )
                # 3초간 출력 누적
                out_lines, err_lines = [], []
                collecting = [True]

                def _read(pipe, buf):
                    # 처음 3초만 모으고, 그 뒤엔 읽어서 버린다(파이프가 차서 kubectl 이 멈추지 않게).
                    # 예전엔 백그라운드로 도는 동안 계속 목록에 쌓아 watch 하나가 몇 시간이면 수백 MB 를 먹었다(v1.5.28 검토)
                    try:
                        for ln in iter(pipe.readline, ''):
                            if collecting[0] and len(buf) < 2000:
                                buf.append(ln)
                    except Exception:
                        pass

                t_out = _th.Thread(target=_read, args=(proc.stdout, out_lines), daemon=True)
                t_err = _th.Thread(target=_read, args=(proc.stderr, err_lines), daemon=True)
                t_out.start(); t_err.start()
                t_out.join(timeout=3); t_err.join(timeout=0.1)
                collecting[0] = False
                out_lines, err_lines = list(out_lines), list(err_lines)

                if proc.poll() is not None:
                    # 이미 종료 → 오류
                    return {
                        'output': ''.join(out_lines),
                        'error': ''.join(err_lines),
                    }
                # 계속 실행 중 — 클러스터 재연결/종료 시 함께 정리되도록 등록
                # (예전엔 등록하지 않아 "재연결 시 자동 종료됩니다" 안내가 실제로는 지켜지지 않았음)
                _kubectl_stream_procs[proc.pid] = {
                    'proc': proc, 'cluster_id': self._active_id or '',
                }
                # 아직 실행 중 → 성공 안내
                hint = ''
                idx = _kubectl_subcommand_index(args)
                first_arg = args[idx] if idx < len(args) else ''
                if first_arg == 'port-forward':
                    # 포워딩 포트 파싱 시도
                    ports = next((a for a in args if ':' in a and a[0].isdigit()), None)
                    local = ports.split(':')[0] if ports else '?'
                    hint = f'\n→ 브라우저에서 http://localhost:{local} 열기'
                return {
                    'output': (
                        ''.join(out_lines) +
                        f'\n[백그라운드 실행 중 — PID {proc.pid}]{hint}\n'
                        '※ Polaris 창을 닫거나 클러스터 재연결 시 자동 종료됩니다.'
                    ),
                    'error': ''.join(err_lines),
                }
            except Exception as e:
                return {'output': '', 'error': str(e)}

        # ── 일반 명령 (60s timeout) ───────────────────────────────────────────
        try:
            r = subprocess.run(
                [kubectl] + args,
                capture_output=True, text=True,
                timeout=60, encoding='utf-8', errors='replace',
                env=env, creationflags=_NO_WINDOW,
            )
            return {'output': r.stdout, 'error': r.stderr}
        except subprocess.TimeoutExpired:
            return {'output': '', 'error': '타임아웃 (60s)'}
        except Exception as e:
            return {'output': '', 'error': str(e)}


    def _stop_kubectl_stream_procs_for_cluster(self, cluster_id: str = ''):
        """kubectl 터미널(run_kubectl)에서 사용자가 직접 실행한 port-forward/watch 등
        백그라운드 스트리밍 프로세스 정리. _stop_port_forward_jobs_for_cluster 와 동일한
        타이밍(클러스터 제거/앱 종료)에 함께 호출된다 — cluster_id='' 면 전체 정리."""
        ids = [
            pid for pid, info in list(_kubectl_stream_procs.items())
            if not cluster_id or info.get('cluster_id') == cluster_id
        ]
        for pid in ids:
            info = _kubectl_stream_procs.pop(pid, None)
            proc = info.get('proc') if info else None
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass


    def launch_k9s(self):
        k9s = _find_k9s()
        if not k9s:
            return {'ok': False, 'not_found': True,
                    'error': 'k9s 실행파일을 찾을 수 없습니다.'}
        try:
            env = {**os.environ}
            if self.k8s.kubeconfig:
                env['KUBECONFIG'] = self.k8s.kubeconfig
            cmd, terminal = _build_k9s_launch_command(k9s, self.k8s.kubeconfig or '')
            subprocess.Popen(
                cmd, env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            return {'ok': True, 'terminal': terminal}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def install_k9s(self) -> dict:
        """GitHub releases에서 k9s 최신 버전을 다운로드하여 ~/.kube/k9s.exe 에 설치.

        공식 checksums.sha256 대조로 무결성 검증(fail-closed, install_kubectl 과 동일 정신) —
        체크섬을 못 받거나 불일치하면 설치를 중단하고 디스크에 아무것도 쓰지 않는다.
        """
        import io
        import json
        import zipfile
        import hashlib
        import urllib.request
        import src.tools as _tools

        def _get(url, timeout):
            req = urllib.request.Request(url, headers={'User-Agent': 'polaris-app'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()

        try:
            # 1. 최신 릴리스 메타데이터 조회
            release = json.loads(_get('https://api.github.com/repos/derailed/k9s/releases/latest', 10))
            tag = release['tag_name']
            assets = release.get('assets', [])

            # 2. Windows amd64 zip asset 이름/URL 탐색 (없으면 표준 이름으로 구성)
            asset_name = next(
                (a['name'] for a in assets
                 if 'windows' in a['name'].lower()
                 and 'amd64' in a['name'].lower()
                 and a['name'].lower().endswith('.zip')),
                'k9s_Windows_amd64.zip',
            )
            asset_url = next(
                (a['browser_download_url'] for a in assets if a['name'] == asset_name),
                f'https://github.com/derailed/k9s/releases/download/{tag}/{asset_name}',
            )

            # 3. zip 다운로드
            zip_data = _get(asset_url, 120)

            # 4. 무결성 검증 (공식 checksums.sha256) — fail-closed
            try:
                checksums = _get(
                    f'https://github.com/derailed/k9s/releases/download/{tag}/checksums.sha256', 30,
                ).decode('utf-8', errors='replace')
            except Exception as e:
                return {'ok': False, 'error': f'체크섬 파일을 받을 수 없어 설치를 중단합니다: {e}'}
            want = next(
                (parts[0].strip().lower() for ln in checksums.splitlines()
                 if len((parts := ln.split())) == 2 and parts[1] == asset_name),
                None,
            )
            if not want:
                return {'ok': False, 'error': f'체크섬 목록에 {asset_name} 항목이 없어 설치를 중단합니다.'}
            if hashlib.sha256(zip_data).hexdigest() != want:
                return {'ok': False, 'error': 'k9s 체크섬 불일치 (다운로드 손상/위변조 의심) — 설치 중단'}

            # 5. zip에서 k9s.exe 추출
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                exe_entry = next(
                    (n for n in zf.namelist()
                     if os.path.basename(n).lower() in ('k9s.exe', 'k9s')),
                    None,
                )
                if not exe_entry:
                    return {'ok': False, 'error': 'zip 파일에서 k9s.exe를 찾을 수 없습니다.'}
                exe_data = zf.read(exe_entry)

            # 6. ~/.kube/k9s.exe 로 저장
            dest = _tools._K9S_LOCAL
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as f:
                f.write(exe_data)

            # 7. 탐색 캐시 초기화 → 다음 _find_k9s() 에서 정상 검출
            _tools._k9s_cached = None

            return {'ok': True, 'version': tag, 'path': dest}

        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def install_kubectl(self) -> dict:
        """kubectl 자동 설치 — dl.k8s.io 공식 stable 바이너리를 ~/.kube/kubectl.exe 로 다운로드.

        설치본을 키우지 않고(번들 X) 대상 PC 에서 1회만 받는다. fresh PC(시스템 kubectl 없음)에서
        파드 YAML 보기·describe·kubectl 터미널·파드 셸(exec)·Helm 이 동작하도록 한다.
        공식 .sha256 대조로 무결성 검증(fail-closed, install_k9s 와 동일 정신) — 체크섬을 못
        받거나 불일치하면 설치를 중단하고 디스크에 아무것도 쓰지 않는다.
        클러스터 연결 시 백엔드가 자동 호출(APIBase._ensure_kubectl_async) — 이미 있으면 호출부가 skip.
        """
        import re as _re
        import hashlib
        import urllib.request
        import src.tools as _tools

        def _get(url, timeout):
            req = urllib.request.Request(url, headers={'User-Agent': 'polaris-app'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()

        try:
            ver = _get('https://dl.k8s.io/release/stable.txt', 15).decode().strip()
            if not _re.match(r'^v\d+\.\d+\.\d+$', ver):
                return {'ok': False, 'error': f'stable 버전 파싱 실패: {ver[:40]}'}
            url = f'https://dl.k8s.io/release/{ver}/bin/windows/amd64/kubectl.exe'
            data = _get(url, 300)
            # 무결성 검증 (공식 .sha256) — fail-closed
            try:
                want = _get(url + '.sha256', 30).decode().split()[0].strip()
            except Exception as e:
                return {'ok': False, 'error': f'체크섬 파일을 받을 수 없어 설치를 중단합니다: {e}'}
            if not want:
                return {'ok': False, 'error': '체크섬 파일이 비어 있어 설치를 중단합니다.'}
            if hashlib.sha256(data).hexdigest() != want:
                return {'ok': False, 'error': 'kubectl 체크섬 불일치 (다운로드 손상/위변조 의심) — 설치 중단'}
            dest = _tools._KUBECTL_LOCAL
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as f:
                f.write(data)
            _tools._kubectl_cached = None   # 탐색 캐시 무효화 → 다음 _find_kubectl() 에서 검출
            _tools._KUBECTL_FOR.clear()     # 클러스터별로 고른 것도 — 새로 받은 kubectl 을 후보에 넣어 다시 고른다(v1.5.74)
            return {'ok': True, 'version': ver, 'path': dest}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def open_pod_shell(self, ns: str, name: str, container: str = ''):
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        kubectl = _find_kubectl(self.k8s.kubeconfig)
        if not kubectl:
            return {'ok': False, 'error': _tools_missing()}
        try:
            args = _build_pod_exec_args(ns, name, container)
            cmd, terminal = _build_pod_shell_command(
                kubectl, args, self.k8s.kubeconfig or '', ns, name)
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            return {'ok': True, 'command': 'kubectl ' + ' '.join(args), 'terminal': terminal}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # ── 파드 exec 내장 셸 (WebSocket 스트림, xterm.js 연결) ──────────────────
    # open_pod_shell 은 외부 터미널을 띄우지만, 아래 세션 API 는 Polaris 안에서
    # 파드 셸을 연다. recv/send/resize/close 폴링 모델.
    def _pod_exec(self):
        if not hasattr(self, '_polaris_pod_exec_mgr'):
            from src.pod_exec import PodExecManager
            self._polaris_pod_exec_mgr = PodExecManager()
        return self._polaris_pod_exec_mgr

    def start_pod_exec(self, namespace: str, pod: str, container: str = '',
                       shell: str = '', cols: int = 80, rows: int = 24) -> dict:
        """파드에 내장 셸(exec) 세션 열기. xterm.js 가 session_id 로 통신."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        return self._pod_exec().start(
            self.k8s.kubeconfig, namespace, pod,
            container=container, shell=shell, cols=cols, rows=rows)

    def recv_pod_exec(self, session_id: str) -> dict:
        return self._pod_exec().recv(session_id)

    def get_pod_exec_snapshot(self, session_id: str) -> dict:
        return self._pod_exec().snapshot(session_id)

    def send_pod_exec(self, session_id: str, data: str) -> dict:
        return self._pod_exec().send(session_id, data)

    def resize_pod_exec(self, session_id: str, cols: int, rows: int) -> dict:
        return self._pod_exec().resize(session_id, cols, rows)

    def close_pod_exec(self, session_id: str) -> dict:
        return self._pod_exec().close(session_id)

    def list_pod_exec_sessions(self) -> list:
        return self._pod_exec().list()

    # port-forward session management


def _tools_missing() -> str:
    from src.tools import KUBECTL_MISSING
    return KUBECTL_MISSING
