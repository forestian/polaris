"""DOCX / TXT / HTML 보고서 생성.

polaris.py 에서 분리된 보고서 모듈:
  - 데이터 수집  : _report_collect (K8sManager 메서드들을 묶어 한 번에 조회)
  - 평가/finding : _report_evaluate (이상 징후 + 권장사항 산출)
  - DOCX 작성   : _report_write_docx (가장 큼 — 표지/요약/상세/AI 분석)
  - TXT 작성    : _report_write_txt
  - HTML 보고서 : _build_report_html (요약 카드 + 표)
  - LLM 호출    : _llm_ask (외부 OpenAI 호환 엔드포인트)

PolarisAPI.start_report() 가 이 모듈의 함수들을 백그라운드 스레드에서 호출.
"""
import json
import re
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

from src.k8s import K8sManager, _age, _parse_cpu, _parse_mem, _pct, _parse_iso

# DOCX 의존 — frozen build 에서 hiddenimports 로 끌어옴
try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# ─────────────────────────────────────────────────────────────────────────────

try:
    from docx import Document as _DocxDoc
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OxmlElem
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

def _report_required_dataset_keys() -> list[str]:
    return [
        'nodes', 'node_metrics', 'namespaces', 'pods', 'pod_metrics',
        'deployments', 'statefulsets', 'daemonsets', 'jobs', 'cronjobs',
        'services', 'ingresses', 'ingress_classes',
        'pvcs', 'pvs', 'configmaps', 'secrets', 'helm',
        'hpa', 'pdbs', 'network_policies', 'storage_classes',
        'resource_quotas', 'limit_ranges', 'rbac', 'kube_system', 'events',
        'readyz',
    ]


_REPORT_SEVERITY_LEVEL = {
    'critical': 'CRITICAL',
    'high': 'HIGH',
    'medium': 'WARNING',
    'low': 'INFO',
    'info': 'INFO',
}


def _report_org():
    """보고서 작성 조직명 — 이 판은 조직 정보를 싣지 않는다."""
    return None


def _report_finding(category: str, severity: str, namespace: str, name: str,
                    value: str, detail: str, rec: str) -> dict:
    severity = (severity or 'info').lower()
    level = _REPORT_SEVERITY_LEVEL.get(severity, 'INFO')
    namespace = namespace or 'cluster'
    name = name or '-'
    value = str(value or '-')
    detail = str(detail or '')
    rec = str(rec or '')
    message = f'{namespace}/{name}: {value} — {detail}'
    if rec:
        message += f' | 권장: {rec}'
    return {
        'level': level,
        'severity': severity,
        'category': category,
        'namespace': namespace,
        'name': name,
        'value': value,
        'detail': detail,
        'rec': rec,
        'message': message,
    }


def _report_build_priority_summary(findings: list[dict]) -> dict:
    counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    summary = {'counts': counts, 'immediate': [], 'short_term': [], 'backlog': []}
    for finding in findings or []:
        sev = (finding.get('severity') or '').lower()
        if not sev:
            level = (finding.get('level') or 'INFO').upper()
            sev = {'CRITICAL': 'critical', 'HIGH': 'high',
                   'WARNING': 'medium', 'INFO': 'info'}.get(level, 'info')
        counts.setdefault(sev, 0)
        counts[sev] += 1
        item = {
            'severity': sev,
            'category': finding.get('category', ''),
            'target': f"{finding.get('namespace', 'cluster')}/{finding.get('name', '-')}",
            'value': finding.get('value', ''),
            'detail': finding.get('detail') or finding.get('message', ''),
            'recommendation': finding.get('rec', ''),
        }
        if sev in ('critical', 'high'):
            summary['immediate'].append(item)
        elif sev == 'medium':
            summary['short_term'].append(item)
        else:
            summary['backlog'].append(item)
    return summary


def _report_fetch_events(k8s):
    events = k8s.core.list_event_for_all_namespaces(
        field_selector='type=Warning', limit=150).items
    return [{
        'namespace': e.metadata.namespace or '',
        'type': e.type or 'Warning',
        'reason': e.reason or '',
        'obj': f'{e.involved_object.kind}/{e.involved_object.name}',
        'message': (e.message or '')[:220],
        'count': e.count or 1,
        'last_time': str(e.last_timestamp)[:19] if e.last_timestamp else '-',
    } for e in events]


def _report_fetch_readyz(k8s) -> dict:
    """apiserver /readyz?verbose — 컨트롤 플레인 컴포넌트별 준비 상태 (v1.2.125).

    Polaris 가 apiserver 에 붙어 있다는 사실만으로는 "살아 있다"까지만 알 수 있다.
    /readyz 는 etcd·informer-sync·poststarthook 단위로 알려준다 — 그게 새로 얻는 정보다.

    응답 형식(verbose):
        [+]ping ok
        [+]etcd ok
        [-]informer-sync failed: reason
        readyz check passed
    준비되지 않았을 때는 **HTTP 500 + 같은 형식의 본문**이 온다. 그래서 예외의 body 도
    똑같이 파싱해야 한다 — 여기가 정작 우리가 알고 싶은 경우다.

    예외를 밖으로 던지지 않는다(_report_collect._run 의 폴백은 [] 라서
    "조회 실패"와 "정상 0건"을 구분할 수 없다). 항상 dict 를 반환하고 ok 로 구분한다.
    """
    out = {'ok': False, 'status': None, 'checks': [], 'failed': [], 'error': None}
    body = ''
    try:
        client = k8s.core.api_client
        body = client.call_api(
            '/readyz', 'GET', {}, [('verbose', 'true')],
            {'Accept': 'text/plain'},
            response_type=None, auth_settings=['BearerToken'],
            _return_http_data_only=True, _preload_content=False,
            _request_timeout=(3.0, 5.0))
        body = body.data.decode('utf-8', 'replace') if hasattr(body, 'data') else str(body)
        out['status'] = 200
    except Exception as e:
        out['status'] = getattr(e, 'status', None)
        body = str(getattr(e, 'body', '') or '')
        if not out['status']:
            out['error'] = f'{type(e).__name__}: {e}'
            return out

    for line in (body or '').splitlines():
        line = line.strip()
        if line.startswith('[+]'):
            out['checks'].append(line[3:].split(' ', 1)[0])
        elif line.startswith('[-]'):
            name = line[3:].split(' ', 1)[0]
            out['failed'].append({'name': name, 'detail': line[3:]})
    # 200 이고 실패 항목이 없으면 정상. 500 이어도 항목이 파싱되면 그 목록이 근거가 된다.
    out['ok'] = (out['status'] == 200 and not out['failed'])
    return out


def _call_collect(fn, errs, *args, **kw):
    """getter 호출 — 그 getter 가 받는 키워드만 넘기고, errors 를 받으면 실패 목록을 넘긴다.

    getter 의 반환값은 건드리지 않는다. 키워드를 모르는 getter(가짜 객체 · 옛 시그니처)는
    예전처럼 위치 인자만으로 부른다.
    """
    import inspect
    try:
        params = inspect.signature(fn).parameters
        var_kw = any(p.kind == p.VAR_KEYWORD for p in params.values())
    except (TypeError, ValueError):
        params, var_kw = {}, False
    kw = {k: v for k, v in kw.items() if var_kw or k in params}
    if var_kw or 'errors' in params:
        kw['errors'] = errs
    return fn(*args, **kw)


# 수집 실패가 dict 로 돌아오는 항목 — 나머지는 [] 로 채운다
_COLLECT_DICT_KEYS = ('rbac', 'kube_system', 'readyz', 'cni_network_policies')


def _report_collect(k8s, log_fn, *, extras=False):
    """K8s 전체 데이터 수집 — 서로 독립적인 조회들을 병렬로 실행.

    data['collect_errors'] = 수집에 실패한 항목 키 목록 (v1.4.13). getter 들은 예외를 삼키고
    [] 를 돌려주므로 이게 없으면 「못 본 것」 과 「0건」 을 구분할 수 없어, 보고서가
    「비정상 파드 없음」 · 「클러스터 상태가 양호합니다」 처럼 확인하지 않은 사실을 적었다.

    extras=True(보고서 · 클러스터 스캔 경로)일 때만 스냅샷 diff 대상(Deployment · Ingress)에
    판단 근거 필드를 더 받고 CNI 정책 수를 센다. take_snapshot 은 extras 없이 부르므로
    diff 대상 항목의 모양이 그대로다 — 업그레이드 직후 첫 비교에 허위 「변경」 이 생기지 않는다.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _c(fn, *args, **kw):
        return lambda errs: _call_collect(fn, errs, *args, **kw)

    data: dict = {}
    steps = [
        ('nodes',            _c(k8s.get_node_extended)),
        ('node_metrics',     _c(k8s.get_node_metrics)),
        ('namespaces',       _c(k8s.get_namespaces_extended)),
        # detail · owner — CrashLoopBackOff(phase 는 Running) · Evicted · 이미 성공한 Job 의
        # 이전 시도를 가려내는 근거. 파드는 스냅샷 diff 대상이 아니라 필드를 늘려도 된다.
        ('pods',             _c(k8s.get_pods, None, detail=True, owner=True)),
        ('pod_metrics',      _c(k8s.get_pod_metrics_all)),
        ('deployments',      (_c(k8s.get_deployments_extended, meta=True) if extras
                              else _c(k8s.get_deployments_extended))),
        ('statefulsets',     _c(k8s.get_statefulsets_extended)),
        ('daemonsets',       _c(k8s.get_daemonsets_extended)),
        ('jobs',             _c(k8s.get_jobs, None)),
        ('cronjobs',         _c(k8s.get_cronjobs, None)),
        ('services',         _c(k8s.get_services, None)),
        ('ingresses',        (_c(k8s.get_ingresses, None, tls=True) if extras
                              else _c(k8s.get_ingresses, None))),
        ('ingress_classes',  _c(k8s.get_ingress_classes)),
        ('pvcs',             _c(k8s.get_pvcs, None)),
        ('pvs',              _c(k8s.get_pvs)),
        ('configmaps',       _c(k8s.get_configmaps, None)),
        ('secrets',          _c(k8s.get_secrets, None)),
        ('helm',             _c(k8s.get_helm_releases)),
        ('hpa',              _c(k8s.get_hpa_extended)),
        # labels · owners — 오퍼레이터가 만든 PDB(Longhorn · Rook)를 가려내는 근거. diff 대상 아님.
        ('pdbs',             _c(k8s.get_pdbs, meta=True)),
        ('network_policies', _c(k8s.get_network_policies)),
        ('storage_classes',  _c(k8s.get_storage_classes)),
        ('resource_quotas',  _c(k8s.get_resource_quotas)),
        ('limit_ranges',     _c(k8s.get_limit_ranges)),
        ('rbac',             _c(k8s.get_rbac_summary)),
        ('rbac_risky',       _c(k8s.get_rbac_risky_subjects)),   # 과도 권한 SA (v1.2.2)
        ('kube_system',      _c(k8s.get_kube_system_info)),
        ('events',           lambda errs: _report_fetch_events(k8s)),
        # 컨트롤 플레인 준비 상태 (v1.2.125). 호출 1회라 다른 28개 조회와 비용이 같고,
        # 스냅샷에도 담기는 게 맞다. 네트워크 스캔(옵트인)과 달리 항상 수집한다.
        ('readyz',           lambda errs: _report_fetch_readyz(k8s)),
    ]
    if extras and hasattr(k8s, 'get_cni_network_policy_counts'):
        steps.append(('cni_network_policies', _c(k8s.get_cni_network_policy_counts)))

    def _run(key, fn):
        errs: list = []
        try:
            return key, fn(errs), errs
        except Exception as e:
            return key, ({} if key in _COLLECT_DICT_KEYS else []), [f'{type(e).__name__}: {e}']

    failed = []
    log_fn(f'  수집 시작: {len(steps)}개 항목 병렬 조회')
    with ThreadPoolExecutor(max_workers=min(8, len(steps))) as ex:
        futures = [ex.submit(_run, key, fn) for key, fn in steps]
        for fut in as_completed(futures):
            key, value, errs = fut.result()
            data[key] = value
            if errs:
                failed.append(key)
                log_fn(f'  [경고] {key} 수집 실패: {errs[0]}')
            else:
                log_fn(f'  수집 완료: {key}')

    data['collect_errors'] = sorted(failed)
    data['hpas'] = data.get('hpa') or []
    data['cluster_version'] = k8s.cluster_info.get('version', 'N/A')
    data['collected_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return data


def _report_collect_ext(k8s, log_fn, *, netscan: bool = False, cancel=None) -> dict:
    """_report_collect(extras=True) + 선택적 네트워크 스캔 (v1.2.121).

    take_snapshot(src/api/snapshots.py)은 _report_collect 를 extras 없이 직접 부른다 —
    여기서 더 받는 판단 근거(Deployment 관리 주체 · Ingress TLS · CNI 정책 수)가 스냅샷에
    들어가면 diff 결과가 바뀌고 업그레이드 직후 첫 diff 에 허위 「변경」 이 쏟아진다.

    netscan=False 면 data 에 'netscan' 키가 아예 없고, _report_evaluate 의 네트워크 규칙이
    한 건도 발동하지 않는다.
    """
    data = _report_collect(k8s, log_fn, extras=True)
    if not netscan:
        return data
    try:
        from src import netscan as _ns     # 지연 import — 변형 빌드 내구성
        log_fn('  netscan: 네트워크 스캔 시작 (클러스터에 배포하지 않음)')
        inputs = _ns.netscan_collect_inputs(k8s, log_fn)
        data['netscan'] = _ns.netscan_run(k8s, _ns.netscan_plan(inputs),
                                          log_fn, cancel=cancel)
    except Exception as e:
        # 네트워크 스캔 실패가 보고서/스캔 전체를 죽이면 안 된다
        log_fn(f'  [경고] 네트워크 스캔 실패: {type(e).__name__}: {e}')
    return data


def _section_on(sections, key: str) -> bool:
    """섹션 포함 여부.

    sections 가 None 이면 전부 포함한다 — 이 인자를 넘기지 않던 기존 호출과
    테스트가 그대로 동작해야 하기 때문이다.
    """
    return sections is None or key in sections


# ── 판정 근거 (v1.4.13) ──────────────────────────────────────────────────────
# 「서두른 판정」 을 고친 곳 — 따르면 오히려 장애가 나는 권고를 내지 않는다.
#   · 수집 실패를 「정상」 으로 적지 않는다           · 파드 상태를 phase 만으로 보지 않는다
#   · 제품(Rancher · Longhorn · Argo CD …)이 요구하는 권한 · PDB 를 「고치라」 고 하지 않는다

_COLLECT_FAIL_TEXT = '수집하지 못했습니다 — 발견 없음이 정상을 뜻하지 않습니다'

# 수집 실패 시 「확인 불가」 발견 사항을 만드는 항목 — 보고서 판단에 쓰이는 것만
_COLLECT_LABELS = {
    'nodes': '노드', 'namespaces': '네임스페이스', 'pods': '파드',
    'deployments': 'Deployment', 'statefulsets': 'StatefulSet', 'jobs': 'Job',
    'services': 'Service', 'ingresses': 'Ingress', 'pvcs': 'PVC',
    'helm': 'Helm 릴리스', 'hpa': 'HPA', 'pdbs': 'PDB',
    'network_policies': 'NetworkPolicy',
    'cni_network_policies': 'CNI 네트워크 정책(Cilium · Calico)',
    'storage_classes': 'StorageClass', 'limit_ranges': 'LimitRange',
    'resource_quotas': 'ResourceQuota', 'kube_system': 'kube-system 구성 요소',
    'events': 'Warning 이벤트',
    'rbac': 'RBAC 구성', 'rbac_risky': '과도 권한 계정(RBAC)',
}
_COLLECT_RBAC_KEYS = ('rbac', 'rbac_risky')


def _collect_failed(data, *keys) -> bool:
    """이 항목들 중 하나라도 수집에 실패했나. 옛 데이터(collect_errors 없음)는 실패 없음으로 본다."""
    failed = (data or {}).get('collect_errors') or []
    return any(k in failed for k in keys)


# 시스템 · 플랫폼 네임스페이스 — HPA 권고 · LimitRange 권고에서 제외한다
_SYSTEM_NS = frozenset({
    'kube-system', 'kube-public', 'kube-node-lease', 'longhorn-system', 'cert-manager',
    'monitoring', 'cattle-system', 'argocd', 'ingress-nginx', 'calico-system',
    'calico-apiserver', 'tigera-operator', 'metallb-system', 'local-path-storage',
    'gatekeeper-system', 'kube-flannel', 'kubevirt', 'cdi', 'velero', 'traefik',
})
_SYSTEM_NS_PREFIX = ('cattle-', 'fleet-', 'rook-', 'rancher-', 'kube-', 'longhorn-')


def _is_system_ns(ns: str) -> bool:
    ns = (ns or '').lower()
    return ns in _SYSTEM_NS or ns.startswith(_SYSTEM_NS_PREFIX)


def _report_now(data):
    """판정 기준 시각 — 수집 시각(로컬) 우선, 없으면 지금."""
    from datetime import timezone
    try:
        return datetime.fromisoformat(str(data.get('collected_at') or '')).astimezone()
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


# 재시작 판정 기준 — 평가(발견 사항)와 DOCX 3.2 표가 이 한 벌을 쓴다
_RESTART_LEVELS = (
    (1000, 'critical', '즉시 분석 필요 (OOMKill / Liveness 실패 가능성)'),
    (200,  'high',     '반복 재시작 — 메모리 누수 또는 의존성 장애 가능성'),
    (50,   'medium',   '비정상 재시작 — 로그와 이벤트 모니터링 필요'),
    (10,   'low',      '간헐적 재시작'),
)
_RESTART_STALE_DAYS = 7      # 마지막 재시작이 이보다 오래면 누적 횟수일 뿐이다


def _restart_judgment(restarts, restarted_at, now):
    """(severity, detail) 또는 None. restartCount 는 리셋되지 않는 누적값이라,
    마지막 재시작이 7일보다 오래됐으면 지금 문제로 보지 않고 낮음으로 내린다."""
    try:
        r = int(restarts or 0)
    except (ValueError, TypeError):
        r = 0
    level = next(((s, d) for th, s, d in _RESTART_LEVELS if r > th), None)
    if level is None:
        return None
    sev, detail = level
    at = _parse_iso(restarted_at) if restarted_at else None
    if at is not None and now is not None:
        try:
            stale = (now - at).days >= _RESTART_STALE_DAYS
        except TypeError:
            stale = False
        if stale:
            sev = 'low'
            detail = (f'누적 {r}회 — 최근 {_RESTART_STALE_DAYS}일 동안 재시작이 없습니다'
                      f'(마지막 {at.astimezone().strftime("%Y-%m-%d")})')
    return sev, detail


def _report_restart_list(data):
    """재시작 판정이 있는 파드 [(pod, severity, detail)] — 누적 횟수 많은 순."""
    now = _report_now(data)
    out = []
    for p in (data.get('pods') or []):
        j = _restart_judgment(p.get('restarts', 0), p.get('restarted_at'), now)
        if j:
            out.append((p, j[0], j[1]))

    def _r(x):
        try:
            return int(x[0].get('restarts', 0))
        except (ValueError, TypeError):
            return 0
    out.sort(key=_r, reverse=True)
    return out


def _pod_job_name(p, jobs):
    """이 파드를 만든 Job 이름 (없으면 None). owner 필드가 없는 옛 데이터는
    Job 파드 이름 규칙(「<job>-<5자>」)으로 추정한다."""
    kind = p.get('owner_kind')
    if kind is not None:
        return p.get('owner_name') if kind == 'Job' else None
    base = (p.get('name') or '').rsplit('-', 1)[0]
    return base if (p.get('namespace'), base) in jobs else None


def _report_pod_health(data):
    """파드 상태 판정 — 평가(발견 사항)와 DOCX 3.1 · 3.3 표가 같은 판정을 쓴다.

    phase 만 보지 않는다: CrashLoopBackOff 는 phase 가 Running 이라 phase 로는 놓친다.
    반대로 phase 가 Failed 라도 서두르지 않는다 —
      · Evicted   : 이미 다른 노드에서 다시 떠 있는 남은 기록 → 낮음(정리 대상)
      · 성공한 Job 의 이전 실패 시도(RKE2 helm-install-* 등) → 판정하지 않음
    kube-system 파드는 여기서 한 번만 판정한다(따로 다시 세지 않는다).
    반환: [{namespace, name, state, severity, category, detail, rec, restarts, age, node}]
    """
    jobs = {(j.get('namespace'), j.get('name')): j.get('status')
            for j in (data.get('jobs') or [])}
    out = []
    for p in (data.get('pods') or []):
        phase = p.get('status') or ''
        reason = p.get('reason') or ''
        ns = p.get('namespace') or ''
        if phase in ('Succeeded', 'Completed'):
            continue
        if reason == 'Evicted':
            sev, state = 'low', 'Evicted'
            detail = '정리 대상(남은 기록) — 서비스 영향 없음'
            rec = '축출 원인(노드 디스크 · 메모리 압박)을 확인한 뒤 남은 파드 기록을 정리하세요'
        elif phase == 'Failed' and jobs.get((ns, _pod_job_name(p, jobs))) == 'Complete':
            continue            # Job 은 결국 성공했다 — 실패한 이전 시도의 기록일 뿐
        elif reason:
            sev, state = 'high', reason
            detail = f'컨테이너 이상: {reason}'
            rec = 'kubectl describe pod 와 kubectl logs --previous 로 원인을 확인하세요'
        elif phase == 'Running':
            continue
        elif phase == 'Pending':
            sev, state = 'medium', 'Pending'
            detail = '스케줄 · 기동 대기(Pending)'
            rec = 'kubectl describe pod 의 Events 에서 노드 자원 · 노드 선택 조건 · PVC 연결을 확인하세요'
        else:
            sev, state = 'high', phase or 'Unknown'
            detail = f'파드 비정상 상태: {state}'
            rec = 'kubectl describe pod 로 이벤트 확인'
        category = 'pod_state'
        if ns == 'kube-system' and sev in ('high', 'critical'):
            sev, category = 'critical', 'kube_system'
            detail += ' — kube-system 구성 요소라 클러스터 기능이 저하될 수 있습니다'
        elif ns == 'kube-system':
            category = 'kube_system'
        out.append({'namespace': ns, 'name': p.get('name', ''), 'state': state,
                    'severity': sev, 'category': category, 'detail': detail, 'rec': rec,
                    'restarts': p.get('restarts', 0), 'age': p.get('age', '-'),
                    'node': p.get('node', '-')})
    return out


def _report_kube_system_fallback(data):
    """파드 목록으로 kube-system 을 판정할 수 없을 때만(파드 수집 실패 · 옛 데이터) 쓰는
    kube_system 정보 기반 판정. phase 밖에 없으므로 긴급으로 단정하지 않는다."""
    pods = data.get('pods') or []
    if not _collect_failed(data, 'pods') and any(p.get('namespace') == 'kube-system' for p in pods):
        return []
    out = []
    for p in ((data.get('kube_system') or {}).get('pods') or []):
        st = p.get('status') or 'Unknown'
        if st in ('Running', 'Succeeded', 'Completed'):
            continue
        out.append({'namespace': 'kube-system', 'name': p.get('name', ''), 'state': st,
                    'severity': 'high', 'category': 'kube_system',
                    'detail': f'kube-system 파드 상태 {st} (phase 기준) — 클러스터 기능 저하 가능',
                    'rec': 'kubectl describe pod -n kube-system 확인',
                    'restarts': p.get('restarts', 0), 'age': '-', 'node': p.get('node', '-')})
    return out


# Ingress 컨트롤러 자신의 진입점 서비스 — 「Ingress 로 전환」 할 대상이 아니다
_INGRESS_CTRL_HINTS = ('ingress-nginx', 'nginx-ingress', 'ingress-controller', 'traefik',
                       'haproxy-ingress', 'kong-proxy', 'contour', 'envoy-gateway',
                       'istio-ingressgateway')


def _is_ingress_controller_svc(s) -> bool:
    name = (s.get('name') or '').lower()
    ns = (s.get('namespace') or '').lower()
    return ns in ('ingress-nginx', 'traefik') or any(h in name for h in _INGRESS_CTRL_HINTS)


def _rbac_is_platform(r) -> bool:
    """제품(쿠버네티스 배포판 · 플랫폼 구성 요소)이 설치하면서 요구한 관리자 권한인가.

    이런 바인딩을 지우거나 줄이면 그 제품의 컨트롤러가 멈춘다 — Rancher 가 클러스터를 못
    관리하고, Longhorn 이 볼륨을 못 붙이고, Argo CD 가 동기화를 못 한다.
    """
    name = (r.get('name') or '').lower()
    ns = (r.get('namespace') or '').lower()
    binding = (r.get('binding') or '').lower()
    if name.startswith('system:'):
        return True
    if ns in ('kube-system', 'cattle-system', 'longhorn-system', 'cert-manager') \
            or ns.startswith(('cattle-', 'fleet-', 'rook-ceph')):
        return True
    if name.startswith(('cattle', 'fleet-', 'cert-manager', 'rook-ceph', 'longhorn')):
        return True
    if binding.startswith('helm-kube-system-'):          # RKE2 helm-controller 가 차트마다 만든다
        return True
    if name in ('argocd-application-controller', 'argocd-server'):
        return True
    if 'prometheus-operator' in name or name.startswith('kube-prometheus'):
        return True
    return False


def _pdb_manager(p) -> str:
    """PDB 관리 주체 — longhorn · rook · operator · user.

    src/upgradecheck.pdb_manager() 와 같은 규칙(그 파일을 import 하지 않고 옮겨 왔다).
    labels · owners 가 없는 옛 데이터는 네임스페이스 · 이름 규칙만으로 판단한다.
    """
    ns, name = p.get('namespace') or '', p.get('name') or ''
    labels, owners = p.get('labels') or {}, p.get('owners') or []
    if (ns == 'longhorn-system' and name.startswith('instance-manager')) \
            or any(str(k).startswith('longhorn.io') for k in labels) \
            or any(k in ('InstanceManager', 'Volume', 'Node') and 'longhorn' in ns for k in owners):
        return 'longhorn'
    if ns.startswith('rook') or any(str(v).startswith('rook-ceph') for v in labels.values()) \
            or 'CephCluster' in owners:
        return 'rook'
    managed_by = str(labels.get('app.kubernetes.io/managed-by', ''))
    if owners or (managed_by and managed_by.lower() not in ('helm', 'kubectl', 'kustomize')):
        return 'operator'
    return 'user'


_PDB_MANAGER_KO = {'longhorn': 'Longhorn', 'rook': 'Rook-Ceph', 'operator': '오퍼레이터',
                   'user': '사용자'}


def _replicas_owner(d) -> str:
    """Deployment 의 replicas 를 다른 컨트롤러가 관리하나 — 'Argo CD' · '오퍼레이터' · ''."""
    mb = str(d.get('managed_by') or '').lower()
    if d.get('argocd') or 'argocd' in mb:
        return 'Argo CD'
    if d.get('owners') or (mb and mb not in ('helm', 'kubectl', 'kustomize')):
        return '오퍼레이터'
    return ''


def _report_hpa_view(data):
    """HPA 판단 재료 — 평가와 DOCX 4장이 같은 기준을 쓴다.

    시스템 네임스페이스(CoreDNS 는 자체 autoscaler 가 있다)는 빼고, replicas 를 다른
    컨트롤러(Argo CD · 오퍼레이터)가 관리하는 Deployment 는 HPA 권고 대상에서 뺀다.
    """
    hpas = data.get('hpa') or data.get('hpas') or []
    targets = set()
    for h in hpas:
        kind, _, name = (h.get('reference') or '').partition('/')
        if kind in ('Deployment', '') and name:
            targets.add((h.get('namespace') or '', name))
    user = [d for d in (data.get('deployments') or []) if not _is_system_ns(d.get('namespace'))]
    with_hpa = [d for d in user if (d.get('namespace') or '', d.get('name')) in targets]
    no_hpa = [d for d in user if (d.get('namespace') or '', d.get('name')) not in targets]
    managed = [d for d in no_hpa if _replicas_owner(d)]
    cand = [d for d in no_hpa if not _replicas_owner(d) and int(d.get('desired', 0) or 0) >= 2]
    return {'hpas': hpas, 'user': user, 'with_hpa': with_hpa, 'no_hpa': no_hpa,
            'managed': managed, 'candidates': cand}


_HPA_REC = ('사용량 근거가 있는 서비스부터 HPA 를 검토하세요. replicas 를 다른 컨트롤러'
            '(Argo CD · 오퍼레이터)가 관리하면 HPA 를 붙이지 마세요')

_PVC_PENDING_DETAIL = ('사용할 파드가 생기면 연결되는 대기 상태일 수 있습니다'
                       '(WaitForFirstConsumer)')
_PVC_LOST_REC = ('삭제하지 마세요 — 백엔드 볼륨을 찾아 같은 이름의 PV(claimRef)로 다시 '
                 '연결하세요. 삭제하면 StatefulSet 이 빈 볼륨을 새로 만듭니다')


def _report_evaluate(data, sections=None):
    """규칙 기반 발견 사항 평가."""
    findings = []

    # 0. 수집 실패 (v1.4.13) — 못 본 항목은 「문제 없음」 이 아니라 「확인 불가」 다
    for key in (data.get('collect_errors') or []):
        label = _COLLECT_LABELS.get(key)
        if not label or (key in _COLLECT_RBAC_KEYS and not _section_on(sections, 'rbac')):
            continue
        findings.append(_report_finding(
            'collect', 'info', 'cluster', label, '확인 불가',
            f'확인 불가 — {label}을(를) 수집하지 못해 판단하지 않았습니다',
            'kubeconfig 권한과 API 서버 응답을 확인한 뒤 다시 점검하세요',
        ))

    # 1. 재시작 과다 파드 — 기준은 _RESTART_LEVELS 한 벌, 마지막 재시작이 오래되면 낮춘다
    for p, sev, detail in _report_restart_list(data):
        try:
            r = int(p.get('restarts', 0))
        except (ValueError, TypeError):
            r = 0
        findings.append(_report_finding(
            'pod_restart', sev, p.get('namespace', ''), p.get('name', ''),
            f'{r}회', detail, 'kubectl logs / describe 로 원인 분석',
        ))

    # 1-2. 비정상 파드 — phase 가 아니라 컨테이너 상태까지 본다(_report_pod_health).
    # kube-system 파드도 여기서 한 번만 센다.
    for h in _report_pod_health(data) + _report_kube_system_fallback(data):
        findings.append(_report_finding(
            h['category'], h['severity'], h['namespace'], h['name'],
            h['state'], h['detail'], h['rec'],
        ))

    # 2. NotReady 노드
    for n in (data.get('nodes') or []):
        for cond in (n.get('conditions') or []):
            if cond['type'] == 'Ready' and cond['status'] != 'True':
                findings.append(_report_finding(
                    'node_notready', 'critical', 'cluster', n.get('name', ''),
                    'NotReady', cond.get('reason') or 'Node Ready 조건 False',
                    'kubectl describe node 로 원인 확인',
                ))

    # 3. 노드 압박
    for n in (data.get('nodes') or []):
        for cond in (n.get('conditions') or []):
            if cond['type'] in ('MemoryPressure', 'DiskPressure', 'PIDPressure') and cond['status'] == 'True':
                findings.append(_report_finding(
                    'node_pressure', 'high', 'cluster', n.get('name', ''),
                    cond['type'], f"{cond['type']} 감지 — 리소스 임박",
                    '노드 리소스 확인 및 파드 재분산',
                ))

    # 4. NodePort 서비스 — 포트 번호로 「민감」 여부를 가리지 않는다(고객마다 다르다).
    # Ingress 컨트롤러 자신의 NodePort 는 Ingress 로 바꿀 대상이 아니다.
    for svc in (s for s in (data.get('services') or []) if s.get('type') == 'NodePort'):
        ports = str(svc.get('ports', ''))
        if _is_ingress_controller_svc(svc):
            findings.append(_report_finding(
                'nodeport', 'info', svc.get('namespace', ''), svc.get('name', ''),
                ports or 'NodePort', 'Ingress 컨트롤러의 진입 포트(NodePort)',
                'Ingress 로 전환할 대상이 아닙니다 — 접근 가능한 범위를 방화벽 ACL 로 제한하세요',
            ))
            continue
        findings.append(_report_finding(
            'nodeport', 'medium', svc.get('namespace', ''), svc.get('name', ''),
            ports or 'NodePort', 'NodePort 직접 외부 노출',
            '외부 노출이 필요한 서비스인지 확인한 뒤 Ingress(+TLS) 전환 또는 방화벽 ACL 적용을 검토하세요',
        ))

    # 5. HPA — 사용자 워크로드 중 replicas≥2 인데 HPA 가 없는 것이 있을 때만
    hv = _report_hpa_view(data)
    if hv['candidates']:
        findings.append(_report_finding(
            'hpa', 'low', 'cluster', 'HPA 설정',
            f"{len(hv['candidates'])}개",
            f"replicas 2 이상인 사용자 Deployment {len(hv['candidates'])}개에 HPA 가 없습니다",
            _HPA_REC,
        ))

    # 6. Lost / Pending PVC — 둘은 전혀 다른 상태다
    for pvc in (data.get('pvcs') or []):
        st = pvc.get('status', '')
        if st == 'Lost':
            findings.append(_report_finding(
                'pvc', 'critical', pvc.get('namespace', ''), pvc.get('name', ''),
                'Lost', 'PV 연결이 끊어졌습니다(Lost) — 데이터가 백엔드에 남아 있을 수 있습니다',
                _PVC_LOST_REC,
            ))
        elif st == 'Pending':
            findings.append(_report_finding(
                'pvc', 'low', pvc.get('namespace', ''), pvc.get('name', ''),
                'Pending', _PVC_PENDING_DETAIL,
                '사용할 파드가 이미 있는데도 대기 중이면 StorageClass · 용량 · accessMode 를 확인하세요',
            ))

    # 7. PDB 허용 중단 0 — 제품이 관리하는 PDB 는 고치라고 하지 않는다
    for pdb in (data.get('pdbs') or []):
        curr = pdb.get('current_healthy', 0)
        desired = pdb.get('desired_healthy', 0)
        allowed = pdb.get('disruptions_allowed', 1)
        unhealthy = isinstance(curr, int) and isinstance(desired, int) and curr < desired
        if not (allowed == 0 or unhealthy):
            continue
        value = f'healthy {curr}/{desired}, disruptions {allowed}'
        mgr = _pdb_manager(pdb)
        if mgr != 'user':
            findings.append(_report_finding(
                'pdb', 'info', pdb.get('namespace', ''), pdb.get('name', ''), value,
                f'{_PDB_MANAGER_KO[mgr]}가 만든 PDB — 허용 중단 0 이 정상인 경우가 많습니다',
                '제품이 관리하는 PDB — 수정 · 삭제하지 마세요. 노드 비우기는 해당 제품 절차를 따르세요',
            ))
        elif curr == 0 and desired == 0:
            continue            # 고른 파드가 없다 — 노드 비우기를 막지 않는다
        elif unhealthy:
            findings.append(_report_finding(
                'pdb', 'medium', pdb.get('namespace', ''), pdb.get('name', ''), value,
                '준비된 파드가 부족해 허용 중단이 0입니다',
                '워크로드를 먼저 복구하세요 — 파드가 준비되면 허용 중단이 다시 생깁니다',
            ))
        else:
            findings.append(_report_finding(
                'pdb', 'medium', pdb.get('namespace', ''), pdb.get('name', ''), value,
                '설정상 허용 중단이 0입니다(minAvailable 이 레플리카 수와 같거나 maxUnavailable 0)',
                '이대로면 노드 비우기(drain)가 멈춥니다 — 레플리카를 늘리거나 minAvailable · maxUnavailable 을 조정하세요',
            ))

    # 8. StorageClass 기본값 없음 — 프로비저닝 자체가 안 되는 것은 아니다
    scs = data.get('storage_classes') or []
    if scs and not any(s.get('is_default') == 'true' for s in scs):
        findings.append(_report_finding(
            'storageclass', 'low', 'cluster', 'StorageClass',
            '기본값 없음',
            'storageClassName 을 적지 않은 PVC 는 프로비저닝되지 않습니다. 기본값을 지정하면 '
            '대기 중인(클래스 없는) PVC 에도 적용되어 정적 PV 대신 새 볼륨이 만들어질 수 있습니다',
            '기본값 지정 전에 클래스 없이 대기 중인 PVC 가 있는지 확인하고, 가능하면 PVC 마다 storageClassName 을 적으세요',
        ))

    # 9. kube-system 이상 — 1-2 에서 함께 판정한다(같은 파드를 두 번 세지 않는다)

    # 10. Deployment Ready < Desired
    for d in (data.get('deployments') or []):
        desired = d.get('desired', 0)
        ready = d.get('ready', 0)
        if desired > 0 and ready < desired:
            findings.append(_report_finding(
                'deployment', 'high', d.get('namespace', ''), d.get('name', ''),
                f'ready {ready}/{desired}', 'Deployment 레플리카 부족',
                'kubectl rollout status deployment 로 확인',
            ))

    # 11. RBAC 과도 권한 (cluster-admin / 와일드카드) — 보안 (v1.2.2)
    # 섹션에서 rbac 를 빼면 여기서 아예 만들지 않는다. 발견 사항 표·우선순위
    # 요약·개선 작업이 모두 findings 에서 파생되므로, 이 한 곳만 막으면
    # 보고서 전체에서 RBAC 경고가 사라진다.
    # v1.4.13 — 제품이 요구하는 권한(Rancher · RKE2 · Argo CD · Longhorn …)은 정보로 낮추고,
    # 그 밖의 계정도 「바로 지우라」 고 하지 않는다(지우면 그 계정을 쓰는 컨트롤러가 멈춘다).
    for r in (data.get('rbac_risky') or []) if _section_on(sections, 'rbac') else []:
        skind = r.get('subject_kind', '') or 'Subject'
        sname = r.get('name', '') or '-'
        subj  = f'{skind}/{sname}'
        detail = (f"{r.get('binding_kind', '')} '{r.get('binding', '')}' → "
                  f"{r.get('role_kind', '')} '{r.get('role', '')}' (클러스터 전체 제어 가능)")
        if _rbac_is_platform(r):
            sev = 'info'
            rec = '제품이 요구하는 권한입니다 — 바인딩을 지우거나 줄이지 마세요'
        elif skind == 'ServiceAccount':
            sev = 'high'
            rec = ('권한을 줄이기 전에 이 계정을 쓰는 프로그램을 확인하세요 — '
                   '바로 지우면 그 컨트롤러가 멈춥니다')
        else:
            sev = 'high'
            rec = ('권한을 줄이기 전에 이 사용자 · 그룹으로 작업하는 사람과 자동화 작업을 '
                   '확인하세요 — 바로 지우면 그 작업이 멈춥니다')
        findings.append(_report_finding(
            'rbac', sev, r.get('namespace', '') or 'cluster', subj,
            r.get('reason', '과도한 권한'), detail, rec,
        ))

    # 12. 컨트롤 플레인 준비 상태 (v1.2.125) — /readyz?verbose 결과.
    # Polaris 가 apiserver 에 붙어 있는 것만으로는 '살아 있다'까지만 알 수 있다.
    # 여기서 etcd·informer-sync·poststarthook 단위의 실패를 잡는다.
    _rz = data.get('readyz')
    if isinstance(_rz, dict):
        _failed = _rz.get('failed') or []
        if _failed:
            _names = [f.get('name') or '?' for f in _failed]
            # etcd·ping 이 죽으면 클러스터 전체가 위험하다. 나머지는 높음.
            _sev = 'critical' if any(n in ('etcd', 'ping') for n in _names) else 'high'
            findings.append(_report_finding(
                'apiserver', _sev, 'cluster', 'apiserver /readyz',
                f"{len(_failed)}개 실패",
                'API 서버 준비 점검 실패: ' + ', '.join(
                    (f.get('detail') or f.get('name') or '')[:70] for f in _failed[:3]),
                'kubectl get --raw \'/readyz?verbose\' 로 전체 항목을 확인하세요',
            ))
        elif _rz.get('error'):
            # 조회 자체가 안 된 경우 — 대개 권한 문제다. 장애로 단정하지 않는다.
            findings.append(_report_finding(
                'apiserver', 'info', 'cluster', 'apiserver /readyz',
                '확인 불가', f"준비 상태를 조회하지 못했습니다: {_rz['error']}",
                'kubeconfig 권한(nonResourceURLs /readyz)을 확인하세요',
            ))
        elif _rz.get('status') and _rz['status'] != 200:
            findings.append(_report_finding(
                'apiserver', 'high', 'cluster', 'apiserver /readyz',
                f"HTTP {_rz['status']}",
                'API 서버가 준비 완료를 보고하지 않았습니다(세부 항목 파싱 실패)',
                'kubectl get --raw \'/readyz?verbose\' 로 원인을 확인하세요',
            ))

    # 13. 네트워크 스캔 (v1.2.121) — 옵트인일 때만 data['netscan'] 이 존재한다.
    # 판정은 순수 함수(netscan_findings)에 위임하고 _report_finding 을 주입한다 →
    # 이 함수는 I/O 없는 순수 함수로 남고, netscan 모듈은 reports 를 import 하지 않는다.
    if data.get('netscan'):
        try:
            from src.netscan import netscan_findings
            findings.extend(netscan_findings(data['netscan'], _report_finding))
        except Exception:
            pass      # 네트워크 규칙 실패가 기존 발견사항을 날리면 안 된다

    order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    findings.sort(key=lambda f: order.get(f.get('severity', 'info'), 9))

    return findings


# ── LLM 응답 대기 상한 ────────────────────────────────────────────────────────
# 로컬 모델은 하드웨어/양자화/추론(reasoning) 여부에 따라 처리량이 한 자릿수 t/s 까지
# 떨어진다. 이 값은 "서버가 죽었는지" 판정선이 아니라 "느린 모델도 끝까지 기다려 준다"는
# 상한이다 — 도달성 판정은 test_llm_connection(GET /v1/models) 이 따로 한다.
#
# 실측(v1.2.126, LM Studio):
#   gemma-4-e4b   35 t/s → 답변 2600 토큰 = 74초    (120초로 충분했음)
#   bonsai-27b     8 t/s → reasoning 936 토큰만 117초 → 답변 첫 글자 직전에 120초 발화
#                          max_tokens=2600 전체로는 325초 필요
# 600초면 4.3 t/s 모델까지 2600 토큰을 끝낸다. 무한 대기는 하지 않는다(응답 없는
# 서버에 UI 가 영구히 묶이면 안 됨).
_LLM_TIMEOUT_S = 600

# LLM 으로 보내기 전에 가리는 비밀값(v1.5.28 검토) — 파드 로그 · 이벤트에 찍힌 토큰 · 비밀번호가 그대로
# (원격일 수도 있는) LLM 서버로 나갔다. 흔한 모양만 가린다 — 진단에 필요한 맥락은 남긴다
_LLM_SECRET_RES = [
    (re.compile(r'''(?i)(\bauthorization\s*[:=]\s*(?:bearer|basic|token)?\s*)[^\s"',]+'''), r'\1***'),
    (re.compile(r'''(?i)(\bbearer\s+)[A-Za-z0-9\-._~+/]{8,}=*'''), r'\1***'),
    (re.compile(r'''(?i)((?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)'''
                r'''["']?\s*[:=]\s*["']?)[^\s"',;&]+'''), r'\1***'),
    (re.compile(r'''(?i)(\b[a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@/]+@'''), r'\1***@'),
    (re.compile(r'''\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'''), '***JWT***'),
    (re.compile(r'''\b(?:glpat|ghp|gho|github_pat|xox[abp]|sk)[-_][A-Za-z0-9_\-]{16,}'''), '***TOKEN***'),
    (re.compile(r'''\bAKIA[0-9A-Z]{16}\b'''), '***AWSKEY***'),
    (re.compile(r'''-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----'''), '***PRIVATE KEY***'),
]


def llm_scrub(text):
    """LLM 으로 나가는 글에서 흔한 비밀값 모양을 *** 로 바꾼다."""
    if not isinstance(text, str) or not text:
        return text
    for rx, rep in _LLM_SECRET_RES:
        text = rx.sub(rep, text)
    return text


_THINK_RE = re.compile(r'<think>.*?(?:</think>|$)', re.S | re.I)


def _llm_complete(url, body, timeout):
    """/v1/chat/completions 에 body 를 보내 답(content)만 돌려준다 — 진단 · 대화 · 보고서가 함께 쓴다.

    v1.5.62(사용자 신고 — Qwen3.5 를 llama.cpp 로 띄우니 AI 진단 답이 비어 나옴): 「생각하는」 모델은 추론을
    reasoning_content 에 따로 쓰고, 그걸로 max_tokens 를 다 쓰면 content 가 빈 채(finish=length)로 온다.
      · chat_template_kwargs.enable_thinking=false 로 생각을 끈다(llama.cpp · vLLM 이 받는다. LM Studio 는 무시).
        모르는 필드를 400 으로 거절하는 서버(OpenAI 등)면 그 필드 없이 한 번 더 보낸다.
      · 답 안에 <think>…</think> 를 섞어 보내는 서버(Ollama 등)는 그 부분을 뗀다.
      · 그래도 비면 빈 칸 대신 이유를 오류로 알린다.
    """
    import urllib.error
    import urllib.request

    def post(b):
        req = urllib.request.Request(url.rstrip('/') + '/v1/chat/completions', data=json.dumps(b).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    try:
        result = post({**body, 'chat_template_kwargs': {'enable_thinking': False}})
    except urllib.error.HTTPError as e:
        if e.code not in (400, 422):
            raise
        result = post(body)
    choice = (result.get('choices') or [{}])[0]
    msg = choice.get('message') or {}
    text = _THINK_RE.sub('', msg.get('content') or '').strip()
    if text:
        return text
    if (msg.get('reasoning_content') or msg.get('reasoning')) and choice.get('finish_reason') == 'length':
        raise RuntimeError('모델이 생각(추론)하는 데 답 길이 한도를 다 써서 답이 비었습니다 — '
                           'LLM 서버에서 생각 모드를 끄거나(llama.cpp: --reasoning-budget 0) 생각하지 않는 모델을 쓰세요.')
    raise RuntimeError('모델이 빈 답을 보냈습니다 — 모델 이름 · 서버 상태를 확인하세요.')


def _llm_ask(url, model, user_prompt, system=None, temperature=None, max_tokens=None,
             timeout=None):
    """OpenAI 호환 API 단순 호출.

    system/temperature/max_tokens 는 선택 인자 — 미지정 시 기존(보고서) 동작 그대로:
    기본 system 프롬프트 + temperature 0.3 + max_tokens 생략(모델 기본값).
    AIOps(이벤트/로그 진단)는 자체 system 프롬프트를 넘겨 재사용한다.

    timeout 미지정 시 _LLM_TIMEOUT_S. 느린 로컬 모델을 쓰는 호출자가 개별로 늘릴
    필요가 없도록 기본값 자체를 넉넉히 잡았다.
    """
    import urllib.request
    from urllib.parse import urlparse as _urlparse

    # ── URL 스킴 검증 (보안): file://, ftp:// 등 비HTTP 스킴 차단 ──────────────
    _parsed = _urlparse(url)
    if _parsed.scheme not in ('http', 'https') or not _parsed.netloc:
        raise ValueError(
            f'허용되지 않는 LLM URL입니다: {url!r}\n'
            'http:// 또는 https:// 로 시작하는 URL만 사용할 수 있습니다.'
        )

    body = {
        'model': model,
        'messages': [
            {'role': 'system',
             'content': system or '당신은 Kubernetes 운영 전문가입니다. 한국어로 간결하게 답변하세요.'},
            {'role': 'user', 'content': llm_scrub(user_prompt)},
        ],
        'temperature': 0.3 if temperature is None else temperature,
    }
    if max_tokens:
        body['max_tokens'] = max_tokens
    return _llm_complete(url, body, _LLM_TIMEOUT_S if timeout is None else timeout)


def _set_cell_bg(cell, hex_color):
    """python-docx 셀 배경색 설정 (XML 직접 조작). v1.4.36 부터 보고서 본문은 바탕색을 쓰지 않는다."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = _OxmlElem('w:shd')
    shd.set(_qn('w:val'), 'clear')
    shd.set(_qn('w:color'), 'auto')
    shd.set(_qn('w:fill'), hex_color)
    tcPr.append(shd)


def _report_write_docx(data, findings, llm_fn, out_path, log_fn, sections=None):
    """v2 스타일 DOCX 보고서 — v1 자동 생성 가능 항목 포함."""
    if not HAS_DOCX:
        log_fn('  [경고] python-docx 미설치 → TXT 폴백')
        txt_path = str(out_path).replace('.docx', '.txt')
        _report_write_txt(data, findings, '', txt_path)
        return txt_path

    # ── 팔레트 ────────────────────────────────────────────────────────────────
    # CHECK 보고서 공용 템플릿(src/docxreport.py)과 같은 디자인. v1.4.36 — **색은 판정 · 등급 글자에만**:
    # 바탕색(칸 · 안내 상자 · 요약 카드) · 위쪽 색 줄 · 파란 강조를 걷어냈다(알록달록해 난잡하다는 의견).
    # 아래 HEX_* 바탕색 이름은 호출부 호환용으로만 남아 있고 그려지지 않는다.
    NAVY   = RGBColor(0x0F, 0x17, 0x2A)      # 제목(슬레이트)
    BLUE   = RGBColor(0x25, 0x63, 0xEB)      # 강조
    RED    = RGBColor(0xB9, 0x1C, 0x1C)
    ORANGE = RGBColor(0xC2, 0x41, 0x0C)
    GREEN  = RGBColor(0x15, 0x80, 0x3D)
    WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
    DARK   = RGBColor(0x33, 0x41, 0x55)
    GRAY   = RGBColor(0x64, 0x74, 0x8B)
    AMBER  = RGBColor(0xA1, 0x62, 0x07)

    HEX_NAVY  = '0F172A'
    HEX_HEAD  = 'F1F5F9'
    HEX_LINE  = 'E2E8F0'
    HEX_CRITD = 'FEE2E2'
    HEX_HIGHD = 'FFEDD5'
    HEX_MEDD  = 'FEF3C7'
    HEX_LOWD  = 'DCFCE7'
    HEX_LGRAY = 'F8FAFC'
    HEX_RULE  = '94A3B8'                  # 표 머리 행 아래 줄
    HEX_BOX   = 'CBD5E1'                  # 안내 상자 · 요약 카드 테두리
    FONT = '맑은 고딕'

    SEV_KO  = {'critical': '긴급', 'high': '높음', 'medium': '중간',
               'warning': '중간', 'low': '낮음', 'info': '정보'}
    SEV_ORD = {'긴급': 0, '높음': 1, '중간': 2, '낮음': 3, '정보': 4}

    def sev_ko(sev):
        return SEV_KO.get(str(sev or '').lower(), '정보')

    def sev_bg(sev):
        k = sev_ko(sev)
        return (HEX_CRITD if k == '긴급' else HEX_HIGHD if k == '높음'
                else HEX_MEDD if k == '중간' else HEX_LOWD)

    def sev_rgb(sev):
        k = sev_ko(sev)
        return (RED if k == '긴급' else ORANGE if k == '높음'
                else AMBER if k == '중간' else GREEN)

    # ── XML/폰트 헬퍼 ────────────────────────────────────────────────────────
    def _para_bg(para, hex_color):
        pPr = para._p.get_or_add_pPr()
        shd = _OxmlElem('w:shd')
        shd.set(_qn('w:val'), 'clear')
        shd.set(_qn('w:color'), 'auto')
        shd.set(_qn('w:fill'), hex_color)
        pPr.append(shd)

    def _rfont(run, size=10, bold=False, color=None):
        run.font.name = 'Segoe UI'                # 영문 · 숫자(한글은 _fix_ea 가 맑은 고딕으로)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color or DARK

    def _fix_ea(doc):
        def fix(run):
            rPr = run._r.get_or_add_rPr()
            rf = rPr.find(_qn('w:rFonts'))
            if rf is None:
                rf = _OxmlElem('w:rFonts')
                rPr.insert(0, rf)
            rf.set(_qn('w:eastAsia'), FONT)
        for p in doc.paragraphs:
            for r in p.runs: fix(r)
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for r in p.runs: fix(r)

    # ── 문서 초기화 ───────────────────────────────────────────────────────────
    doc = _DocxDoc()
    for sec in doc.sections:
        # A4 — 크기를 안 정하면 기본 서식의 US Letter(21.6cm)로 나와 본문이 17.1cm 가 되고,
        # 16.5cm 표 · 카드보다 머리글 · 제목 줄이 길게 나왔다(v1.4.9)
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.top_margin    = Cm(2.2)
        sec.bottom_margin = Cm(2.0)
        sec.left_margin   = Cm(2.5)                  # 본문 폭 16.5cm — 표 폭이 모두 여기에 맞춰져 있다
        sec.right_margin  = Cm(2.0)
        sec.different_first_page_header_footer = True     # 표지에는 머리글 · 바닥글 없음
    _compat = doc.settings.element.find(_qn('w:compat'))
    if _compat is None:
        _compat = _OxmlElem('w:compat'); doc.settings.element.append(_compat)
    _cs = _OxmlElem('w:compatSetting')                    # Word 2013 배치 — 표 가장자리를 본문 여백에 맞춘다
    _cs.set(_qn('w:name'), 'compatibilityMode'); _cs.set(_qn('w:uri'), 'http://schemas.microsoft.com/office/word'); _cs.set(_qn('w:val'), '15')
    _compat.append(_cs)

    def _tbl_lines(t, pad=70):
        """가로줄만 · 칸 여백 — CHECK 보고서와 같은 표"""
        tp = t._tbl.tblPr
        b = _OxmlElem('w:tblBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            e = _OxmlElem(f'w:{side}')
            if side in ('top', 'bottom', 'insideH'):
                e.set(_qn('w:val'), 'single'); e.set(_qn('w:sz'), '4'); e.set(_qn('w:color'), HEX_LINE); e.set(_qn('w:space'), '0')
            else:
                e.set(_qn('w:val'), 'nil')
            b.append(e)
        tp.append(b)
        m = _OxmlElem('w:tblCellMar')
        for side, v in (('top', pad), ('bottom', pad), ('left', 110), ('right', 110)):
            e = _OxmlElem(f'w:{side}'); e.set(_qn('w:w'), str(v)); e.set(_qn('w:type'), 'dxa'); m.append(e)
        tp.append(m)

    def _setup_hf():
        for sec in doc.sections:
            sec.header_distance = Cm(1.0)
            hdr = sec.header
            hdr.is_linked_to_previous = False
            hp = hdr.paragraphs[0] if hdr.paragraphs else hdr.add_paragraph()
            hp.clear(); hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = hp.add_run('POLARIS   ')
            _rfont(r, size=7.5, bold=True, color=NAVY)
            r = hp.add_run('Kubernetes 클러스터 운영 점검 리포트')
            _rfont(r, size=8, color=GRAY)
            pPr = hp._p.get_or_add_pPr()
            pBdr = _OxmlElem('w:pBdr')
            bot = _OxmlElem('w:bottom')
            bot.set(_qn('w:val'), 'single'); bot.set(_qn('w:sz'), '4')
            bot.set(_qn('w:space'), '6');    bot.set(_qn('w:color'), HEX_LINE)
            pBdr.append(bot); pPr.append(pBdr)
            sec.footer_distance = Cm(1.0)
            ftr = sec.footer
            ftr.is_linked_to_previous = False
            fp = ftr.paragraphs[0] if ftr.paragraphs else ftr.add_paragraph()
            fp.clear(); fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r_pre = fp.add_run(''); _rfont(r_pre, size=8, color=GRAY)
            fp_p = fp._p
            rb = _OxmlElem('w:r'); fb = _OxmlElem('w:fldChar')
            fb.set(_qn('w:fldCharType'), 'begin'); rb.append(fb); fp_p.append(rb)
            ri = _OxmlElem('w:r'); it = _OxmlElem('w:instrText')
            it.text = ' PAGE '; ri.append(it); fp_p.append(ri)
            re_ = _OxmlElem('w:r'); fe = _OxmlElem('w:fldChar')
            fe.set(_qn('w:fldCharType'), 'end'); re_.append(fe); fp_p.append(re_)
            for _fr in (rb, ri, re_):                     # 쪽 번호도 본문과 같은 글꼴 · 크기 · 색
                _rp = _OxmlElem('w:rPr'); _rf = _OxmlElem('w:rFonts')
                for _a in ('w:ascii', 'w:hAnsi', 'w:eastAsia'):
                    _rf.set(_qn(_a), 'Segoe UI')
                _sz = _OxmlElem('w:sz'); _sz.set(_qn('w:val'), '16')
                _co = _OxmlElem('w:color'); _co.set(_qn('w:val'), '64748B')
                _rp.append(_rf); _rp.append(_co); _rp.append(_sz); _fr.insert(0, _rp)
            r_post = fp.add_run(''); _rfont(r_post, size=8, color=GRAY)

    _setup_hf()

    # ── DocBuilder ────────────────────────────────────────────────────────────
    def h1(text):
        p = doc.add_paragraph(); p.clear()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after  = Pt(10)
        num, _, rest = text.partition(' ')
        if num.rstrip('.').replace('.', '').isdigit() and rest:
            _rfont(p.add_run(num + ' '), size=15, bold=True, color=NAVY)
            _rfont(p.add_run(rest), size=15, bold=True, color=NAVY)
        else:
            _rfont(p.add_run(text), size=15, bold=True, color=NAVY)
        pPr = p._p.get_or_add_pPr()
        pBdr = _OxmlElem('w:pBdr'); bot = _OxmlElem('w:bottom')
        bot.set(_qn('w:val'), 'single'); bot.set(_qn('w:sz'), '6'); bot.set(_qn('w:space'), '6'); bot.set(_qn('w:color'), HEX_LINE)
        pBdr.append(bot); pPr.append(pBdr)

    def h2(text):
        p = doc.add_paragraph(); p.clear()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after  = Pt(3)
        # 왼쪽 파란 막대는 없앴다(v1.4.9) — 굵기 · 크기로만 구분
        run = p.add_run(text)
        _rfont(run, size=11.5, bold=True, color=NAVY)

    def para(text, bold=False, color=None, size=10, indent=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(2)
        if indent: p.paragraph_format.left_indent = Cm(0.5)
        run = p.add_run(text)
        _rfont(run, size=size, bold=bold, color=color)

    def bullet(text, color=None, size=9.5):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after  = Pt(1)
        p.paragraph_format.left_indent  = Cm(0.5)
        run = p.add_run(f'• {text}')
        _rfont(run, size=size, color=color)

    def callout(text, hex_bg=None, color=None):
        """안내 상자 — 회색 테두리만, 등급은 글자색(color)으로. hex_bg 는 예전 호출 호환용(쓰지 않는다, v1.4.36)"""
        p = doc.add_paragraph(); p.clear()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after  = Pt(4)
        pPr = p._p.get_or_add_pPr()
        # Word 는 테두리를 글자 바깥(들여쓰기 - 간격)에 그리므로 들여쓰기 = 간격 + 굵기 로 두면
        # 상자 가장자리가 표 가장자리(본문 여백)와 정확히 맞는다
        _bd = _OxmlElem('w:pBdr')
        for _side in ('top', 'left', 'bottom', 'right'):
            _e = _OxmlElem(f'w:{_side}')
            _e.set(_qn('w:val'), 'single'); _e.set(_qn('w:sz'), '4'); _e.set(_qn('w:space'), '5'); _e.set(_qn('w:color'), HEX_BOX)
            _bd.append(_e)
        pPr.append(_bd)
        ind = _OxmlElem('w:ind')
        ind.set(_qn('w:left'), '110'); ind.set(_qn('w:right'), '110')     # 5pt(100) + 0.5pt(10)
        pPr.append(ind)
        run = p.add_run(text)
        _rfont(run, size=9.5, color=color or DARK)

    def tbl(headers, rows, col_widths=None, alt=True):
        if not rows:
            p = doc.add_paragraph('(데이터 없음)')
            if p.runs: p.runs[0].font.italic = True; p.runs[0].font.size = Pt(9)
            return
        t = doc.add_table(rows=1, cols=len(headers))
        _tbl_lines(t)
        hdr = t.rows[0]
        for i, h in enumerate(headers):
            c = hdr.cells[i]; c.text = ''
            r = c.paragraphs[0].add_run(h)
            _rfont(r, size=8.5, bold=True, color=NAVY)
            _hb = _OxmlElem('w:tcBorders'); _he = _OxmlElem('w:bottom')     # 바탕 대신 아래 진한 줄
            _he.set(_qn('w:val'), 'single'); _he.set(_qn('w:sz'), '8'); _he.set(_qn('w:color'), HEX_RULE); _he.set(_qn('w:space'), '0')
            _hb.append(_he); c._tc.get_or_add_tcPr().append(_hb)
            if col_widths and i < len(col_widths): c.width = Cm(col_widths[i])
        for ridx, row_data in enumerate(rows):
            tr = t.add_row()
            for ci, val in enumerate(row_data):
                c = tr.cells[ci]; c.text = ''
                if isinstance(val, tuple):
                    txt     = str(val[0]) if val[0] is not None else ''
                    vbold   = val[1] if len(val) > 1 else False
                    vclr    = val[2] if len(val) > 2 else None
                    valg    = val[3] if len(val) > 3 else 'LEFT'
                    # val[4] 는 예전 칸 바탕색 — 그리지 않는다(v1.4.36). 줄무늬 바탕도 없앴다
                else:
                    txt, vbold, vclr, valg = str(val or ''), False, None, 'LEFT'
                r = c.paragraphs[0].add_run(txt)
                _rfont(r, size=9, bold=vbold, color=vclr)
                pa = c.paragraphs[0]
                if valg in ('CENTER', 'center'): pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif valg in ('RIGHT', 'right'): pa.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                if col_widths and ci < len(col_widths): c.width = Cm(col_widths[ci])
        doc.add_paragraph('')

    def spacer(n=1):
        for _ in range(n):
            p = doc.add_paragraph('')
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after  = Pt(2)

    def ai_comment(label, ctx):
        """섹션 AI 한 마디 — llm_fn 없으면 no-op."""
        if not llm_fn:
            return
        try:
            log_fn(f'    [AI] {label}...')
            text = llm_fn(ctx)
            if not text or not text.strip():
                return
            spacer()
            p = doc.add_paragraph()
            run = p.add_run('▶ AI: ' + text.strip())
            _rfont(run, size=9.5, color=GRAY)
            run.font.italic = True
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after  = Pt(8)
        except Exception as _e:
            log_fn(f'    [AI] {label} 실패: {_e}')

    # ── 기초 데이터 & 분석 ────────────────────────────────────────────────────
    priority  = _report_build_priority_summary(findings)
    counts    = priority['counts']
    # 수집에 실패한 항목 — 그 장에서는 「정상」 · 「없음」 을 적지 않는다(v1.4.13)
    FAIL_TXT  = _COLLECT_FAIL_TEXT

    def _failed(*keys):
        return _collect_failed(data, *keys)

    def fail_callout():
        callout(FAIL_TXT, HEX_LGRAY, GRAY)

    nodes_all = data.get('nodes') or []
    pods_all  = data.get('pods')  or []
    # 파드 판정은 평가와 같은 함수 — phase 만 보지 않고, Evicted · 성공한 Job 의 이전 시도를 가린다
    pods_judged = _report_pod_health(data)
    pods_nr   = [h for h in pods_judged if h['severity'] not in ('low', 'info')]
    pods_hi   = _report_restart_list(data)[:20]
    svc_all   = data.get('services') or []
    nodeport  = [s for s in svc_all if s.get('type') == 'NodePort']
    pvcs_all  = data.get('pvcs') or []
    pvcs_lost = [p for p in pvcs_all if p.get('status') == 'Lost']
    pvcs_pend = [p for p in pvcs_all if p.get('status') == 'Pending']
    pvcs_bad  = [p for p in pvcs_all if p.get('status') not in ('Bound', 'Released')]
    deps_all  = data.get('deployments') or []
    sts_all   = data.get('statefulsets') or []
    hpas      = data.get('hpa') or []
    ingresses = data.get('ingresses') or []
    nss       = data.get('namespaces') or []
    helmlist  = data.get('helm') or []
    # 발견 사항 위험도를 표에 그대로 쓴다 — 표마다 따로 정하면 같은 대상이 장마다 다르게 나온다
    sev_of = {(f.get('category'), f.get('namespace'), f.get('name')): f.get('severity')
              for f in findings}
    rec_of = {(f.get('category'), f.get('namespace'), f.get('name')): f.get('rec')
              for f in findings}

    ko_counts = {'긴급': counts.get('critical', 0),
                 '높음': counts.get('high', 0),
                 '중간': counts.get('medium', 0) + counts.get('warning', 0),
                 '낮음': counts.get('low', 0),
                 '정보': counts.get('info', 0)}

    # 노드 역할 분석
    def _parse_roles(n):
        return [r.strip() for r in n.get('roles', 'worker').split(',') if r.strip()]

    all_roles = set()
    for n in nodes_all:
        for r in _parse_roles(n): all_roles.add(r)
    has_dedicated_worker = any(
        not any(cp in _parse_roles(n) for cp in ('control-plane', 'master', 'etcd'))
        for n in nodes_all)
    kernels = list({n.get('kernel', '') for n in nodes_all if n.get('kernel', '')})
    kernel_diff = len(kernels) > 1

    # Deployment/StatefulSet 이상
    deps_nr = [d for d in deps_all
               if int(d.get('ready', 0)) < int(d.get('desired', 0))]
    sts_nr  = [s for s in sts_all
               if int(s.get('ready', 0)) < int(s.get('desired', 0))]

    # HPA 미적용 워크로드 — 시스템 네임스페이스 제외, 평가와 같은 기준
    hpa_view    = _report_hpa_view(data)
    deps_no_hpa = hpa_view['no_hpa']

    # Ingress class 분류
    from collections import Counter as _Counter
    class_dist = _Counter(i.get('class', '<none>') or '<none>' for i in ingresses)
    no_class_ns = sorted({i.get('namespace', '')
                          for i in ingresses
                          if (i.get('class', '<none>') or '<none>') == '<none>'})

    # 대용량 PVC (50Gi 이상)
    def _parse_gi(cap):
        s = str(cap or '').upper().strip()
        try:
            if 'TI' in s: return float(s.replace('TI', '').strip()) * 1024
            if 'GI' in s: return float(s.replace('GI', '').strip())
            if 'G' in s:  return float(s.replace('G', '').strip())
        except: pass
        return 0
    large_pvcs = sorted(
        [(p, _parse_gi(p.get('capacity', ''))) for p in pvcs_all
         if _parse_gi(p.get('capacity', '')) >= 50],
        key=lambda x: x[1], reverse=True)

    # ArgoCD 감지 — 네임스페이스가 있다는 사실만 안다
    has_argocd = any(n.get('name', '') == 'argocd' for n in nss)
    # Helm 이상
    helm_failed = [h for h in helmlist if h.get('status', '') not in ('deployed', 'superseded')]

    # ═══════════════════════════════════════════════════════════════════════════
    # 표지
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [1/10] 표지...')
    _org = _report_org()
    # 제목 — 어두운 띠 없이(v1.4.9). 제목 아래 가는 줄 하나
    _bp = doc.add_paragraph()
    _bp.paragraph_format.space_before = Pt(18); _bp.paragraph_format.space_after = Pt(10)
    _rfont(_bp.add_run('POLARIS  ·  클러스터 점검 보고서'), size=8.5, bold=True, color=GRAY)
    _bp = doc.add_paragraph()
    _rfont(_bp.add_run('Kubernetes 클러스터 운영 점검 리포트'), size=24, bold=True, color=NAVY)
    _bp.paragraph_format.space_after = Pt(4)
    _bp = doc.add_paragraph()
    _rfont(_bp.add_run(f"{data.get('cluster_version', 'N/A')} · 노드 {len(nodes_all)}개"), size=11, color=GRAY)
    _bp.paragraph_format.space_after = Pt(0)
    _bpPr = _bp._p.get_or_add_pPr(); _bb = _OxmlElem('w:pBdr'); _bot = _OxmlElem('w:bottom')
    _bot.set(_qn('w:val'), 'single'); _bot.set(_qn('w:sz'), '8'); _bot.set(_qn('w:space'), '12'); _bot.set(_qn('w:color'), HEX_LINE)
    _bb.append(_bot); _bpPr.append(_bb)
    spacer()
    chip_data = [('긴급', ko_counts['긴급'], RED),
                 ('높음', ko_counts['높음'], ORANGE),
                 ('중간', ko_counts['중간'], AMBER),
                 ('낮음', ko_counts['낮음'], GREEN)]
    # 카드 사이에 빈 칸(틈)을 둔다(v1.4.9). 카드는 회색 테두리 상자 — 바탕색 · 위쪽 색 줄 없이 건수 글자색만(v1.4.36)
    _gap_cm = 0.25
    _card_cm = (16.5 - _gap_cm * 3) / 4
    t_cov = doc.add_table(rows=1, cols=7)
    for gi in (1, 3, 5):
        gv = t_cov.rows[0].cells[gi]; gv.width = Cm(_gap_cm)
        _gb = _OxmlElem('w:tcBorders')
        for side in ('top', 'left', 'bottom', 'right'):
            e = _OxmlElem(f'w:{side}'); e.set(_qn('w:val'), 'nil'); _gb.append(e)
        _gm = _OxmlElem('w:tcMar')
        for side in ('top', 'bottom', 'left', 'right'):
            e = _OxmlElem(f'w:{side}'); e.set(_qn('w:w'), '0'); e.set(_qn('w:type'), 'dxa'); _gm.append(e)
        _gp = gv._tc.get_or_add_tcPr(); _gp.append(_gb); _gp.append(_gm)
    for ci, (label, cnt, clr) in enumerate(chip_data):
        cv = t_cov.rows[0].cells[ci * 2]; cv.text = ''; cv.width = Cm(_card_cm)
        _tb = _OxmlElem('w:tcBorders')
        for side in ('top', 'left', 'bottom', 'right'):
            e = _OxmlElem(f'w:{side}')
            e.set(_qn('w:val'), 'single'); e.set(_qn('w:sz'), '4'); e.set(_qn('w:color'), HEX_BOX); e.set(_qn('w:space'), '0')
            _tb.append(e)
        _cm = _OxmlElem('w:tcMar')
        for side, v in (('top', 150), ('bottom', 150), ('left', 180), ('right', 120)):
            e = _OxmlElem(f'w:{side}'); e.set(_qn('w:w'), str(v)); e.set(_qn('w:type'), 'dxa'); _cm.append(e)
        _tcp = cv._tc.get_or_add_tcPr(); _tcp.append(_tb); _tcp.append(_cm)
        _rfont(cv.paragraphs[0].add_run(label), size=8, color=GRAY)
        _vp = cv.add_paragraph()
        _rfont(_vp.add_run(f'{cnt}건'), size=17, bold=True, color=clr if cnt else NAVY)
    # 칸 너비를 표 격자에도 적는다 — 칸에만 적으면 Word 가 7칸을 같은 너비로 다시 나눈다
    for _gc, _w in zip(t_cov._tbl.tblGrid.findall(_qn('w:gridCol')),
                       [_card_cm, _gap_cm, _card_cm, _gap_cm, _card_cm, _gap_cm, _card_cm]):
        _gc.set(_qn('w:w'), str(int(_w * 567)))
    _tpr = t_cov._tbl.tblPr
    _lay = _OxmlElem('w:tblLayout'); _lay.set(_qn('w:type'), 'fixed'); _tpr.append(_lay)
    spacer()
    t_meta = doc.add_table(rows=0, cols=2)
    _tbl_lines(t_meta)
    for k, v in [row for row in [('점검 일시', data.get('collected_at', '')), ('작성 조직', _org) if _org else None,
                                 ('클러스터', data.get('cluster_version', 'N/A')), ('노드', f'{len(nodes_all)}개')] if row]:
        cells = t_meta.add_row().cells
        cells[0].text = cells[1].text = ''
        _rfont(cells[0].paragraphs[0].add_run(k), size=9, color=GRAY); cells[0].width = Cm(3.6)
        _rfont(cells[1].paragraphs[0].add_run(str(v)), size=10, color=NAVY); cells[1].width = Cm(12.9)
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. 점검 개요
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [2/10] 점검 개요...')
    h1('1. 점검 개요')
    h2('1.1 점검 목적')
    para('본 리포트는 운영 중인 Kubernetes 클러스터의 전반적인 상태를 점검하고, '
         '잠재적 위험 요소를 식별하여 안정적인 서비스 운영을 위한 개선 방향을 제시합니다.', size=10)
    h2('1.2 점검 범위')
    for item in ['클러스터 기본 현황 (노드, 버전, 리소스)',
                 '워크로드 상태 (Pod, Deployment, StatefulSet 등)',
                 'HPA 및 오토스케일링 구성',
                 'Ingress 및 Service 노출 구조',
                 'PVC / 스토리지 상태',
                 # 제외했으면 점검 범위에도 적지 않는다 — 범위에 있는데 내용이
                 # 없으면 누락된 보고서로 읽힌다
                 ('보안 위험 항목 (RBAC, NetworkPolicy)' if _section_on(sections, 'rbac')
                  else '보안 위험 항목 (NetworkPolicy)'),
                 '발견 이슈 분석 및 개선 우선순위']:
        bullet(item)
    h2('1.3 점검 정보')
    tbl(['항목', '내용'], [row for row in [
        ['클러스터 버전',   data.get('cluster_version', 'N/A')],
        ['점검 일시',       data.get('collected_at', '')],
        (['작성 조직', _org] if _org else None),
        ['노드 수',         f"{len(nodes_all)}개"],
        ['전체 파드 수',    f"{len(pods_all)}개"],
        ['네임스페이스 수', f"{len(nss)}개"],
        ['발견 이슈',       f"긴급 {ko_counts['긴급']}건 / 높음 {ko_counts['높음']}건 / "
                            f"중간 {ko_counts['중간']}건"],
        (['수집 실패 항목', ', '.join(_COLLECT_LABELS.get(k, k) for k in data.get('collect_errors')
                                    if k in _COLLECT_LABELS
                                    and (k not in _COLLECT_RBAC_KEYS or _section_on(sections, 'rbac')))]
         if any(k in _COLLECT_LABELS and (k not in _COLLECT_RBAC_KEYS or _section_on(sections, 'rbac'))
                for k in (data.get('collect_errors') or [])) else None),
    ] if row], col_widths=[4, 12.5])
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. 클러스터 기본 현황
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [3/10] 클러스터 기본 현황...')
    h1('2. 클러스터 기본 현황')

    h2('2.1 노드 상태')
    not_ready = [n for n in nodes_all if n.get('status') != 'Ready']
    ready_cnt = len(nodes_all) - len(not_ready)
    # 역할 분석 산문 (v1 스타일)
    role_desc = ', '.join(sorted(all_roles)) or 'worker'
    worker_note = (
        '' if has_dedicated_worker
        else f' 전용 워커 노드가 없어 시스템/사용자 워크로드가 동일 노드에서 실행됩니다.')
    if _failed('nodes'):
        fail_callout()
    else:
        para(f"총 {len(nodes_all)}개 노드 중 {ready_cnt}개가 Ready 상태이며, "
             f"{role_desc} 역할을 겸합니다.{worker_note}", size=10,
             color=RED if not_ready else None)
    if not_ready:
        callout(f"⚠ NotReady 노드: {', '.join(n.get('name','') for n in not_ready)}",
                HEX_CRITD, RED)
    if not has_dedicated_worker and len(nodes_all) > 0 and not _failed('nodes'):
        callout('전용 워커 노드 없음 — 컨트롤 플레인 노드에 사용자 워크로드가 혼재합니다. '
                '장기적으로 전용 워커 노드 추가를 권장합니다.', HEX_MEDD, AMBER)
    if kernel_diff:
        callout(f"⚠ 커널 버전 혼재: {' / '.join(kernels)} — "
                f"노드 간 OS 패치 동기화가 필요합니다.", HEX_HIGHD, ORANGE)
    node_rows = []
    for n in nodes_all:
        st   = n.get('status', 'Unknown')
        ok   = st == 'Ready'
        conds = n.get('conditions') or []
        press = [c['type'].replace('Pressure', '') for c in conds
                 if c['type'] in ('MemoryPressure', 'DiskPressure', 'PIDPressure')
                 and c['status'] == 'True']
        node_rows.append([
            n.get('name', ''),
            n.get('roles', '-'),
            (st, True, GREEN if ok else RED, 'CENTER', HEX_LOWD if ok else HEX_CRITD),
            n.get('version', '-'),
            n.get('os', '-'),
            n.get('allocatable_cpu', '-'),
            n.get('allocatable_mem', '-'),
            n.get('kernel', '-'),
            ', '.join(press) or '정상',
        ])
    tbl(['노드명', '역할', '상태', '버전', 'OS', 'CPU(Alloc)', 'MEM(Alloc)', '커널', '압박'],
        node_rows, col_widths=[2.2, 1.5, 1.5, 2.0, 2.8, 1.7, 1.8, 1.5, 1.5])

    h2('2.2 전체 워크로드 현황')
    running   = len([p for p in pods_all if p.get('status') == 'Running'])
    completed = len([p for p in pods_all if p.get('status') in ('Succeeded', 'Completed')])

    def _n(key, text):
        return '수집 실패' if _failed(key) else text
    tbl(['항목', '수치'], [
        ['전체 Pod',         _n('pods', str(len(pods_all)))],
        ['Running',          _n('pods', str(running))],
        ['Completed (정상)', _n('pods', str(completed))],
        ['비정상',           _n('pods', str(len(pods_nr)))],
        ['Deployment',       _n('deployments', f"{len(deps_all)}개 (이상 {len(deps_nr)}개)")],
        ['StatefulSet',      _n('statefulsets', f"{len(sts_all)}개 (이상 {len(sts_nr)}개)")],
        ['DaemonSet',        str(len(data.get('daemonsets') or []))],
        ['Job',              _n('jobs', str(len(data.get('jobs') or [])))],
        ['CronJob',          str(len(data.get('cronjobs') or []))],
        ['Service',          _n('services', str(len(svc_all)))],
        ['PVC',              _n('pvcs', str(len(pvcs_all)))],
        ['Helm 릴리스',      _n('helm', f"{len(helmlist)}개 (이상 {len(helm_failed)}개)")],
    ], col_widths=[5, 11.5])

    h2('2.3 주요 관찰사항')
    obs = []
    if _failed('deployments'):
        obs.append(f"Deployment: {FAIL_TXT}")
    elif not deps_nr:
        obs.append(f"전체 Deployment {len(deps_all)}개 모두 READY 상태 (정상)")
    else:
        obs.append(f"Deployment {len(deps_nr)}개 미준비 — "
                   f"{', '.join(d.get('name','') for d in deps_nr[:5])}")
    if _failed('statefulsets'):
        obs.append(f"StatefulSet: {FAIL_TXT}")
    elif not sts_nr:
        obs.append(f"StatefulSet {len(sts_all)}개 모두 정상 운영 중")
    else:
        obs.append(f"StatefulSet {len(sts_nr)}개 미준비 — "
                   f"{', '.join(s.get('name','') for s in sts_nr[:3])}")
    if has_argocd:
        obs.append("argocd 네임스페이스가 있습니다 — Argo CD 로 배포를 관리하는 것으로 보입니다")
    if _failed('helm'):
        obs.append(f"Helm 릴리스: {FAIL_TXT}")
    elif helm_failed:
        obs.append(f"Helm 비정상 릴리스 {len(helm_failed)}개 — "
                   f"{', '.join(h.get('name','') for h in helm_failed[:3])}")
    else:
        obs.append(f"Helm 릴리스 {len(helmlist)}개 모두 정상 배포 상태")
    # kube-system 은 파드 판정에서 한 번만 센다 — 파드 목록이 없을 때만 kube_system 정보로 본다
    ks_bad = ([h for h in pods_judged if h['namespace'] == 'kube-system'
               and h['severity'] not in ('low', 'info')]
              + [h for h in _report_kube_system_fallback(data)])
    ks_unknown = _failed('pods') and (_failed('kube_system') or not data.get('kube_system'))
    if ks_bad:
        obs.append(f"kube-system 비정상 파드 {len(ks_bad)}개 — 컨트롤 플레인 점검 필요")
    elif ks_unknown:
        obs.append(f"kube-system 파드: {FAIL_TXT}")
    else:
        obs.append("kube-system 파드 정상 운영 중")
    for o in obs:
        bullet(o)

    h2('2.4 운영 중인 네임스페이스')
    ns_names = [n.get('name', '') for n in nss]
    para(f"총 {len(ns_names)}개 네임스페이스 운영 중:", size=10)
    # 한 행에 여러 이름 나열
    chunk = 8
    for i in range(0, len(ns_names), chunk):
        bullet(', '.join(ns_names[i:i+chunk]), size=9)
    ai_comment('클러스터 기본 현황', f"""Kubernetes 클러스터 기본 현황:
- 노드: 총 {len(nodes_all)}개 (Ready {len(nodes_all) - len(not_ready)}개, NotReady {len(not_ready)}개)
- 역할 구성: {', '.join(sorted(all_roles)) or '미확인'}
- 파드: {len(pods_all)}개 (비정상 {len(pods_nr)}개)
- Deployment {len(deps_all)}개, StatefulSet {len(sts_all)}개, 네임스페이스 {len(nss)}개

클러스터 전반 상태를 1~2문장으로 평가하세요.""")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. 워크로드 상태
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [4/10] 워크로드 상태...')
    h1('3. 워크로드 상태')

    h2('3.1 비정상 파드')
    _sev_rank = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    if _failed('pods'):
        fail_callout()
    elif pods_judged:
        _cleanup = [h for h in pods_judged if h['severity'] in ('low', 'info')]
        if pods_nr:
            _top = min((h['severity'] for h in pods_nr), key=lambda s: _sev_rank.get(s, 9))
            callout(f"⚠ 비정상 파드 {len(pods_nr)}건 — 원인 분석이 필요합니다.",
                    sev_bg(_top), sev_rgb(_top))
        if _cleanup:
            callout(f"정리 대상 파드 {len(_cleanup)}건(Evicted 등 남은 기록) — 서비스 영향은 없습니다.",
                    HEX_LGRAY, GRAY)
        _rows = sorted(pods_judged, key=lambda h: _sev_rank.get(h['severity'], 9))
        tbl(['네임스페이스', '파드명', '위험도', '상태', '재시작', 'Age'],
            [[h['namespace'], h['name'],
              (sev_ko(h['severity']), True, sev_rgb(h['severity']), 'CENTER', sev_bg(h['severity'])),
              h['state'], str(h.get('restarts', 0)), h.get('age', '-')]
             for h in _rows[:30]], col_widths=[2.5, 5, 1.5, 2.5, 1.5, 3.5])
    else:
        callout('✓ 비정상 파드 없음 — 전체 워크로드 Running/Completed 정상 상태입니다.',
                HEX_LOWD, GREEN)

    h2('3.2 재시작 이상 파드')
    if _failed('pods'):
        fail_callout()
    elif pods_hi:
        # 위험도는 발견 사항과 같은 기준(_RESTART_LEVELS) — 마지막 재시작이 7일보다 오래면 낮음
        _top = min((s for _p, s, _d in pods_hi), key=lambda s: _sev_rank.get(s, 9))
        callout(f"⚠ 재시작 이상 파드 {len(pods_hi)}건 — "
                "OOMKill, Liveness Probe 실패, 의존성 장애 등 원인 분석 필요 "
                f"(최근 {_RESTART_STALE_DAYS}일 안에 재시작이 없으면 낮음으로 표시)",
                sev_bg(_top), sev_rgb(_top))

        def _last(p):
            at = _parse_iso(p.get('restarted_at')) if p.get('restarted_at') else None
            return at.astimezone().strftime('%Y-%m-%d %H:%M') if at else '-'
        tbl(['네임스페이스', '파드명', '위험도', '재시작(누적)', '마지막 재시작'],
            [[p.get('namespace', ''), p.get('name', ''),
              (sev_ko(s), True, sev_rgb(s), 'CENTER', sev_bg(s)),
              (f"{p.get('restarts',0)}회 ({p.get('age','-')})", True, sev_rgb(s)),
              _last(p)]
             for p, s, _d in pods_hi], col_widths=[2.5, 5.5, 1.5, 3.5, 3.5])
    else:
        callout('✓ 재시작 이상 파드 없음 — 전체 Pod 재시작 횟수가 정상 범위입니다.',
                HEX_LOWD, GREEN)

    if ks_bad:
        h2('3.3 kube-system 이상 파드')
        callout(f"⚠ kube-system 비정상 파드 {len(ks_bad)}개 — 컨트롤 플레인 점검 필요",
                HEX_CRITD, RED)
        tbl(['파드명', '상태', '재시작', '노드'],
            [[p.get('name',''), p.get('state',''),
              str(p.get('restarts',0)), p.get('node','-')]
             for p in ks_bad], col_widths=[6, 2.5, 2, 6])

    # 메모리 순으로 정렬한 뒤 10개를 자른다 — 수집 결과는 CPU 순이다
    metrics = sorted(data.get('pod_metrics') or [],
                     key=lambda x: int(x.get('mem_mi', 0) or 0), reverse=True)[:10]
    if metrics:
        h2('3.4 메모리 사용 상위 파드 (Top 10)')
        para('메모리 사용량이 많은 파드입니다. Limit 이 없으면 노드 메모리가 부족해질 때 다른 파드까지 '
             '축출될 수 있고, Limit 이 사용량에 가깝게 설정되어 있으면 Limit 에 도달하는 순간 '
             'OOMKill 됩니다. Limit 은 실제 사용량을 관찰한 뒤 여유를 두고 정하세요.', size=10)
        tbl(['네임스페이스', '파드명', 'CPU (m)', 'MEM (MiB)'],
            [[m.get('namespace',''), m.get('name',''),
              f"{m.get('cpu_m',0)}m", f"{m.get('mem_mi',0)}Mi"]
             for m in metrics],
            col_widths=[3, 7, 2.5, 4])

    # Request/Limit 현황
    lr_items = data.get('limit_ranges') or []
    rq_items = data.get('resource_quotas') or []
    h2('3.5 리소스 Request/Limit 현황')
    lr_ns = {lr.get('namespace','') for lr in lr_items}
    rq_ns = {rq.get('namespace','') for rq in rq_items}
    para(f"LimitRange 설정 네임스페이스: {len(lr_ns)}개 | "
         f"ResourceQuota 설정 네임스페이스: {len(rq_ns)}개", size=10)
    if _failed('limit_ranges'):
        fail_callout()
    elif not lr_items:
        callout('LimitRange 미설정 — Request/Limit 을 적지 않은 파드는 노드 메모리를 제한 없이 쓸 수 '
                '있습니다. LimitRange 는 사용자 애플리케이션 네임스페이스에만 적용하고, 시스템 · 스토리지 '
                '네임스페이스(kube-system, longhorn-system, rook-ceph, cattle-*, cert-manager, monitoring)에는 '
                '적용하지 마세요 — 다시 시작된 파드에 기본 Limit 이 붙어 OOMKill · CPU 스로틀링이 생기거나 '
                '생성이 거부될 수 있습니다. 기본값은 관찰한 사용량을 근거로 정하세요.', HEX_MEDD, AMBER)
    else:
        bullet(f"LimitRange 적용 네임스페이스: {', '.join(sorted(lr_ns))}")
    ai_comment('워크로드 상태', f"""Kubernetes 워크로드 현황:
- 비정상 파드: {len(pods_nr)}개
- 재시작 이상 파드(10회 초과): {len(pods_hi)}개
- LimitRange 적용 네임스페이스: {len(lr_ns)}개 / ResourceQuota: {len(rq_ns)}개

워크로드 상태의 원인 분석과 운영 조치를 1~2문장으로 작성하세요.""")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. HPA / 오토스케일링
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [5/10] HPA/오토스케일링...')
    h1('4. HPA / 오토스케일링')

    h2('4.1 HPA 현황')
    _hpa_fail = _failed('hpa', 'deployments')
    if _hpa_fail:
        fail_callout()
    else:
        # 문장은 수치로만 만든다 — 데이터와 무관한 「대부분」 같은 표현을 쓰지 않는다
        para(f"점검 시점 기준 HPA(Horizontal Pod Autoscaler)는 {len(hpas)}개입니다. "
             f"시스템 네임스페이스를 뺀 사용자 Deployment {len(hpa_view['user'])}개 중 "
             f"HPA 적용 {len(hpa_view['with_hpa'])}개, 고정 레플리카 {len(hpa_view['no_hpa'])}개"
             + (f"(그중 replicas 를 Argo CD · 오퍼레이터가 관리 {len(hpa_view['managed'])}개)"
                if hpa_view['managed'] else '') + "입니다.", size=10)
    if not hpas and hpa_view['candidates'] and not _hpa_fail:
        callout(f"HPA 검토 대상 {len(hpa_view['candidates'])}개(replicas 2 이상 · 사용자 Deployment) — "
                "트래픽 급증 시 수동 스케일 아웃만 가능합니다.", HEX_MEDD, AMBER)
    elif hpas:
        tbl(['네임스페이스', '이름', '대상', 'Min', 'Max', '현재'],
            [[h.get('namespace',''), h.get('name',''), h.get('reference','-'),
              str(h.get('min',1)), str(h.get('max',1)), str(h.get('current',0))]
             for h in hpas], col_widths=[2.5, 3.5, 4, 1.5, 1.5, 3.5])

    h2('4.2 HPA 미적용 주요 워크로드')
    # 표시 우선순위: 검토 대상(replicas≥2 · 직접 관리) → 비정상 → 이름순. 시스템 네임스페이스는 뺀다
    _cand_keys = {(d.get('namespace'), d.get('name')) for d in hpa_view['candidates']}
    show_no_hpa = sorted(deps_no_hpa, key=lambda d: (
        0 if (d.get('namespace'), d.get('name')) in _cand_keys else 1,
        0 if int(d.get('ready',0)) < int(d.get('desired',0)) else 1,
        d.get('name', '')))[:20]

    def _hpa_note(d):
        owner = _replicas_owner(d)
        if owner:
            return f'replicas 를 {owner}가 관리 — HPA 를 붙이지 마세요'
        if int(d.get('desired', 0) or 0) >= 2:
            return 'HPA 검토 가능(사용량 근거 확인 후)'
        return '단일 레플리카'
    if _hpa_fail:
        fail_callout()
    elif show_no_hpa:
        para(f"HPA 미설정 사용자 Deployment {len(deps_no_hpa)}개 — 이 중 검토 대상은 "
             f"{len(hpa_view['candidates'])}개입니다. replicas 를 다른 컨트롤러(Argo CD · 오퍼레이터)가 "
             "관리하면 HPA 를 붙이지 마세요 — 두 컨트롤러가 replicas 를 번갈아 바꿉니다.", size=10)
        tbl(['네임스페이스', '이름', 'Ready/Desired', '비고'],
            [[d.get('namespace',''), d.get('name',''),
              f"{d.get('ready',0)}/{d.get('desired',0)}",
              _hpa_note(d)]
             for d in show_no_hpa], col_widths=[3, 5.5, 2.5, 5.5])
    else:
        callout('✓ HPA 검토 대상인 사용자 Deployment 가 없습니다.', HEX_LOWD, GREEN)

    pdbs = data.get('pdbs') or []
    if pdbs:
        h2('4.3 PDB (Pod Disruption Budget)')
        _prod = [p for p in pdbs if _pdb_manager(p) != 'user']
        if _prod:
            callout(f"제품이 관리하는 PDB {len(_prod)}개(Longhorn · Rook-Ceph · 오퍼레이터) — "
                    "수정 · 삭제하지 마세요. 노드 비우기는 해당 제품 절차를 따르세요.",
                    HEX_LGRAY, GRAY)
        tbl(['네임스페이스', '이름', 'MinAvail', 'Healthy', '허용 중단', '관리'],
            [[p.get('namespace',''), p.get('name',''),
              str(p.get('min_available','-')),
              f"{p.get('current_healthy',0)}/{p.get('desired_healthy',0)}",
              str(p.get('disruptions_allowed', '-')),
              _PDB_MANAGER_KO.get(_pdb_manager(p), '-')]
             for p in pdbs], col_widths=[3, 4, 2, 2, 2, 3.5])
    ai_comment('HPA/오토스케일링', f"""HPA(오토스케일링) 현황:
- 설정된 HPA: {len(hpas)}개
- 사용자 Deployment 중 HPA 미적용: {len(deps_no_hpa)}개 / 사용자 Deployment {len(hpa_view['user'])}개
- HPA 검토 대상(replicas 2 이상, replicas 를 다른 컨트롤러가 관리하지 않음): {len(hpa_view['candidates'])}개
- StatefulSet: {len(sts_all)}개

HPA 적용 현황과 오토스케일링 운영 전략을 1~2문장으로 평가하세요.""")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. Ingress / Service 구조
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [6/10] Ingress/Service...')
    h1('5. Ingress / Service 구조')

    h2('5.1 Ingress 현황')
    if _failed('ingresses'):
        fail_callout()
    else:
        para(f"총 {len(ingresses)}개 Ingress 구성.", size=10)
    if class_dist:
        tbl(['IngressClass', '개수', '해당 네임스페이스 (예시)'],
            [[cls, str(cnt),
              ', '.join(sorted({i.get('namespace','') for i in ingresses
                                if (i.get('class','<none>') or '<none>') == cls})[:5])]
             for cls, cnt in class_dist.most_common()],
            col_widths=[3.5, 2, 11])
    if no_class_ns:
        callout(f"<none> IngressClass {class_dist.get('<none>',0)}개 — "
                f"명시적 class 지정 권고: "
                f"{', '.join(no_class_ns[:10])}"
                + ('...' if len(no_class_ns) > 10 else ''),
                HEX_MEDD, AMBER)

    h2('5.2 TLS/HTTPS 현황')
    # cert-manager 감지
    has_cert_manager = any(n.get('name','') == 'cert-manager' for n in nss)
    if has_cert_manager:
        # 네임스페이스가 있다는 사실만 안다 — 「운영 중」 으로 단정하지 않는다
        para('cert-manager 네임스페이스가 있습니다. 인증서 발급 · 갱신 상태는 Certificate 리소스에서 '
             '확인하세요.', size=10)
    # spec.tls 로 판단한다(수집 시 tls 필드). 필드가 없는 데이터(옛 스냅샷 등)는 판단하지 않는다
    _tls_known   = [i for i in ingresses if isinstance(i.get('tls'), list)]
    tls_ingress  = [i for i in _tls_known if i['tls']]
    no_tls       = [i for i in _tls_known if not i['tls']]
    if _failed('ingresses'):
        fail_callout()
    elif ingresses and not _tls_known:
        callout('Ingress 의 TLS 설정(spec.tls)을 수집하지 않아 HTTPS 적용 여부를 판단하지 않았습니다.',
                HEX_LGRAY, GRAY)
    elif _tls_known:
        para(f"TLS 설정이 있는 Ingress {len(tls_ingress)}개 / 없는 Ingress {len(no_tls)}개.", size=10)
        if no_tls:
            callout(f"TLS 설정이 없는 Ingress {len(no_tls)}개 — HTTPS 적용 여부를 검토하세요. "
                    "앞단 로드밸런서에서 TLS 를 종료하는 구성이면 정상입니다.", HEX_MEDD, AMBER)

    h2('5.3 NodePort 노출 서비스')
    if _failed('services'):
        fail_callout()
    elif nodeport:
        _ctrl = [s for s in nodeport if _is_ingress_controller_svc(s)]
        callout(f"NodePort 노출 서비스 {len(nodeport)}건"
                + (f"(Ingress 컨트롤러 진입점 {len(_ctrl)}건 포함)" if _ctrl else '')
                + " — 외부 노출이 필요한 서비스인지 확인하세요.", HEX_MEDD, AMBER)
        def _ports(s):
            p = str(s.get('ports') or '-')
            return p if len(p) <= 30 else p[:29] + '…'

        def _np_sev(s):
            return sev_of.get(('nodeport', s.get('namespace', '') or 'cluster', s.get('name', '') or '-'),
                              'medium')

        def _np_rec(s):
            return (rec_of.get(('nodeport', s.get('namespace', '') or 'cluster', s.get('name', '') or '-'))
                    or '외부 노출 필요 여부 확인')
        tbl(['네임스페이스', '서비스명', '위험도', '포트', '권장 조치'],
            [[s.get('namespace',''), s.get('name',''),
              (sev_ko(_np_sev(s)), True, sev_rgb(_np_sev(s)), 'CENTER', sev_bg(_np_sev(s))),
              _ports(s), _np_rec(s)]
             for s in nodeport], col_widths=[2.5, 3.5, 1.5, 4, 5])
    else:
        callout('✓ NodePort 직접 노출 서비스 없음', HEX_LOWD, GREEN)

    lb_svcs = [s for s in svc_all if s.get('type') == 'LoadBalancer']
    if lb_svcs:
        h2('5.4 LoadBalancer 서비스')
        para(f"외부 노출 LoadBalancer 서비스 {len(lb_svcs)}개 — 보안 검토 권장.", size=10)
        def _ports2(s):
            p = str(s.get('ports') or '-')
            return p if len(p) <= 22 else p[:21] + '…'
        tbl(['네임스페이스', '서비스명', 'Cluster-IP', '포트', 'Age'],
            [[s.get('namespace',''), s.get('name',''),
              s.get('cluster-ip','-'), _ports2(s), s.get('age','-')]
             for s in lb_svcs], col_widths=[2.5, 4.5, 2.5, 4, 3])
    ai_comment('Ingress/Service 구조', f"""네트워크 노출 구조:
- Ingress: {len(ingresses)}개, Class 분포: {dict(class_dist)}
- NodePort 서비스: {len(nodeport)}개

네트워크 노출 관점의 보안·운영 이슈를 1~2문장으로 평가하세요.""")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. PVC / 스토리지
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [7/10] PVC/스토리지...')
    h1('6. PVC / 스토리지')

    h2('6.1 스토리지 구성 개요')
    pvcs_bound = len([p for p in pvcs_all if p.get('status') == 'Bound'])
    sc_list    = data.get('storage_classes') or []
    sc_names   = [s.get('name','') for s in sc_list]
    if _failed('pvcs'):
        fail_callout()
    else:
        para(f"주력 StorageClass: {', '.join(sc_names) if sc_names else 'N/A'}. "
             f"전체 PVC {len(pvcs_all)}개 중 Bound(정상) {pvcs_bound}개, "
             f"Lost {len(pvcs_lost)}개, Pending {len(pvcs_pend)}개입니다.", size=10)
    nfs_only = all('nfs' in s.get('provisioner','').lower() for s in sc_list) and sc_list
    if nfs_only:
        callout('NFS 기반 StorageClass만 운영 중 — NFS 서버 가용성이 전체 스토리지의 '
                '단일 장애점(SPOF)입니다. 디스크 사용률 모니터링을 강화하세요.',
                HEX_MEDD, AMBER)
    tbl(['항목', '수치'], [
        ['전체 PVC',       _n('pvcs', str(len(pvcs_all)))],
        ['Bound (정상)',   _n('pvcs', str(pvcs_bound))],
        ['Lost',           _n('pvcs', str(len(pvcs_lost)))],
        ['Pending',        _n('pvcs', str(len(pvcs_pend)))],
        ['StorageClass 수', _n('storage_classes', str(len(sc_list)))],
    ], col_widths=[5, 11.5])

    h2('6.2 이상 PVC (Lost / Pending)')
    if _failed('pvcs'):
        fail_callout()
    elif pvcs_bad:
        if pvcs_lost:
            callout(f"⚠ PV 연결이 끊어진(Lost) PVC {len(pvcs_lost)}건 — 삭제하지 마세요. 백엔드 볼륨을 "
                    "찾아 같은 이름의 PV(claimRef)로 다시 연결해야 합니다.", HEX_CRITD, RED)
        if pvcs_pend:
            callout(f"Pending PVC {len(pvcs_pend)}건 — {_PVC_PENDING_DETAIL}.", HEX_LGRAY, GRAY)

        def _pvc_row(p):
            st = p.get('status', '')
            if st == 'Lost':
                sev, rec = 'critical', _PVC_LOST_REC
            elif st == 'Pending':
                sev, rec = 'low', '파드가 이미 있는데도 대기 중이면 StorageClass · 용량 · accessMode 확인'
            else:
                sev, rec = 'medium', 'kubectl describe pvc 로 상태 확인'
            return [p.get('namespace',''), p.get('name',''),
                    (sev_ko(sev), True, sev_rgb(sev), 'CENTER', sev_bg(sev)),
                    st, p.get('capacity','-'), rec]
        tbl(['네임스페이스', 'PVC명', '위험도', '상태', '용량', '권장 조치'],
            [_pvc_row(p) for p in sorted(pvcs_bad, key=lambda x: x.get('status') != 'Lost')],
            col_widths=[2.5, 3.5, 1.5, 1.5, 2, 5.5])
    else:
        callout('✓ 이상 PVC 없음 — 전체 PVC가 정상 Bound 상태입니다.', HEX_LOWD, GREEN)

    if large_pvcs:
        h2(f'6.3 대용량 PVC ({len(large_pvcs)}개, 50Gi 이상)')
        tbl(['네임스페이스', 'PVC명', '용량', '상태', '비고'],
            [[p.get('namespace',''), p.get('name',''), p.get('capacity','-'),
              p.get('status','-'), 'retention 정책 점검 권장']
             for p, gi in large_pvcs[:15]], col_widths=[2.5, 5, 2, 2, 5])

    if sc_list:
        h2('6.4 StorageClass')
        tbl(['이름', 'Provisioner', 'Reclaim', '기본값'],
            [[s.get('name',''), s.get('provisioner',''),
              s.get('reclaim_policy','-'), s.get('is_default','false')]
             for s in sc_list], col_widths=[4, 7, 2.5, 3])
    ai_comment('PVC/스토리지', f"""스토리지 현황:
- PVC 총 {len(pvcs_all)}개 (Bound: {pvcs_bound}개, Lost: {len(pvcs_lost)}개, Pending: {len(pvcs_pend)}개)
- StorageClass: {', '.join(sc_names) if sc_names else 'N/A'}
- NFS 단독 구성: {'예' if nfs_only else '아니오'}

스토리지 운영 관점의 위험 요소를 1~2문장으로 평가하세요.""")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. 보안
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [8/10] 보안...')
    h1('7. 보안')

    # RBAC 를 빼면 하위 번호를 당겨 7.1 이 비지 않게 한다
    rbac_on = _section_on(sections, 'rbac')
    rbac = data.get('rbac') or {}
    sub = 0
    if rbac_on:
        sub += 1
        h2(f'7.{sub} RBAC 구성')
        if _failed('rbac'):
            fail_callout()
        else:
            tbl(['항목', '수량'], [
                ['ClusterRole',        str(rbac.get('cluster_roles', 0))],
                ['ClusterRoleBinding', str(rbac.get('cluster_role_bindings', 0))],
                ['Role',               str(rbac.get('roles', 0))],
                ['RoleBinding',        str(rbac.get('role_bindings', 0))],
                ['ServiceAccount',     str(rbac.get('service_accounts', 0))],
            ], col_widths=[5, 11.5])
        _risky = data.get('rbac_risky') or []
        _plat = [r for r in _risky if _rbac_is_platform(r)]
        if _failed('rbac_risky'):
            callout(f"과도 권한 계정: {FAIL_TXT}", HEX_LGRAY, GRAY)
        elif _risky:
            para(f"클러스터 관리자급 권한 계정 {len(_risky)}개 — 제품 구성 요소 {len(_plat)}개(정보), "
                 f"그 밖의 계정 {len(_risky) - len(_plat)}개(높음).", size=10)
            callout('Rancher · RKE2 · Argo CD · Longhorn · cert-manager 등 제품이 설치하며 요구한 권한은 '
                    '바인딩을 지우거나 줄이지 마세요. 그 밖의 계정도 권한을 줄이기 전에 그 계정을 쓰는 '
                    '프로그램을 먼저 확인하세요 — 바로 지우면 그 컨트롤러가 멈춥니다.', HEX_LGRAY, DARK)

    sub += 1
    h2(f'7.{sub} NetworkPolicy')
    netpols = data.get('network_policies') or []
    # CNI 전용 정책(Cilium · Calico)도 센다. 키가 없으면(스냅샷 · 옛 데이터) 확인하지 않은 것이다.
    _cni = data.get('cni_network_policies')
    _cni_known = {k: v for k, v in (_cni or {}).items() if isinstance(v, int)}
    _cni_unknown = (not isinstance(_cni, dict) or _failed('cni_network_policies')
                    or any(v is None for v in (_cni or {}).values()))
    _cni_total = sum(_cni_known.values())
    if _failed('network_policies'):
        fail_callout()
    elif netpols or _cni_total:
        para(f"Kubernetes NetworkPolicy {len(netpols)}개"
             + ''.join(f" · {k} {v}개" for k, v in _cni_known.items() if v)
             + " 설정됨.", size=10)
    elif _cni_unknown:
        callout('ℹ Kubernetes NetworkPolicy 가 없습니다. CNI 전용 정책(Cilium · Calico)은 확인하지 못해 '
                '트래픽 제한이 없다고 단정할 수 없습니다.', HEX_LGRAY, DARK)
    else:
        callout('ℹ NetworkPolicy 미설정 — 네임스페이스 간 트래픽 제한이 없습니다. '
                '주요 서비스 네임스페이스에 NetworkPolicy 적용을 검토하세요.', HEX_MEDD, DARK)
    if not _failed('network_policies'):
        bullet('기본 거부(default-deny) 정책을 넣을 때는 DNS(53) · Ingress 컨트롤러 · 모니터링 · '
               '웹훅 · 스토리지 복제 트래픽을 허용하는 규칙을 함께 넣어야 합니다. 한 네임스페이스에서 '
               '먼저 시험한 뒤 넓히세요.', size=9)
    # AI 요약에도 RBAC 수치를 넘기지 않는다 — 넘기면 제외했는데도 본문에 다시 등장한다
    _rbac_line = (f"\n- RBAC: ClusterRole {rbac.get('cluster_roles', 0)}개, "
                  f"ClusterRoleBinding {rbac.get('cluster_role_bindings', 0)}개" if rbac_on else '')
    ai_comment('보안 점검', f"""보안 점검 결과:
- NodePort 노출 서비스: {len(nodeport)}개{_rbac_line}
- NetworkPolicy: {len(netpols)}개 (Cilium · Calico 정책 {_cni_total}개{', 일부 확인 불가' if _cni_unknown else ''})

보안 관점의 핵심 위험 요소와 권고 조치를 1~2문장으로 작성하세요.""")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. 발견 사항 및 권고
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [9/10] 발견 사항...')
    h1('8. 발견 사항 및 권고')

    if not findings and not (data.get('collect_errors') or []):
        callout('✓ 발견된 이슈가 없습니다. 클러스터 상태가 양호합니다.', HEX_LOWD, GREEN)
    elif not findings:
        # 수집 실패가 있으면 「양호」 라고 적지 않는다
        callout(f"발견된 이슈는 없지만 일부 항목을 {FAIL_TXT}", HEX_LGRAY, GRAY)
    else:
        if ko_counts['긴급'] > 0:
            callout(f"⚠ 긴급 이슈 {ko_counts['긴급']}건: 서비스 중단이나 데이터 손실로 이어질 수 있는 항목입니다. "
                    "각 항목의 권장 조치를 먼저 확인하세요.",
                    HEX_CRITD, RED)
        if ko_counts['높음'] > 0:
            callout(f"▲ 높음 이슈 {ko_counts['높음']}건: 단기 방치 시 장애로 발전할 수 있는 전조 증상입니다.",
                    HEX_HIGHD, ORANGE)
        if any(f.get('category') == 'collect' for f in findings):
            callout('수집하지 못한 항목이 있습니다 — 그 항목은 판단하지 않았으며, 발견 없음이 정상을 뜻하지 않습니다.',
                    HEX_LGRAY, GRAY)
        sf = sorted(findings, key=lambda f: SEV_ORD.get(
            sev_ko(f.get('severity') or f.get('level', 'INFO')), 9))

        def sev_cell(f):
            orig = f.get('severity') or f.get('level', '')
            s = sev_ko(orig)
            return (s, True, sev_rgb(orig), 'CENTER', sev_bg(orig))

        tbl(['위험도', '유형', '대상', '현황', '설명', '권장 조치'],
            [[sev_cell(f), f.get('category',''),
              f"{f.get('namespace','cluster')}/{f.get('name','-')}",
              f.get('value',''), f.get('detail',''), f.get('rec','')]
             for f in sf], col_widths=[1.5, 2.5, 2.5, 2, 4, 4])

    h2('8.1 긴급 — 즉시 조치 (1주 이내)')
    if priority['immediate']:
        tbl(['#', '위험도', '대상', '현황', '권장 조치'],
            [[str(i+1),
              (sev_ko(r['severity']), True, sev_rgb(r['severity']), 'CENTER', sev_bg(r['severity'])),
              r['target'], r['value'], r['recommendation']]
             for i, r in enumerate(priority['immediate'][:15])],
            col_widths=[0.8, 1.5, 3.5, 2, 8.7])
    else:
        callout('✓ 즉시 조치가 필요한 긴급/높음 이슈가 없습니다.', HEX_LOWD, GREEN)

    h2('8.2 중간 — 1~4주 내 조치')
    if priority['short_term']:
        tbl(['#', '위험도', '대상', '현황', '권장 조치'],
            [[str(i+1),
              (sev_ko(r['severity']), True, sev_rgb(r['severity']), 'CENTER', sev_bg(r['severity'])),
              r['target'], r['value'], r['recommendation']]
             for i, r in enumerate(priority['short_term'][:15])],
            col_widths=[0.8, 1.5, 3.5, 2, 8.7])
    else:
        para('중간 우선순위 항목이 없습니다.', size=10, color=GRAY)

    if priority.get('backlog'):
        h2('8.3 낮음 — 분기 내 추적')
        tbl(['#', '위험도', '대상', '설명'],
            [[str(i+1),
              (sev_ko(r['severity']), True, sev_rgb(r['severity']), 'CENTER', sev_bg(r['severity'])),
              r['target'], r.get('detail', '-')]
             for i, r in enumerate(priority['backlog'][:12])],
            col_widths=[0.8, 1.5, 4, 10.2])

    events = data.get('events') or []
    if events:
        h2('8.4 Warning 이벤트')
        para(f"총 {len(events)}건의 Warning 이벤트가 수집되었습니다.", size=10)
        tbl(['네임스페이스', '대상', '이유', '횟수', '메시지'],
            [[e.get('namespace',''), e.get('obj',''), e.get('reason',''),
              str(e.get('count',1)), e.get('message','')[:60]]
             for e in events[:20]], col_widths=[2, 3, 2, 1.5, 8])
    _top_f = '; '.join(
        f"[{sev_ko(r.get('severity',''))}] {r.get('detail', r.get('message', ''))}"
        for r in findings[:5]
    ) if findings else '없음'
    ai_comment('발견사항 종합', f"""발견 이슈 요약:
- 긴급: {ko_counts['긴급']}건, 높음: {ko_counts['높음']}건, 중간: {ko_counts['중간']}건, 낮음: {ko_counts['낮음']}건
- 주요 이슈: {_top_f}

전체 발견사항에 대한 핵심 조치 방향을 1~2문장으로 작성하세요.""")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════════
    # 9. 예상 개선 작업 (v1 스타일 자동 생성)
    # ═══════════════════════════════════════════════════════════════════════════
    log_fn('  [10/10] 예상 개선 작업...')
    h1('9. 예상 개선 작업')
    para('발견 이슈 기반으로 자동 생성된 개선 작업 목록입니다. '
         '우선순위와 예상 공수는 이슈 유형에 따라 자동 산정되었습니다.', size=10, color=GRAY)
    spacer()

    # 아래 next(...) 는 substring 매칭이라 **dict 삽입 순서에 의존한다.**
    # 'network' 가 'service'/'ingress' 보다 앞에 있어야 netscan 의 network_ingress·
    # network_reach 카테고리가 '보안/네트워크' 로 잡힌다. 순서를 바꾸지 말 것.
    AREA_MAP = {
        'apiserver': '인프라',
        'pod_restart': '운영/SRE', 'pvc': '인프라', 'node': '인프라',
        'security': '보안', 'network': '보안/네트워크', 'rbac': '보안',
        'hpa': '운영', 'resource': '운영', 'deployment': '운영',
        'service': '네트워크', 'ingress': '네트워크',
        'helm': '운영', 'statefulset': '운영', 'daemonset': '운영',
    }
    EFFORT_MAP = {'긴급': '1~3일', '높음': '1~5일', '중간': '3~10일', '낮음': '1~2주'}

    work_rows = []
    seen = set()
    for r in (priority['immediate'] + priority['short_term'] + (priority.get('backlog') or [])):
        # 정보(info)는 작업이 아니다 — 「수정 · 삭제하지 마세요」 같은 권고가 개선 작업으로 올라가면 안 된다
        if (r.get('severity') or '') == 'info':
            continue
        rec = r.get('recommendation', '')[:60]
        if rec in seen: continue
        seen.add(rec)
        cat  = r.get('category', '').lower()
        area = next((v for k, v in AREA_MAP.items() if k in cat), '운영')
        sev  = sev_ko(r['severity'])
        work_rows.append([
            str(len(work_rows) + 1),
            rec,
            area,
            EFFORT_MAP.get(sev, '미정'),
            (sev, True, sev_rgb(r['severity']), 'CENTER', sev_bg(r['severity'])),
        ])
        if len(work_rows) >= 20: break

    if work_rows:
        tbl(['#', '작업명', '담당 영역', '예상 공수', '우선순위'],
            work_rows, col_widths=[0.8, 8, 2.5, 2, 3.2])
    else:
        callout('✓ 즉시 개선 작업이 필요한 이슈가 없습니다.', HEX_LOWD, GREEN)

    # ═══════════════════════════════════════════════════════════════════════════
    # 10. 네트워크 스캔 (선택 점검) — v1.2.121
    #     「네트워크 스캔」을 체크했을 때만 존재한다. 체크 안 하면 이 장 자체가 없어
    #     기존 보고서와 구조가 동일하다. 발견된 문제는 이 장과 별개로 8장 발견사항 표·
    #     8.1~8.3 버킷·표지 심각도 칩·9장 개선작업에 이미 합류돼 있다.
    # ═══════════════════════════════════════════════════════════════════════════
    _ns = data.get('netscan') or {}
    if _ns.get('ran'):
        doc.add_page_break()
        log_fn('  [+] 네트워크 스캔 결과...')
        h1('10. 네트워크 스캔 (선택 점검)')

        h2('10.1 점검 범위 및 방법')
        para('클러스터에 디버그 파드를 배포하지 않고, API 서버를 경유해 확인했습니다.',
             size=10, color=DARK)
        bullet(f"점검 대상: {_ns.get('target_count', 0)}건"
               + (f" / 후보 {_ns.get('total_candidates', 0)}건"
                  if _ns.get('truncated') else '')
               + f" · 제외 {len(_ns.get('skipped') or [])}건"
               + f" · 소요 {_ns.get('duration_s', 0)}초")
        bullet('도달성: API 서버 Service proxy 로 각 서비스의 루트 경로에 1회 요청')
        bullet('TLS: Ingress 가 참조하는 Secret 의 인증서를 읽어 만료일·SAN 확인 '
               '(네트워크를 타지 않음)')
        # 예산 초과로 못 본 게 있으면 반드시 밝힌다 — 조용히 빠지면 '정상'으로 오독된다
        if _ns.get('budget_exceeded'):
            _un = []
            _probed = len(_ns.get('probes') or [])
            if _ns.get('target_count', 0) > _probed:
                _un.append(f"도달성 {_ns['target_count'] - _probed}건")
            if _ns.get('certs_skipped'):
                _un.append(f"TLS 인증서 {_ns['certs_skipped']}건")
            callout('⚠ 시간이 초과되어 일부를 점검하지 못했습니다'
                    + (f" ({' · '.join(_un)} 미점검)" if _un else '')
                    + " — '발견 없음'이 '정상'을 뜻하지 않습니다.", HEX_HIGHD, ORANGE)
        if _ns.get('truncated'):
            callout(f"⚠ 대상이 상한을 넘어 {_ns.get('target_count', 0)}건만 점검했습니다 — "
                    f"'발견 없음'이 '정상'을 뜻하지 않습니다.", HEX_MEDD, AMBER)
        if _ns.get('permission') == 'denied':
            callout('⚠ 이 kubeconfig 에 services/proxy 권한이 없어 도달성 점검을 '
                    '건너뛰었습니다. TLS·정합성 검사 결과만 유효합니다.', HEX_MEDD, AMBER)
        callout('※ 점검 한계 — API 서버가 서비스를 엔드포인트로 해석해 직접 접속하므로 '
                'ClusterIP·kube-proxy 경로는 검증되지 않았습니다. 파드 간 통신'
                '(NetworkPolicy 실효·CNI 오버레이)과 비-HTTP 포트는 점검 범위가 아닙니다.',
                HEX_LGRAY, GRAY)

        # 제외 사유 집계 — 왜 안 봤는지가 본 결과만큼 중요하다
        _skip_by = {}
        for s in (_ns.get('skipped') or []):
            _skip_by[s.get('reason') or '-'] = _skip_by.get(s.get('reason') or '-', 0) + 1
        if _skip_by:
            spacer()
            para('제외 사유', bold=True, size=10, color=NAVY)
            tbl(['제외 사유', '건수'],
                [[k, str(v)] for k, v in sorted(_skip_by.items(), key=lambda x: -x[1])],
                col_widths=[13.5, 3])

        h2('10.2 도달성 결과')
        _probes = sorted(_ns.get('probes') or [],
                         key=lambda p: (bool(p.get('ok')), p.get('namespace') or ''))
        if _probes:
            _rows = []
            for p in _probes[:60]:
                if p.get('ok'):
                    _res = ('정상', True, GREEN, 'CENTER', HEX_LOWD)
                    _st = p.get('status')
                    if p.get('redirected') or (_st and 300 <= int(_st) < 400):
                        _det = (f"HTTP {_st or '3xx'} 리다이렉트 · "
                                f"{p.get('latency_ms', 0):.0f}ms (응답함)")
                    else:
                        _det = f"HTTP {_st or 200} · {p.get('latency_ms', 0):.0f}ms"
                elif p.get('status') is None:
                    _res = ('실패', True, RED, 'CENTER', HEX_CRITD)
                    _det = str(p.get('error') or '연결되지 않음')[:80]
                elif 500 <= int(p['status']) <= 599:
                    _res = ('오류', True, RED, 'CENTER', HEX_CRITD)
                    _det = f"HTTP {p['status']} — 서버 오류"
                else:
                    _res = ('응답', True, GRAY, 'CENTER', HEX_LGRAY)
                    _det = f"HTTP {p['status']} — 정상 취급(인증 보호·루트 경로 없음 등)"
                _rows.append([p.get('namespace') or '-', p.get('name') or '-',
                              str(p.get('port') or '-'),
                              (p.get('scheme') or 'http').upper(), _res, _det])
            tbl(['네임스페이스', '서비스', '포트', '프로토콜', '결과', '상세'],
                _rows, col_widths=[2.5, 3.5, 1.5, 1.5, 2, 5.5])
            if len(_probes) > 60:
                para(f'… 총 {len(_probes)}건 중 60건만 표시', size=9, color=GRAY)
        else:
            callout('점검할 도달성 대상이 없었습니다 (10.1 의 제외 사유 참고).',
                    HEX_LGRAY, GRAY)

        h2('10.3 TLS 인증서 만료')
        _certs = _ns.get('certs') or []
        if _certs:
            _crows = []
            for c in sorted(_certs, key=lambda x: (x.get('days_left') is None,
                                                   x.get('days_left') or 0)):
                _d = c.get('days_left')
                if c.get('error'):
                    _left = ('확인 실패', True, ORANGE, 'CENTER', HEX_HIGHD)
                elif not isinstance(_d, int):
                    _left = '-'      # 평문 — 튜플로 주면 cell_bg=None 이 _set_cell_bg 를 깨뜨린다
                elif _d < 14:
                    _left = (f'D-{_d}', True, RED, 'CENTER', HEX_CRITD)
                elif _d < 30:
                    _left = (f'D-{_d}', True, ORANGE, 'CENTER', HEX_HIGHD)
                elif _d < 60:
                    _left = (f'D-{_d}', True, AMBER, 'CENTER', HEX_MEDD)
                else:
                    _left = (f'D-{_d}', False, GREEN, 'CENTER', HEX_LOWD)
                _crows.append([
                    c.get('namespace') or '-', c.get('ingress') or '-',
                    c.get('secret') or '-',
                    ', '.join((c.get('hosts') or [])[:2]) or '-',
                    _left,
                    ('SAN 불일치' if c.get('san_ok') is False
                     else (str(c.get('error'))[:40] if c.get('error')
                           else (c.get('not_after') or '')[:10])),
                ])
            tbl(['네임스페이스', 'Ingress', 'Secret', '호스트', '남은 기간', '만료일/비고'],
                _crows, col_widths=[2.3, 3, 3, 3, 1.7, 3.5])
        else:
            callout('TLS 를 사용하는 Ingress 가 없거나 인증서 참조가 없습니다.',
                    HEX_LGRAY, GRAY)

        ai_comment('네트워크 스캔', f"""점검 대상 {_ns.get('target_count', 0)}건, \
제외 {len(_ns.get('skipped') or [])}건, TLS 인증서 {len(_certs)}건을 확인했습니다.
도달성 실패 {sum(1 for p in _probes if not p.get('ok'))}건.
이 점검은 API 서버 경유이므로 ClusterIP·kube-proxy 경로와 파드 간 통신은 검증되지 않았습니다.
위 결과만 근거로 네트워크 관점에서 확인이 필요한 부분을 1~2문장으로 짚어주세요.""")

    _fix_ea(doc)
    doc.save(out_path)
    return out_path


def _report_write_txt(data, findings, llm_summary, out_path):
    """python-docx 없을 때 TXT 폴백."""
    priority = _report_build_priority_summary(findings)
    lines = [
        '=' * 60,
        'Kubernetes 클러스터 보고서',
        f"생성: {data.get('collected_at', '')}",
        f"버전: {data.get('cluster_version', 'N/A')}",
        '=' * 60, '',
        f"노드: {len(data.get('nodes') or [])}, "
        f"파드: {len(data.get('pods') or [])}, "
        f"Deployment: {len(data.get('deployments') or [])}, "
        f"Job: {len(data.get('jobs') or [])}, "
        f"CronJob: {len(data.get('cronjobs') or [])}",
        '', '── 발견 사항 ──',
    ]
    for f in findings:
        lines.append(
            f"  [{(f.get('severity') or f.get('level', 'INFO')).upper()}] "
            f"{f.get('namespace', 'cluster')}/{f.get('name', '-')}: "
            f"{f.get('value', '-')} — {f.get('detail') or f.get('message', '')} "
            f"(권장: {f.get('rec', '-')})"
        )
    lines += ['', '── 개선 우선순위 ──']
    lines.append(
        f"긴급 {priority['counts'].get('critical', 0)} / "
        f"높음 {priority['counts'].get('high', 0)} / "
        f"중간 {priority['counts'].get('medium', 0)}"
    )
    for row in priority['immediate'][:10]:
        lines.append(f"  [즉시] {row['target']} — {row['recommendation']}")
    for row in priority['short_term'][:10]:
        lines.append(f"  [단기] {row['target']} — {row['recommendation']}")
    if data.get('events'):
        lines += ['', '── Warning 이벤트 ──']
        for e in (data.get('events') or [])[:30]:
            lines.append(
                f"  [{e.get('reason', '-')}] {e.get('namespace', '')}/{e.get('obj', '')}: "
                f"{e.get('message', '')}"
            )
    if llm_summary:
        lines += ['', '── AI 분석 ──', llm_summary]
    Path(out_path).write_text('\n'.join(lines), encoding='utf-8')
    return out_path




# ─────────────────────────────────────────────────────────────────────────────

def _esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _table(headers: list, rows: list, keys: list) -> str:
    th = ''.join(f'<th>{h}</th>' for h in headers)
    trs = ''
    for row in rows:
        tds = ''.join(f'<td>{_esc(row.get(k, ""))}</td>' for k in keys)
        trs += f'<tr>{tds}</tr>'
    return f'<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def _build_report_html(k8s: K8sManager, ns: str, sections: set) -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ver = k8s.cluster_info.get('version', 'N/A')
    parts = []

    def section(title, content):
        parts.append(f'<section><h2>{_esc(title)}</h2>{content}</section>')

    # ── 노드 ──
    if 'nodes' in sections:
        rows = k8s.get_nodes()
        section('노드 상태', _table(
            ['이름', '상태', '역할', 'Version', 'OS', 'Age'],
            rows, ['name', 'status', 'roles', 'version', 'os', 'age']))

    # ── 파드 ──
    if 'pods' in sections:
        rows = [{k: v for k, v in r.items() if not k.startswith('_')}
                for r in k8s.get_pods(ns or None)]
        section(f'파드{"" if not ns else f" ({ns})"}', _table(
            ['이름', '네임스페이스', '상태', 'Ready', '재시작', '노드', 'Age'],
            rows, ['name', 'namespace', 'status', 'ready', 'restarts', 'node', 'age']))

    # ── 디플로이먼트 ──
    if 'deployments' in sections:
        rows = [{k: v for k, v in r.items() if not k.startswith('_')}
                for r in k8s.get_deployments(ns or None)]
        section(f'디플로이먼트', _table(
            ['이름', '네임스페이스', 'Ready', 'Up-to-date', 'Available', 'Age'],
            rows, ['name', 'namespace', 'ready', 'up-to-date', 'available', 'age']))

    # ── 서비스 ──
    if 'services' in sections:
        rows = [{k: v for k, v in r.items() if not k.startswith('_')}
                for r in k8s.get_services(ns or None)]
        section('서비스', _table(
            ['이름', '네임스페이스', '타입', 'Cluster IP', 'External IP', 'Port(s)', 'Age'],
            rows, ['name', 'namespace', 'type', 'cluster-ip', 'external-ip', 'ports', 'age']))

    # ── PVC ──
    if 'pvcs' in sections:
        rows = [{k: v for k, v in r.items() if not k.startswith('_')}
                for r in k8s.get_pvcs(ns or None)]
        section('PVC', _table(
            ['이름', '네임스페이스', '상태', 'Volume', 'Capacity', 'Access Modes', 'Age'],
            rows, ['name', 'namespace', 'status', 'volume', 'capacity', 'access-modes', 'age']))

    # ── Helm ──
    if 'helm' in sections:
        rows = [{k: v for k, v in r.items() if not k.startswith('_')}
                for r in k8s.get_helm_releases()]
        section('Helm 릴리스', _table(
            ['이름', '네임스페이스', '차트', 'App Version', '상태', 'Revision', '업데이트'],
            rows, ['name', 'namespace', 'chart', 'app_version', 'status', 'revision', 'updated']))

    # ── ArgoCD ──
    if 'argocd' in sections:
        raw = k8s.get_argocd_apps()
        if raw:
            rows = [PolarisAPI._transform_argo(item) for item in raw]
            section('ArgoCD 앱', _table(
                ['이름', '네임스페이스', 'Sync', 'Health', 'Repo', 'Revision'],
                rows, ['name', 'namespace', 'sync', 'health', 'repo', 'revision']))

    body = '\n'.join(parts) if parts else '<p>선택된 섹션이 없습니다.</p>'

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Polaris 클러스터 보고서</title>
<style>
  body {{ font-family: "Segoe UI", "Noto Sans KR", sans-serif; margin: 0; padding: 24px;
         background: #fff; color: #1e293b; font-size: 13px; }}
  h1 {{ font-size: 22px; color: #0f172a; margin-bottom: 4px; }}
  .meta {{ color: #64748b; font-size: 12px; margin-bottom: 32px; }}
  section {{ margin-bottom: 32px; }}
  h2 {{ font-size: 14px; font-weight: 700; color: #0f172a; border-bottom: 1px solid #cbd5e1;
        padding-bottom: 6px; margin-bottom: 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead {{ color: #0f172a; border-bottom: 1px solid #94a3b8; }}
  th {{ padding: 9px 12px; text-align: left; font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: .05em; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #e2e8f0; }}
  tr:last-child td {{ border-bottom: none; }}
</style>
</head>
<body>
<h1>⎈ Polaris 클러스터 보고서</h1>
<div class="meta">생성 시각: {now} &nbsp;·&nbsp; 클러스터 버전: {_esc(ver)}</div>
{body}
</body>
</html>'''


