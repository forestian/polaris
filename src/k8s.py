"""K8sManager 클래스 + Kubernetes 도메인 헬퍼.

이 모듈은 kubernetes Python 라이브러리에 의존합니다. PolarisAPI 의 모든 K8s
호출은 이 모듈을 통해 이루어집니다.

구성:
  - 파싱 헬퍼: _age, _parse_cpu, _parse_mem, _pct, _build_node_metrics, ...
  - 보안: _redact_secret_yaml, _redact_secret_describe (시크릿 마스킹)
  - 검증: RFC1123 정규식 + _build_pod_exec_args / _build_port_forward_spec
  - ArgoCD spec 빌더
  - K8sManager 클래스: kubernetes 클라이언트 래퍼 (각 리소스 getter)
"""
import re
import os
import json
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.tools import _NO_WINDOW, _find_helm

# ── kubernetes 라이브러리 ─────────────────────────────────────────────────────
try:
    from kubernetes import client as k8s, config as k8s_cfg
    HAS_K8S = True
except ImportError:
    HAS_K8S = False


# ─────────────────────────────────────────────────────────────────────────────
# 파싱 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _age(ts):
    """kubernetes 객체의 creation_timestamp → 경과 시간 문자열."""
    if not ts:
        return 'N/A'
    s = int((datetime.now(timezone.utc) - ts).total_seconds())
    if s < 60:    return f'{s}s'
    if s < 3600:  return f'{s // 60}m'
    if s < 86400: return f'{s // 3600}h'
    return f'{s // 86400}d'


def _jsonpath_get(obj, path):
    """CRD additionalPrinterColumns 의 단순 JSONPath(.a.b.c) 값 추출.

    printer column 의 jsonPath 는 대부분 `.status.phase`, `.spec.replicas`,
    `.metadata.creationTimestamp` 같은 단순 dot 경로. 배열 인덱스나 필터는
    드물어 미지원(빈 문자열 반환). 값이 dict/list 면 빈 문자열.
    """
    if not path:
        return ''
    p = str(path).lstrip('.')
    cur = obj
    for part in p.split('.'):
        if not part:
            continue
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return ''
    if cur is None:
        return ''
    if isinstance(cur, bool):
        return 'true' if cur else 'false'
    if isinstance(cur, (str, int, float)):
        return str(cur)
    return ''   # dict/list 등 복합 타입은 표시 생략


def _parse_ts(value):
    """ISO8601 타임스탬프 문자열(또는 datetime) → tz-aware datetime. 실패 시 None.

    custom object(dict) 의 metadata.creationTimestamp 는 '2024-01-01T00:00:00Z'
    같은 문자열이므로 _age() 에 넘기기 전에 변환한다.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        s = str(value).replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _parse_cpu(s):
    """metrics.k8s.io CPU 값 ('123n', '45m', '0.1') → millicore (int)."""
    if not s:
        return 0
    try:
        if s.endswith('n'):   return int(s[:-1]) // 1_000_000
        if s.endswith('u'):   return int(s[:-1]) // 1_000
        if s.endswith('m'):   return int(s[:-1])
        return int(float(s) * 1000)
    except Exception:
        return 0


def _parse_mem(s):
    """memory 값 ('123Ki', '456Mi', '789') → bytes (int)."""
    if not s:
        return 0
    try:
        units = {
            'Ki': 1024, 'Mi': 1024 ** 2, 'Gi': 1024 ** 3, 'Ti': 1024 ** 4,
            'K':  1000, 'M':  1000 ** 2, 'G':  1000 ** 3, 'T':  1000 ** 4,
        }
        for u, mul in units.items():
            if s.endswith(u):
                return int(s[: -len(u)]) * mul
        return int(s)
    except Exception:
        return 0


def _pct(used, total):
    if not total:
        return None
    return min(round((used or 0) / total * 100), 100)


def _build_node_metrics(items):
    out = []
    for item in items or []:
        usage = item.get('usage', {})
        name = item.get('metadata', {}).get('name', '')
        if not name:
            continue
        out.append({
            'name': name,
            'cpu_m': _parse_cpu(usage.get('cpu', '0')),
            'mem_mi': _parse_mem(usage.get('memory', '0')) // (1024 * 1024),
        })
    return out


def _apply_node_metric(node, metric):
    enriched = dict(node)
    if not metric:
        enriched.update({
            'metrics_available': False,
            'cpu_used_m': 0,
            'mem_used_mi': 0,
            'cpu_pct': None,
            'mem_pct': None,
        })
        return enriched

    cpu_used = int(metric.get('cpu_m') or 0)
    mem_used = int(metric.get('mem_mi') or 0)
    enriched.update({
        'metrics_available': True,
        'cpu_used_m': cpu_used,
        'mem_used_mi': mem_used,
        'cpu_pct': _pct(cpu_used, enriched.get('cpu_alloc_m') or 0),
        'mem_pct': _pct(mem_used, enriched.get('mem_alloc_mi') or 0),
    })
    return enriched


# ─────────────────────────────────────────────────────────────────────────────
# 연결 에러 진단 (사용자 친화적 메시지로 변환)
# ─────────────────────────────────────────────────────────────────────────────

def _diagnose_connect_error(e: Exception, path: str) -> str:
    """연결 실패 원인을 사용자 친화적 메시지로 변환."""
    import ssl
    msg     = str(e)
    msg_low = msg.lower()

    # ── kubeconfig 파일 문제 ──────────────────────────────────────────────────
    if isinstance(e, FileNotFoundError):
        return f'kubeconfig 파일을 찾을 수 없습니다: {path}'

    try:
        import yaml
        if isinstance(e, yaml.YAMLError):
            return 'kubeconfig 파일 형식이 올바르지 않습니다 (YAML 파싱 오류).'
    except ImportError:
        pass

    if HAS_K8S:
        try:
            from kubernetes.config.config_exception import ConfigException
            if isinstance(e, ConfigException):
                if 'no configuration' in msg_low or 'invalid' in msg_low or 'context' in msg_low:
                    return ('kubeconfig 구성 오류입니다.\n'
                            '• 파일에 유효한 컨텍스트가 있는지 확인하세요.\n'
                            f'• 상세: {msg}')
                return f'kubeconfig 구성 오류: {msg}'
        except ImportError:
            pass

    # ── SSL / TLS 인증서 문제 ─────────────────────────────────────────────────
    if isinstance(e, (ssl.SSLError, ssl.SSLCertVerificationError)) or \
            'ssl' in msg_low or 'certificate verify failed' in msg_low:
        return ('TLS/SSL 인증서 오류입니다.\n'
                '• 클러스터 CA 인증서가 kubeconfig에 올바르게 포함되어 있는지 확인하세요.\n'
                '• 자체 서명 인증서라면 insecure-skip-tls-verify 옵션을 확인하세요.')

    # ── 인증 / 권한 문제 ──────────────────────────────────────────────────────
    if HAS_K8S:
        try:
            from kubernetes.client.exceptions import ApiException
            if isinstance(e, ApiException):
                if e.status == 401:
                    return ('인증 실패 (401 Unauthorized).\n'
                            '• 클러스터 자격증명(토큰/인증서)이 만료됐거나 올바르지 않습니다.\n'
                            '• kubeconfig를 다시 발급받으세요.')
                if e.status == 403:
                    return ('권한 없음 (403 Forbidden).\n'
                            '• 현재 사용자에게 클러스터 접근 권한이 없습니다.\n'
                            '• 클러스터 관리자에게 RBAC 권한을 요청하세요.')
                return f'API 오류 ({e.status}): {e.reason}'
        except ImportError:
            pass

    # 지연 import (circular import 방지)
    from src.tools import _extract_host_port

    # ── 연결 타임아웃 ─────────────────────────────────────────────────────────
    if isinstance(e, TimeoutError) or 'timed out' in msg_low or 'timeout' in msg_low:
        hp = _extract_host_port(msg)
        return (f'연결 시간 초과 ({hp}).\n'
                '• 서버가 응답하지 않습니다. 네트워크/VPN 연결 상태를 확인하세요.\n'
                '• 방화벽이 해당 포트(일반적으로 6443)를 차단하고 있을 수 있습니다.')

    # ── 포트 접근 불가 / 연결 거부 ───────────────────────────────────────────
    if ('connection refused' in msg_low or 'newconnectionerror' in msg_low
            or 'max retries exceeded' in msg_low or 'failed to establish' in msg_low
            or 'nodename nor servname' in msg_low or 'name or service not known' in msg_low):
        hp = _extract_host_port(msg)
        return (f'서버({hp})에 접근할 수 없습니다.\n'
                '• 네트워크/VPN 연결 상태를 확인하세요.\n'
                f'• 방화벽이 {hp} 포트를 허용하는지 확인하세요.\n'
                '• kubeconfig의 server 주소가 올바른지 확인하세요.\n'
                '• kubectl cluster-info 로 클러스터 상태를 직접 확인해보세요.')

    # ── DNS 해석 실패 ─────────────────────────────────────────────────────────
    if 'getaddrinfo' in msg_low or 'dns' in msg_low or 'name resolution' in msg_low:
        hp = _extract_host_port(msg)
        return (f'DNS 해석 실패 ({hp}).\n'
                '• 호스트명을 IP로 해석할 수 없습니다.\n'
                '• VPN 연결 여부 및 DNS 설정을 확인하세요.')

    # ── 기타 ─────────────────────────────────────────────────────────────────
    return f'연결 실패: {msg}'


# ─────────────────────────────────────────────────────────────────────────────
# RFC1123 검증 + Secret 마스킹
# ─────────────────────────────────────────────────────────────────────────────

# RFC1123 DNS label (네임스페이스 / 컨테이너) : 1~63자, 영소문자·숫자·하이픈
# RFC1123 DNS subdomain (파드 이름) : 최대 253자, 점(.) 포함 가능
_RFC1123_DNS_LABEL     = re.compile(r'^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$')
_RFC1123_DNS_SUBDOMAIN = re.compile(
    r'^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?(\.[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?)*$'
)


def _is_secret_kind(kind: str) -> bool:
    """Kubernetes Secret 리소스 여부 (UI alias 도 포함)."""
    return (kind or '').lower().rstrip('s') == 'secret'


def _redact_secret_yaml(yaml_text: str) -> str:
    """Secret YAML 의 data: / stringData: 블록 값을 '[REDACTED]' 로 치환.

    base64 인코딩된 token / TLS key / 패스워드가 UI 에 평문 노출되지 않게 한다.
    파싱 실패 시 입력 그대로 반환 (안전한 폴백).
    """
    if not yaml_text or 'kind: Secret' not in yaml_text:
        return yaml_text
    try:
        lines = yaml_text.split('\n')
        out = []
        in_block = False
        block_indent = -1
        for line in lines:
            stripped_r = line.rstrip()
            leading = len(stripped_r) - len(stripped_r.lstrip(' '))
            bare = stripped_r.strip()
            # 'data:' / 'stringData:' 블록 시작 (key 만 있고 값 비어있는 형태)
            if (bare == 'data:' or bare == 'stringData:' or
                bare == 'data: {}' or bare == 'stringData: {}'):
                in_block = bare in ('data:', 'stringData:')
                block_indent = leading
                out.append(line)
                continue
            if in_block:
                if not bare:
                    out.append(line)
                    continue
                # 블록 외부로 나옴 (같은/짧은 들여쓰기)
                if leading <= block_indent:
                    in_block = False
                    out.append(line)
                    continue
                # 블록 내부 'key: value' → 값 마스킹
                if ':' in bare:
                    key = bare.split(':', 1)[0].rstrip()
                    out.append(' ' * leading + f'{key}: "[REDACTED]"')
                    continue
            out.append(line)
        return '\n'.join(out)
    except Exception:
        return yaml_text


# describe 출력에서 token / cert / key 가 value 형태로 노출되는 라인 패턴.
_DESCRIBE_SENSITIVE = re.compile(
    r'(?im)^(\s*(?:[\w\-./]*?(?:token|password|secret|cert|key|credential)[\w\-./]*?)\s*:)\s*[^\s].*$'
)


def _redact_secret_describe(text: str) -> str:
    """kubectl describe secret 출력에서 token/password/cert/key 가 들어간 라인의
    값을 마스킹. describe 의 'Data' 섹션은 길이만 노출하지만,
    Annotations/Events 등에 평문이 새는 케이스 보강."""
    if not text:
        return text
    try:
        return _DESCRIBE_SENSITIVE.sub(r'\1 [REDACTED]', text)
    except Exception:
        return text


# ─────────────────────────────────────────────────────────────────────────────
# 파드 exec / 로그 args 빌더
# ─────────────────────────────────────────────────────────────────────────────

def _build_pod_exec_args(ns: str, name: str, container: str = '') -> list[str]:
    ns = str(ns or '').strip()
    name = str(name or '').strip()
    container = str(container or '').strip()
    if not ns or not name:
        raise ValueError('namespace and pod name are required')
    # 보안 — terminal/cmd start title 등에 사용자 제어 문자열이 그대로 들어가지 않도록
    # K8s RFC1123 명명 규칙으로 화이트리스트 검증.
    if len(ns) > 63 or not _RFC1123_DNS_LABEL.match(ns):
        raise ValueError(f'invalid namespace name: {ns!r}')
    if len(name) > 253 or not _RFC1123_DNS_SUBDOMAIN.match(name):
        raise ValueError(f'invalid pod name: {name!r}')
    if container and (len(container) > 63 or not _RFC1123_DNS_LABEL.match(container)):
        raise ValueError(f'invalid container name: {container!r}')
    args = ['exec', '-it', '-n', ns, name]
    if container:
        args.extend(['-c', container])
    args.extend(['--', 'sh'])
    return args


_LOG_SOURCE_ALIASES = {
    'pod': 'pod',
    'pods': 'pod',
    'deployment': 'deployment',
    'deployments': 'deployment',
    'deploy': 'deployment',
    'deploys': 'deployment',
    'statefulset': 'statefulset',
    'statefulsets': 'statefulset',
    'sts': 'statefulset',
    'replicaset': 'replicaset',
    'replicasets': 'replicaset',
    'rs': 'replicaset',
    'daemonset': 'daemonset',
    'daemonsets': 'daemonset',
    'ds': 'daemonset',
    'job': 'job',
    'jobs': 'job',
    'ingress': 'ingress',
    'ingresses': 'ingress',
}

_WORKLOAD_LOG_TYPES = {'deployment', 'statefulset', 'replicaset', 'daemonset', 'job'}


def _normalize_log_source_type(source_type: str) -> str:
    key = str(source_type or 'pod').strip().lower()
    return _LOG_SOURCE_ALIASES.get(key, key)


def _build_pod_log_args(ns: str, name: str, container: str = '',
                        tail: int = 200, follow: bool = False,
                        all_containers: bool = False) -> list[str]:
    name = str(name or '').strip()
    if not name:
        raise ValueError('pod name is required')
    try:
        tail = max(1, int(tail))
    except Exception:
        tail = 200
    args = ['logs', name, f'--tail={tail}']
    if ns:
        args.extend(['-n', str(ns).strip()])
    if all_containers:
        args.append('--all-containers=true')
    elif container:
        args.extend(['-c', str(container).strip()])
    if follow:
        args.append('--follow')
    return args


def _is_ingress_controller_pod(name: str, labels: dict | None = None) -> bool:
    text = str(name or '').lower()
    label_text = ' '.join(f'{k}={v}' for k, v in (labels or {}).items()).lower()
    haystack = f'{text} {label_text}'
    keywords = ('ingress', 'traefik', 'contour', 'istio-ingressgateway')
    return any(kw in haystack for kw in keywords)


# ─────────────────────────────────────────────────────────────────────────────
# port-forward spec 빌더
# ─────────────────────────────────────────────────────────────────────────────

_PORT_FORWARD_KIND_ALIASES = {
    'pod': 'pod',
    'pods': 'pod',
    'service': 'service',
    'services': 'service',
    'svc': 'service',
    'svcs': 'service',
}


def _normalize_port_forward_kind(kind: str) -> str:
    key = str(kind or 'service').strip().lower()
    normalized = _PORT_FORWARD_KIND_ALIASES.get(key)
    if not normalized:
        raise ValueError('kind must be service or pod')
    return normalized


def _coerce_port(value, label: str) -> int:
    try:
        port = int(str(value).strip())
    except Exception as exc:
        raise ValueError(f'{label} port must be a number') from exc
    if port < 1 or port > 65535:
        raise ValueError(f'{label} port must be between 1 and 65535')
    return port


def _build_port_forward_spec(kind: str, namespace: str, name: str,
                             local_port, remote_port) -> dict:
    normalized = _normalize_port_forward_kind(kind)
    namespace = str(namespace or '').strip()
    name = str(name or '').strip()
    if not namespace:
        raise ValueError('namespace is required')
    if not name:
        raise ValueError('target name is required')

    remote = _coerce_port(remote_port, 'remote')
    local_blank = local_port is None or str(local_port).strip() == ''
    local = remote if local_blank else _coerce_port(local_port, 'local')
    prefix = 'svc' if normalized == 'service' else 'pod'
    resource = f'{prefix}/{name}'
    return {
        'kind': normalized,
        'namespace': namespace,
        'name': name,
        'resource': resource,
        'local_port': local,
        'remote_port': remote,
        'args': ['-n', namespace, 'port-forward', resource, f'{local}:{remote}'],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ArgoCD spec 빌더
# ─────────────────────────────────────────────────────────────────────────────

def _clean_argo_sources(sources) -> list[dict]:
    cleaned = []
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        item = {}
        for key in (
            'repoURL', 'path', 'chart', 'targetRevision', 'helm', 'kustomize',
            'directory', 'plugin', 'ref',
        ):
            if key in src and src[key] not in (None, ''):
                item[key] = src[key]
        if item.get('repoURL'):
            cleaned.append(item)
    return cleaned


def _argo_sources_from_spec(spec: dict) -> list[dict]:
    if isinstance(spec.get('sources'), list) and spec.get('sources'):
        return _clean_argo_sources(spec.get('sources'))
    source = spec.get('source')
    return _clean_argo_sources([source]) if isinstance(source, dict) else []


def _argo_primary_source(spec: dict) -> dict:
    sources = _argo_sources_from_spec(spec)
    return sources[0] if sources else {}


def _build_argocd_spec(project: str, repo_url: str, path: str, revision: str,
                       dest_ns: str, dest_server: str, sync_policy=None,
                       sources=None) -> dict:
    spec = {
        'project': project or 'default',
        'destination': {'server': dest_server, 'namespace': dest_ns},
        'syncPolicy': sync_policy or {},
    }
    clean_sources = _clean_argo_sources(sources)
    if clean_sources:
        spec['sources'] = clean_sources
    else:
        source = {
            'repoURL': repo_url,
            'targetRevision': revision or 'HEAD',
        }
        if path:
            source['path'] = path
        spec['source'] = source
    return spec


def _build_argocd_sync_operation(is_multi_source: bool = False) -> dict:
    sync = {'prune': False}
    if not is_multi_source:
        sync['revision'] = 'HEAD'
    return {
        'operation': {
            'sync': sync,
            'initiatedBy': {'username': 'polaris'},
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 리소스 이벤트 field selector
# ─────────────────────────────────────────────────────────────────────────────

_RESOURCE_EVENT_KIND_MAP = {
    'pods': 'Pod',
    'pod': 'Pod',
    'deployments': 'Deployment',
    'deployment': 'Deployment',
    'statefulsets': 'StatefulSet',
    'statefulset': 'StatefulSet',
    'daemonsets': 'DaemonSet',
    'daemonset': 'DaemonSet',
    'replicasets': 'ReplicaSet',
    'replicaset': 'ReplicaSet',
    'jobs': 'Job',
    'job': 'Job',
    'cronjobs': 'CronJob',
    'cronjob': 'CronJob',
    'services': 'Service',
    'service': 'Service',
    'ingresses': 'Ingress',
    'ingress': 'Ingress',
    'configmaps': 'ConfigMap',
    'configmap': 'ConfigMap',
    'secrets': 'Secret',
    'secret': 'Secret',
    'pvcs': 'PersistentVolumeClaim',
    'persistentvolumeclaims': 'PersistentVolumeClaim',
}


def _resource_event_field_selector(kind: str, name: str) -> str:
    name = str(name or '').strip()
    mapped = _RESOURCE_EVENT_KIND_MAP.get(str(kind or '').strip().lower())
    if mapped:
        return f'involvedObject.kind={mapped},involvedObject.name={name}'
    return f'involvedObject.name={name}'


# ─────────────────────────────────────────────────────────────────────────────
# 리소스 쓰기 (scale / rollout restart) args 빌더 — 순수 함수, 단위 테스트 대상
# ─────────────────────────────────────────────────────────────────────────────

# UI 내부 리소스 키 → kubectl 정식 리소스 타입
_KUBECTL_KIND_ALIASES = {
    'pods': 'pods', 'pod': 'pods',
    'deployments': 'deployments', 'deployment': 'deployments', 'deploy': 'deployments',
    'statefulsets': 'statefulsets', 'statefulset': 'statefulsets', 'sts': 'statefulsets',
    'daemonsets': 'daemonsets', 'daemonset': 'daemonsets', 'ds': 'daemonsets',
    'replicasets': 'replicasets', 'replicaset': 'replicasets', 'rs': 'replicasets',
    'services': 'services', 'service': 'services', 'svc': 'services',
    'ingresses': 'ingresses', 'ingress': 'ingresses',
    'configmaps': 'configmaps', 'configmap': 'configmaps', 'cm': 'configmaps',
    'secrets': 'secrets', 'secret': 'secrets',
    'jobs': 'jobs', 'job': 'jobs',
    'cronjobs': 'cronjobs', 'cronjob': 'cronjobs', 'cj': 'cronjobs',
    'pvcs': 'persistentvolumeclaims', 'pvc': 'persistentvolumeclaims',
    'pvs': 'persistentvolumes', 'pv': 'persistentvolumes',
    'namespaces': 'namespaces', 'namespace': 'namespaces', 'ns': 'namespaces',
    'nodes': 'nodes', 'node': 'nodes',
}

# scale 가능한 리소스 (replicas 필드를 가진 워크로드)
_SCALABLE_KINDS = {'deployments', 'statefulsets', 'replicasets'}

# rollout restart 가능한 리소스
_RESTARTABLE_KINDS = {'deployments', 'statefulsets', 'daemonsets'}


def _normalize_kubectl_kind(kind: str) -> str:
    """UI 키 → kubectl 정식 리소스 타입. 매핑 없으면 입력값 그대로 (소문자)."""
    key = str(kind or '').strip().lower()
    return _KUBECTL_KIND_ALIASES.get(key, key)


def _build_scale_args(kind: str, ns: str, name: str, replicas) -> list[str]:
    """kubectl scale args 빌더. 검증 실패 시 ValueError."""
    k = _normalize_kubectl_kind(kind)
    if k not in _SCALABLE_KINDS:
        raise ValueError(f'scale 불가 리소스: {kind} (지원: deployment/statefulset/replicaset)')
    name = str(name or '').strip()
    if not name:
        raise ValueError('리소스 이름이 필요합니다.')
    if len(name) > 253 or not _RFC1123_DNS_SUBDOMAIN.match(name):
        raise ValueError(f'잘못된 리소스 이름: {name!r}')
    try:
        r = int(replicas)
    except Exception as exc:
        raise ValueError('replicas 는 정수여야 합니다.') from exc
    if r < 0 or r > 1000:
        raise ValueError('replicas 는 0~1000 범위여야 합니다.')
    ns = str(ns or '').strip()
    if ns and (len(ns) > 63 or not _RFC1123_DNS_LABEL.match(ns)):
        raise ValueError(f'잘못된 네임스페이스: {ns!r}')
    return (['-n', ns] if ns else []) + ['scale', k, name, f'--replicas={r}']


def _build_rollout_restart_args(kind: str, ns: str, name: str) -> list[str]:
    """kubectl rollout restart args 빌더. 검증 실패 시 ValueError."""
    k = _normalize_kubectl_kind(kind)
    if k not in _RESTARTABLE_KINDS:
        raise ValueError(f'restart 불가 리소스: {kind} (지원: deployment/statefulset/daemonset)')
    name = str(name or '').strip()
    if not name:
        raise ValueError('리소스 이름이 필요합니다.')
    if len(name) > 253 or not _RFC1123_DNS_SUBDOMAIN.match(name):
        raise ValueError(f'잘못된 리소스 이름: {name!r}')
    ns = str(ns or '').strip()
    if ns and (len(ns) > 63 or not _RFC1123_DNS_LABEL.match(ns)):
        raise ValueError(f'잘못된 네임스페이스: {ns!r}')
    # kubectl rollout restart deployments/<name> 형태
    return (['-n', ns] if ns else []) + ['rollout', 'restart', f'{k}/{name}']


# ─────────────────────────────────────────────────────────────────────────────
# K8sManager — kubernetes Python 클라이언트 래퍼
# ─────────────────────────────────────────────────────────────────────────────

class K8sManager:
    def __init__(self):
        self.kubeconfig    = None
        self.connected     = False
        self.cluster_info  = {}
        self._api_client   = None   # 인스턴스 전용 ApiClient (전역 config 분리)
        self._temp_kubeconfig = None  # vault content 로 연결 시 세션 임시 파일
        self.core = self.apps = self.batch = self.net = None
        self.custom = self.autoscaling = self.storage = self.rbac = self.policy = None

    # ── 임시 kubeconfig (vault content 복원용) ─────────────────────────────────
    # kubectl 기반 기능(logs/port-forward/terminal 등)이 self.kubeconfig 파일
    # 경로를 필요로 하므로, vault 에 보관된 내용으로 연결할 때는 세션 동안 유지되는
    # 임시 파일을 만들고 disconnect 시 삭제한다.
    def _write_temp_kubeconfig(self, content: str) -> str:
        self._cleanup_temp_kubeconfig()
        fd, tmp = tempfile.mkstemp(suffix='.yaml', prefix='polaris-kc-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(tmp, 0o600)   # 소유자만 읽기 (best-effort)
        except Exception:
            pass
        self._temp_kubeconfig = tmp
        return tmp

    def _cleanup_temp_kubeconfig(self):
        tmp = getattr(self, '_temp_kubeconfig', None)
        if tmp:
            try:
                os.remove(tmp)
            except Exception:
                pass
            self._temp_kubeconfig = None

    # ── 연결 ─────────────────────────────────────────────────────────────────

    def connect(self, path: str = None, context: str = None, content: str = None):
        if not HAS_K8S:
            return False, 'pip install kubernetes 후 재시작하세요.'

        # ── content 기반 연결 (vault 복원) — 세션 임시 파일 생성 ────────────────
        used_temp = False
        if content is not None:
            try:
                path = self._write_temp_kubeconfig(content)
                used_temp = True
            except Exception as e:
                return False, f'kubeconfig 임시 파일 생성 실패: {e}'

        # ── 사전 검증 ──────────────────────────────────────────────────────────
        p = Path(path) if path else None
        if not p or not p.is_file():
            if used_temp:
                self._cleanup_temp_kubeconfig()
            return False, f'kubeconfig 파일을 찾을 수 없습니다: {path}'
        if p.stat().st_size > 5 * 1024 * 1024:  # 5 MB 초과는 kubeconfig 아님
            if used_temp:
                self._cleanup_temp_kubeconfig()
            return False, 'kubeconfig 파일이 너무 큽니다 (5 MB 초과).'

        try:
            # ── 인스턴스 전용 Configuration 생성 (전역 덮어쓰기 방지) ───────────
            cfg = k8s.Configuration()
            k8s_cfg.load_kube_config(
                config_file=path,
                context=context or None,
                client_configuration=cfg,
            )
            api_client       = k8s.ApiClient(configuration=cfg)
            self._api_client = api_client

            self.core        = k8s.CoreV1Api(api_client=api_client)
            self.apps        = k8s.AppsV1Api(api_client=api_client)
            self.batch       = k8s.BatchV1Api(api_client=api_client)
            self.net         = k8s.NetworkingV1Api(api_client=api_client)
            self.custom      = k8s.CustomObjectsApi(api_client=api_client)
            self.autoscaling = k8s.AutoscalingV1Api(api_client=api_client)
            self.storage     = k8s.StorageV1Api(api_client=api_client)
            self.rbac        = k8s.RbacAuthorizationV1Api(api_client=api_client)
            self.policy      = k8s.PolicyV1Api(api_client=api_client)
            ver = k8s.VersionApi(api_client=api_client).get_code()
            # 컨텍스트 이름 결정: 지정된 context 우선, 없으면 current-context
            if context:
                ctx_name = context
            else:
                try:
                    _, active_ctx = k8s_cfg.list_kube_config_contexts(config_file=path)
                    ctx_name = (active_ctx.get('context', {}).get('cluster', '')
                                or active_ctx.get('name', ''))
                except Exception:
                    ctx_name = ''
            self.kubeconfig   = path
            self.connected    = True
            self.cluster_info = {'version': ver.git_version, 'context': ctx_name}
            return True, f'연결 성공 — {ver.git_version}'
        except Exception as e:
            self.connected = False
            if used_temp:
                self._cleanup_temp_kubeconfig()
            return False, _diagnose_connect_error(e, path)

    def disconnect(self):
        self.connected = False
        self.kubeconfig = None
        self.cluster_info = {}
        self._cleanup_temp_kubeconfig()
        # ApiClient 연결 풀 해제
        try:
            if self._api_client:
                self._api_client.rest_client.pool_manager.clear()
        except Exception:
            pass
        self._api_client = None
        self.core = self.apps = self.batch = self.net = None
        self.custom = self.autoscaling = self.storage = self.rbac = self.policy = None

    # ── 내부 유틸 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _an(ns) -> bool:
        """All-Namespaces 여부 확인."""
        return not ns or str(ns).lower() in ('all namespaces', 'all', '')

    # ── 네임스페이스 ──────────────────────────────────────────────────────────

    def get_namespaces_list(self) -> list:
        try:
            return [n.metadata.name for n in self.core.list_namespace().items]
        except Exception:
            return []

    def get_namespaces(self, _=None) -> list:
        try:
            return [{'name': n.metadata.name,
                     'status': n.status.phase or 'Active',
                     'age': _age(n.metadata.creation_timestamp),
                     '_ns': None, '_kind': 'namespace'}
                    for n in self.core.list_namespace().items]
        except Exception:
            return []

    # ── 노드 ──────────────────────────────────────────────────────────────────

    def get_nodes(self, _=None) -> list:
        rows = []
        try:
            for n in self.core.list_node().items:
                labels = n.metadata.labels or {}
                roles = [lbl.split('/')[-1] for lbl in labels
                         if 'node-role.kubernetes.io/' in lbl] or ['<none>']
                status = 'Unknown'
                for cond in (n.status.conditions or []):
                    if cond.type == 'Ready':
                        status = 'Ready' if cond.status == 'True' else 'NotReady'
                ni = n.status.node_info
                rows.append({
                    'name':    n.metadata.name,
                    'status':  status,
                    'roles':   ','.join(roles),
                    'version': ni.kubelet_version if ni else 'N/A',
                    'os':      ni.os_image if ni else 'N/A',
                    'age':     _age(n.metadata.creation_timestamp),
                    '_ns': None, '_kind': 'node',
                })
        except Exception:
            pass
        return rows

    # ── 파드 ──────────────────────────────────────────────────────────────────

    def get_pods(self, ns=None) -> list:
        try:
            items = (self.core.list_namespaced_pod(ns).items
                     if not self._an(ns)
                     else self.core.list_pod_for_all_namespaces().items)
        except Exception:
            return []
        rows = []
        for p in items:
            total = len(p.spec.containers)
            ready = restarts = 0
            if p.status.container_statuses:
                for cs in p.status.container_statuses:
                    if cs.ready:
                        ready += 1
                    restarts += cs.restart_count or 0
            rows.append({
                'name':      p.metadata.name,
                'namespace': p.metadata.namespace,
                'ready':     f'{ready}/{total}',
                'status':    p.status.phase or 'Unknown',
                'restarts':  str(restarts),
                'node':      p.spec.node_name or 'N/A',
                'age':       _age(p.metadata.creation_timestamp),
                '_ns': p.metadata.namespace, '_kind': 'pod',
            })
        return rows

    # ── 디플로이먼트 ──────────────────────────────────────────────────────────

    def get_deployments(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_deployment(ns).items
                     if not self._an(ns)
                     else self.apps.list_deployment_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':       d.metadata.name,
            'namespace':  d.metadata.namespace,
            'ready':      f'{d.status.ready_replicas or 0}/{d.spec.replicas or 0}',
            'up-to-date': str(d.status.updated_replicas or 0),
            'available':  str(d.status.available_replicas or 0),
            'age':        _age(d.metadata.creation_timestamp),
            '_ns': d.metadata.namespace, '_kind': 'deployment',
        } for d in items]

    # ── 스테이트풀셋 ──────────────────────────────────────────────────────────

    def get_statefulsets(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_stateful_set(ns).items
                     if not self._an(ns)
                     else self.apps.list_stateful_set_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      s.metadata.name,
            'namespace': s.metadata.namespace,
            'ready':     f'{s.status.ready_replicas or 0}/{s.spec.replicas or 0}',
            'age':       _age(s.metadata.creation_timestamp),
            '_ns': s.metadata.namespace, '_kind': 'statefulset',
        } for s in items]

    # ── 데몬셋 ───────────────────────────────────────────────────────────────

    def get_daemonsets(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_daemon_set(ns).items
                     if not self._an(ns)
                     else self.apps.list_daemon_set_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      d.metadata.name,
            'namespace': d.metadata.namespace,
            'desired':   str(d.status.desired_number_scheduled or 0),
            'ready':     str(d.status.number_ready or 0),
            'age':       _age(d.metadata.creation_timestamp),
            '_ns': d.metadata.namespace, '_kind': 'daemonset',
        } for d in items]

    # ── 레플리카셋 ────────────────────────────────────────────────────────────

    def get_replicasets(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_replica_set(ns).items
                     if not self._an(ns)
                     else self.apps.list_replica_set_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      r.metadata.name,
            'namespace': r.metadata.namespace,
            'desired':   str(r.spec.replicas or 0),
            'ready':     str(r.status.ready_replicas or 0),
            'age':       _age(r.metadata.creation_timestamp),
            '_ns': r.metadata.namespace, '_kind': 'replicaset',
        } for r in items]

    # ── 잡 ───────────────────────────────────────────────────────────────────

    def get_jobs(self, ns=None) -> list:
        try:
            items = (self.batch.list_namespaced_job(ns).items
                     if not self._an(ns)
                     else self.batch.list_job_for_all_namespaces().items)
        except Exception:
            return []
        rows = []
        for j in items:
            conditions = j.status.conditions or []
            cond_types = {c.type for c in conditions if c.status == 'True'}
            if 'Complete' in cond_types:
                status = 'Complete'
            elif 'Failed' in cond_types:
                status = 'Failed'
            elif j.status.active:
                status = 'Running'
            else:
                status = 'Pending'
            rows.append({
                'name':        j.metadata.name,
                'namespace':   j.metadata.namespace,
                'completions': f'{j.status.succeeded or 0}/{j.spec.completions or 1}',
                'status':      status,
                'age':         _age(j.metadata.creation_timestamp),
                '_ns': j.metadata.namespace, '_kind': 'job',
            })
        return rows

    # ── 크론잡 ───────────────────────────────────────────────────────────────

    def get_cronjobs(self, ns=None) -> list:
        try:
            items = (self.batch.list_namespaced_cron_job(ns).items
                     if not self._an(ns)
                     else self.batch.list_cron_job_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':          c.metadata.name,
            'namespace':     c.metadata.namespace,
            'schedule':      c.spec.schedule,
            'suspend':       str(c.spec.suspend or False),
            'last-schedule': (_age(c.status.last_schedule_time)
                              if c.status.last_schedule_time else 'Never'),
            'age':           _age(c.metadata.creation_timestamp),
            '_ns': c.metadata.namespace, '_kind': 'cronjob',
        } for c in items]

    # ── 서비스 ───────────────────────────────────────────────────────────────

    def get_services(self, ns=None) -> list:
        try:
            items = (self.core.list_namespaced_service(ns).items
                     if not self._an(ns)
                     else self.core.list_service_for_all_namespaces().items)
        except Exception:
            return []
        rows = []
        for s in items:
            ext = []
            if s.status.load_balancer and s.status.load_balancer.ingress:
                ext = [i.ip or i.hostname or ''
                       for i in s.status.load_balancer.ingress]
            ports = [f'{p.port}{":" + str(p.node_port) if p.node_port else ""}/{p.protocol}'
                     for p in (s.spec.ports or [])]
            rows.append({
                'name':        s.metadata.name,
                'namespace':   s.metadata.namespace,
                'type':        s.spec.type,
                'cluster-ip':  s.spec.cluster_ip or 'None',
                'external-ip': ','.join(ext) if ext else '<none>',
                'ports':       ','.join(ports),
                'age':         _age(s.metadata.creation_timestamp),
                '_ns': s.metadata.namespace, '_kind': 'service',
            })
        return rows

    # ── 인그레스 ─────────────────────────────────────────────────────────────

    def get_ingresses(self, ns=None) -> list:
        try:
            items = (self.net.list_namespaced_ingress(ns).items
                     if not self._an(ns)
                     else self.net.list_ingress_for_all_namespaces().items)
        except Exception:
            return []
        rows = []
        for i in items:
            hosts = [r.host for r in (i.spec.rules or []) if r.host]
            addrs = [x.ip or x.hostname or ''
                     for x in ((i.status.load_balancer.ingress or [])
                                if i.status.load_balancer else [])]
            rows.append({
                'name':      i.metadata.name,
                'namespace': i.metadata.namespace,
                'class':     i.spec.ingress_class_name or '<none>',
                'hosts':     ','.join(hosts) or '*',
                'address':   ','.join(addrs),
                'age':       _age(i.metadata.creation_timestamp),
                '_ns': i.metadata.namespace, '_kind': 'ingress',
            })
        return rows

    # ── 컨피그맵 ─────────────────────────────────────────────────────────────

    def get_configmaps(self, ns=None) -> list:
        try:
            items = (self.core.list_namespaced_config_map(ns).items
                     if not self._an(ns)
                     else self.core.list_config_map_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      c.metadata.name,
            'namespace': c.metadata.namespace,
            'data':      str(len(c.data) if c.data else 0),
            'age':       _age(c.metadata.creation_timestamp),
            '_ns': c.metadata.namespace, '_kind': 'configmap',
        } for c in items]

    # ── 시크릿 ───────────────────────────────────────────────────────────────

    def get_secrets(self, ns=None) -> list:
        try:
            items = (self.core.list_namespaced_secret(ns).items
                     if not self._an(ns)
                     else self.core.list_secret_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      s.metadata.name,
            'namespace': s.metadata.namespace,
            'type':      s.type,
            'data':      str(len(s.data) if s.data else 0),
            'age':       _age(s.metadata.creation_timestamp),
            '_ns': s.metadata.namespace, '_kind': 'secret',
        } for s in items]

    # ── PVC ──────────────────────────────────────────────────────────────────

    def get_pvcs(self, ns=None) -> list:
        try:
            items = (self.core.list_namespaced_persistent_volume_claim(ns).items
                     if not self._an(ns)
                     else self.core.list_persistent_volume_claim_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':         p.metadata.name,
            'namespace':    p.metadata.namespace,
            'status':       p.status.phase or 'Unknown',
            'volume':       p.spec.volume_name or '',
            'capacity':     (p.status.capacity or {}).get('storage', 'N/A'),
            'access-modes': ','.join(p.spec.access_modes or []),
            'age':          _age(p.metadata.creation_timestamp),
            '_ns': p.metadata.namespace, '_kind': 'persistentvolumeclaim',
        } for p in items]

    # ── PV ───────────────────────────────────────────────────────────────────

    def get_pvs(self, _=None) -> list:
        rows = []
        try:
            for p in self.core.list_persistent_volume().items:
                ref = p.spec.claim_ref
                rows.append({
                    'name':           p.metadata.name,
                    'capacity':       (p.spec.capacity or {}).get('storage', 'N/A'),
                    'access-modes':   ','.join(p.spec.access_modes or []),
                    'reclaim-policy': p.spec.persistent_volume_reclaim_policy or 'N/A',
                    'status':         p.status.phase or 'Unknown',
                    'claim':          f'{ref.namespace}/{ref.name}' if ref else '',
                    'age':            _age(p.metadata.creation_timestamp),
                    '_ns': None, '_kind': 'persistentvolume',
                })
        except Exception:
            pass
        return rows

    # ── 리소스 라우터 ─────────────────────────────────────────────────────────

    GETTERS = {
        'nodes':        get_nodes,
        'namespaces':   get_namespaces,
        'pods':         get_pods,
        'deployments':  get_deployments,
        'statefulsets': get_statefulsets,
        'daemonsets':   get_daemonsets,
        'replicasets':  get_replicasets,
        'jobs':         get_jobs,
        'cronjobs':     get_cronjobs,
        'services':     get_services,
        'ingresses':    get_ingresses,
        'configmaps':   get_configmaps,
        'secrets':      get_secrets,
        'pvcs':         get_pvcs,
        'pvs':          get_pvs,
    }

    def get_resources(self, rtype: str, ns=None) -> list:
        fn = self.GETTERS.get(rtype)
        return fn(self, ns) if fn else []

    def get_workload_pods(self, ns: str, wl_type: str, wl_name: str):
        wl_type = _normalize_log_source_type(wl_type)
        wl_name = str(wl_name or '').strip()
        if wl_type not in _WORKLOAD_LOG_TYPES:
            return [], f'지원하지 않는 워크로드 타입: {wl_type}'
        if not ns or not wl_name:
            return [], 'namespace와 워크로드 이름이 필요합니다.'

        try:
            if wl_type == 'deployment':
                wl = self.apps.read_namespaced_deployment(wl_name, ns)
            elif wl_type == 'statefulset':
                wl = self.apps.read_namespaced_stateful_set(wl_name, ns)
            elif wl_type == 'daemonset':
                wl = self.apps.read_namespaced_daemon_set(wl_name, ns)
            elif wl_type == 'replicaset':
                wl = self.apps.read_namespaced_replica_set(wl_name, ns)
            else:
                wl = self.batch.read_namespaced_job(wl_name, ns)
        except Exception as e:
            return [], f'워크로드 조회 실패: {e}'

        wl_uid = getattr(wl.metadata, 'uid', None)
        sel_labels = (wl.spec.selector.match_labels or {}) if wl.spec and wl.spec.selector else {}
        desired = getattr(wl.spec, 'replicas', None)
        ready = (getattr(wl.status, 'ready_replicas', None) or
                 getattr(wl.status, 'number_ready', None) or
                 getattr(wl.status, 'succeeded', None) or 0)

        if wl_type == 'deployment' and sel_labels:
            try:
                label_sel = ','.join(f'{k}={v}' for k, v in sel_labels.items())
                rss = self.apps.list_namespaced_replica_set(ns, label_selector=label_sel).items
                owned_rs_uids = {
                    rs.metadata.uid for rs in rss
                    if any(o.uid == wl_uid for o in (rs.metadata.owner_references or []))
                }
                if owned_rs_uids:
                    pods = self.core.list_namespaced_pod(ns).items
                    names = [p.metadata.name for p in pods
                             if any(o.uid in owned_rs_uids
                                    for o in (p.metadata.owner_references or []))]
                    if names:
                        return sorted(names), None
            except Exception:
                pass

        try:
            pods = self.core.list_namespaced_pod(ns).items
            owned = [p.metadata.name for p in pods
                     if any(o.uid == wl_uid for o in (p.metadata.owner_references or []))]
            if owned:
                return sorted(owned), None
        except Exception:
            pass

        if sel_labels:
            try:
                label_sel = ','.join(f'{k}={v}' for k, v in sel_labels.items())
                pods = self.core.list_namespaced_pod(ns, label_selector=label_sel).items
                names = [p.metadata.name for p in pods]
                if names:
                    return sorted(names), None
            except Exception as e:
                return [], f'파드 조회 실패: {e}'

        if desired == 0:
            return [], f'{wl_type}의 desired replicas가 0입니다.'
        return [], f'{wl_type}/{wl_name}에 연결된 활성 파드가 없습니다. ready={ready}'

    def get_ingress_log_pods(self):
        candidates = ['kube-system', 'ingress-nginx', 'nginx-ingress', 'traefik', 'istio-system']
        found: list[tuple[str, str]] = []
        seen = set()

        def add_matches(items):
            for pod in items or []:
                ns = pod.metadata.namespace
                name = pod.metadata.name
                key = (ns, name)
                if key in seen:
                    continue
                if _is_ingress_controller_pod(name, pod.metadata.labels or {}):
                    seen.add(key)
                    found.append(key)

        for ns in candidates:
            try:
                add_matches(self.core.list_namespaced_pod(ns).items)
            except Exception:
                pass
        if found:
            return found, None

        try:
            add_matches(self.core.list_pod_for_all_namespaces().items)
        except Exception as e:
            return [], f'Ingress controller 파드 조회 실패: {e}'

        if found:
            return found, None
        return [], 'ingress / traefik / contour / istio-ingressgateway 키워드로 controller 파드를 찾지 못했습니다.'

    # ── 대시보드 ─────────────────────────────────────────────────────────────

    def get_node_metrics(self):
        if not self.custom:
            return []
        try:
            r = self.custom.list_cluster_custom_object(
                group='metrics.k8s.io', version='v1beta1', plural='nodes')
            return _build_node_metrics(r.get('items', []))
        except Exception:
            return []

    def get_dashboard_data(self) -> dict:
        result = {
            'pods': [], 'nodes': [], 'node_metrics': [],
            'total_restarts': 0, 'namespace_count': 0,
        }
        if not self.core:
            return result
        try:
            pods = self.get_pods(None)
            result['pods'] = pods
            result['total_restarts'] = sum(int(p.get('restarts', 0)) for p in pods)

            node_pod_cnt = {}
            for p in pods:
                nd = p.get('node', '')
                node_pod_cnt[nd] = node_pod_cnt.get(nd, 0) + 1

            for n in self.core.list_node().items:
                labels = n.metadata.labels or {}
                roles = [lbl.split('/')[-1] for lbl in labels
                         if 'node-role.kubernetes.io/' in lbl] or ['<none>']
                status = 'Ready'
                for cond in (n.status.conditions or []):
                    if cond.type == 'Ready':
                        status = 'Ready' if cond.status == 'True' else 'NotReady'
                alloc = n.status.allocatable or {}
                result['nodes'].append(_apply_node_metric({
                    'name':         n.metadata.name,
                    'status':       status,
                    'role':         ','.join(roles),
                    'cpu_alloc_m':  _parse_cpu(alloc.get('cpu', '0')),
                    'mem_alloc_mi': _parse_mem(alloc.get('memory', '0')) // (1024 * 1024),
                    'max_pods':     int(alloc.get('pods', '110')),
                    'pod_count':    node_pod_cnt.get(n.metadata.name, 0),
                }, None))

            result['node_metrics'] = self.get_node_metrics()
            metrics = {m['name']: m for m in result['node_metrics']}
            result['nodes'] = [
                _apply_node_metric(n, metrics.get(n['name']))
                for n in result['nodes']
            ]
            result['namespace_count'] = len(self.core.list_namespace().items)
        except Exception:
            pass
        return result

    # ── CRD (CustomResourceDefinition) 자동 발견 ─────────────────────────────

    def get_crds(self):
        """클러스터의 모든 CRD 메타 목록.

        반환: [{name, group, version(스토리지 버전), kind, plural, scoped, ...}]
        custom API 로 apiextensions.k8s.io/v1/customresourcedefinitions 조회.
        """
        if not self.custom:
            return []
        try:
            result = self.custom.list_cluster_custom_object(
                group='apiextensions.k8s.io', version='v1',
                plural='customresourcedefinitions',
            )
        except Exception:
            return []
        out = []
        for item in result.get('items', []):
            spec = item.get('spec', {})
            md   = item.get('metadata', {})
            names = spec.get('names', {})
            versions = spec.get('versions', []) or []
            # 스토리지/served 버전 선택 (storage=true 우선, 없으면 첫 served)
            storage_v = next((v.get('name') for v in versions if v.get('storage')), '')
            served    = [v.get('name') for v in versions if v.get('served')]
            ver = storage_v or (served[0] if served else (versions[0].get('name') if versions else ''))
            group = spec.get('group', '')
            # 선택된 버전의 additionalPrinterColumns 추출 (없으면 [])
            ver_obj = next((v for v in versions if v.get('name') == ver), {})
            printer_cols = [
                {'name': c.get('name', ''), 'jsonPath': c.get('jsonPath', '')}
                for c in (ver_obj.get('additionalPrinterColumns', []) or [])
                if c.get('name') and c.get('jsonPath')
                and c.get('name', '').lower() != 'age'   # Age 는 우리가 따로 표시
            ]
            out.append({
                'name':    md.get('name', ''),
                'group':   group,
                'version': ver,
                'kind':    names.get('kind', ''),
                'plural':  names.get('plural', ''),
                'short':   ','.join(names.get('shortNames', []) or []),
                'scope':   spec.get('scope', 'Namespaced'),
                'namespaced': spec.get('scope', 'Namespaced') == 'Namespaced',
                'versions': served,
                'printer_columns': printer_cols[:5],   # 너무 많으면 5개로 제한
                'age':     _age(_parse_ts(md.get('creationTimestamp'))),
            })
        out.sort(key=lambda x: (x['group'], x['kind']))
        return out

    def get_crd_objects(self, group: str, version: str, plural: str,
                        namespaced: bool, ns: str = None,
                        printer_columns: list = None):
        """특정 CRD 의 커스텀 객체 목록 (generic 테이블용).

        printer_columns: [{'name', 'jsonPath'}] — CRD 가 정의한 추가 컬럼.
        각 객체에서 jsonPath 값을 추출해 'col_<name>' 키로 담는다.

        반환: [{name, namespace, age, col_<...>, _ns, _kind}]
        """
        if not self.custom:
            return []
        try:
            if namespaced and ns and not self._an(ns):
                result = self.custom.list_namespaced_custom_object(
                    group=group, version=version, namespace=ns, plural=plural)
            else:
                result = self.custom.list_cluster_custom_object(
                    group=group, version=version, plural=plural)
        except Exception:
            return []
        cols = printer_columns or []
        rows = []
        for item in result.get('items', []):
            md = item.get('metadata', {})
            row = {
                'name':      md.get('name', ''),
                'namespace': md.get('namespace', '') or '',
                'age':       _age(_parse_ts(md.get('creationTimestamp'))),
                '_ns':       md.get('namespace'),
                '_kind':     f'{plural}.{group}',
            }
            for c in cols:
                row[f'col_{c["name"]}'] = _jsonpath_get(item, c.get('jsonPath', ''))
            rows.append(row)
        return rows


    # ── ArgoCD ───────────────────────────────────────────────────────────────

    def get_argocd_apps(self):
        """ArgoCD Application CRD 목록. CRD 없으면 None."""
        if not self.custom:
            return None
        try:
            result = self.custom.list_cluster_custom_object(
                group='argoproj.io', version='v1alpha1', plural='applications')
            return result.get('items', [])
        except Exception:
            return None

    def create_argocd_app(self, ns, name, project, repo_url, path,
                           revision, dest_ns, dest_server, sync_policy=None,
                           sources=None):
        body = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'Application',
            'metadata': {'name': name, 'namespace': ns},
            'spec': _build_argocd_spec(
                project, repo_url, path, revision,
                dest_ns, dest_server, sync_policy, sources,
            ),
        }
        self.custom.create_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', body=body)

    def update_argocd_app(self, ns, name, project, repo_url, path,
                           revision, dest_ns, dest_server, sync_policy=None,
                           sources=None):
        patch = {
            'spec': _build_argocd_spec(
                project, repo_url, path, revision,
                dest_ns, dest_server, sync_policy, sources,
            ),
        }
        self.custom.patch_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name, body=patch)

    def delete_argocd_app(self, ns, name):
        self.custom.delete_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name)

    def sync_argocd_app(self, ns, name):
        is_multi_source = False
        try:
            app = self.custom.get_namespaced_custom_object(
                group='argoproj.io', version='v1alpha1',
                namespace=ns, plural='applications', name=name)
            is_multi_source = len(_argo_sources_from_spec(app.get('spec', {}))) > 1
        except Exception:
            is_multi_source = False
        patch = _build_argocd_sync_operation(is_multi_source=is_multi_source)
        self.custom.patch_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name, body=patch)

    def rollback_argocd_app(self, ns, name, history_id):
        patch = {
            'operation': {
                'rollback': {'id': int(history_id), 'prune': False},
                'initiatedBy': {'username': 'polaris'},
            }
        }
        self.custom.patch_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name, body=patch)

    # ── Helm ─────────────────────────────────────────────────────────────────

    def get_helm_releases(self) -> list:
        """Helm 릴리스 목록 — helm CLI 우선, K8s Secret 폴백."""
        helm = _find_helm()
        if helm and self.kubeconfig:
            try:
                cmd = [helm, 'list', '--all-namespaces', '-o', 'json',
                       '--kubeconfig', self.kubeconfig]
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=30, creationflags=_NO_WINDOW)
                if r.returncode == 0:
                    data = json.loads(r.stdout or '[]')
                    return [{
                        'name':        d.get('name', '-'),
                        'namespace':   d.get('namespace', '-'),
                        'chart':       d.get('chart', '-'),
                        'app_version': d.get('app_version', '-'),
                        'status':      d.get('status', '-'),
                        'revision':    str(d.get('revision', '-')),
                        'updated':     (d.get('updated', '')[:19]
                                        if d.get('updated') else '-'),
                    } for d in data]
            except Exception:
                pass
        return self._helm_releases_from_secrets()

    def _helm_releases_from_secrets(self) -> list:
        """K8s Secret (type=helm.sh/release.v1) 에서 릴리즈 메타 추출."""
        if not self.core:
            return []
        try:
            seen: dict = {}
            for s in self.core.list_secret_for_all_namespaces().items:
                if s.type != 'helm.sh/release.v1':
                    continue
                lbl = s.metadata.labels or {}
                if lbl.get('owner') != 'helm':
                    continue
                rname = lbl.get('name', s.metadata.name)
                rns   = s.metadata.namespace
                rev   = int(lbl.get('version', 0))
                key   = (rname, rns)
                if key not in seen or rev > seen[key]['_rev']:
                    seen[key] = {
                        'name':        rname,
                        'namespace':   rns,
                        'chart':       lbl.get('chart', '-'),
                        'app_version': lbl.get('app.kubernetes.io/version', '-'),
                        'status':      lbl.get('status', '-'),
                        'revision':    str(rev),
                        'updated':     _age(s.metadata.creation_timestamp),
                        '_rev':        rev,
                    }
            return [v for v in seen.values()]
        except Exception:
            return []


    def get_helm_releases_by_label(self, label_key: str, label_value: str = None,
                                    extra_meta_key: str = '') -> dict:
        """레이블로 필터링된 helm 릴리스의 최신 리비전 메타.

        plugin 들이 자기 출처를 표시하는 helm --labels 메타데이터를 K8s Secret 에서 읽기 위한
        범용 헬퍼. K8sManager 자체는 도메인 특화 라벨(=특정 기능명)을 알지 못한다.

        Args:
            label_key:      필터링할 레이블 키 (예: 'polaris-catalog')
            label_value:    필터링할 값. None 이면 키 존재만 체크.
            extra_meta_key: 결과 dict 값으로 가져올 추가 레이블 키.

        Returns:
            {(release_name, namespace): extra_meta_value}  — extra_meta_key 없으면 ''
        """
        result: dict = {}
        rev_map: dict = {}
        if not self.core:
            return result
        try:
            for s in self.core.list_secret_for_all_namespaces().items:
                if s.type != 'helm.sh/release.v1':
                    continue
                lbl = s.metadata.labels or {}
                if lbl.get('owner') != 'helm':
                    continue
                if label_value is None:
                    if label_key not in lbl:
                        continue
                else:
                    if lbl.get(label_key) != label_value:
                        continue
                rname = lbl.get('name', s.metadata.name)
                rns   = s.metadata.namespace
                rev   = int(lbl.get('version', 0))
                key   = (rname, rns)
                if key not in result or rev > rev_map.get(key, -1):
                    result[key]   = lbl.get(extra_meta_key, '') if extra_meta_key else ''
                    rev_map[key]  = rev
        except Exception:
            pass
        return result


    # ── 보고서용 확장 getter ─────────────────────────────────────────────────

    def get_node_extended(self):
        try:
            out = []
            for n in self.core.list_node().items:
                status = n.status or type('', (), {})()
                ni     = getattr(status, 'node_info', None)
                alloc  = getattr(status, 'allocatable', None) or {}
                conds  = [{'type': c.type, 'status': c.status,
                           'reason': c.reason or '', 'message': (c.message or '')[:100]}
                          for c in (getattr(status, 'conditions', None) or [])]
                taints = [f'{t.key}={t.value or ""}:{t.effect}'
                          for t in (getattr(n.spec, 'taints', None) or [])]
                labels = n.metadata.labels or {}
                roles  = ', '.join(
                    k.replace('node-role.kubernetes.io/', '')
                    for k in labels if k.startswith('node-role.kubernetes.io/')
                ) or 'worker'
                ready_cond = next((c for c in conds if c['type'] == 'Ready'), None)
                ready_st   = ready_cond['status'] if ready_cond else 'Unknown'
                out.append({
                    'name':              n.metadata.name,
                    'status':            'Ready' if ready_st == 'True' else 'NotReady',
                    'roles':             roles,
                    'version':           ni.kubelet_version if ni else 'N/A',
                    'age':               _age(n.metadata.creation_timestamp),
                    'conditions':        conds,
                    'taints':            taints,
                    'allocatable_cpu':   alloc.get('cpu', 'N/A'),
                    'allocatable_mem':   alloc.get('memory', 'N/A'),
                    'kernel':            ni.kernel_version if ni else 'N/A',
                    'os':                ni.os_image if ni else 'N/A',
                    'container_runtime': ni.container_runtime_version if ni else 'N/A',
                })
            return out
        except Exception:
            return []

    def get_namespaces_extended(self):
        try:
            return [{'name':   n.metadata.name,
                     'status': n.status.phase if n.status else 'Unknown',
                     'age':    _age(n.metadata.creation_timestamp)}
                    for n in self.core.list_namespace().items]
        except Exception:
            return []

    def get_pod_metrics_all(self):
        if not self.custom:
            return []
        try:
            r = self.custom.list_cluster_custom_object(
                group='metrics.k8s.io', version='v1beta1', plural='pods')
            out = []
            for pod in r.get('items', []):
                ns   = pod.get('metadata', {}).get('namespace', '')
                name = pod.get('metadata', {}).get('name', '')
                cpu_t = mem_t = 0
                for c in pod.get('containers', []):
                    u = c.get('usage', {})
                    cpu_t += _parse_cpu(u.get('cpu', '0'))
                    mem_t += _parse_mem(u.get('memory', '0'))
                out.append({'namespace': ns, 'name': name,
                            'cpu_m': cpu_t, 'mem_mi': mem_t // (1024 * 1024)})
            out.sort(key=lambda x: x['cpu_m'], reverse=True)
            return out
        except Exception:
            return []

    def get_pod_metrics(self, namespace: str, name: str):
        """단일 파드의 현재 메트릭 (컨테이너별 CPU/MEM).
        반환: {ok, timestamp, window, containers: [{name, cpu_m, mem_mi}],
               total: {cpu_m, mem_mi}, requests: {cpu_m, mem_mi}, limits: {cpu_m, mem_mi}}
        """
        if not self.custom or not self.core:
            return {'ok': False, 'error': 'metrics API 미연결'}
        try:
            r = self.custom.get_namespaced_custom_object(
                group='metrics.k8s.io', version='v1beta1',
                namespace=namespace, plural='pods', name=name)
            containers = []
            cpu_total = 0
            mem_total = 0
            for c in r.get('containers', []):
                u = c.get('usage', {})
                cpu_m  = _parse_cpu(u.get('cpu', '0'))
                mem_mi = _parse_mem(u.get('memory', '0')) // (1024 * 1024)
                containers.append({
                    'name':   c.get('name', ''),
                    'cpu_m':  cpu_m,
                    'mem_mi': mem_mi,
                })
                cpu_total += cpu_m
                mem_total += mem_mi

            # Pod spec에서 requests / limits 가져오기
            req_cpu = req_mem = lim_cpu = lim_mem = 0
            try:
                pod = self.core.read_namespaced_pod(name=name, namespace=namespace)
                for spec_c in (pod.spec.containers or []):
                    res = spec_c.resources
                    if not res:
                        continue
                    req = res.requests or {}
                    lim = res.limits   or {}
                    req_cpu += _parse_cpu(req.get('cpu', '0'))
                    req_mem += _parse_mem(req.get('memory', '0')) // (1024 * 1024)
                    lim_cpu += _parse_cpu(lim.get('cpu', '0'))
                    lim_mem += _parse_mem(lim.get('memory', '0')) // (1024 * 1024)
            except Exception:
                pass

            return {
                'ok':         True,
                'timestamp':  r.get('timestamp', ''),
                'window':     r.get('window', ''),
                'containers': containers,
                'total':      {'cpu_m': cpu_total, 'mem_mi': mem_total},
                'requests':   {'cpu_m': req_cpu,   'mem_mi': req_mem},
                'limits':     {'cpu_m': lim_cpu,   'mem_mi': lim_mem},
            }
        except Exception as e:
            err_str = str(e)
            # metrics-server 미설치 케이스 식별
            if 'NotFound' in err_str or '404' in err_str or 'metrics.k8s.io' in err_str:
                return {'ok': False, 'error': 'metrics-server가 설치되어 있지 않거나 응답하지 않습니다.',
                        'no_metrics_server': True}
            return {'ok': False, 'error': err_str}

    def get_deployments_extended(self):
        try:
            items = self.apps.list_deployment_for_all_namespaces().items
            return [{'namespace': d.metadata.namespace, 'name': d.metadata.name,
                     'ready':    d.status.ready_replicas or 0,
                     'desired':  d.spec.replicas or 0,
                     'available': d.status.available_replicas or 0,
                     'strategy': d.spec.strategy.type if d.spec and d.spec.strategy else '-',
                     'age':      _age(d.metadata.creation_timestamp)}
                    for d in items]
        except Exception:
            return []

    def get_statefulsets_extended(self):
        try:
            items = self.apps.list_stateful_set_for_all_namespaces().items
            return [{'namespace': s.metadata.namespace, 'name': s.metadata.name,
                     'ready':   s.status.ready_replicas or 0,
                     'desired': s.spec.replicas or 0,
                     'service': s.spec.service_name or '-',
                     'age':     _age(s.metadata.creation_timestamp)}
                    for s in items]
        except Exception:
            return []

    def get_daemonsets_extended(self):
        try:
            items = self.apps.list_daemon_set_for_all_namespaces().items
            return [{'namespace': d.metadata.namespace, 'name': d.metadata.name,
                     'desired':  d.status.desired_number_scheduled or 0,
                     'ready':    d.status.number_ready or 0,
                     'available': d.status.number_available or 0,
                     'age':      _age(d.metadata.creation_timestamp)}
                    for d in items]
        except Exception:
            return []

    def get_resource_quotas(self):
        try:
            return [{'namespace': rq.metadata.namespace, 'name': rq.metadata.name,
                     'hard': {k: str(v) for k, v in (rq.status.hard or {}).items()},
                     'used': {k: str(v) for k, v in (rq.status.used or {}).items()}}
                    for rq in self.core.list_resource_quota_for_all_namespaces().items]
        except Exception:
            return []

    def get_limit_ranges(self):
        try:
            out = []
            for lr in self.core.list_limit_range_for_all_namespaces().items:
                limits = []
                for lim in (lr.spec.limits or []) if lr.spec else []:
                    limits.append({
                        'type':            lim.type or '-',
                        'default':         {k: str(v) for k, v in (lim.default or {}).items()},
                        'default_request': {k: str(v) for k, v in (lim.default_request or {}).items()},
                    })
                out.append({'namespace': lr.metadata.namespace,
                            'name': lr.metadata.name, 'limits': limits})
            return out
        except Exception:
            return []

    def get_hpa_extended(self):
        if not self.autoscaling:
            return []
        try:
            return [{'namespace':   h.metadata.namespace, 'name': h.metadata.name,
                     'reference':   f'{h.spec.scale_target_ref.kind}/{h.spec.scale_target_ref.name}' if h.spec and h.spec.scale_target_ref else '-',
                     'min':         h.spec.min_replicas or 1,
                     'max':         h.spec.max_replicas or 1,
                     'current':     h.status.current_replicas or 0,
                     'desired':     h.status.desired_replicas or 0,
                     'target_cpu':  h.spec.target_cpu_utilization_percentage or '-',
                     'current_cpu': h.status.current_cpu_utilization_percentage or '-',
                     'age':         _age(h.metadata.creation_timestamp)}
                    for h in self.autoscaling.list_horizontal_pod_autoscaler_for_all_namespaces().items]
        except Exception:
            return []

    def get_pdbs(self):
        if not self.policy:
            return []
        try:
            return [{'namespace':           p.metadata.namespace, 'name': p.metadata.name,
                     'min_available':       getattr(p.spec, 'min_available', '-'),
                     'max_unavailable':     getattr(p.spec, 'max_unavailable', '-'),
                     'current_healthy':     getattr(p.status, 'current_healthy', 0),
                     'desired_healthy':     getattr(p.status, 'desired_healthy', 0),
                     'disruptions_allowed': getattr(p.status, 'disruptions_allowed', 0),
                     'age':                 _age(p.metadata.creation_timestamp)}
                    for p in self.policy.list_pod_disruption_budget_for_all_namespaces().items]
        except Exception:
            return []

    def get_network_policies(self):
        if not self.net:
            return []
        try:
            return [{'namespace':     n.metadata.namespace, 'name': n.metadata.name,
                     'pod_selector':  str(n.spec.pod_selector.match_labels or 'all') if n.spec and n.spec.pod_selector else '-',
                     'ingress_rules': len(n.spec.ingress or []) if n.spec else 0,
                     'egress_rules':  len(n.spec.egress  or []) if n.spec else 0,
                     'age':           _age(n.metadata.creation_timestamp)}
                    for n in self.net.list_network_policy_for_all_namespaces().items]
        except Exception:
            return []

    def get_ingress_classes(self):
        if not self.net:
            return []
        try:
            return [{'name':       ic.metadata.name,
                     'controller': ic.spec.controller if ic.spec else '-',
                     'is_default': (ic.metadata.annotations or {}).get(
                         'ingressclass.kubernetes.io/is-default-class', 'false'),
                     'age':        _age(ic.metadata.creation_timestamp)}
                    for ic in self.net.list_ingress_class().items]
        except Exception:
            return []

    def get_storage_classes(self):
        if not self.storage:
            return []
        try:
            return [{'name':          sc.metadata.name,
                     'provisioner':   sc.provisioner or '-',
                     'reclaim_policy': sc.reclaim_policy or '-',
                     'binding_mode':  sc.volume_binding_mode or '-',
                     'is_default':    (sc.metadata.annotations or {}).get(
                         'storageclass.kubernetes.io/is-default-class', 'false'),
                     'age':           _age(sc.metadata.creation_timestamp)}
                    for sc in self.storage.list_storage_class().items]
        except Exception:
            return []

    def get_rbac_summary(self):
        if not self.rbac:
            return {}
        try:
            crs  = self.rbac.list_cluster_role().items
            crbs = self.rbac.list_cluster_role_binding().items
            roles = self.rbac.list_role_for_all_namespaces().items
            rbs  = self.rbac.list_role_binding_for_all_namespaces().items
            sas  = self.core.list_service_account_for_all_namespaces().items
            return {
                'cluster_roles':         len(crs),
                'cluster_role_bindings': len(crbs),
                'roles':                 len(roles),
                'role_bindings':         len(rbs),
                'service_accounts':      len(sas),
                'cluster_roles_list': [{'name': cr.metadata.name,
                                        'age':  _age(cr.metadata.creation_timestamp)}
                                       for cr in crs if not cr.metadata.name.startswith('system:')][:30],
                'cluster_role_bindings_list': [{'name': crb.metadata.name,
                                                'subjects': len(crb.subjects or [])}
                                               for crb in crbs if not crb.metadata.name.startswith('system:')][:30],
            }
        except Exception:
            return {}

    # ── RBAC 분석 뷰어 ───────────────────────────────────────────────────────

    def get_rbac_roles(self, include_system: bool = False):
        """Role + ClusterRole 목록 (규칙 포함).

        반환: [{name, namespace('' if cluster), kind('Role'|'ClusterRole'),
                rules:[{verbs, resources, apiGroups}], rule_count, age}]
        """
        if not self.rbac:
            return []
        out = []

        def add(items, kind):
            for r in items:
                name = r.metadata.name
                if not include_system and name.startswith('system:'):
                    continue
                rules = []
                for rule in (r.rules or []):
                    rules.append({
                        'verbs':     list(rule.verbs or []),
                        'resources': list(rule.resources or []),
                        'apiGroups': list(rule.api_groups or []),
                    })
                out.append({
                    'name':       name,
                    'namespace':  getattr(r.metadata, 'namespace', '') or '',
                    'kind':       kind,
                    'rules':      rules,
                    'rule_count': len(rules),
                    'age':        _age(r.metadata.creation_timestamp),
                })
        try:
            add(self.rbac.list_cluster_role().items, 'ClusterRole')
            add(self.rbac.list_role_for_all_namespaces().items, 'Role')
        except Exception:
            pass
        out.sort(key=lambda x: (x['kind'] != 'ClusterRole', x['name']))
        return out

    def get_rbac_bindings(self, include_system: bool = False):
        """RoleBinding + ClusterRoleBinding 목록 (roleRef + subjects).

        반환: [{name, namespace, kind, role_ref:{kind,name}, subjects:[{kind,name,namespace}], age}]
        """
        if not self.rbac:
            return []
        out = []

        def add(items, kind):
            for b in items:
                name = b.metadata.name
                if not include_system and name.startswith('system:'):
                    continue
                rr = b.role_ref
                subs = []
                for s in (b.subjects or []):
                    subs.append({
                        'kind':      getattr(s, 'kind', ''),
                        'name':      getattr(s, 'name', ''),
                        'namespace': getattr(s, 'namespace', '') or '',
                    })
                out.append({
                    'name':      name,
                    'namespace': getattr(b.metadata, 'namespace', '') or '',
                    'kind':      kind,
                    'role_ref':  {'kind': getattr(rr, 'kind', ''), 'name': getattr(rr, 'name', '')},
                    'subjects':  subs,
                    'age':       _age(b.metadata.creation_timestamp),
                })
        try:
            add(self.rbac.list_cluster_role_binding().items, 'ClusterRoleBinding')
            add(self.rbac.list_role_binding_for_all_namespaces().items, 'RoleBinding')
        except Exception:
            pass
        out.sort(key=lambda x: (x['kind'] != 'ClusterRoleBinding', x['name']))
        return out

    def get_service_accounts(self):
        """ServiceAccount 목록. 반환: [{name, namespace, secrets, age}]"""
        if not self.core:
            return []
        try:
            return [{
                'name':      sa.metadata.name,
                'namespace': sa.metadata.namespace,
                'secrets':   len(sa.secrets or []),
                'age':       _age(sa.metadata.creation_timestamp),
            } for sa in self.core.list_service_account_for_all_namespaces().items]
        except Exception:
            return []

    def get_rbac_risky_subjects(self, include_system: bool = False):
        """과도한 권한(클러스터 관리자급) 보유 subject 목록 — 보고서 보안 점검용.

        판정 기준:
          • cluster-admin ClusterRole 에 바인딩된 subject
          • 와일드카드 규칙(apiGroups=*, resources=*, verbs=*) 보유 role 에 바인딩된 subject

        system: 접두 이름(빌드인 system:masters 등)은 기본 제외(노이즈 감소).
        반환: [{subject_kind, name, namespace, role, role_kind,
                binding, binding_kind, reason}]
        """
        try:
            roles    = self.get_rbac_roles(include_system)
            bindings = self.get_rbac_bindings(include_system)
        except Exception:
            return []

        role_idx = {(r['kind'], r['name'], r['namespace']): r for r in roles}

        def _is_wildcard(role):
            for rule in (role.get('rules') or []):
                ag  = rule.get('apiGroups') or []
                res = rule.get('resources') or []
                vb  = rule.get('verbs') or []
                if '*' in ag and '*' in res and '*' in vb:
                    return True
            return False

        risky = []
        for b in bindings:
            rr    = b.get('role_ref') or {}
            rname = rr.get('name', '')
            rkind = rr.get('kind', '')
            is_admin = (rkind == 'ClusterRole' and rname == 'cluster-admin')
            role = (role_idx.get(('ClusterRole', rname, ''))
                    or role_idx.get(('Role', rname, b.get('namespace', ''))))
            wild = bool(role and _is_wildcard(role))
            if not (is_admin or wild):
                continue
            reason = 'cluster-admin 바인딩' if is_admin else '와일드카드 권한(*/*/*)'
            for s in (b.get('subjects') or []):
                sname = s.get('name', '')
                if not include_system and sname.startswith('system:'):
                    continue
                risky.append({
                    'subject_kind': s.get('kind', ''),
                    'name':         sname,
                    'namespace':    s.get('namespace', '') or b.get('namespace', '') or '-',
                    'role':         rname,
                    'role_kind':    rkind,
                    'binding':      b.get('name', ''),
                    'binding_kind': b.get('kind', ''),
                    'reason':       reason,
                })
        return risky

    def get_kube_system_info(self):
        NS = 'kube-system'
        try:
            pods = self.core.list_namespaced_pod(NS).items
            deps = self.apps.list_namespaced_deployment(NS).items
            dss  = self.apps.list_namespaced_daemon_set(NS).items
            return {
                'pods': [{'name': p.metadata.name,
                          'status': p.status.phase or 'Unknown',
                          'restarts': sum(c.restart_count or 0
                                         for c in (p.status.container_statuses or [])),
                          'node': p.spec.node_name or '-'} for p in pods],
                'deployments': [{'name': d.metadata.name,
                                 'ready': f'{d.status.ready_replicas or 0}/{d.spec.replicas or 0}'}
                                for d in deps],
                'daemonsets':  [{'name': ds.metadata.name,
                                 'desired': ds.status.desired_number_scheduled or 0,
                                 'ready':   ds.status.number_ready or 0} for ds in dss],
            }
        except Exception:
            return {}
