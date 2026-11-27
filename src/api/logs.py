"""LogsMixin — kubectl logs --follow 로그 스트리밍 4 메서드.
"""
import threading
import subprocess
import uuid
from collections import deque

from src.tools import _find_kubectl, _NO_WINDOW
from src.k8s import _build_pod_log_args, _normalize_log_source_type, _WORKLOAD_LOG_TYPES
from src._state import _log_jobs

_MAX_PENDING_LINES = 50_000


class LogsMixin:
    def start_log_stream(self, ns: str, name: str, container: str = '',
                         tail: int = 200, follow: bool = False,
                         source_type: str = 'pod'):
        """파드/워크로드/인그레스 로그 스트리밍 시작. job_id 반환."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        kubectl = _find_kubectl(self.k8s.kubeconfig)
        if not kubectl:
            return {'ok': False, 'error': _tools_missing()}

        # kubeconfig를 지금 캡처 — 클러스터 전환 후 백그라운드 스레드가 잘못된 값을 쓰는 것 방지
        kubeconfig = self.k8s.kubeconfig

        source_type = _normalize_log_source_type(source_type)
        if source_type == 'ingress':
            targets, hint = self.k8s.get_ingress_log_pods()
            if not targets:
                return {'ok': False, 'error': hint or 'Ingress controller 파드를 찾을 수 없습니다.'}
            header = f'[Ingress 통합 로그] controller pod {len(targets)}개: '
            header += ', '.join(f'{n}/{p}' for n, p in targets)
            return self._start_pod_log_job(
                kubectl, targets, tail, follow,
                all_containers=True, prefix=True, header=header,
                _kubeconfig=kubeconfig,
            )

        if source_type in _WORKLOAD_LOG_TYPES:
            pods, hint = self.k8s.get_workload_pods(ns, source_type, name)
            if not pods:
                msg = f'파드를 찾을 수 없습니다: {source_type}/{name}'
                if hint:
                    msg += f'\n{hint}'
                return {'ok': False, 'error': msg}
            targets = [(ns, p) for p in pods]
            header = f'[워크로드 로그] {source_type}/{name} -> 파드 {len(pods)}개: '
            header += ', '.join(pods)
            return self._start_pod_log_job(
                kubectl, targets, tail, follow,
                all_containers=True, prefix=True, header=header,
                _kubeconfig=kubeconfig,
            )

        if source_type != 'pod':
            return {'ok': False, 'error': f'지원하지 않는 로그 대상: {source_type}'}
        return self._start_pod_log_job(
            kubectl, [(ns, name)], tail, follow,
            container=container, all_containers=False, prefix=False,
            _kubeconfig=kubeconfig,
        )


    def _start_pod_log_job(self, kubectl: str, targets: list[tuple[str, str]],
                           tail: int = 200, follow: bool = False,
                           container: str = '', all_containers: bool = False,
                           prefix: bool = False, header: str = '',
                           _kubeconfig: str = ''):
        import uuid
        # kubeconfig를 호출 시점에 캡처 (클러스터 전환 후 클로저가 잘못된 값을 참조하는 버그 방지)
        kubeconfig = _kubeconfig or (self.k8s.kubeconfig if self.k8s else '')
        job_id = str(uuid.uuid4())
        job = {
            'lines': [],
            'procs': [],
            'stopped': False,
            'error': None,
            'remaining': len(targets),
            'lock': threading.Lock(),
            'kubeconfig': kubeconfig,
        }
        if header:
            job['lines'].append(header)
        _log_jobs[job_id] = job

        def run_one(target_ns: str, pod_name: str):
            cmd = [kubectl, '--kubeconfig', kubeconfig] + _build_pod_log_args(
                target_ns, pod_name, container, tail, follow, all_containers=all_containers)
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    creationflags=_NO_WINDOW,
                )
                with job['lock']:
                    job['procs'].append(proc)
                    stopped_early = job['stopped']
                if stopped_early:
                    # 등록 전에 [중지] 가 눌렸다 — 예전엔 이 kubectl 이 끝없이 남았다(v1.5.28 검토)
                    proc.terminate()
                    return
                for line in proc.stdout:
                    if job['stopped']:
                        break
                    stripped = line.rstrip('\n\r')
                    if stripped:
                        if prefix:
                            stripped = f'[{target_ns}/{pod_name}] {stripped}'
                        with job['lock']:
                            job['lines'].append(stripped)
                            # 화면이 가져가지 않는 동안(창 숨김 · 멈춤) 무한히 쌓이지 않게 — 오래된 것부터 버린다
                            if len(job['lines']) > _MAX_PENDING_LINES:
                                del job['lines'][:len(job['lines']) - _MAX_PENDING_LINES]
                proc.wait()
                if proc.returncode != 0 and not job.get('error'):
                    job['error'] = f'{target_ns}/{pod_name} 로그 스트림이 종료되었습니다. exit={proc.returncode}'
            except Exception as e:
                job['error'] = f'{target_ns}/{pod_name}: {e}'
            finally:
                with job['lock']:
                    job['remaining'] -= 1
                    if job['remaining'] <= 0:
                        job['stopped'] = True

        for target_ns, pod_name in targets:
            threading.Thread(target=run_one, args=(target_ns, pod_name), daemon=True).start()
        return {'ok': True, 'job_id': job_id}


    def get_log_chunk(self, job_id: str):
        """누적된 로그 라인 반환 후 버퍼 비움."""
        job = _log_jobs.get(job_id)
        if not job:
            return {'ok': False, 'error': 'Job not found', 'lines': [], 'stopped': True}
        with job['lock']:
            lines = job['lines']
            job['lines'] = []
        if job['stopped']:
            # 끝난 작업은 마지막으로 가져갈 때 지운다 — 예전엔 중지를 누르지 않으면 영영 남았다
            if all(p.poll() is not None for p in job.get('procs') or []):
                _log_jobs.pop(job_id, None)
        return {
            'ok':      True,
            'lines':   lines,
            'stopped': job['stopped'],
            'error':   job.get('error'),
        }


    def stop_log_stream(self, job_id: str):
        """로그 스트리밍 중단."""
        job = _log_jobs.pop(job_id, None)
        if not job:
            return {'ok': False}
        with job['lock']:
            job['stopped'] = True
            procs = list(job.get('procs') or [])
        if job.get('proc'):
            procs.append(job.get('proc'))
        for proc in procs:
            try:
                proc.terminate()
            except Exception:
                pass
        return {'ok': True}


    def _stop_log_streams_for_kubeconfig(self, kubeconfig: str):
        """클러스터 탭을 닫을 때 그 클러스터의 로그 스트림(kubectl logs -f)도 끝낸다(v1.5.28 검토)."""
        if not kubeconfig:
            return
        for jid, job in list(_log_jobs.items()):
            if job.get('kubeconfig') == kubeconfig:
                self.stop_log_stream(jid)


def _tools_missing() -> str:
    from src.tools import KUBECTL_MISSING
    return KUBECTL_MISSING
