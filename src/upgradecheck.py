# -*- coding: utf-8 -*-
"""K8s 업그레이드 사전 점검 (CHECK 탭, v1.4.1) — 수집(collect) + 판정(evaluate).

목표 버전으로 올리기 **전에** 막히거나 서비스가 끊길 곳을 찾는다. 클러스터는 바꾸지 않는다(GET 만).

판정 항목:
  1. 사라지는 API — 목표 버전에서 제거되는 apiVersion 을 누가 쓰는가. 세 곳에서 본다:
       · API 서버 지표 `apiserver_requested_deprecated_apis` — 실제로 그 API 를 **요청한** 기록.
         제거 버전(removed_release)이 서버가 직접 알려 주므로 아래 표에 없는 새 버전에도 통한다.
       · 오브젝트의 managedFields · last-applied-configuration — 그 버전으로 **써 넣은** 흔적
       · Helm 릴리스(최신 리비전)의 매니페스트 — 다음 `helm upgrade` 에서 실패할 것
  2. 버전 차이(skew) — 컨트롤 플레인을 목표로 올린 뒤 kubelet 이 3단계보다 뒤처지면 안 된다.
     한 번에 한 단계(마이너)씩만 올린다.
  3. 노드 비우기(drain) 방해 — 허용 중단 0 인 PDB, 컨트롤러 없는 파드, 복제본 1개, emptyDir.
  4. 지금 상태 — NotReady 노드, 준비 안 된 kube-system 파드, 컨트롤 플레인 readyz.
  5. 애드온 — 설치된 주요 애드온과 버전(호환 여부는 각 프로젝트 표를 확인하도록 안내).

문구는 업무 문장 — [[ui-wording]].
"""
from __future__ import annotations

import base64
import gzip
import json
import re

# 쿠버네티스 공식 「Deprecated API Migration Guide」 기준 — (제거 버전 마이너, group/version, kind, 대체)
REMOVED_APIS = [
    (16, 'extensions/v1beta1', 'Deployment', 'apps/v1'), (16, 'extensions/v1beta1', 'DaemonSet', 'apps/v1'),
    (16, 'extensions/v1beta1', 'ReplicaSet', 'apps/v1'), (16, 'extensions/v1beta1', 'NetworkPolicy', 'networking.k8s.io/v1'),
    (16, 'apps/v1beta1', 'Deployment', 'apps/v1'), (16, 'apps/v1beta1', 'StatefulSet', 'apps/v1'),
    (16, 'apps/v1beta2', 'Deployment', 'apps/v1'), (16, 'apps/v1beta2', 'StatefulSet', 'apps/v1'),
    (16, 'apps/v1beta2', 'DaemonSet', 'apps/v1'), (16, 'apps/v1beta2', 'ReplicaSet', 'apps/v1'),
    (22, 'admissionregistration.k8s.io/v1beta1', 'MutatingWebhookConfiguration', 'admissionregistration.k8s.io/v1'),
    (22, 'admissionregistration.k8s.io/v1beta1', 'ValidatingWebhookConfiguration', 'admissionregistration.k8s.io/v1'),
    (22, 'apiextensions.k8s.io/v1beta1', 'CustomResourceDefinition', 'apiextensions.k8s.io/v1'),
    (22, 'apiregistration.k8s.io/v1beta1', 'APIService', 'apiregistration.k8s.io/v1'),
    (22, 'certificates.k8s.io/v1beta1', 'CertificateSigningRequest', 'certificates.k8s.io/v1'),
    (22, 'coordination.k8s.io/v1beta1', 'Lease', 'coordination.k8s.io/v1'),
    (22, 'extensions/v1beta1', 'Ingress', 'networking.k8s.io/v1'),
    (22, 'networking.k8s.io/v1beta1', 'Ingress', 'networking.k8s.io/v1'),
    (22, 'networking.k8s.io/v1beta1', 'IngressClass', 'networking.k8s.io/v1'),
    (22, 'rbac.authorization.k8s.io/v1beta1', 'ClusterRole', 'rbac.authorization.k8s.io/v1'),
    (22, 'rbac.authorization.k8s.io/v1beta1', 'ClusterRoleBinding', 'rbac.authorization.k8s.io/v1'),
    (22, 'rbac.authorization.k8s.io/v1beta1', 'Role', 'rbac.authorization.k8s.io/v1'),
    (22, 'rbac.authorization.k8s.io/v1beta1', 'RoleBinding', 'rbac.authorization.k8s.io/v1'),
    (22, 'scheduling.k8s.io/v1beta1', 'PriorityClass', 'scheduling.k8s.io/v1'),
    (22, 'storage.k8s.io/v1beta1', 'CSIDriver', 'storage.k8s.io/v1'),
    (22, 'storage.k8s.io/v1beta1', 'CSINode', 'storage.k8s.io/v1'),
    (22, 'storage.k8s.io/v1beta1', 'StorageClass', 'storage.k8s.io/v1'),
    (22, 'storage.k8s.io/v1beta1', 'VolumeAttachment', 'storage.k8s.io/v1'),
    (25, 'batch/v1beta1', 'CronJob', 'batch/v1'),
    (25, 'discovery.k8s.io/v1beta1', 'EndpointSlice', 'discovery.k8s.io/v1'),
    (25, 'autoscaling/v2beta1', 'HorizontalPodAutoscaler', 'autoscaling/v2'),
    (25, 'policy/v1beta1', 'PodDisruptionBudget', 'policy/v1'),
    (25, 'policy/v1beta1', 'PodSecurityPolicy', '(대체 없음 — Pod Security Admission)'),
    (25, 'node.k8s.io/v1beta1', 'RuntimeClass', 'node.k8s.io/v1'),
    (26, 'flowcontrol.apiserver.k8s.io/v1beta1', 'FlowSchema', 'flowcontrol.apiserver.k8s.io/v1'),
    (26, 'flowcontrol.apiserver.k8s.io/v1beta1', 'PriorityLevelConfiguration', 'flowcontrol.apiserver.k8s.io/v1'),
    (26, 'autoscaling/v2beta2', 'HorizontalPodAutoscaler', 'autoscaling/v2'),
    (27, 'storage.k8s.io/v1beta1', 'CSIStorageCapacity', 'storage.k8s.io/v1'),
    (29, 'flowcontrol.apiserver.k8s.io/v1beta2', 'FlowSchema', 'flowcontrol.apiserver.k8s.io/v1'),
    (29, 'flowcontrol.apiserver.k8s.io/v1beta2', 'PriorityLevelConfiguration', 'flowcontrol.apiserver.k8s.io/v1'),
    (32, 'flowcontrol.apiserver.k8s.io/v1beta3', 'FlowSchema', 'flowcontrol.apiserver.k8s.io/v1'),
    (32, 'flowcontrol.apiserver.k8s.io/v1beta3', 'PriorityLevelConfiguration', 'flowcontrol.apiserver.k8s.io/v1'),
]
TABLE_KNOWN_UNTIL = 32          # 표가 아는 제거 버전의 끝 — 그 뒤는 API 서버 지표가 알려 준다

# v1.5.24 — 공식 출처에서 만든 표(src/_k8s_upgrade_data.py)가 있으면 그것을 쓴다(사라지는 API 안내 전체 + 최신 버전까지 확인한 범위)
from src import upgraderules as UR                                    # noqa: E402 — 표 판정 · 애플리케이션 점검
if UR.removed_apis():
    REMOVED_APIS = UR.removed_apis()
    TABLE_KNOWN_UNTIL = max(UR.latest_minor() or 0, max(r[0] for r in REMOVED_APIS))

# 지금 버전으로 읽어 managedFields 를 볼 종류 → 목록 경로 (kind 별로 지금 쓰는 버전)
KIND_PATHS = {
    'Deployment': '/apis/apps/v1/deployments', 'DaemonSet': '/apis/apps/v1/daemonsets',
    'StatefulSet': '/apis/apps/v1/statefulsets', 'ReplicaSet': None,      # 디플로이먼트가 만든다 — 사람이 안 쓴다
    'NetworkPolicy': '/apis/networking.k8s.io/v1/networkpolicies',
    'Ingress': '/apis/networking.k8s.io/v1/ingresses', 'IngressClass': '/apis/networking.k8s.io/v1/ingressclasses',
    'CronJob': '/apis/batch/v1/cronjobs', 'HorizontalPodAutoscaler': '/apis/autoscaling/v2/horizontalpodautoscalers',
    'PodDisruptionBudget': '/apis/policy/v1/poddisruptionbudgets', 'PriorityClass': '/apis/scheduling.k8s.io/v1/priorityclasses',
    'ClusterRole': '/apis/rbac.authorization.k8s.io/v1/clusterroles', 'ClusterRoleBinding': '/apis/rbac.authorization.k8s.io/v1/clusterrolebindings',
    'Role': '/apis/rbac.authorization.k8s.io/v1/roles', 'RoleBinding': '/apis/rbac.authorization.k8s.io/v1/rolebindings',
    'MutatingWebhookConfiguration': '/apis/admissionregistration.k8s.io/v1/mutatingwebhookconfigurations',
    'ValidatingWebhookConfiguration': '/apis/admissionregistration.k8s.io/v1/validatingwebhookconfigurations',
    'CustomResourceDefinition': '/apis/apiextensions.k8s.io/v1/customresourcedefinitions',
    'StorageClass': '/apis/storage.k8s.io/v1/storageclasses', 'CSIDriver': '/apis/storage.k8s.io/v1/csidrivers',
    'RuntimeClass': '/apis/node.k8s.io/v1/runtimeclasses',
    'FlowSchema': '/apis/flowcontrol.apiserver.k8s.io/v1/flowschemas',
    'PriorityLevelConfiguration': '/apis/flowcontrol.apiserver.k8s.io/v1/prioritylevelconfigurations',
}

KUBELET_MAX_SKEW = 3            # 1.28+ — kubelet 은 API 서버보다 3단계까지 뒤처질 수 있다
MAX_HELM_RELEASES = 300

# 이미지 이름으로 알아보는 주요 애드온 — (표시 이름, 이미지 정규식)
ADDONS = [
    ('ingress-nginx', r'ingress-nginx/controller|nginx-ingress-controller'),
    ('Traefik', r'(^|/)traefik:'),
    ('cert-manager', r'cert-manager-controller'),
    ('Calico', r'calico/node'), ('Cilium', r'cilium/cilium:|cilium/cilium@'), ('Canal · Flannel', r'flannel'),
    ('CoreDNS', r'coredns'), ('metrics-server', r'metrics-server'),
    ('Longhorn', r'longhornio/longhorn-manager'), ('Argo CD', r'argoproj/argocd'),
    ('Velero', r'velero/velero:'), ('Rancher', r'rancher/rancher:'),
    ('Prometheus Operator', r'prometheus-operator/prometheus-operator'),
]

SEV_ORDER = {'block': 0, 'warn': 1, 'info': 2}


def minor_of(ver: str) -> tuple[int, int] | None:
    m = re.match(r'v?(\d+)\.(\d+)', str(ver or ''))
    return (int(m.group(1)), int(m.group(2))) if m else None


def removed_between(cur_minor: int, target_minor: int):
    """현재 < 제거 버전 <= 목표 인 항목 — 이번 업그레이드 경로에서 사라지는 것"""
    return [r for r in REMOVED_APIS if cur_minor < r[0] <= target_minor]


# ── 수집 ────────────────────────────────────────────────────────────────────
def _get(api_client, path, accept='application/json', text=False, timeout=None, query=None):
    from src.k8s_http import DEFAULT_TIMEOUT
    resp = api_client.call_api(path, 'GET', query_params=query or [], header_params={'Accept': accept},
                               auth_settings=['BearerToken'],
                               _preload_content=False, _return_http_data_only=True,
                               _request_timeout=timeout or DEFAULT_TIMEOUT)
    try:
        raw = resp.data
    finally:
        try:
            resp.release_conn()
        except Exception:
            pass
    if text:
        return (raw or b'').decode('utf-8', 'replace')
    return json.loads(raw or b'{}')


def _items(api_client, path, errors, label=''):
    try:
        return _get(api_client, path).get('items') or []
    except Exception as e:
        errors.append(f'{label or path}: {_short_err(e)}')
        return []


def _short_err(e):
    s = getattr(e, 'status', None)
    if s == 403:
        return '권한 없음(403)'
    if s == 404:
        return '이 클러스터에 없음(404)'
    return f'{type(e).__name__}: {str(e)[:120]}'


def decode_helm_release(b64: str) -> dict | None:
    """Secret data.release → 릴리스 JSON (base64 두 번 + gzip)."""
    try:
        raw = base64.b64decode(base64.b64decode(b64))
        if raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        return json.loads(raw)
    except Exception:
        return None


def manifest_kinds(manifest: str):
    """Helm 매니페스트(여러 문서) → [(apiVersion, kind, name)]"""
    out = []
    for doc in re.split(r'^---\s*$', manifest or '', flags=re.M):
        av = re.search(r'^apiVersion:\s*["\']?([^\s"\']+)', doc, re.M)
        kd = re.search(r'^kind:\s*["\']?([^\s"\']+)', doc, re.M)
        nm = re.search(r'^metadata:\s*\n(?:[ \t]+.*\n)*?[ \t]+name:\s*["\']?([^\s"\']+)', doc + '\n', re.M)
        if av and kd:
            out.append((av.group(1), kd.group(1), nm.group(1) if nm else ''))
    return out


def parse_deprecated_metrics(text: str):
    """`apiserver_requested_deprecated_apis{group,version,resource,removed_release}` — 값 1 인 것"""
    out = []
    for ln in (text or '').splitlines():
        if not ln.startswith('apiserver_requested_deprecated_apis{'):
            continue
        m = re.match(r'apiserver_requested_deprecated_apis\{([^}]*)\}\s+([0-9.eE+-]+)', ln)
        if not m:
            continue
        labels = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if float(m.group(2)) <= 0:
            continue
        out.append({'group': labels.get('group', ''), 'version': labels.get('version', ''),
                    'resource': labels.get('resource', ''), 'subresource': labels.get('subresource', ''),
                    'removed_release': labels.get('removed_release', '')})
    return out


def collect(k8s, target: str, progress=lambda *_: None) -> dict:
    """클러스터에서 판정에 쓸 것을 모은다(GET 만). target = '1.36' 같은 문자열."""
    api = k8s._api_client
    errors = []
    data = {'errors': errors, 'target': target}
    progress('버전 확인')
    v = _get(api, '/version')
    data['version'] = v.get('gitVersion', '')
    cur = minor_of(data['version'])
    tgt = minor_of(target)
    data['cur_minor'], data['target_minor'] = (cur[1] if cur else None), (tgt[1] if tgt else None)

    progress('노드')
    data['nodes'] = [{
        'name': n['metadata']['name'],
        'kubelet': (n.get('status', {}).get('nodeInfo') or {}).get('kubeletVersion', ''),
        'runtime': (n.get('status', {}).get('nodeInfo') or {}).get('containerRuntimeVersion', ''),
        'os': (n.get('status', {}).get('nodeInfo') or {}).get('osImage', ''),
        'kernel': (n.get('status', {}).get('nodeInfo') or {}).get('kernelVersion', ''),
        'ready': any(c.get('type') == 'Ready' and c.get('status') == 'True'
                     for c in (n.get('status', {}).get('conditions') or [])),
        'control_plane': any(k in (n['metadata'].get('labels') or {}) for k in
                             ('node-role.kubernetes.io/control-plane', 'node-role.kubernetes.io/master')),
        'unschedulable': bool((n.get('spec') or {}).get('unschedulable')),
    } for n in _items(api, '/api/v1/nodes', errors, '노드')]

    progress('컨트롤 플레인 상태')
    try:
        data['readyz'] = _get(api, '/readyz', accept='text/plain', text=True, query=[('verbose', 'true')])
    except Exception as e:
        # readyz 가 실패하면 HTTP 500 과 함께 「[-]항목 failed」 본문을 준다 — 버리면 준비되지 않은 컨트롤 플레인이
        # 「일부를 확인하지 못했습니다(참고)」 로만 보였다(v1.4.13). 본문에 [-] 가 있으면 그대로 판정에 쓴다
        body = getattr(e, 'body', None)
        if isinstance(body, bytes):
            body = body.decode('utf-8', 'replace')
        if getattr(e, 'status', None) and body and '[-]' in str(body):
            data['readyz'] = str(body)
        else:
            data['readyz'] = None
            errors.append(f'readyz: {_short_err(e)}')

    progress('API 서버 지표(사라지는 API 요청 기록)')
    try:
        txt = _get(api, '/metrics', accept='text/plain', text=True, timeout=30)
        data['deprecated_requests'] = parse_deprecated_metrics(txt)
        data['metrics_ok'] = True
    except Exception as e:
        data['deprecated_requests'], data['metrics_ok'] = [], False
        errors.append(f'API 서버 지표: {_short_err(e)}')

    # 이번 경로에서 사라지는 종류만 managedFields · last-applied 를 본다
    progress('사라지는 API 를 쓴 흔적')
    gone = removed_between(data['cur_minor'] or 0, data['target_minor'] or 0) if cur and tgt else []
    kinds = sorted({r[2] for r in gone if KIND_PATHS.get(r[2])})
    gv_by_kind = {}
    for r in gone:
        gv_by_kind.setdefault(r[2], set()).add(r[1])
    writes = []
    for kind in kinds:
        for o in _items(api, KIND_PATHS[kind], errors, kind):
            md = o.get('metadata') or {}
            ref = {'kind': kind, 'namespace': md.get('namespace', ''), 'name': md.get('name', '')}
            for mf in md.get('managedFields') or []:
                if mf.get('apiVersion') in gv_by_kind[kind]:
                    writes.append({**ref, 'api': mf['apiVersion'], 'source': 'managedFields',
                                   'manager': mf.get('manager', '')})
            la = (md.get('annotations') or {}).get('kubectl.kubernetes.io/last-applied-configuration')
            if la:
                try:
                    av = json.loads(la).get('apiVersion')
                except Exception:
                    av = None
                if av in gv_by_kind[kind]:
                    writes.append({**ref, 'api': av, 'source': 'kubectl apply', 'manager': 'kubectl'})
    data['writes'] = writes

    progress('Helm 릴리스 매니페스트')
    data['helm'] = _helm_manifests(api, errors)

    progress('노드 비우기(drain) 방해 요소')
    data['pdbs'] = [_pdb_brief(p) for p in _items(api, '/apis/policy/v1/poddisruptionbudgets', errors, 'PodDisruptionBudget')]
    pods = _items(api, '/api/v1/pods', errors, '파드')
    data['pods'] = [_pod_brief(p) for p in pods]
    data['workloads'] = []
    for path, kind in (('/apis/apps/v1/deployments', 'Deployment'), ('/apis/apps/v1/statefulsets', 'StatefulSet')):
        for w in _items(api, path, errors, kind):
            data['workloads'].append(_workload_brief(w, kind))

    progress('CRD · 애드온')
    data['crds'] = []
    for c in _items(api, '/apis/apiextensions.k8s.io/v1/customresourcedefinitions', errors, 'CRD'):
        vs = (c.get('spec') or {}).get('versions') or []
        dep = [x['name'] for x in vs if x.get('deprecated') and x.get('served')]
        if dep:
            data['crds'].append({'name': c['metadata']['name'], 'deprecated': dep,
                                 'storage': next((x['name'] for x in vs if x.get('storage')), '')})
    imgs = set()
    for p in pods:
        for ctr in (p.get('spec') or {}).get('containers') or []:
            if ctr.get('image'):
                imgs.add(ctr['image'])
    data['images'] = sorted(imgs)
    # v1.5.24 — 공식 표 판정(기능 게이트 · 플래그 · 볼륨 종류 · 공식 안내 주제) · 설치된 애플리케이션 점검에 쓸 것
    try:
        UR.collect_extra(api, _get, _items, data, pods, errors, progress)
    except Exception as e:
        errors.append(f'추가 수집: {_short_err(e)}')
    return data


def _pod_brief(p):
    md, sp, st = p.get('metadata') or {}, p.get('spec') or {}, p.get('status') or {}
    owners = md.get('ownerReferences') or []
    return {
        'namespace': md.get('namespace'), 'name': md.get('name'), 'node': sp.get('nodeName', ''),
        'phase': st.get('phase'), 'owner': owners[0].get('kind') if owners else None,
        'mirror': 'kubernetes.io/config.mirror' in (md.get('annotations') or {}),
        'emptydir': any('emptyDir' in v for v in sp.get('volumes') or []),
        'ready': all(c.get('ready') for c in st.get('containerStatuses') or []) if st.get('containerStatuses') else False,
    }


def _owner_kinds(md):
    return [o.get('kind', '') for o in md.get('ownerReferences') or []]


def pdb_manager(p: dict) -> str:
    """PDB 를 누가 관리하나 — longhorn · rook · operator(다른 컨트롤러) · user(직접 · Helm).

    오퍼레이터가 만든 PDB 는 허용 중단 0 이 정상인 경우가 많고(Longhorn instance-manager 는 늘 0),
    직접 지우거나 고치면 오퍼레이터가 되돌리거나 · 지키던 데이터(볼륨 복제본 · Ceph OSD)를 잃을 수 있다(v1.4.13).
    """
    ns, name = p.get('namespace') or '', p.get('name') or ''
    labels, owners = p.get('labels') or {}, p.get('owners') or []
    if (ns == 'longhorn-system' and name.startswith('instance-manager')) or any(k.startswith('longhorn.io') for k in labels) \
            or any(k in ('InstanceManager', 'Volume', 'Node') and 'longhorn' in ns for k in owners):
        return 'longhorn'
    if ns.startswith('rook') or any(str(v).startswith('rook-ceph') for v in labels.values()) or 'CephCluster' in owners:
        return 'rook'
    managed_by = str(labels.get('app.kubernetes.io/managed-by', ''))
    if owners or (managed_by and managed_by.lower() not in ('helm', 'kubectl', 'kustomize')):
        return 'operator'
    return 'user'


def _pdb_brief(p):
    md, sp, st = p.get('metadata') or {}, p.get('spec') or {}, p.get('status') or {}
    return {
        'namespace': md.get('namespace'), 'name': md.get('name'),
        'allowed': st.get('disruptionsAllowed'), 'expected': st.get('expectedPods'),
        'healthy': st.get('currentHealthy'), 'desired': st.get('desiredHealthy'),
        'min_available': sp.get('minAvailable'), 'max_unavailable': sp.get('maxUnavailable'),
        'labels': md.get('labels') or {}, 'owners': _owner_kinds(md),
    }


def _workload_brief(w, kind):
    md, sp = w.get('metadata') or {}, w.get('spec') or {}
    tpl = ((sp.get('template') or {}).get('spec') or {})
    pvc = any('persistentVolumeClaim' in v for v in tpl.get('volumes') or []) or bool(sp.get('volumeClaimTemplates'))
    labels = md.get('labels') or {}
    return {'kind': kind, 'namespace': md.get('namespace'), 'name': md.get('name'),
            'replicas': sp.get('replicas', 1), 'pvc': pvc,
            'recreate': ((sp.get('strategy') or {}).get('type') == 'Recreate'),
            'managed': bool(_owner_kinds(md)) or str(labels.get('app.kubernetes.io/managed-by', '')).lower() not in ('', 'helm', 'kubectl', 'kustomize')}


def _helm_manifests(api, errors):
    """릴리스마다 **최신 리비전 하나**만 받아 매니페스트의 (apiVersion, kind) 를 본다."""
    try:
        from src.k8s_fast import list_metadata
        metas = list_metadata(api, '/api/v1/secrets', label_selector='owner=helm',
                              field_selector='type=helm.sh/release.v1').items
    except Exception as e:
        errors.append(f'Helm 릴리스: {_short_err(e)}')
        return None                                  # 못 본 것 — 「문제 없음」 과 구별한다
    latest = {}
    for m in metas:
        md = m.get('metadata') or {}
        lb = md.get('labels') or {}
        key = (md.get('namespace'), lb.get('name'))
        try:
            rev = int(lb.get('version', 0))
        except ValueError:
            rev = 0
        if lb.get('status') not in ('deployed', 'failed', 'pending-upgrade', None):
            continue
        if key not in latest or rev > latest[key][0]:
            latest[key] = (rev, md.get('name'))
    out = []
    for (ns, rname), (rev, sname) in list(latest.items())[:MAX_HELM_RELEASES]:
        try:
            s = _get(api, f'/api/v1/namespaces/{ns}/secrets/{sname}')
        except Exception as e:
            errors.append(f'Helm {ns}/{rname}: {_short_err(e)}')
            continue
        rel = decode_helm_release((s.get('data') or {}).get('release', ''))
        if not rel:
            continue
        chart = ((rel.get('chart') or {}).get('metadata') or {})
        out.append({'namespace': ns, 'release': rname, 'revision': rev,
                    'chart': f"{chart.get('name', '')}-{chart.get('version', '')}",
                    'objects': manifest_kinds(rel.get('manifest', ''))})
    return out


# ── 판정 ────────────────────────────────────────────────────────────────────
def evaluate(data: dict) -> dict:
    cur, tgt = data.get('cur_minor'), data.get('target_minor')
    findings, passed = [], []

    def add(sev, cat, title, detail='', items=None, action=''):
        findings.append({'severity': sev, 'category': cat, 'title': title, 'detail': detail,
                         'items': (items or [])[:200], 'more': max(0, len(items or []) - 200), 'action': action})

    if cur is None or tgt is None:
        add('block', 'version', '버전을 읽지 못했습니다', f"서버 버전: {data.get('version') or '알 수 없음'}")
        return _result(data, findings, passed)
    steps = list(range(cur + 1, tgt + 1))
    if tgt <= cur:
        add('info', 'version', '목표 버전이 지금 버전보다 높지 않습니다', f'지금 1.{cur} · 목표 1.{tgt}')
    elif len(steps) > 1:
        add('warn', 'version', f'한 번에 한 단계씩 올려야 합니다 — {len(steps)}단계',
            '쿠버네티스는 마이너 버전을 건너뛰어 올릴 수 없습니다. 단계마다 이 점검을 다시 실행하세요.',
            [f'1.{s - 1} → 1.{s}' for s in steps], '순서대로: ' + ' → '.join(f'1.{s}' for s in [cur] + steps))
    else:
        passed.append(f'1.{cur} → 1.{tgt} — 한 단계 업그레이드입니다')

    # 1) 사라지는 API ─────────────────────────────────────────────────────────
    gone = removed_between(cur, tgt)
    gone_gv = {(r[1], r[2]): r for r in gone}
    req = []
    for d in data.get('deprecated_requests') or []:
        rr = minor_of(d.get('removed_release'))
        if rr and cur < rr[1] <= tgt:
            gv = f"{d['group']}/{d['version']}" if d.get('group') else d.get('version')
            req.append(f"{gv} {d['resource']}{('/' + d['subresource']) if d.get('subresource') else ''} — 1.{rr[1]} 에서 제거")
    if req:
        add('block', 'api', f'제거될 API 를 요청한 기록이 있습니다 — {len(req)}종류',
            'API 서버가 최근에 받은 요청 중, 목표 버전에서 사라지는 API 를 쓴 것이 있습니다. '
            '요청한 프로그램(배포 도구 · 오퍼레이터 · 스크립트)을 찾아 새 버전으로 바꿔야 합니다.',
            sorted(set(req)), 'API 서버 감사 로그나 각 오퍼레이터의 버전을 확인해 새 apiVersion 으로 바꾸세요.')
    elif data.get('metrics_ok'):
        # 이 지표는 API 서버가 마지막으로 시작된 뒤 · 응답한 그 인스턴스 기준이다 — 가끔 도는 작업은 빠질 수 있다
        passed.append('API 서버 지표: 제거될 API 를 요청한 기록이 없습니다(이 API 서버 인스턴스가 시작된 뒤 기준 — '
                      '가끔 도는 CronJob · CI 배포는 빠질 수 있으니 매니페스트도 확인하세요)')
    later = sorted({(f"{d['group']}/{d['version']}" if d.get('group') else d.get('version')) + f" {d['resource']}"
                    + (f" — 1.{minor_of(d['removed_release'])[1]} 에서 제거 예정" if minor_of(d.get('removed_release')) else ' — 제거 일정 없음')
                    for d in data.get('deprecated_requests') or []
                    if not (minor_of(d.get('removed_release')) and cur < minor_of(d['removed_release'])[1] <= tgt)})
    if later:
        add('info', 'api', f'더 이상 권장하지 않는 API 요청 — {len(later)}종류(이번 업그레이드와는 무관)',
            '이번 목표 버전에서는 동작하지만 언젠가 사라집니다. 쓰는 프로그램을 미리 확인해 두세요.', later)

    w = [f"{x['kind']} {(x['namespace'] + '/') if x['namespace'] else ''}{x['name']} — {x['api']} "
         f"({x['source']}{', ' + x['manager'] if x['manager'] and x['source'] == 'managedFields' else ''})"
         for x in data.get('writes') or []]
    if w:
        add('warn', 'api', f'제거될 API 버전으로 작성된 오브젝트 — {len(w)}건',
            '이 오브젝트는 클러스터 안에서는 자동 변환되어 계속 동작하지만, 같은 매니페스트로 다시 적용하면 '
            '목표 버전에서 실패합니다. 원본 매니페스트(저장소 · CI)의 apiVersion 을 바꾸세요.',
            sorted(set(w)))
    elif gone:
        passed.append('제거될 API 버전으로 작성된 오브젝트가 없습니다')

    hb = []
    for h in data.get('helm') or []:
        for av, kind, name in h['objects']:
            r = gone_gv.get((av, kind))
            if r:
                hb.append(f"{h['namespace']}/{h['release']} ({h['chart']}) — {kind} {name}: {av} → {r[3]} (1.{r[0]} 에서 제거)")
    if hb:
        add('block', 'api', f'Helm 릴리스가 제거될 API 를 씁니다 — {len(hb)}건',
            '업그레이드 뒤에는 이 릴리스를 helm upgrade · rollback 할 수 없게 됩니다. '
            '차트를 새 버전으로 올리거나, 업그레이드 뒤라면 helm-mapkubeapis 로 릴리스 기록을 고쳐야 합니다.',
            hb, '업그레이드 전에 해당 차트를 새 API 를 쓰는 버전으로 올리세요.')
    elif data.get('helm') is not None:
        passed.append(f"Helm 릴리스 {len(data['helm'])}개: 제거될 API 를 쓰지 않습니다")
    if tgt > TABLE_KNOWN_UNTIL:
        passed.append(f'참고: 1.{TABLE_KNOWN_UNTIL + 1} 이후 제거 API 는 Polaris 표에 없고(그 버전의 공식 안내가 아직 없음), API 서버 지표로 확인합니다')

    crd = [f"{c['name']} — {', '.join(c['deprecated'])} (저장 버전 {c['storage']})" for c in data.get('crds') or []]
    if crd:
        add('info', 'api', f'더 이상 권장하지 않는 버전을 제공하는 CRD — {len(crd)}개',
            '쿠버네티스 업그레이드와 무관하게 해당 오퍼레이터가 언젠가 그 버전을 뺍니다. 오퍼레이터 업그레이드 계획에 넣으세요.', crd)

    # 2) 버전 차이 ────────────────────────────────────────────────────────────
    nodes = data.get('nodes') or []
    lag, newer = [], []
    for n in nodes:
        km = minor_of(n['kubelet'])
        if km and tgt - km[1] > KUBELET_MAX_SKEW:
            lag.append(f"{n['name']} — kubelet {n['kubelet']}")
        if km and km[1] > cur:
            newer.append(f"{n['name']} — kubelet {n['kubelet']}")
    if lag:
        add('block', 'skew', f'목표 버전과 차이가 큰 노드 — {len(lag)}대',
            f'kubelet 은 API 서버보다 {KUBELET_MAX_SKEW}단계까지만 뒤처질 수 있습니다. 이 노드의 kubelet 을 지금 API 서버 버전(1.{cur}) 이하로 '
            '먼저 올리세요 — 목표 버전으로 바로 올리면 kubelet 이 API 서버보다 새 버전이 됩니다.', lag)
    if newer:
        add('warn', 'skew', f'API 서버보다 kubelet 이 새 노드 — {len(newer)}대',
            'kubelet 은 API 서버보다 새면 안 됩니다. 컨트롤 플레인부터 올렸는지 확인하세요.', newer)
    vers = sorted({n['kubelet'] for n in nodes if n['kubelet']})
    if len(vers) > 1:
        add('info', 'skew', f'노드 버전이 섞여 있습니다 — {len(vers)}가지', '이전 업그레이드가 끝나지 않았을 수 있습니다.',
            [f"{v}: {', '.join(n['name'] for n in nodes if n['kubelet'] == v)}" for v in vers])
    elif nodes and not lag:
        passed.append(f'노드 {len(nodes)}대의 kubelet 버전이 같고 차이 허용 범위 안입니다')
    # Docker 엔진: 그 노드의 kubelet 이 1.24 미만이면 dockershim 이라 막고, 1.24 이상이면 이미 cri-dockerd 다(v1.4.13 —
    # 예전엔 클러스터가 이미 1.24 이상이어도 막았다)
    def _kminor(n):
        km = minor_of(n['kubelet'])
        return km[1] if km else None
    dnodes = [n for n in nodes if n['runtime'].startswith('docker://')]
    shim = [f"{n['name']} — {n['runtime']}" for n in dnodes if (_kminor(n) or 0) < 24]
    cri = [f"{n['name']} — {n['runtime']}" for n in dnodes if (_kminor(n) or 0) >= 24]
    if shim and tgt >= 24:
        add('block', 'skew', f'Docker 엔진을 컨테이너 런타임으로 쓰는 노드 — {len(shim)}대',
            '1.24 부터 kubelet 이 Docker 엔진(dockershim)을 직접 지원하지 않습니다. containerd 로 바꾸거나 cri-dockerd 를 설치해야 합니다.', shim)
    if cri:
        add('info', 'skew', f'cri-dockerd(Docker 엔진)로 도는 노드 — {len(cri)}대',
            '이미 cri-dockerd 를 쓰고 있습니다. 설치된 cri-dockerd 가 목표 버전을 지원하는지 확인하세요.', cri)

    # 3) 지금 상태 ────────────────────────────────────────────────────────────
    nr = [n['name'] for n in nodes if not n['ready']]
    if nr:
        add('block', 'health', f'준비되지 않은(NotReady) 노드 — {len(nr)}대', '업그레이드 전에 원인을 해결하세요.', nr)
    elif nodes:
        passed.append('모든 노드가 Ready 입니다')
    if len(nodes) == 1:
        add('warn', 'health', '노드가 1대뿐입니다',
            '노드를 비우면 옮겨 갈 곳이 없어 업그레이드하는 동안 모든 서비스가 중단됩니다. 작업 시간을 공지하세요.',
            [nodes[0]['name']])
    cordon = [n['name'] for n in nodes if n['unschedulable']]
    if cordon:
        add('info', 'health', f'스케줄링이 막힌(cordon) 노드 — {len(cordon)}대', '이전 작업이 끝나지 않았는지 확인하세요.', cordon)
    rz = data.get('readyz')
    if rz is not None:
        bad = [ln.strip() for ln in rz.splitlines() if ln.strip().startswith('[-]')]
        if bad:
            add('block', 'health', '컨트롤 플레인 점검 항목에 실패가 있습니다(readyz)', '', bad)
        else:
            passed.append('컨트롤 플레인 readyz 가 모두 정상입니다')
    pods = data.get('pods') or []
    ks = [f"{p['name']} ({p['phase']})" for p in pods if p['namespace'] == 'kube-system'
          and p['phase'] not in ('Succeeded',) and not (p['phase'] == 'Running' and p['ready'])]
    if ks:
        add('warn', 'health', f'준비되지 않은 kube-system 파드 — {len(ks)}개', '시스템 구성 요소가 불안정한 상태에서 올리면 원인을 가리기 어렵습니다.', ks)

    # 4) 노드 비우기(drain) 방해 ───────────────────────────────────────────────
    # PDB 는 누가 만들었는지로 나눠 안내한다(v1.4.13). 예전엔 모두 「복제본을 늘리거나 PDB 를 잠시 조정」 이라 적어
    # Longhorn 이 지키는 PDB 를 지우게 만들 수 있었다 — 그러면 볼륨의 하나 남은 복제본이 있는 노드를 비울 수 있다
    zero = [p for p in data.get('pdbs') or [] if p.get('allowed') == 0 and (p.get('expected') or 0) > 0]
    fmt = lambda p: f"{p['namespace']}/{p['name']} (허용 중단 {p['allowed']} · 파드 {p['expected']})"
    by = {k: [p for p in zero if pdb_manager(p) == k] for k in ('longhorn', 'rook', 'operator', 'user')}
    if by['longhorn']:
        add('info', 'drain', f'Longhorn 이 관리하는 PodDisruptionBudget — {len(by["longhorn"])}개 (직접 고치지 마세요)',
            'Longhorn 이 노드마다 instance-manager 파드를 지키려고 스스로 만든 PDB 입니다. 평소에도 허용 중단이 0 인 것이 정상이고, '
            '노드를 비울 때 Longhorn 이 그 노드의 볼륨이 안전한지(설정 Node Drain Policy 기준) 보고 스스로 풉니다. '
            'PDB 를 지우거나 고치면 볼륨의 하나 남은 정상 복제본이 있는 노드를 비우게 되어 데이터를 잃을 수 있습니다.',
            [fmt(p) for p in by['longhorn']],
            '노드를 비우기 전에 Longhorn UI 에서 모든 볼륨이 Healthy 이고 복제본이 여러 노드에 나뉘어 있는지 확인하세요. '
            'drain 이 오래 멈추면 PDB 가 아니라 그 노드에만 남은 복제본과 Node Drain Policy 를 확인하세요.')
    if by['rook']:
        add('info', 'drain', f'Rook-Ceph 가 관리하는 PodDisruptionBudget — {len(by["rook"])}개 (직접 고치지 마세요)',
            'Rook 이 Ceph OSD · MON 을 지키려고 만든 PDB 입니다. 한 노드를 비우는 동안 다른 노드의 PDB 가 0 이 되는 것이 정상입니다. '
            '직접 고치면 여러 OSD 가 함께 내려가 데이터에 접근하지 못할 수 있습니다.',
            [fmt(p) for p in by['rook']],
            '노드를 비우기 전에 ceph status 가 HEALTH_OK 인지 확인하고, 한 노드씩 비운 뒤 다시 HEALTH_OK 가 될 때까지 기다리세요.')
    if by['operator']:
        add('info', 'drain', f'오퍼레이터가 만든 PodDisruptionBudget — {len(by["operator"])}개',
            '컨트롤러(오퍼레이터)가 만들고 관리하는 PDB 입니다. 직접 고치면 되돌려지거나, 그 오퍼레이터가 지키던 것(쿼럼 · 데이터)이 깨질 수 있습니다.',
            [fmt(p) for p in by['operator']],
            '각 오퍼레이터 문서의 노드 유지보수 절차를 따르세요. drain 이 멈추면 그 오퍼레이터가 관리하는 파드의 상태부터 확인하세요.')
    user = by['user']
    if user:
        unhealthy = [p for p in user if p.get('healthy') is not None and p.get('desired') is not None and p['healthy'] < p['desired']]
        tight = [p for p in user if p not in unhealthy]
        detail = 'drain 이 이 PDB 가 지키는 파드를 옮기지 못하고 기다립니다.'
        if unhealthy:
            detail += f" 이 중 {len(unhealthy)}개는 지금 준비되지 않은 파드가 있어 0 입니다 — 먼저 그 파드를 정상으로 돌리세요."
        if tight:
            detail += f" {len(tight)}개는 설정상 파드를 하나도 내려놓을 수 없습니다(minAvailable = 복제본 수 또는 maxUnavailable 0)."
        add('warn', 'drain', f'노드 비우기를 멈추게 할 PodDisruptionBudget — {len(user)}개', detail,
            [fmt(p) + (' · 준비 안 된 파드 있음' if p in unhealthy else '') for p in user],
            '무상태 서비스면 업그레이드 전에 복제본을 늘려 허용 중단이 1 이상이 되게 하세요. 복제본을 늘릴 수 없는 서비스(단일 DB 등)는 '
            '담당자와 중단 시간을 정하세요. PDB 를 지우거나 고치는 것은 서비스 담당자와 확인한 뒤에만 하고, 작업이 끝나면 원래대로 되돌리세요.')
    pdb = user
    bare = [f"{p['namespace']}/{p['name']}" for p in pods if not p['owner'] and not p['mirror']
            and p['phase'] in ('Running', 'Pending')]
    if bare:
        add('warn', 'drain', f'컨트롤러 없이 직접 만든 파드 — {len(bare)}개',
            '노드를 비울 때 삭제되고 다시 만들어지지 않습니다(drain 은 --force 가 있어야 진행).', bare)
    ones = [w for w in data.get('workloads') or [] if w.get('replicas') == 1 and w['namespace'] not in ('kube-system',)]
    if ones:
        # 복제본을 늘리면 안 되는 것을 따로 표시한다(v1.4.13) — StatefulSet(단일 DB 등) · 볼륨(PVC)을 쓰는 것 ·
        # Recreate 전략은 두 개로 늘리면 같은 볼륨을 두 파드가 쓰려다 멈추거나 데이터가 깨질 수 있다
        def tag(w):
            why = [x for x, on in (('StatefulSet', w['kind'] == 'StatefulSet'), ('볼륨 사용', w.get('pvc')),
                                   ('Recreate', w.get('recreate'))) if on]
            t = f"{w['kind']} {w['namespace']}/{w['name']}"
            if why:
                t += f" — 늘리지 마세요({' · '.join(dict.fromkeys(why))})"
            elif w.get('managed'):
                t += ' — 오퍼레이터가 관리(직접 늘리면 되돌려짐)'
            return t
        stateful = sum(1 for w in ones if w['kind'] == 'StatefulSet' or w.get('pvc') or w.get('recreate'))
        add('info', 'drain', f'복제본이 1개인 워크로드 — {len(ones)}개',
            '해당 파드가 있는 노드를 비우는 동안 잠시 서비스가 중단됩니다. '
            '무상태 서비스는 업그레이드 동안 복제본을 2개로 늘리면 중단을 피할 수 있습니다(Helm · 오퍼레이터가 관리하면 그쪽 설정으로). '
            + (f'「늘리지 마세요」 로 표시한 {stateful}개는 단일 DB · 볼륨을 한 파드만 쓰는 구조일 수 있어, 늘리면 멈추거나 데이터가 깨질 수 있습니다 — '
               '늘리지 말고 중단 시간을 공지하세요.' if stateful else ''),
            [tag(w) for w in ones])
    ed = [f"{p['namespace']}/{p['name']}" for p in pods if p['emptydir'] and p['owner'] and p['phase'] == 'Running'
          and p['namespace'] != 'kube-system']
    if ed:
        add('info', 'drain', f'emptyDir 을 쓰는 파드 — {len(ed)}개',
            '노드를 비우면 emptyDir 의 데이터가 사라집니다(drain 은 --delete-emptydir-data 가 필요). 임시 데이터인지 확인하세요.', ed)
    if not (zero or bare):
        passed.append('노드 비우기를 막는 PDB · 단독 파드가 없습니다')
    elif not (pdb or bare):
        passed.append('직접 만든 PDB · 단독 파드 중 노드 비우기를 막는 것은 없습니다(오퍼레이터가 관리하는 PDB 는 위 안내 참고)')

    # v1.5.24 — 공식 표 × 이 클러스터 · 설치된 애플리케이션
    try:
        UR.evaluate_extra(data, add, passed)
        UR.evaluate_apps(data, add, passed)
        UR.evaluate_addons(data, add, passed)              # v1.5.29 애드온 공식 호환표
        UR.evaluate_rke2(data, add, passed)                # v1.5.30 RKE2 업그레이드 경로
    except Exception as e:
        add('info', 'scope', '추가 판정 중 오류가 있었습니다', f'{type(e).__name__}: {e}')

    # 5) 애드온 ───────────────────────────────────────────────────────────────
    found = []
    for name, pat in ADDONS:
        tags = sorted({img for img in data.get('images') or [] if re.search(pat, img)})
        if tags:
            found.append(f"{name} — {', '.join(_tag(t) for t in tags)}")
    rke2 = '+rke2' in (data.get('version') or '')
    if found:
        add('info', 'addon', f'설치된 주요 애드온 — {len(found)}개',
            ('RKE2 에 함께 들어 있는 애드온(CoreDNS · ingress-nginx/Traefik · CNI · metrics-server)은 RKE2 와 함께 올라갑니다. '
             if rke2 else '') + '그 밖의 애드온은 각 프로젝트의 호환 버전 표에서 목표 버전을 지원하는지 확인하세요.', found)

    if data.get('errors'):
        add('info', 'scope', f'일부를 확인하지 못했습니다 — {len(data["errors"])}건',
            '권한이 없거나 이 클러스터에 없는 항목입니다. 결과가 완전하지 않을 수 있습니다.', data['errors'])
    return _result(data, findings, passed)


def _tag(img):
    t = img.rsplit('@', 1)[0]
    return t.rsplit(':', 1)[-1] if ':' in t.rsplit('/', 1)[-1] else 'latest'


DRAIN_STEP = '노드마다: 비우기(drain) → 업그레이드 → 상태 확인 → 다시 배치 허용(uncordon)'


def checklist(data: dict) -> list:
    """v1.5.61 검토: 「노드마다」 로 시작하는 RKE2 명령 줄을 비우기 단계로 잘못 찾아, 업그레이드 · 재시작이 비우기보다 앞에 나왔다
    → 비우기 단계는 문구 그대로 찾고, 업그레이드 명령은 비우기 단계 바로 뒤에 둔다."""
    rke2 = '+rke2' in (data.get('version') or '')
    out = ['etcd 스냅샷을 먼저 남기세요' + (' — rke2 etcd-snapshot save' if rke2 else ' — etcdctl snapshot save'),
           'Velero 등으로 중요한 네임스페이스를 백업하세요(되돌릴 길을 만든다)',
           '컨트롤 플레인(서버) 노드를 한 대씩 먼저 올리고, 그다음 워커(에이전트) 노드를 올립니다',
           DRAIN_STEP,
           '단계(마이너)마다 이 점검을 다시 실행하세요']
    if rke2:
        try:
            r2 = UR.rke2_checklist(data)                   # v1.5.30 — 이 클러스터의 실제 RKE2 판 순서
        except Exception:
            r2 = []
        cmd = [x for x in r2 if x.startswith('업그레이드 단계 명령')]
        r2 = [x for x in r2 if x not in cmd]
        out[2:2] = r2 or ['RKE2 는 system-upgrade-controller(Plan) 로 자동 진행하거나, 노드마다 설치 스크립트에 INSTALL_RKE2_VERSION 을 지정해 올립니다']
        d = out.index(DRAIN_STEP)
        out[d + 1:d + 1] = cmd
    mgr = {pdb_manager(p) for p in data.get('pdbs') or []}
    i = out.index(DRAIN_STEP)
    if 'longhorn' in mgr:
        out.insert(i, 'Longhorn: 노드를 비우기 전마다 모든 볼륨이 Healthy 인지 확인하세요 — instance-manager PDB 는 직접 고치지 않습니다')
    if 'rook' in mgr:
        out.insert(i, 'Rook-Ceph: 노드를 비우기 전마다 ceph status 가 HEALTH_OK 인지 확인하세요')
    try:
        extra = UR.extra_checklist(data)
    except Exception:
        extra = []
    try:
        first = UR.addon_checklist(data)                    # v1.5.29 — 쿠버네티스보다 먼저 올릴 애드온
    except Exception:
        first = []
    j = out.index(DRAIN_STEP)
    for t in reversed(extra):
        out.insert(j, t)
    # 백업(etcd 스냅샷 · Velero) 바로 뒤, 쿠버네티스를 올리기 전에
    k = next((i + 1 for i, x in enumerate(out) if x.startswith('Velero')), 0)
    for t in reversed(first):
        out.insert(k, t)
    return out


def _result(data, findings, passed):
    findings.sort(key=lambda f: SEV_ORDER.get(f['severity'], 9))
    counts = {k: sum(1 for f in findings if f['severity'] == k) for k in ('block', 'warn', 'info')}
    return {
        'version': data.get('version'), 'cur_minor': data.get('cur_minor'), 'target_minor': data.get('target_minor'),
        'rke2': '+rke2' in (data.get('version') or ''),
        'nodes': len(data.get('nodes') or []), 'helm_releases': len(data.get('helm') or []),
        'findings': findings, 'passed': passed, 'counts': counts,
        'verdict': 'blocked' if counts['block'] else ('caution' if counts['warn'] else 'ready'),
        'checklist': checklist(data),
    }


# ── 업그레이드 사전 점검 보고서 (DOCX, v1.4.4) — 모양은 공용 템플릿(src/docxreport.py) ──────
CATEGORY_KO = {'version': '버전 경로', 'api': '사라지는 API', 'skew': '버전 차이', 'health': '지금 상태',
               'drain': '노드 비우기', 'addon': '애드온', 'scope': '점검 범위',
               'gate': '기능 게이트 · 플래그', 'storage': '스토리지', 'notes': '공식 안내', 'app': '애플리케이션', 'rke2': 'RKE2'}


def write_docx(res: dict, meta: dict, path: str) -> str:
    """res = upgrade_check 결과(+ cluster). 판정 · 발견사항 · 확인 완료 · 업그레이드 순서 · 부록(제거 API 표)."""
    from src.docxreport import Report, Sev
    cur, tgt = res.get('cur_minor'), res.get('target_minor')
    cl = res.get('cluster') or ''
    verdict_text = {'blocked': f"판정: 업그레이드 전에 먼저 해결해야 할 문제 {res['counts'].get('block', 0)}건",
                    'caution': f"판정: 막는 문제는 없지만 주의할 항목 {res['counts'].get('warn', 0)}건",
                    'ready': '판정: 업그레이드를 막는 문제가 없습니다'}.get(res.get('verdict'), '')
    rep = Report('Kubernetes 업그레이드 사전 점검 보고서', footer=f"Polaris {meta.get('version', '')} · {meta.get('when', '')}")
    rep.cover(f"{cl + ' · ' if cl else ''}{res.get('version', '')} → 1.{tgt}",
              [('점검일', meta.get('when', '')), ('클러스터', cl or '—'), ('지금 버전', res.get('version', '')),
               ('목표 버전', f'1.{tgt}'), ('작성', meta.get('author', '') or '—'), ('조직', meta.get('org', '') or '—')],
              verdict=res.get('verdict'), verdict_text=verdict_text)

    rep.h1('1. 점검 요약')
    rep.callout(verdict_text, {'blocked': 'block', 'caution': 'warn', 'ready': 'ok'}.get(res.get('verdict'), 'info'))
    rep.kv([('클러스터', cl or '—'), ('지금 버전', res.get('version', '')), ('목표 버전', f'1.{tgt}'),
            ('업그레이드 경로', ' → '.join(f'1.{m}' for m in range(cur, tgt + 1)) if cur and tgt and tgt > cur else '—'),
            ('배포판', 'RKE2' if res.get('rke2') else '—'), ('노드', f"{res.get('nodes', 0)}대"),
            ('Helm 릴리스', f"{res.get('helm_releases', 0)}개")])
    rep.counts_table(res.get('counts') or {}, keys=('block', 'warn', 'info'))

    rep.h1('2. 발견사항')
    fs = res.get('findings') or []
    if fs:
        rep.table(['등급', '분류', '항목', '조치'],
                  [[Sev(f['severity']), CATEGORY_KO.get(f['category'], f['category']), f['title'], f.get('action') or f.get('detail', '')]
                   for f in fs], [2.0, 2.4, 6.6, 6.0])
        for i, f in enumerate(fs, 1):
            rep.h2(f"2.{i} {f['title']}")
            if f.get('detail'):
                rep.para(f['detail'], 9.5)
            if f.get('action'):
                rep.callout(f"조치: {f['action']}", f['severity'])
            if f.get('items'):
                rep.table(['대상'], [[x] for x in f['items'][:200]], [17], font_size=8.5)
                if f.get('more'):
                    rep.para(f"그 밖에 {f['more']}건", 9)
    else:
        rep.callout('확인할 발견사항이 없습니다.', 'ok')

    rep.h1('3. 확인 완료')
    if res.get('passed'):
        for t in res['passed']:
            rep.bullet(t)
    else:
        rep.para('(없음)')

    rep.h1('4. 업그레이드 순서')
    rep.table(['순서', '작업'], [[str(i), t] for i, t in enumerate(res.get('checklist') or [], 1)], [1.5, 15.5])

    rep.h1('부록. 점검 방법과 기준')
    rep.para('클러스터의 API 서버에 조회(GET)만 했습니다 — 클러스터를 변경하지 않음.', 9.5)
    for t in ('사라지는 API(요청 기록): API 서버 지표 apiserver_requested_deprecated_apis — 제거 버전은 API 서버가 알려 줌',
              '사라지는 API(작성된 흔적): 오브젝트의 managedFields · kubectl last-applied-configuration · Helm 릴리스 최신 리비전 매니페스트',
              f'버전 차이: kubelet 은 API 서버보다 {KUBELET_MAX_SKEW}단계까지만 뒤처질 수 있음(1.28+) · 마이너 버전은 건너뛸 수 없음',
              '노드 비우기: 허용 중단 0 인 PodDisruptionBudget · 컨트롤러 없는 파드 · 복제본 1개 · emptyDir',
              '지금 상태: 노드 Ready · /readyz · kube-system 파드'):
        rep.bullet(t)
    gone = removed_between(cur or 0, tgt or 0)
    if gone:
        rep.para('이번 경로에서 제거되는 API (공식 Deprecated API Migration Guide)', 9.5, True)
        rep.table(['제거 버전', 'apiVersion', 'kind', '대체'], [[f'1.{r[0]}', r[1], r[2], r[3]] for r in gone], [2.2, 6.0, 4.5, 4.3], font_size=8.5)
    else:
        rep.para(f'이번 경로(1.{cur} → 1.{tgt})에서 제거되는 API 는 Polaris 내장 표(1.{TABLE_KNOWN_UNTIL} 까지)에 없습니다 — '
                 'API 서버 지표가 알려 주는 제거 일정으로 판단했습니다.', 9)
    return rep.save(path)
