"""DetailsMixin — 파드 메트릭 + 리소스 상세 (events / logs / yaml / describe).
"""
from datetime import datetime, timezone

from src.tools import _run_kubectl
from src.k8s import (
    _age,
    _is_secret_kind, _redact_secret_yaml, _redact_secret_describe,
    _resource_event_field_selector, _normalize_log_source_type,
    _WORKLOAD_LOG_TYPES,
)


class DetailsMixin:
    def get_pod_metrics(self, ns: str, name: str):
        """단일 파드의 현재 메트릭 — MetricsTab 폴링 대상."""
        return self.k8s.get_pod_metrics(ns, name)


    def get_pod_detail(self, ns: str, name: str):
        """파드 상세 정보 (컨테이너·컨디션·볼륨)."""
        if not self.k8s.core:
            return {'ok': False, 'error': '연결되지 않음'}
        try:
            p = self.k8s.core.read_namespaced_pod(name=name, namespace=ns)
            spec_map = {c.name: c for c in (p.spec.containers or [])}

            containers = []
            for cs in (p.status.container_statuses or []):
                state = 'Unknown'
                if cs.state:
                    if cs.state.running:
                        state = 'Running'
                    elif cs.state.terminated:
                        r = cs.state.terminated.reason or ''
                        state = f'Terminated ({r})' if r else 'Terminated'
                    elif cs.state.waiting:
                        r = cs.state.waiting.reason or ''
                        state = f'Waiting ({r})' if r else 'Waiting'
                sc = spec_map.get(cs.name)
                containers.append({
                    'name':     cs.name,
                    'image':    sc.image if sc else '',
                    'ready':    cs.ready,
                    'restarts': cs.restart_count or 0,
                    'state':    state,
                })

            init_containers = []
            for cs in (p.status.init_container_statuses or []):
                state = 'Unknown'
                if cs.state:
                    if cs.state.running:      state = 'Running'
                    elif cs.state.terminated: state = 'Completed'
                    elif cs.state.waiting:
                        r = cs.state.waiting.reason or ''
                        state = f'Waiting ({r})' if r else 'Waiting'
                init_containers.append({
                    'name': cs.name, 'ready': cs.ready,
                    'restarts': cs.restart_count or 0, 'state': state,
                })

            conditions = [{'type': c.type, 'status': c.status, 'reason': c.reason or ''}
                          for c in (p.status.conditions or [])]
            volumes = [v.name for v in (p.spec.volumes or [])]
            labels  = {k: v for k, v in (p.metadata.labels or {}).items()}

            return {
                'ok':              True,
                'name':            p.metadata.name,
                'namespace':       p.metadata.namespace,
                'node':            p.spec.node_name or 'N/A',
                'pod_ip':          p.status.pod_ip or 'N/A',
                'host_ip':         p.status.host_ip or 'N/A',
                'phase':           p.status.phase or 'Unknown',
                'qos':             p.status.qos_class or 'N/A',
                'start_time':      str(p.status.start_time)[:19] if p.status.start_time else 'N/A',
                'age':             _age(p.metadata.creation_timestamp),
                'labels':          labels,
                'containers':      containers,
                'init_containers': init_containers,
                'conditions':      conditions,
                'volumes':         volumes,
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def get_resource_events(self, kind: str, ns: str, name: str):
        """리소스 이벤트 목록."""
        if not self.k8s.core or not ns:
            return []
        try:
            evts = self.k8s.core.list_namespaced_event(
                namespace=ns,
                field_selector=_resource_event_field_selector(kind, name),
            ).items

            def _ts(e):
                t = e.last_timestamp or e.event_time or e.metadata.creation_timestamp
                return t if t else datetime.min.replace(tzinfo=timezone.utc)

            return [{
                'type':    e.type or '',
                'reason':  e.reason or '',
                'message': (e.message or '')[:300],
                'count':   e.count or 1,
                'age':     _age(_ts(e)),
                'source':  (e.source.component if e.source and e.source.component else ''),
            } for e in sorted(evts, key=_ts, reverse=True)[:30]]
        except Exception:
            return []


    def get_resource_logs(self, ns: str, name: str,
                          container: str = '', tail: int = 200):
        """파드 로그 (kubectl logs)."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음', 'logs': ''}
        args = ['logs', f'-n={ns}', name, f'--tail={tail}']
        if container:
            args += ['-c', container]
        out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
        if err and not out:
            return {'ok': False, 'error': err, 'logs': ''}
        return {'ok': True, 'logs': out, 'error': err or ''}

    # UI 내부 리소스 키 → kubectl 리소스 타입 이름 정규화

    _KUBECTL_KIND_MAP = {
        'pvcs': 'persistentvolumeclaims',
        'pvs':  'persistentvolumes',
    }


    def get_resource_yaml(self, kind: str, ns: str, name: str):
        """kubectl get <kind> <name> -o yaml."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음', 'yaml': ''}
        kubectl_kind = self._KUBECTL_KIND_MAP.get(kind, kind)
        args = ['get', kubectl_kind, name, '-o', 'yaml'] + (['-n', ns] if ns else [])
        out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
        if err and not out:
            return {'ok': False, 'error': err, 'yaml': ''}
        # 보안 — Secret 의 data / stringData 평문(=base64 토큰·TLS key 등) UI 노출 차단
        if _is_secret_kind(kind):
            out = _redact_secret_yaml(out)
        return {'ok': True, 'yaml': out, 'error': err or ''}


    def get_resource_describe(self, kind: str, ns: str, name: str):
        """kubectl describe <kind> <name>."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음', 'describe': ''}
        kubectl_kind = self._KUBECTL_KIND_MAP.get(kind, kind)
        args = ['describe', kubectl_kind, name] + (['-n', ns] if ns else [])
        out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
        if err and not out:
            return {'ok': False, 'error': err, 'describe': ''}
        # 보안 — describe 자체는 길이만 노출하지만, Annotations/Token 영역 보강 마스킹
        if _is_secret_kind(kind):
            out = _redact_secret_describe(out)
        return {'ok': True, 'describe': out, 'error': err or ''}

