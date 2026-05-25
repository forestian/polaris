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
    _kubectl_subcommand_index,
)
from src.k8s import _build_pod_exec_args


class TerminalMixin:
    _STREAMING_SUBCMDS = frozenset(['port-forward', 'watch'])


    def run_kubectl(self, cmd: str):
        if not self.k8s.kubeconfig:
            return {'output': '', 'error': '클러스터에 연결되지 않았습니다.'}
        kubectl = _find_kubectl()
        if not kubectl:
            return {'output': '', 'error': 'kubectl을 찾을 수 없습니다.'}
        try:
            args = _parse_kubectl_command(cmd)
        except ValueError as e:
            return {'output': '', 'error': f'kubectl 명령 파싱 실패: {e}'}
        if not args:
            return {'output': '', 'error': 'kubectl 명령을 입력하세요.'}

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

                def _read(pipe, buf):
                    try:
                        for ln in iter(pipe.readline, ''):
                            buf.append(ln)
                    except Exception:
                        pass

                t_out = _th.Thread(target=_read, args=(proc.stdout, out_lines), daemon=True)
                t_err = _th.Thread(target=_read, args=(proc.stderr, err_lines), daemon=True)
                t_out.start(); t_err.start()
                t_out.join(timeout=3); t_err.join(timeout=0.1)

                if proc.poll() is not None:
                    # 이미 종료 → 오류
                    return {
                        'output': ''.join(out_lines),
                        'error': ''.join(err_lines),
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


    def launch_k9s(self):
        k9s = _find_k9s()
        if not k9s:
            return {'ok': False, 'error': 'k9s 실행파일을 찾을 수 없습니다.\n~/.kube/k9s.exe 또는 PATH에 k9s를 설치하세요.'}
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


    def open_pod_shell(self, ns: str, name: str, container: str = ''):
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        kubectl = _find_kubectl()
        if not kubectl:
            return {'ok': False, 'error': 'kubectl을 찾을 수 없습니다.'}
        try:
            args = _build_pod_exec_args(ns, name, container)
            cmd, terminal = _build_pod_shell_command(
                kubectl, args, self.k8s.kubeconfig or '', ns, name)
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            return {'ok': True, 'command': 'kubectl ' + ' '.join(args), 'terminal': terminal}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # port-forward session management

