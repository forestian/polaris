"""PortForwardMixin — kubectl port-forward 세션 8 메서드.
"""
import os
import re
import sys
import time
import threading
import subprocess
import uuid
from collections import deque
from datetime import datetime, timezone

from src.tools import _find_kubectl, _NO_WINDOW
from src.k8s import _build_port_forward_spec, _normalize_port_forward_kind, _coerce_port
from src._state import _port_forward_jobs


class PortForwardMixin:
    def _serialize_port_forward_job(self, job: dict) -> dict:
        lock = job.get('lock')
        if lock:
            lock.acquire()
        try:
            proc = job.get('proc')
            if proc and job.get('status') in ('starting', 'running') and proc.poll() is not None:
                if job.get('stopped'):
                    job['status'] = 'stopped'
                elif proc.returncode == 0:
                    job['status'] = 'stopped'
                else:
                    job['status'] = 'error'
                    job['error'] = job.get('error') or f'kubectl exited with code {proc.returncode}'
            return {
                'id': job.get('id'),
                'cluster_id': job.get('cluster_id', ''),
                'cluster_name': job.get('cluster_name', ''),
                'kind': job.get('kind', ''),
                'namespace': job.get('namespace', ''),
                'name': job.get('name', ''),
                'resource': job.get('resource', ''),
                'local_port': job.get('local_port'),
                'remote_port': job.get('remote_port'),
                'status': job.get('status', 'unknown'),
                'pid': job.get('pid'),
                'started_at': job.get('started_at', ''),
                'last_event': job.get('last_event', ''),
                'error': job.get('error'),
                'connections': job.get('connections', 0),
                'lines': list(job.get('lines', []))[-80:],
                'flow': f"localhost:{job.get('local_port')} -> {job.get('resource')}:{job.get('remote_port')}",
            }
        finally:
            if lock:
                lock.release()


    def _terminate_port_forward_job(self, job_id: str, remove: bool = True) -> bool:
        job = _port_forward_jobs.pop(job_id, None) if remove else _port_forward_jobs.get(job_id)
        if not job:
            return False
        proc = job.get('proc')
        with job.get('lock', threading.Lock()):
            job['stopped'] = True
            job['status'] = 'stopped'
            job['last_event'] = 'Stopped by user'
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        return True


    def _stop_port_forward_jobs_for_cluster(self, cluster_id: str = ''):
        ids = [
            jid for jid, job in list(_port_forward_jobs.items())
            if not cluster_id or job.get('cluster_id') == cluster_id
        ]
        for jid in ids:
            self._terminate_port_forward_job(jid, remove=True)


    def get_port_forward_targets(self, ns: str = ''):
        if not self.k8s.connected or not self.k8s.core:
            return {'ok': False, 'error': 'cluster is not connected', 'pods': [], 'services': []}
        ns = str(ns or '').strip()
        if not ns or ns.lower() in ('all namespaces', 'all'):
            return {'ok': False, 'error': 'namespace is required', 'pods': [], 'services': []}

        def pod_ports(pod):
            ports = []
            for c in (pod.spec.containers or []):
                for p in (c.ports or []):
                    port = getattr(p, 'container_port', None)
                    if not port:
                        continue
                    name = getattr(p, 'name', '') or ''
                    proto = getattr(p, 'protocol', '') or 'TCP'
                    label = f'{name} ' if name else ''
                    ports.append({
                        'name': name,
                        'port': int(port),
                        'protocol': proto,
                        'container': c.name,
                        'label': f'{label}{port}/{proto}',
                    })
            return ports

        def service_ports(svc):
            ports = []
            for p in (svc.spec.ports or []):
                port = getattr(p, 'port', None)
                if not port:
                    continue
                name = getattr(p, 'name', '') or ''
                proto = getattr(p, 'protocol', '') or 'TCP'
                target = getattr(p, 'target_port', '') or ''
                suffix = f' -> {target}' if target and str(target) != str(port) else ''
                label = f'{name} ' if name else ''
                ports.append({
                    'name': name,
                    'port': int(port),
                    'target_port': str(target) if target else '',
                    'protocol': proto,
                    'label': f'{label}{port}/{proto}{suffix}',
                })
            return ports

        try:
            pods = self.k8s.core.list_namespaced_pod(ns).items
            services = self.k8s.core.list_namespaced_service(ns).items
            return {
                'ok': True,
                'pods': [{
                    'name': p.metadata.name,
                    'namespace': p.metadata.namespace,
                    'status': p.status.phase or 'Unknown',
                    'ports': pod_ports(p),
                } for p in sorted(pods, key=lambda x: x.metadata.name or '')],
                'services': [{
                    'name': s.metadata.name,
                    'namespace': s.metadata.namespace,
                    'type': s.spec.type or '',
                    'ports': service_ports(s),
                } for s in sorted(services, key=lambda x: x.metadata.name or '')],
            }
        except Exception as e:
            return {'ok': False, 'error': str(e), 'pods': [], 'services': []}


    def start_port_forward(self, kind: str, ns: str, name: str, local_port, remote_port):
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': 'cluster is not connected'}
        kubectl = _find_kubectl()
        if not kubectl:
            return {'ok': False, 'error': 'kubectl was not found'}
        try:
            spec = _build_port_forward_spec(kind, ns, name, local_port, remote_port)
        except ValueError as e:
            return {'ok': False, 'error': str(e)}

        import uuid
        job_id = str(uuid.uuid4())
        cluster_id = self._active_id or ''
        cluster_info = self._clusters.get(cluster_id, {})
        env = {**os.environ, 'KUBECONFIG': self.k8s.kubeconfig}
        cmd = [kubectl] + spec['args']

        job = {
            'id': job_id,
            'cluster_id': cluster_id,
            'cluster_name': cluster_info.get('display_name', ''),
            'kind': spec['kind'],
            'namespace': spec['namespace'],
            'name': spec['name'],
            'resource': spec['resource'],
            'local_port': spec['local_port'],
            'remote_port': spec['remote_port'],
            'status': 'starting',
            'pid': None,
            'started_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'last_event': 'Starting kubectl port-forward',
            'lines': [],
            'error': None,
            'connections': 0,
            'stopped': False,
            'lock': threading.Lock(),
        }

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                creationflags=_NO_WINDOW,
            )
        except Exception as e:
            return {'ok': False, 'error': str(e)}

        job['proc'] = proc
        job['pid'] = proc.pid
        _port_forward_jobs[job_id] = job

        def append_line(line: str):
            line = (line or '').rstrip('\r\n')
            if not line:
                return
            lower = line.lower()
            with job['lock']:
                job['lines'].append(line)
                del job['lines'][:-200]
                job['last_event'] = line
                if 'forwarding from' in lower:
                    job['status'] = 'running'
                if 'handling connection' in lower:
                    job['status'] = 'running'
                    job['connections'] = int(job.get('connections') or 0) + 1
                if any(token in lower for token in ('error', 'unable', 'failed', 'address already in use')):
                    if not job.get('stopped'):
                        job['status'] = 'error'
                        job['error'] = line

        def reader():
            try:
                if proc.stdout:
                    for line in proc.stdout:
                        append_line(line)
                        if job.get('stopped'):
                            break
            except Exception as e:
                with job['lock']:
                    job['status'] = 'error'
                    job['error'] = str(e)

        def monitor():
            proc.wait()
            with job['lock']:
                if job.get('stopped'):
                    job['status'] = 'stopped'
                    return
                if proc.returncode == 0:
                    job['status'] = 'stopped'
                    job['last_event'] = job.get('last_event') or 'Port-forward stopped'
                else:
                    job['status'] = 'error'
                    job['error'] = job.get('error') or f'kubectl exited with code {proc.returncode}'

        threading.Thread(target=reader, daemon=True).start()
        threading.Thread(target=monitor, daemon=True).start()
        return {'ok': True, 'session': self._serialize_port_forward_job(job)}


    def get_port_forwards(self):
        sessions = [self._serialize_port_forward_job(job) for job in list(_port_forward_jobs.values())]
        sessions.sort(key=lambda s: s.get('started_at') or '', reverse=True)
        return {'ok': True, 'sessions': sessions}


    def stop_port_forward(self, job_id: str):
        if self._terminate_port_forward_job(str(job_id or ''), remove=True):
            return {'ok': True}
        return {'ok': False, 'error': 'Port-forward session not found'}


    def stop_all_port_forwards(self):
        self._stop_port_forward_jobs_for_cluster('')
        return {'ok': True}

