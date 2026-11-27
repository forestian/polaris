# -*- coding: utf-8 -*-
"""네트워크 스캐닝 — 클러스터 스캔의 선택(옵트인) 점검. v1.2.121

건강 스캔(→ 클러스터 스캔)과 보고서에서 「네트워크 스캐닝」을 체크했을 때만 동작한다.
**클러스터에 아무것도 배포하지 않는다** — netshoot 같은 디버그 이미지를 띄우지 않고,
로컬 kubeconfig + API 서버 경유로만 확인한다(kubectl/k9s 를 로컬에 두고 원격을 보는
Polaris 의 기존 방식과 같은 성격). 그래서 Falco 런타임 규칙을 건드리지 않는다.

점검 수단
  - 도달성 → API 서버 Service proxy (core.connect_get_namespaced_service_proxy).
             서브프로세스·로컬 포트 바인딩·고아 프로세스가 없다.
  - TLS    → Ingress 가 참조하는 kubernetes.io/tls Secret 의 tls.crt 를 읽어 파싱.
             네트워크를 타지 않으므로 결과가 결정적이다.

왜 kubectl port-forward 가 아닌가 (검토 후 배제)
  1. `_build_port_forward_spec` (src/k8s.py) 은 로컬 포트를 비우면 `local = remote` 로
     처리한다 — "kubectl 이 빈 포트를 고른다"가 아니다. 로컬 443/80 을 붙잡아 관리자 PC의
     다른 프로그램과 충돌하고, 그 충돌이 클러스터 장애로 오탐된다.
  2. TLS 가 원리적으로 틀린다. SNI 를 접속 호스트로 고정하면
     127.0.0.1 을 SNI 로 보내고, ingress-nginx 는 가짜 기본 인증서를 돌려준다 — 만료일·SAN
     전부 무의미해진다. HTTP 도 Host: 127.0.0.1 이라 default backend 응답을 받는다.
  3. 프로브는 daemon 스레드에서 돌고, 앱 종료 시 daemon 은 unwind 없이 죽어 finally 가
     실행되지 않는다 → kubectl.exe 가 루프백 포트를 물고 남는다.

한계 (보고서 10.1 에 그대로 표기한다)
  - API 서버가 Service 를 엔드포인트로 해석해 직접 붙으므로 **ClusterIP·kube-proxy 경로는
    검증되지 않는다.**
  - 파드 간 통신(NetworkPolicy 실효·CNI 오버레이)은 범위 밖이다.
  - HTTP 계열 포트만 점검한다. 비-HTTP(raw TCP/UDP)는 대상이 아니다.

4단계 — I/O 와 판정을 분리한다. reports._report_evaluate 가 순수 함수로 남아야 하기 때문이다.
  netscan_collect_inputs(k8s)   → inputs   (I/O · 목록 조회)
  netscan_plan(inputs)          → plan     (순수 · 대상/제외 결정)
  netscan_run(k8s, plan, ...)   → result   (I/O · 프로브)   → data['netscan'] 이 된다
  netscan_findings(result)      → findings (순수 · 규칙 판정)
"""
import base64
import fnmatch
import re
import time
from concurrent.futures import (ThreadPoolExecutor, as_completed,
                                TimeoutError as FuturesTimeout)
from datetime import datetime, timezone

# ── 스캔 제외 기준 ────────────────────────────────────────────────────────────
# 시스템 네임스페이스는 기본 제외. metrics-server 는 인증이 걸려 401, kube-dns 는 UDP,
# 컨트롤러 내부 서비스는 루트 경로가 없어 — 구조적으로 오탐만 쏟아진다.
# cert-manager·ingress-nginx 처럼 사용자가 설치한 인프라는 제외하지 않는다.
_SYS_NS = frozenset({'kube-system', 'kube-public', 'kube-node-lease'})
_SYS_NS_GLOB = ('kube-*', 'cattle-*', 'calico-*', 'tigera-*', 'fleet-*',
                'longhorn-*', 'rancher-*')

# HTTP 로 봐도 되는 포트. 이름(name/appProtocol) 우선, 없으면 번호로 추정.
_HTTP_NAMES = frozenset({'http', 'https', 'http2', 'web', 'api', 'ui',
                         'http-web', 'https-web', 'metrics'})
_HTTP_NUMS = frozenset({80, 443, 3000, 5000, 8000, 8080, 8443, 9090, 9100})
# TLS 로 붙어야 하는 포트 (Service proxy 의 scheme 접두를 https 로)
_TLS_NAMES = frozenset({'https', 'https-web'})
_TLS_NUMS = frozenset({443, 8443})

# 제외 이유 — 테스트가 이 문자열로 검증하므로 값을 바꿀 때 테스트도 같이 바꿔야 한다.
SKIP_SYSTEM_NS = '시스템 네임스페이스'
SKIP_EXTERNALNAME = 'ExternalName 서비스'
SKIP_NO_PORTS = '노출 포트 없음'
SKIP_HEADLESS = 'headless 서비스'
SKIP_NO_SELECTOR = 'selector 없음 (수동 endpoints)'
SKIP_GRPC = 'gRPC 포트'
SKIP_NON_HTTP = 'HTTP 포트 아님'
SKIP_MESH = '서비스 메시 사이드카 (mTLS 로 평문 거부)'
SKIP_NO_ENDPOINT = 'ready endpoint 없음 (도달성 점검 불가)'
SKIP_CAP = '대상 상한 초과'

# 정상으로 취급하는 HTTP 상태코드 — 신고하지 않는다. 이걸 신고하면 기능이 노이즈가 되고
# 사용자가 옵션을 끈다.
#   400 HTTPS 포트에 평문 요청 · 401/403 인증 보호 · 404 루트 경로 없음 ·
#   405 메서드 불허 · 426 업그레이드 필요 · 501 미구현(gRPC-over-HTTP 등)
# 501 은 5xx 범위지만 "서버 장애"가 아니라 "그 요청을 지원하지 않음"이라 여기에 둔다.
_BENIGN_STATUS = frozenset({400, 401, 403, 404, 405, 426, 501})

# 시간 예산·동시성 (v1.2.122 재조정)
#
# v1.2.121 초기값(동시 4 · 프로브 8초 · 예산 90초 · 상한 100)은 서로 모순이었다:
#   100건 × 8초 ÷ 4 = 200초  →  예산 90초에서 무조건 잘린다(대상 45건 초과 시 확정).
#   게다가 인증서 읽기가 순차 15초 타임아웃 + 예산 미적용이라 전체가 260초를 넘었다.
# 이 값들은 API 서버로 가는 I/O 바운드 HTTP 요청이라 동시성을 올려도 CPU 부담이 없고,
# apiserver 입장에서 16 동시 요청은 부담이 아니다.
#   100건 × 3초 ÷ 16 ≈ 19초, 인증서 20건 × 6초 ÷ 16 ≈ 8초  →  합 30초 미만.
_DEFAULT_BUDGET_S = 60.0     # 전체(프로브+인증서) 상한. 위 계산 대비 2배 이상 여유
_DEFAULT_WORKERS = 16
_DEFAULT_TARGET_CAP = 100
_PROBE_TIMEOUT_S = 3.0       # apiserver 경유로 3초를 못 넘기면 사실상 도달 불가 = 판정 동일
_CERT_TIMEOUT_S = 6.0
_LIST_TIMEOUT_S = 15.0
_SLOW_MS = 3000.0

# ⚠ 타임아웃을 실제로 지키게 하는 두 조건 (v1.2.123 — 실측으로 확정)
#
# 응답 없는 대상 1건을 블랙홀 IP 로 재현해 잰 값:
#     _request_timeout=3.0 (float)              →  84.2초   ← 3초가 전혀 안 지켜진다
#     retries=0 + 3.0 (float)                   →  21.0초
#     _request_timeout=(3,3) (튜플)             →  12.0초
#     retries=0 + (3,3)                         →   3.0초   ← 이 조합만 정확하다
#
# ① float 을 주면 k8s 클라이언트가 urllib3.Timeout(total=N) 으로 바꾸는데, 이건 소켓
#    단계별 상한이 아니라서 연결 재시도가 겹치면 몇 배로 늘어난다. (connect, read)
#    튜플로 줘야 단계별로 하드 캡이 걸린다.
# ② kubernetes Configuration.retries 기본값이 None 이라 urllib3 이 Retry(3) = 총 4회
#    시도를 한다. 타임아웃이 그대로 4배가 된다.
#
# retries 는 Configuration 속성이라 공유 클라이언트(k8s.core)를 바꾸면 Polaris 의 다른
# 모든 API 호출이 영향받는다(재시도가 필요한 곳이 많다). 그래서 프로브 전용 ApiClient 를
# 따로 만든다 — Configuration.__deepcopy__ 가 정의돼 있어 인증·TLS 설정은 그대로 승계된다.
_PROBE_TIMEOUT = (_PROBE_TIMEOUT_S, _PROBE_TIMEOUT_S)   # (connect, read)
_CERT_TIMEOUT = (_CERT_TIMEOUT_S, _CERT_TIMEOUT_S)


def _is_system_ns(ns: str) -> bool:
    ns = (ns or '').strip()
    if ns in _SYS_NS:
        return True
    return any(fnmatch.fnmatch(ns, g) for g in _SYS_NS_GLOB)


def _port_hint(port: dict) -> str:
    """포트의 성격 힌트 문자열 (name + appProtocol 소문자)."""
    return f"{port.get('name') or ''} {port.get('app_protocol') or ''}".strip().lower()


def _is_grpc(port: dict) -> bool:
    return 'grpc' in _port_hint(port)


def _is_http(port: dict) -> bool:
    """HTTP 로 프로브해도 되는 포트인가. 이름이 있으면 이름을 믿고, 없으면 번호로 추정."""
    hint = _port_hint(port)
    if hint:
        for tok in hint.split():
            if tok in _HTTP_NAMES:
                return True
        # 이름이 붙어 있는데 HTTP 계열이 아니면 번호 추정을 하지 않는다
        # (postgres:5432 같은 걸 5432 아니라서 통과시키는 실수 방지)
        if any(tok and tok not in _HTTP_NAMES for tok in hint.split()):
            return False
    try:
        return int(port.get('port')) in _HTTP_NUMS
    except (TypeError, ValueError):
        return False


def _is_tls(port: dict) -> bool:
    hint = _port_hint(port)
    if any(tok in _TLS_NAMES for tok in hint.split()):
        return True
    try:
        return int(port.get('port')) in _TLS_NUMS
    except (TypeError, ValueError):
        return False


# ═════════════════════════════════════════════════════════════════════════════
# 1단계 — 입력 수집 (I/O). "수집 실패"와 "0건"을 반드시 구분한다.
# ═════════════════════════════════════════════════════════════════════════════

def netscan_collect_inputs(k8s, log_fn=None) -> dict:
    """스캔 판정에 필요한 목록을 읽는다.

    reports._report_collect 에 끼워넣지 않는 이유: 그 함수는 take_snapshot 과
    비옵트인 health_scan 이 공유하므로, 여기에 손대면 스냅샷 크기와 diff 가 변한다.
    netscan 은 자기 입력을 자기가 읽어 완전히 격리된다.

    각 항목에 *_ok 센티널을 둔다 — 조회가 실패했을 때 빈 리스트를 "0건"으로 오해하면
    모든 Service 를 장애로 신고하게 된다.
    """
    log = log_fn or (lambda *_a, **_k: None)
    out = {
        'services': [], 'services_ok': False,
        'endpoints': {}, 'endpoints_ok': False,
        'ingresses': [], 'ingresses_ok': False,
        'mesh_namespaces': [], 'mesh_ok': False,
    }
    core = getattr(k8s, 'core', None)
    net = getattr(k8s, 'net', None)
    if core is None:
        return out

    # 서비스 — selector / ports / type / clusterIP 가 판정에 필요하다.
    # (기존 k8s.get_services() 는 selector 를 반환하지 않고 ports 를 문자열로 합쳐서 준다)
    try:
        for s in core.list_service_for_all_namespaces(_request_timeout=_LIST_TIMEOUT_S).items:
            spec = s.spec
            out['services'].append({
                'namespace': s.metadata.namespace,
                'name': s.metadata.name,
                'type': spec.type or 'ClusterIP',
                'cluster_ip': spec.cluster_ip or '',
                'selector': dict(spec.selector) if spec.selector else None,
                'ports': [{
                    'name': p.name or '',
                    'port': p.port,
                    'protocol': p.protocol or 'TCP',
                    'app_protocol': getattr(p, 'app_protocol', None) or '',
                } for p in (spec.ports or [])],
            })
        out['services_ok'] = True
        log(f"  netscan: 서비스 {len(out['services'])}건")
    except Exception as e:
        log(f'  [경고] netscan 서비스 조회 실패: {type(e).__name__}: {e}')

    # 엔드포인트 — ready 주소만 센다. notReady 는 증거로만 쓴다.
    try:
        for ep in core.list_endpoints_for_all_namespaces(_request_timeout=_LIST_TIMEOUT_S).items:
            ready = not_ready = 0
            for sub in (ep.subsets or []):
                ready += len(sub.addresses or [])
                not_ready += len(sub.not_ready_addresses or [])
            key = f'{ep.metadata.namespace}/{ep.metadata.name}'
            out['endpoints'][key] = {'ready': ready, 'not_ready': not_ready}
        out['endpoints_ok'] = True
        log(f"  netscan: endpoints {len(out['endpoints'])}건")
    except Exception as e:
        log(f'  [경고] netscan endpoints 조회 실패: {type(e).__name__}: {e}')

    # 인그레스 — 백엔드 참조와 TLS Secret 참조를 뽑는다.
    if net is not None:
        try:
            for ing in net.list_ingress_for_all_namespaces(_request_timeout=_LIST_TIMEOUT_S).items:
                spec = ing.spec
                backends, hosts = [], []
                for rule in (spec.rules or []):
                    if rule.host:
                        hosts.append(rule.host)
                    http = getattr(rule, 'http', None)
                    for path in (getattr(http, 'paths', None) or []):
                        svc = getattr(getattr(path, 'backend', None), 'service', None)
                        if svc is None:
                            continue      # resource 백엔드 (Service 아님) — 검사 대상 아님
                        port = getattr(svc, 'port', None)
                        backends.append({
                            'service': svc.name,
                            'port_number': getattr(port, 'number', None),
                            'port_name': getattr(port, 'name', None) or '',
                            'path': path.path or '/',
                        })
                default_svc = getattr(getattr(spec, 'default_backend', None), 'service', None)
                out['ingresses'].append({
                    'namespace': ing.metadata.namespace,
                    'name': ing.metadata.name,
                    'hosts': hosts,
                    'backends': backends,
                    'default_backend': ({'service': default_svc.name}
                                        if default_svc is not None else None),
                    'tls': [{'secret_name': t.secret_name or '',
                             'hosts': list(t.hosts or [])} for t in (spec.tls or [])],
                })
            out['ingresses_ok'] = True
            log(f"  netscan: 인그레스 {len(out['ingresses'])}건")
        except Exception as e:
            log(f'  [경고] netscan 인그레스 조회 실패: {type(e).__name__}: {e}')

    # 서비스 메시 주입 네임스페이스 — 네임스페이스 라벨로 판별한다.
    # mTLS STRICT 인 곳에 평문으로 붙으면 사이드카가 RST 를 돌려주므로, 걸러내지 않으면
    # 메시가 깔린 클러스터 전체가 오탐이 된다. (파드 단위 주석 오버라이드는 감지 못 함)
    try:
        mesh = []
        for ns in core.list_namespace(_request_timeout=_LIST_TIMEOUT_S).items:
            labels = ns.metadata.labels or {}
            if (labels.get('istio-injection') == 'enabled'
                    or 'istio.io/rev' in labels
                    or labels.get('linkerd.io/inject') == 'enabled'):
                mesh.append(ns.metadata.name)
        out['mesh_namespaces'] = mesh
        out['mesh_ok'] = True
        if mesh:
            log(f'  netscan: 메시 주입 네임스페이스 {len(mesh)}건 — 제외 대상')
    except Exception as e:
        log(f'  [경고] netscan 네임스페이스 조회 실패: {type(e).__name__}: {e}')

    return out


# ═════════════════════════════════════════════════════════════════════════════
# 2단계 — 대상/제외 결정 (순수 함수). 오탐 방지가 전부 여기에 모여 있다.
# ═════════════════════════════════════════════════════════════════════════════

def netscan_plan(inputs: dict, *, target_cap: int = _DEFAULT_TARGET_CAP) -> dict:
    """수집된 목록만 보고 프로브 대상과 제외 대상을 가른다.

    반환: {'targets': [...], 'skipped': [{namespace,name,port,reason}], 'truncated': bool,
           'static': {...}}   — static 은 프로브 없이 판정할 정적 검사 입력
    """
    inputs = inputs or {}
    services = inputs.get('services') or []
    endpoints = inputs.get('endpoints') or {}
    mesh_ns = set(inputs.get('mesh_namespaces') or [])
    targets, skipped = [], []

    def skip(ns, name, reason, port=None):
        skipped.append({'namespace': ns, 'name': name,
                        'port': port, 'reason': reason})

    for svc in services:
        ns, name = svc.get('namespace') or '', svc.get('name') or ''
        if _is_system_ns(ns):
            skip(ns, name, SKIP_SYSTEM_NS)
            continue
        if (svc.get('type') or '') == 'ExternalName':
            skip(ns, name, SKIP_EXTERNALNAME)
            continue
        ports = svc.get('ports') or []
        if not ports:
            skip(ns, name, SKIP_NO_PORTS)
            continue
        if ns in mesh_ns:
            skip(ns, name, SKIP_MESH)
            continue
        if (svc.get('cluster_ip') or '').lower() == 'none':
            # headless — 정적 검사는 유효하지만 peer 포트를 찔러보는 건 의미가 없다
            skip(ns, name, SKIP_HEADLESS)
            continue
        if not svc.get('selector'):
            # selector 가 없으면 endpoints 를 컨트롤러/사람이 직접 쓴 것이라 우리가
            # 추론할 파드가 없다 → 실패해도 조치할 대상이 없다.
            #
            # 대표 사례가 default/kubernetes(apiserver 자신의 Service)다. 이걸 apiserver
            # Service proxy 로 찌르면 "apiserver 에게 자기 자신으로 프록시해달라"가 되는데,
            # 프록시는 호출자 크리덴셜을 백엔드로 넘기지 않고 백엔드(=apiserver)는 인증을
            # 요구하므로 **건강한 클러스터에서도 절대 200 이 안 나온다**(실측 503).
            # v1.2.124 까지는 이게 '높음'으로 올라가 보고서 8.1 「긴급」을 오염시켰다.
            # apiserver 자체의 건강은 /readyz 로 따로 본다(reports._report_fetch_readyz).
            skip(ns, name, SKIP_NO_SELECTOR)
            continue
        ep = endpoints.get(f'{ns}/{name}') or {}
        if not ep.get('ready'):
            # 도달성 프로브를 해봐야 무조건 실패한다. 정적 규칙이 이미 잡는 사안이라
            # 프로브로 중복 신고하지 않는다.
            skip(ns, name, SKIP_NO_ENDPOINT)
            continue
        for p in ports:
            if (p.get('protocol') or 'TCP').upper() != 'TCP':
                skip(ns, name, SKIP_NON_HTTP, p.get('port'))
                continue
            if _is_grpc(p):
                skip(ns, name, SKIP_GRPC, p.get('port'))
                continue
            if not _is_http(p):
                skip(ns, name, SKIP_NON_HTTP, p.get('port'))
                continue
            targets.append({
                'namespace': ns, 'name': name, 'port': p.get('port'),
                'port_name': p.get('name') or '',
                'scheme': 'https' if _is_tls(p) else 'http',
            })

    truncated = len(targets) > target_cap
    if truncated:
        for t in targets[target_cap:]:
            skip(t['namespace'], t['name'], SKIP_CAP, t['port'])
        targets = targets[:target_cap]

    return {
        'targets': targets,
        'skipped': skipped,
        'truncated': truncated,
        'total_candidates': len(targets) + sum(1 for s in skipped if s['reason'] == SKIP_CAP),
        'static': {
            'services': services,
            'services_ok': bool(inputs.get('services_ok')),
            'endpoints': endpoints,
            'endpoints_ok': bool(inputs.get('endpoints_ok')),
            'ingresses': inputs.get('ingresses') or [],
            'ingresses_ok': bool(inputs.get('ingresses_ok')),
            'mesh_namespaces': sorted(mesh_ns),
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3단계 — 실행 (I/O)
# ═════════════════════════════════════════════════════════════════════════════

def _parse_cert(der: bytes) -> dict:
    """인증서 → 메타데이터. SAN 까지 뽑는다.

    원본 바이트는 반환하지 않는다 — 결과가 스냅샷/보고서에 실릴 수 있으므로 즉시
    메타데이터로 환원한다.
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        c = x509.load_der_x509_certificate(der, default_backend())
        not_after = getattr(c, 'not_valid_after_utc', None) or c.not_valid_after
        now = datetime.now(timezone.utc) if not_after.tzinfo else datetime.utcnow()
        try:
            san = [n.value for n in
                   c.extensions.get_extension_for_class(
                       x509.SubjectAlternativeName).value]
        except Exception:
            san = []
        return {
            'subject': c.subject.rfc4514_string(),
            'issuer': c.issuer.rfc4514_string(),
            'not_after': not_after.isoformat(),
            'days_left': (not_after - now).days,
            'san': [str(s) for s in san],
        }
    except Exception as e:
        return {'error': f'{type(e).__name__}: {e}'}


def _san_matches(host: str, san: list) -> bool:
    """와일드카드 SAN 포함 매칭 (*.example.com 은 a.example.com 에만 매칭)."""
    host = (host or '').lower().strip()
    if not host:
        return True
    for entry in san or []:
        e = str(entry).lower().strip()
        if e == host:
            return True
        if e.startswith('*.') and '.' in host:
            if host.split('.', 1)[1] == e[2:]:
                return True
    return False


_RBAC_HINT = re.compile(r'services/proxy|is forbidden', re.I)
# 리다이렉트 때문에 난 예외는 '연결 실패'가 아니다 — 서비스가 응답을 준 것이다.
_REDIRECT_HINT = re.compile(r'too many redirects|exceeded.*redirect', re.I)


def _no_retry_client(k8s):
    """프로브 전용 CoreV1Api — retries=0. 실패 시 공유 클라이언트로 폴백.

    공유 k8s.core 의 retries 를 건드리면 Polaris 의 다른 모든 API 호출이 재시도를
    잃는다. Configuration.__deepcopy__ 가 정의돼 있어 인증·TLS 는 그대로 승계된다.
    반환: (api, closer) — closer 는 다 쓴 뒤 호출(공유 클라이언트면 no-op).
    """
    core = getattr(k8s, 'core', None)
    if core is None:
        return None, (lambda: None)
    try:
        import copy
        import kubernetes.client as _kc
        import urllib3
        cfg = copy.deepcopy(core.api_client.configuration)
        # ⚠ retries=0 (정수) 를 주면 안 된다 — urllib3 이 Retry(total=0) 으로 해석하고
        #   **리다이렉트도 total 에 카운트**해서, 리다이렉트 1회만으로
        #   MaxRetryError('too many redirects') 를 던진다. 그 예외에는 .status 가 없어
        #   우리 코드가 '연결 실패'(high)로 신고했다 — Prometheus(/→/graph)·
        #   Vault UI(/→/ui/) 처럼 **정상 서비스가 전부 오탐**됐다 (v1.2.123 사고).
        #   redirect=False 로 두면 3xx 를 응답으로 그대로 받는다(실측: status=302).
        cfg.retries = urllib3.Retry(total=0, redirect=False, connect=0, read=False)
        client = _kc.ApiClient(cfg)
        return _kc.CoreV1Api(client), client.close
    except Exception:
        # 클라이언트 버전 차이 등으로 실패하면 공유 클라이언트를 쓴다
        # (느려질 수 있지만 예산이 막아준다)
        return core, (lambda: None)


def _probe_service(api, target: dict, timeout=_PROBE_TIMEOUT) -> dict:
    """API 서버 Service proxy 로 루트 경로 1회 요청. 반환은 순수 데이터.

    timeout 은 반드시 (connect, read) 튜플이어야 한다 — float 을 주면
    urllib3.Timeout(total=N) 이 되어 실제로는 몇 배로 늘어난다(위 상수 주석 참고).
    """
    ns, name, port = target['namespace'], target['name'], target['port']
    ref = f"{target.get('scheme') or 'http'}:{name}:{port}"
    t0 = time.monotonic()
    try:
        api.connect_get_namespaced_service_proxy(
            name=ref, namespace=ns, _request_timeout=timeout)
        return {**target, 'status': 200, 'ok': True,
                'latency_ms': round((time.monotonic() - t0) * 1000, 1)}
    except Exception as e:
        ms = round((time.monotonic() - t0) * 1000, 1)
        status = getattr(e, 'status', None)
        body = str(getattr(e, 'body', '') or '')
        if status in (401, 403) and _RBAC_HINT.search(body):
            # 애플리케이션의 401/403 이 아니라 kubeconfig 권한 부족.
            # 이걸 구분하지 않으면 대상 수만큼 허위 장애가 찍힌다.
            return {**target, 'status': status, 'ok': False,
                    'rbac_denied': True, 'latency_ms': ms}
        if status:
            # 2xx·3xx 는 서비스가 HTTP 응답을 만들어냈다는 뜻 = 확실히 살아 있다.
            # 리다이렉트(302 등)를 실패로 세면 Prometheus·Vault UI 가 전부 오탐이 된다.
            return {**target, 'status': int(status), 'ok': 200 <= int(status) < 400,
                    'latency_ms': ms}
        if _REDIRECT_HINT.search(str(e)):
            # 폴백(공유 클라이언트, redirect 따라감) 경로에서 리다이렉트 한도를 넘긴 경우.
            # 응답을 준 것이므로 도달 가능으로 본다 — 연결 실패가 아니다.
            return {**target, 'status': None, 'ok': True, 'redirected': True,
                    'latency_ms': ms}
        return {**target, 'status': None, 'ok': False,
                'error': f'{type(e).__name__}: {e}', 'latency_ms': ms}


def netscan_run(k8s, plan: dict, log_fn=None, *,
                budget_s: float = _DEFAULT_BUDGET_S,
                max_workers: int = _DEFAULT_WORKERS,
                cancel=None, probe=None, cert_reader=None) -> dict:
    """plan 을 실행한다. 반환값이 그대로 data['netscan'] 이 된다.

    probe / cert_reader 는 테스트 주입점이다 (None 이면 실제 API 호출).
    """
    log = log_fn or (lambda *_a, **_k: None)
    plan = plan or {}
    targets = plan.get('targets') or []
    static = plan.get('static') or {}
    result = {
        'ran': True,
        'mechanism': 'apiserver-service-proxy',
        'permission': 'ok',
        'probes': [],
        'certs': [],
        'skipped': plan.get('skipped') or [],
        'truncated': bool(plan.get('truncated')),
        'target_count': len(targets),
        'total_candidates': plan.get('total_candidates') or len(targets),
        'static': static,
        'duration_s': 0.0,
        'budget_exceeded': False,
    }
    # 프로브 전용 클라이언트(retries=0). probe 가 주입되면 만들지 않는다(테스트).
    _probe_api, _close_probe_api = (None, (lambda: None)) if probe else _no_retry_client(k8s)
    _probe = probe or (lambda t: _probe_service(_probe_api, t))
    workers = max(1, int(max_workers))
    t_start = time.monotonic()

    def _elapsed():
        return time.monotonic() - t_start

    def _out_of_budget():
        return _elapsed() > budget_s

    def _stop():
        """중단 조건 — 예산 초과 또는 취소. 프로브와 인증서 양쪽에서 함께 본다.

        예산을 넘긴 시점에 플래그를 남긴다 — 단계를 통째로 건너뛴 경우에도
        '초과 아님'으로 보고되면 미점검을 정상으로 오해하게 된다.
        """
        if _out_of_budget():
            result['budget_exceeded'] = True
            return True
        return cancel is not None and cancel.is_set()

    def _drain(ex, futs, kind, on_result):
        """완료 순서로 결과를 모으며 중단 조건을 감시한다.

        중단 시 shutdown(wait=False, cancel_futures=True) 로 **대기 없이** 빠져나온다.
        `with ThreadPoolExecutor` 를 쓰면 __exit__ 가 wait=True 로 실행 중인 작업을
        끝까지 기다려서, 예산을 넘긴 뒤에도 추가로 시간을 더 쓰게 된다.
        """
        done = 0
        total = len(futs)
        step = max(1, total // 4)         # 25% 단위 진행 로그 (침묵 구간 제거)
        try:
            # as_completed 에 timeout 을 준다 = 하드 월클럭 상한.
            # 완료 후 검사만 하면, 응답 없는 대상 하나가 예산을 통째로 넘겨버린다
            # (v1.2.122 에서 실제로 84초짜리 요청 하나가 131초를 만들었다).
            remaining = max(0.1, budget_s - _elapsed())
            for fut in as_completed(futs, timeout=remaining):
                try:
                    r = fut.result()
                except Exception as e:
                    r = {**futs[fut], 'status': None, 'ok': False,
                         'error': f'{type(e).__name__}: {e}'}
                done += 1
                if on_result(r) is False:      # on_result 가 중단을 요청
                    return done, total
                if done % step == 0 and done < total:
                    log(f'  netscan: {kind} {done}/{total} ({_elapsed():.0f}초)')
                if _stop():
                    log(f'  netscan: 시간 예산({budget_s:.0f}초) 초과 — {kind} '
                        f'{done}/{total} 까지만 점검')
                    return done, total
        except FuturesTimeout:
            result['budget_exceeded'] = True
            log(f'  netscan: 시간 예산({budget_s:.0f}초) 초과 — {kind} '
                f'{done}/{total} 까지만 점검 (응답 없는 대상 대기 중단)')
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
        return done, total

    # ── 도달성 프로브 ────────────────────────────────────────────────────────
    if targets and not _stop():
        log(f'  netscan: 도달성 점검 {len(targets)}건 (동시 {workers}, '
            f'건당 최대 {_PROBE_TIMEOUT_S:.0f}초)')

        def _on_probe(r):
            result['probes'].append(r)
            if r.get('rbac_denied'):
                # 첫 권한 거부에서 전면 중단 — 같은 이유로 N 건이 실패하는 걸 막는다
                result['permission'] = 'denied'
                log('  [경고] netscan: services/proxy 권한이 없어 도달성 점검을 중단합니다')
                return False
            return True

        ex = ThreadPoolExecutor(max_workers=workers)
        _drain(ex, {ex.submit(_probe, t): t for t in targets}, '도달성', _on_probe)
        if result['permission'] == 'denied':
            result['probes'] = [p for p in result['probes'] if not p.get('rbac_denied')]

    # ── TLS 인증서 (Ingress 가 참조하는 Secret 의 tls.crt 만 읽는다) ──────────
    # 같은 Secret 을 여러 Ingress 가 참조하면 1회만 읽는다.
    refs, seen = [], set()
    for ing in (static.get('ingresses') or []):
        if _is_system_ns(ing.get('namespace')):
            continue
        for t in (ing.get('tls') or []):
            nm = t.get('secret_name')
            key = (ing['namespace'], nm)
            if not nm or key in seen:
                continue
            seen.add(key)
            refs.append({'namespace': ing['namespace'], 'secret': nm,
                         'ingress': ing.get('name') or '',
                         'hosts': t.get('hosts') or ing.get('hosts') or []})

    _read = cert_reader or (lambda ns, nm: _read_tls_crt(k8s, ns, nm))

    def _one_cert(ref):
        der = _read(ref['namespace'], ref['secret'])
        if not der:
            return {**ref, 'error': 'tls.crt 없음'}
        info = _parse_cert(der)
        return {**ref, **info,
                'san_ok': _san_matches((ref['hosts'] or [''])[0], info.get('san') or [])}

    if refs and not _stop():
        # v1.2.121 에서는 이 루프가 순차 + 예산 미적용이라 전체 시간을 260초까지 밀어올렸다.
        log(f'  netscan: TLS 인증서 {len(refs)}건 확인 (동시 {workers})')
        ex = ThreadPoolExecutor(max_workers=workers)
        _drain(ex, {ex.submit(_one_cert, r): r for r in refs}, 'TLS',
               lambda r: result['certs'].append(r) or True)
    elif refs:
        log(f'  netscan: 예산 초과로 TLS 인증서 {len(refs)}건 미점검')

    # 미점검 인증서 수 — 0건으로 보이면 "인증서가 없다"로 오해한다
    result['certs_total'] = len(refs)
    result['certs_skipped'] = max(0, len(refs) - len(result['certs']))
    _close_probe_api()
    result['duration_s'] = round(_elapsed(), 1)
    log(f"  netscan: 완료 — 도달성 {len(result['probes'])}건 · "
        f"TLS {len(result['certs'])}건 · {result['duration_s']}초")
    return result


def _read_tls_crt(k8s, namespace: str, secret: str) -> bytes:
    """Secret 에서 tls.crt 만 읽어 DER 로 돌려준다. tls.key 는 읽지 않는다."""
    sec = k8s.core.read_namespaced_secret(name=secret, namespace=namespace,
                                          _request_timeout=_CERT_TIMEOUT)
    blob = (sec.data or {}).get('tls.crt')
    if not blob:
        return b''
    pem = base64.b64decode(blob)
    # PEM 체인의 첫 인증서(리프)만 DER 로 변환
    marker = b'-----BEGIN CERTIFICATE-----'
    if marker in pem:
        first = pem.split(marker, 1)[1].split(b'-----END CERTIFICATE-----', 1)[0]
        return base64.b64decode(re.sub(rb'\s+', b'', first))
    return pem


# ═════════════════════════════════════════════════════════════════════════════
# 4단계 — 규칙 판정 (순수 함수). reports._report_evaluate 가 이걸 호출한다.
# ═════════════════════════════════════════════════════════════════════════════

def netscan_findings(netscan: dict, finding_fn=None) -> list:
    """netscan 결과 → _report_finding 스키마 리스트.

    netscan 이 None/빈 값이면 빈 리스트 — 스냅샷과 비옵트인 스캔은 여기 오지 않는다.
    카테고리는 모두 network_ 접두 (reports.AREA_MAP 의 'network' 항목에 매칭돼
    9장 예상 개선작업에서 담당 영역이 자동 분류된다).

    finding_fn 은 reports._report_finding 을 주입받는다 — 이 모듈이 reports 를 import
    하지 않게 해서 순환 참조를 없앤다. 생략하면 지연 import 로 가져온다(단독 테스트용).
    """
    if not netscan or not netscan.get('ran'):
        return []
    if finding_fn is None:
        from src.reports import _report_finding as finding_fn   # noqa: PLW2901
    F = finding_fn

    out = []
    static = netscan.get('static') or {}

    # ① 권한 부족 — 대상 수만큼 실패를 찍는 대신 안내 1건
    if netscan.get('permission') == 'denied':
        out.append(F(
            'network_scan', 'info', 'cluster', 'services/proxy',
            '권한 없음',
            '이 kubeconfig 에 services/proxy 조회 권한이 없어 도달성 점검을 건너뜀',
            'edit 이상 권한의 kubeconfig 를 쓰거나 도달성 점검 없이 정적 검사만 활용하세요',
        ))

    # ② Service 에 ready endpoint 가 없다 (정적)
    if static.get('services_ok') and static.get('endpoints_ok'):
        eps = static.get('endpoints') or {}
        for svc in (static.get('services') or []):
            ns, name = svc.get('namespace') or '', svc.get('name') or ''
            if _is_system_ns(ns) or (svc.get('type') or '') == 'ExternalName':
                continue
            if not svc.get('selector'):
                continue          # 수동 endpoints (kubernetes.default 등) — 정상
            if not (svc.get('ports') or []):
                continue
            ep = eps.get(f'{ns}/{name}') or {}
            ready, not_ready = ep.get('ready') or 0, ep.get('not_ready') or 0
            if ready:
                continue
            if not_ready:
                out.append(F(
                    'network_endpoints', 'medium', ns, name,
                    f'ready 0 / notReady {not_ready}',
                    'selector 에 맞는 파드가 있으나 Ready 가 아니어서 트래픽을 받지 못합니다 '
                    '(롤링 업데이트 중이면 일시적)',
                    'readinessProbe 와 파드 로그를 확인하세요',
                ))
            else:
                out.append(F(
                    'network_endpoints', 'high', ns, name,
                    'endpoint 0',
                    'selector 에 맞는 파드가 없어 이 서비스로 온 트래픽이 갈 곳이 없습니다',
                    'selector 라벨 오타, 워크로드 미배포, 또는 스케일 0 여부를 확인하세요',
                ))

    # ③ Ingress 백엔드 정합성 (정적)
    if static.get('ingresses_ok') and static.get('services_ok'):
        svc_index = {}
        for s in (static.get('services') or []):
            key = f"{s.get('namespace')}/{s.get('name')}"
            svc_index[key] = s
        eps = static.get('endpoints') or {}
        ep_ok = bool(static.get('endpoints_ok'))
        for ing in (static.get('ingresses') or []):
            ns, iname = ing.get('namespace') or '', ing.get('name') or ''
            if _is_system_ns(ns):
                continue
            backends = list(ing.get('backends') or [])
            if ing.get('default_backend'):
                backends.append({**ing['default_backend'], 'path': '(default)'})
            for b in backends:
                sname = b.get('service') or ''
                svc = svc_index.get(f'{ns}/{sname}')
                if svc is None:
                    out.append(F(
                        'network_ingress', 'high', ns, f'{iname} → {sname}',
                        '백엔드 서비스 없음',
                        f"Ingress 가 참조하는 Service '{sname}' 가 이 네임스페이스에 없습니다",
                        'Service 이름 오타이거나 삭제된 서비스입니다 — Ingress 를 수정하세요',
                    ))
                    continue
                pname = b.get('port_name') or ''
                if pname:
                    names = {(p.get('name') or '') for p in (svc.get('ports') or [])}
                    if pname not in names:
                        out.append(F(
                            'network_ingress', 'high', ns, f'{iname} → {sname}',
                            f"포트 이름 '{pname}' 불일치",
                            f"Service 가 노출하는 포트 이름은 {sorted(n for n in names if n)} 입니다",
                            'Ingress 의 backend.service.port.name 을 실제 포트 이름과 맞추세요',
                        ))
                        continue
                if ep_ok and not ((eps.get(f'{ns}/{sname}') or {}).get('ready')):
                    out.append(F(
                        'network_ingress', 'medium', ns, f'{iname} → {sname}',
                        '백엔드 endpoint 0',
                        '백엔드 서비스는 있으나 받을 파드가 없어 502/503 이 납니다',
                        '백엔드 워크로드 상태를 확인하세요',
                    ))

    # ④ TLS 인증서 만료 / SAN
    for c in (netscan.get('certs') or []):
        ns = c.get('namespace') or 'cluster'
        who = f"{c.get('ingress') or ''} ({c.get('secret') or ''})".strip()
        if c.get('error'):
            out.append(F(
                'network_tls', 'medium', ns, who,
                '인증서 확인 실패', str(c['error']),
                'Secret 이 존재하고 tls.crt 가 올바른 PEM 인지 확인하세요',
            ))
            continue
        days = c.get('days_left')
        if isinstance(days, int):
            if days < 0:
                sev, det = 'critical', f'인증서가 {abs(days)}일 전에 만료되었습니다'
            elif days < 14:
                sev, det = 'critical', f'{days}일 후 만료 — 즉시 갱신이 필요합니다'
            elif days < 30:
                sev, det = 'high', f'{days}일 후 만료'
            elif days < 60:
                sev, det = 'medium', f'{days}일 후 만료'
            else:
                sev = det = ''
            if sev:
                out.append(F(
                    'network_tls', sev, ns, who, f'D-{days}', det,
                    'cert-manager 자동 갱신 상태를 확인하거나 인증서를 교체하세요',
                ))
        if c.get('san_ok') is False:
            host = (c.get('hosts') or [''])[0]
            out.append(F(
                'network_tls', 'medium', ns, who,
                'SAN 불일치',
                f"인증서 SAN 에 Ingress 호스트 '{host}' 가 없습니다 "
                f"(SAN: {', '.join((c.get('san') or [])[:4]) or '없음'})",
                '해당 호스트를 포함한 인증서로 교체하세요 (의도된 구성이면 무시)',
            ))

    # ⑤ 도달성 프로브 결과 — 5xx 와 연결 실패만 신고한다
    for p in (netscan.get('probes') or []):
        ns, name = p.get('namespace') or '', p.get('name') or ''
        who = f"{name}:{p.get('port')}"
        st = p.get('status')
        if p.get('ok'):
            ms = p.get('latency_ms') or 0
            if ms > _SLOW_MS:
                out.append(F(
                    'network_reach', 'medium', ns, who,
                    f'{ms:.0f}ms',
                    f'응답이 {_SLOW_MS/1000:.0f}초를 넘습니다 (API 서버 경유 시간 포함)',
                    '애플리케이션 응답 시간과 리소스 여유를 확인하세요',
                ))
            continue
        if st is None:
            out.append(F(
                'network_reach', 'high', ns, who,
                '연결 실패',
                f"API 서버 Service proxy 로 연결되지 않았습니다: {p.get('error') or '원인 불명'}",
                '파드가 해당 포트를 실제로 listen 하는지, targetPort 가 맞는지 확인하세요',
            ))
        elif int(st) not in _BENIGN_STATUS and 500 <= int(st) <= 599:
            out.append(F(
                'network_reach', 'high', ns, who,
                f'HTTP {st}',
                '서비스가 서버 오류를 반환했습니다',
                '애플리케이션 로그를 확인하세요',
            ))
        # 그 외(_BENIGN_STATUS · 3xx · 그 밖의 4xx)는 정상 취급 — 신고하지 않는다
    return out
