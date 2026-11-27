# -*- coding: utf-8 -*-
"""네트워크 스캐닝 (v1.2.121) — 오탐 방지 규칙과 회귀 가드.

클러스터가 필요 없다. netscan_plan/netscan_findings 는 순수 함수이고,
netscan_run 은 probe/cert_reader 주입점으로 테스트한다.

가장 중요한 테스트는 TestNoNetscanRegression — 옵트인하지 않으면 network_* 발견사항이
한 건도 안 나오고 기존 건수가 그대로여야 한다. take_snapshot 과 비옵트인 health_scan 이
영향받지 않음을 이 테스트가 증명한다.
"""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.netscan import (          # noqa: E402
    netscan_plan, netscan_findings, netscan_run,
    _is_http, _is_grpc, _is_tls, _is_system_ns, _san_matches,
    SKIP_SYSTEM_NS, SKIP_EXTERNALNAME, SKIP_NO_PORTS, SKIP_HEADLESS,
    SKIP_GRPC, SKIP_NON_HTTP, SKIP_MESH, SKIP_NO_ENDPOINT, SKIP_CAP,
    SKIP_NO_SELECTOR,
)
from src.reports import _report_evaluate, _report_finding   # noqa: E402


def svc(ns='app', name='web', type_='ClusterIP', cluster_ip='10.0.0.1',
        selector=None, ports=None):
    return {
        'namespace': ns, 'name': name, 'type': type_, 'cluster_ip': cluster_ip,
        'selector': {'app': name} if selector is None else selector,
        'ports': [{'name': 'http', 'port': 80, 'protocol': 'TCP', 'app_protocol': ''}]
                 if ports is None else ports,
    }


def inputs(services, endpoints=None, ingresses=None, mesh=None, **ok):
    base = {
        'services': services, 'services_ok': True,
        'endpoints': {f"{s['namespace']}/{s['name']}": {'ready': 1, 'not_ready': 0}
                      for s in services} if endpoints is None else endpoints,
        'endpoints_ok': True,
        'ingresses': ingresses or [], 'ingresses_ok': True,
        'mesh_namespaces': mesh or [], 'mesh_ok': True,
    }
    base.update(ok)
    return base


def reasons(plan, name):
    return {s['reason'] for s in plan['skipped'] if s['name'] == name}


# ═════════════════════════════════════════════════════════════════════════════
class TestPortClassification(unittest.TestCase):
    """포트 성격 판별 — 여기가 틀리면 postgres 를 HTTP 로 찔러 오탐이 난다."""

    def test_named_http_ports(self):
        for nm in ('http', 'https', 'http2', 'web', 'api', 'ui', 'metrics'):
            self.assertTrue(_is_http({'name': nm, 'port': 12345}), nm)

    def test_named_non_http_port_is_not_probed_even_on_http_number(self):
        # 이름이 붙어 있으면 이름을 믿는다 — 8080 이라도 'postgres' 면 HTTP 아님
        self.assertFalse(_is_http({'name': 'postgres', 'port': 8080}))
        self.assertFalse(_is_http({'name': 'redis', 'port': 80}))

    def test_unnamed_port_falls_back_to_number(self):
        self.assertTrue(_is_http({'name': '', 'port': 8080}))
        self.assertTrue(_is_http({'name': '', 'port': 443}))
        self.assertFalse(_is_http({'name': '', 'port': 5432}))
        self.assertFalse(_is_http({'name': '', 'port': 6379}))

    def test_grpc_detected_by_name_or_app_protocol(self):
        self.assertTrue(_is_grpc({'name': 'grpc', 'port': 9000}))
        self.assertTrue(_is_grpc({'name': '', 'app_protocol': 'grpc', 'port': 9000}))
        self.assertFalse(_is_grpc({'name': 'http', 'port': 80}))

    def test_tls_scheme_detection(self):
        self.assertTrue(_is_tls({'name': 'https', 'port': 8443}))
        self.assertTrue(_is_tls({'name': '', 'port': 443}))
        self.assertFalse(_is_tls({'name': 'http', 'port': 80}))

    def test_system_namespace_globs(self):
        for ns in ('kube-system', 'kube-public', 'kube-node-lease',
                   'cattle-system', 'calico-system', 'tigera-operator',
                   'fleet-local', 'longhorn-system'):
            self.assertTrue(_is_system_ns(ns), ns)
        # 사용자가 설치한 인프라는 제외하지 않는다 — 점검할 값이 있다
        for ns in ('default', 'app', 'cert-manager', 'ingress-nginx', 'monitoring'):
            self.assertFalse(_is_system_ns(ns), ns)


# ═════════════════════════════════════════════════════════════════════════════
class TestPlanSkips(unittest.TestCase):
    """오탐 방지 — 각 제외 사유가 정확한 이유 문자열로 기록되는지."""

    def test_plain_http_service_becomes_target(self):
        plan = netscan_plan(inputs([svc()]))
        self.assertEqual(len(plan['targets']), 1)
        t = plan['targets'][0]
        self.assertEqual((t['namespace'], t['name'], t['port'], t['scheme']),
                         ('app', 'web', 80, 'http'))

    def test_system_namespace_skipped(self):
        plan = netscan_plan(inputs([svc(ns='kube-system', name='kube-dns')]))
        self.assertEqual(plan['targets'], [])
        self.assertIn(SKIP_SYSTEM_NS, reasons(plan, 'kube-dns'))

    def test_external_name_skipped(self):
        plan = netscan_plan(inputs([svc(name='ext', type_='ExternalName')]))
        self.assertIn(SKIP_EXTERNALNAME, reasons(plan, 'ext'))

    def test_no_ports_skipped(self):
        plan = netscan_plan(inputs([svc(name='noport', ports=[])]))
        self.assertIn(SKIP_NO_PORTS, reasons(plan, 'noport'))

    def test_headless_skipped_from_probing(self):
        plan = netscan_plan(inputs([svc(name='hl', cluster_ip='None')]))
        self.assertIn(SKIP_HEADLESS, reasons(plan, 'hl'))

    def test_mesh_namespace_skipped(self):
        # istio/linkerd mTLS STRICT 에 평문으로 붙으면 사이드카가 RST → 메시 전체 오탐
        plan = netscan_plan(inputs([svc(ns='mesh', name='m')], mesh=['mesh']))
        self.assertIn(SKIP_MESH, reasons(plan, 'm'))

    def test_no_ready_endpoint_skipped_from_probing(self):
        # 정적 규칙이 이미 잡는 사안 — 프로브로 중복 신고하지 않는다
        plan = netscan_plan(inputs(
            [svc(name='dead')], endpoints={'app/dead': {'ready': 0, 'not_ready': 2}}))
        self.assertIn(SKIP_NO_ENDPOINT, reasons(plan, 'dead'))

    def test_grpc_and_non_http_ports_skipped(self):
        s = svc(name='multi', ports=[
            {'name': 'http', 'port': 80, 'protocol': 'TCP', 'app_protocol': ''},
            {'name': 'grpc', 'port': 9000, 'protocol': 'TCP', 'app_protocol': ''},
            {'name': 'postgres', 'port': 5432, 'protocol': 'TCP', 'app_protocol': ''},
            {'name': 'dns', 'port': 53, 'protocol': 'UDP', 'app_protocol': ''},
        ])
        plan = netscan_plan(inputs([s]))
        self.assertEqual([t['port'] for t in plan['targets']], [80])
        self.assertIn(SKIP_GRPC, reasons(plan, 'multi'))
        self.assertIn(SKIP_NON_HTTP, reasons(plan, 'multi'))

    def test_target_cap_truncates_and_reports(self):
        many = [svc(name=f'w{i}') for i in range(10)]
        plan = netscan_plan(inputs(many), target_cap=4)
        self.assertTrue(plan['truncated'])
        self.assertEqual(len(plan['targets']), 4)
        self.assertEqual(plan['total_candidates'], 10)
        self.assertEqual(sum(1 for s in plan['skipped'] if s['reason'] == SKIP_CAP), 6)

    def test_empty_inputs_are_safe(self):
        for bad in (None, {}, {'services': None}):
            plan = netscan_plan(bad)
            self.assertEqual(plan['targets'], [])
            self.assertFalse(plan['truncated'])


# ═════════════════════════════════════════════════════════════════════════════
class TestStaticFindings(unittest.TestCase):
    """정적 규칙 — Endpoints / Ingress 정합성."""

    def _find(self, static, **kw):
        ns = {'ran': True, 'static': static, 'probes': [], 'certs': [], **kw}
        return netscan_findings(ns, _report_finding)

    def test_selector_service_without_endpoints_is_high(self):
        f = self._find(inputs([svc(name='orphan')],
                              endpoints={'app/orphan': {'ready': 0, 'not_ready': 0}}))
        got = [x for x in f if x['category'] == 'network_endpoints']
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]['severity'], 'high')

    def test_not_ready_endpoints_downgraded_to_medium(self):
        # 롤링 업데이트 중이면 일시적일 수 있으므로 high 로 올리지 않는다
        f = self._find(inputs([svc(name='rolling')],
                              endpoints={'app/rolling': {'ready': 0, 'not_ready': 3}}))
        got = [x for x in f if x['category'] == 'network_endpoints']
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]['severity'], 'medium')

    def test_selectorless_service_never_flagged(self):
        # kubernetes.default 처럼 수동 endpoints 를 쓰는 서비스는 정상이다
        f = self._find(inputs([svc(name='manual', selector={})],
                              endpoints={'app/manual': {'ready': 0, 'not_ready': 0}}))
        self.assertEqual([x for x in f if x['category'] == 'network_endpoints'], [])

    def test_external_name_never_flagged(self):
        f = self._find(inputs([svc(name='ext', type_='ExternalName', selector={})],
                              endpoints={}))
        self.assertEqual([x for x in f if x['category'] == 'network_endpoints'], [])

    def test_endpoints_collection_failure_suppresses_all_endpoint_rules(self):
        """수집 실패를 0건으로 오해하면 모든 Service 를 장애로 신고한다 — 그걸 막는 가드."""
        st = inputs([svc(name=f'w{i}') for i in range(5)], endpoints={})
        st['endpoints_ok'] = False
        f = self._find(st)
        self.assertEqual([x for x in f if x['category'] == 'network_endpoints'], [])

    def test_ingress_backend_missing_service_is_high(self):
        ing = [{'namespace': 'app', 'name': 'ing', 'hosts': ['a.com'],
                'backends': [{'service': 'nope', 'port_number': 80,
                              'port_name': '', 'path': '/'}],
                'default_backend': None, 'tls': []}]
        f = self._find(inputs([svc()], ingresses=ing))
        got = [x for x in f if x['category'] == 'network_ingress']
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]['severity'], 'high')

    def test_ingress_backend_port_name_mismatch_is_high(self):
        ing = [{'namespace': 'app', 'name': 'ing', 'hosts': [],
                'backends': [{'service': 'web', 'port_number': None,
                              'port_name': 'nosuch', 'path': '/'}],
                'default_backend': None, 'tls': []}]
        f = self._find(inputs([svc()], ingresses=ing))
        got = [x for x in f if x['category'] == 'network_ingress']
        self.assertEqual(len(got), 1)
        self.assertIn('포트 이름', got[0]['value'])

    def test_ingress_backend_valid_port_name_passes(self):
        ing = [{'namespace': 'app', 'name': 'ing', 'hosts': [],
                'backends': [{'service': 'web', 'port_number': None,
                              'port_name': 'http', 'path': '/'}],
                'default_backend': None, 'tls': []}]
        f = self._find(inputs([svc()], ingresses=ing))
        self.assertEqual([x for x in f if x['category'] == 'network_ingress'], [])


# ═════════════════════════════════════════════════════════════════════════════
class TestProbeFindings(unittest.TestCase):
    """도달성 — 5xx·연결실패만 신고하고 4xx 는 무시한다."""

    def _find(self, probes):
        return netscan_findings({'ran': True, 'static': {}, 'certs': [],
                                 'probes': probes}, _report_finding)

    def _probe(self, **kw):
        base = {'namespace': 'app', 'name': 'web', 'port': 80, 'scheme': 'http',
                'ok': False, 'latency_ms': 10.0}
        base.update(kw)
        return base

    def test_benign_status_codes_are_not_reported(self):
        # 인증 보호(401/403) · 루트 경로 없음(404) · HTTPS 포트에 평문(400) ·
        # 메서드 불허(405) · 업그레이드 필요(426) — 정상 운영에서 흔하다
        for st in (400, 401, 403, 404, 405, 426, 501, 301, 302):
            f = self._find([self._probe(status=st)])
            self.assertEqual(f, [], f'HTTP {st} 는 신고하지 않아야 함')

    def test_5xx_is_high(self):
        for st in (500, 502, 503, 599):
            f = self._find([self._probe(status=st)])
            self.assertEqual(len(f), 1, f'HTTP {st}')
            self.assertEqual(f[0]['severity'], 'high')
            self.assertEqual(f[0]['category'], 'network_reach')

    def test_connection_failure_is_high(self):
        f = self._find([self._probe(status=None, error='ConnectionError')])
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'high')
        self.assertIn('연결 실패', f[0]['value'])

    def test_ok_fast_response_not_reported(self):
        self.assertEqual(self._find([self._probe(ok=True, status=200, latency_ms=50)]), [])

    def test_ok_slow_response_is_medium(self):
        f = self._find([self._probe(ok=True, status=200, latency_ms=5000)])
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'medium')

    def test_rbac_denied_yields_single_info_finding(self):
        ns = {'ran': True, 'static': {}, 'certs': [], 'probes': [],
              'permission': 'denied'}
        f = netscan_findings(ns, _report_finding)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'info')
        self.assertEqual(f[0]['category'], 'network_scan')


# ═════════════════════════════════════════════════════════════════════════════
class TestTlsFindings(unittest.TestCase):
    """TLS 만료 임계값 경계 + SAN."""

    def _find(self, certs):
        return netscan_findings({'ran': True, 'static': {}, 'probes': [],
                                 'certs': certs}, _report_finding)

    def _cert(self, days, **kw):
        c = {'namespace': 'app', 'ingress': 'ing', 'secret': 'tls',
             'hosts': ['a.example.com'], 'days_left': days,
             'san': ['a.example.com'], 'san_ok': True,
             'not_after': '2026-12-31T00:00:00+00:00'}
        c.update(kw)
        return c

    def test_expiry_thresholds_at_boundaries(self):
        cases = [(-1, 'critical'), (0, 'critical'), (13, 'critical'),
                 (14, 'high'), (29, 'high'),
                 (30, 'medium'), (59, 'medium'),
                 (60, None), (200, None)]
        for days, expect in cases:
            f = [x for x in self._find([self._cert(days)])
                 if x['category'] == 'network_tls']
            if expect is None:
                self.assertEqual(f, [], f'D-{days} 는 신고하지 않아야 함')
            else:
                self.assertEqual(len(f), 1, f'D-{days}')
                self.assertEqual(f[0]['severity'], expect, f'D-{days}')

    def test_san_mismatch_is_medium(self):
        f = self._find([self._cert(200, san_ok=False, san=['other.com'])])
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'medium')
        self.assertIn('SAN', f[0]['value'])

    def test_cert_read_error_is_medium(self):
        f = self._find([{'namespace': 'app', 'ingress': 'i', 'secret': 's',
                         'hosts': [], 'error': 'tls.crt 없음'}])
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'medium')

    def test_wildcard_san_matching(self):
        self.assertTrue(_san_matches('a.example.com', ['*.example.com']))
        self.assertFalse(_san_matches('a.b.example.com', ['*.example.com']))
        self.assertTrue(_san_matches('x.com', ['x.com']))
        self.assertFalse(_san_matches('y.com', ['x.com']))
        self.assertTrue(_san_matches('', []))      # 호스트 미지정이면 판단 보류


# ═════════════════════════════════════════════════════════════════════════════
class TestNetscanRun(unittest.TestCase):
    """실행 — 주입점으로 예산/취소/권한거부 처리를 검증(클러스터 불필요)."""

    def _plan(self, n):
        return netscan_plan(inputs([svc(name=f'w{i}') for i in range(n)]))

    def test_probe_results_collected(self):
        calls = []

        def fake(t):
            calls.append(t['name'])
            return {**t, 'ok': True, 'status': 200, 'latency_ms': 1.0}

        r = netscan_run(None, self._plan(5), probe=fake, cert_reader=lambda *_: b'')
        self.assertEqual(len(r['probes']), 5)
        self.assertEqual(len(calls), 5)
        self.assertEqual(r['permission'], 'ok')
        self.assertEqual(r['mechanism'], 'apiserver-service-proxy')

    def test_rbac_denial_short_circuits_and_drops_bogus_failures(self):
        """첫 403 에서 중단 — 같은 이유로 N 건 허위 실패가 찍히면 안 된다."""
        def fake(t):
            return {**t, 'ok': False, 'status': 403, 'rbac_denied': True}

        r = netscan_run(None, self._plan(20), probe=fake, cert_reader=lambda *_: b'',
                        max_workers=1)
        self.assertEqual(r['permission'], 'denied')
        self.assertEqual(r['probes'], [], 'rbac 실패는 발견사항으로 남기지 않는다')
        # 판정에서도 안내 1건만
        f = netscan_findings(r, _report_finding)
        self.assertEqual([x['category'] for x in f], ['network_scan'])

    def test_probe_exception_does_not_kill_the_run(self):
        def fake(t):
            if t['name'] == 'w1':
                raise RuntimeError('boom')
            return {**t, 'ok': True, 'status': 200, 'latency_ms': 1.0}

        r = netscan_run(None, self._plan(3), probe=fake, cert_reader=lambda *_: b'',
                        max_workers=1)
        self.assertEqual(len(r['probes']), 3)
        failed = [p for p in r['probes'] if not p.get('ok')]
        self.assertEqual(len(failed), 1)
        self.assertIn('RuntimeError', failed[0]['error'])

    def test_cancel_event_stops_early(self):
        ev = threading.Event()

        def fake(t):
            ev.set()      # 첫 프로브 후 취소 신호
            return {**t, 'ok': True, 'status': 200, 'latency_ms': 1.0}

        r = netscan_run(None, self._plan(20), probe=fake, cert_reader=lambda *_: b'',
                        max_workers=1, cancel=ev)
        self.assertLess(len(r['probes']), 20)

    def test_budget_exceeded_flag(self):
        def fake(t):
            return {**t, 'ok': True, 'status': 200, 'latency_ms': 1.0}

        r = netscan_run(None, self._plan(10), probe=fake, cert_reader=lambda *_: b'',
                        budget_s=-1, max_workers=1)
        self.assertTrue(r['budget_exceeded'],
                        '단계를 건너뛴 경우에도 초과 플래그가 남아야 한다')
        self.assertLess(len(r['probes']), 10)

    def test_tls_reads_run_in_parallel_and_respect_budget(self):
        """v1.2.121 회귀 — 인증서 읽기가 순차 + 예산 미적용이라 전체가 260초를 넘었다."""
        from src.netscan import _DEFAULT_WORKERS
        refs = [{'namespace': 'app', 'name': f'i{i}', 'hosts': [], 'backends': [],
                 'default_backend': None,
                 'tls': [{'secret_name': f's{i}', 'hosts': []}]} for i in range(8)]
        plan = netscan_plan(inputs([svc()], ingresses=refs))
        # 예산이 이미 소진된 상태로 진입하면 인증서 단계도 건너뛴다
        r = netscan_run(None, plan, probe=lambda t: {**t, 'ok': True, 'status': 200,
                                                    'latency_ms': 1.0},
                        cert_reader=lambda *_: b'', budget_s=-1)
        self.assertEqual(r['certs'], [], '예산 초과면 인증서 단계도 건너뛴다')
        self.assertTrue(r['budget_exceeded'])
        # 동시성 기본값이 1 이면 순차라 느리다 — 병렬이어야 한다
        self.assertGreaterEqual(_DEFAULT_WORKERS, 8)


class TestTimeoutIsActuallyEnforced(unittest.TestCase):
    """★ v1.2.122 사고 — 타임아웃 3초가 실제로는 84초였다.

    블랙홀 IP 로 실측한 값:
        _request_timeout=3.0 (float)  →  84.2초
        retries=0 + (3,3) 튜플        →   3.0초
    두 가지가 곱해져서 사용자 클러스터에서 131초가 나왔다.
    ① float 을 주면 urllib3.Timeout(total=N) 이 되어 단계별 하드 캡이 안 걸린다
    ② Configuration.retries 기본값 None → urllib3 Retry(3) = 총 4회 시도
    """

    def test_probe_timeout_is_a_connect_read_tuple_not_a_float(self):
        from src.netscan import _PROBE_TIMEOUT, _CERT_TIMEOUT, _PROBE_TIMEOUT_S
        for name, val in (('_PROBE_TIMEOUT', _PROBE_TIMEOUT),
                          ('_CERT_TIMEOUT', _CERT_TIMEOUT)):
            self.assertIsInstance(val, tuple, f'{name} 은 (connect, read) 튜플이어야 한다')
            self.assertEqual(len(val), 2, name)
            self.assertTrue(all(isinstance(x, (int, float)) for x in val), name)
        self.assertEqual(_PROBE_TIMEOUT, (_PROBE_TIMEOUT_S, _PROBE_TIMEOUT_S))

    def test_probe_passes_tuple_timeout_to_client(self):
        """_probe_service 가 튜플을 그대로 넘기는지 (float 로 바꾸면 안 된다)."""
        from src.netscan import _probe_service, _PROBE_TIMEOUT
        seen = {}

        class FakeApi:
            def connect_get_namespaced_service_proxy(self, name, namespace,
                                                     _request_timeout=None):
                seen['timeout'] = _request_timeout
                seen['name'] = name
                return ''

        r = _probe_service(FakeApi(), {'namespace': 'app', 'name': 'web',
                                       'port': 80, 'scheme': 'http'})
        self.assertEqual(seen['timeout'], _PROBE_TIMEOUT)
        self.assertEqual(seen['name'], 'http:web:80')
        self.assertTrue(r['ok'])

    def test_no_retry_client_does_not_mutate_shared_client(self):
        """전용 클라이언트를 만들어도 공유 클라이언트의 retries 는 그대로여야 한다.

        공유 쪽을 0 으로 바꾸면 Polaris 의 다른 모든 API 호출이 재시도를 잃는다.
        """
        try:
            import kubernetes.client as kc
        except ImportError:
            self.skipTest('kubernetes 클라이언트 없음')
        from src.netscan import _no_retry_client

        cfg = kc.Configuration()
        cfg.host = 'https://example.invalid:6443'
        shared_api = kc.CoreV1Api(kc.ApiClient(cfg))

        class K8s:
            core = shared_api

        # v1.3.41 부터 공유 클라이언트도 기본 재시도(연결 1번)를 갖는다(src/k8s_http.py).
        # 지켜야 할 것은 「None 인가」 가 아니라 「netscan 이 그 값을 바꾸지 않는가」 다.
        shared_before = shared_api.api_client.configuration.retries
        api, closer = _no_retry_client(K8s())
        try:
            self.assertIsNotNone(api)
            # 재시도는 없어야 응답 없는 대상에서 빨리 끊긴다 (total=0).
            # 정수 0 이 아니라 Retry 객체여야 한다 — 정수를 주면 리다이렉트가 재시도로
            # 카운트돼 정상 서비스가 오탐된다(위 end-to-end 테스트가 그 계약을 지킨다).
            self.assertEqual(api.api_client.configuration.retries.total, 0,
                             '전용 클라이언트는 재시도 없음')
            self.assertIs(shared_api.api_client.configuration.retries, shared_before,
                          '공유 클라이언트는 건드리지 않는다')
            self.assertEqual(api.api_client.configuration.host, cfg.host,
                             '인증·호스트 설정은 승계')
            self.assertIsNot(api, shared_api, '별도 인스턴스여야 한다')
        finally:
            closer()
            shared_api.api_client.close()

    def test_no_retry_client_falls_back_to_shared_on_failure(self):
        from src.netscan import _no_retry_client

        class Broken:
            core = object()      # api_client 속성이 없어 deepcopy 가 실패한다

        api, closer = _no_retry_client(Broken())
        self.assertIsNotNone(api, '실패 시 공유 클라이언트로 폴백해야 한다')
        closer()

    def test_hard_wall_clock_cap_when_probes_never_return(self):
        """응답 없는 대상이 예산을 넘겨도 as_completed(timeout=) 이 끊는다.

        v1.2.122 에서는 완료 후 검사만 해서, 84초짜리 요청 하나가 전체를 131초로 만들었다.
        """
        started = threading.Event()

        def never_returns(t):
            started.set()
            time.sleep(30)       # 예산보다 훨씬 길게 — 실제로는 여기서 끊겨야 한다
            return {**t, 'ok': True, 'status': 200, 'latency_ms': 1.0}

        plan = netscan_plan(inputs([svc(name=f'w{i}') for i in range(4)]))
        t0 = time.monotonic()
        r = netscan_run(None, plan, probe=never_returns,
                        cert_reader=lambda *_: b'', budget_s=1.0, max_workers=4)
        dt = time.monotonic() - t0
        self.assertTrue(started.is_set())
        self.assertLess(dt, 10.0,
                        f'{dt:.1f}초 — 예산 1초인데 프로브 30초를 기다렸다')
        self.assertTrue(r['budget_exceeded'])

    def test_skipped_counts_are_reported(self):
        """못 본 건 수를 결과에 남긴다 — UI/보고서가 '0건'을 '없음'으로 오해하지 않게."""
        ings = [{'namespace': 'app', 'name': f'i{i}', 'hosts': [], 'backends': [],
                 'default_backend': None,
                 'tls': [{'secret_name': f's{i}', 'hosts': []}]} for i in range(10)]
        plan = netscan_plan(inputs([svc()], ingresses=ings))
        r = netscan_run(None, plan, probe=lambda t: {**t, 'ok': True, 'status': 200,
                                                    'latency_ms': 1.0},
                        cert_reader=lambda *_: b'', budget_s=-1)
        self.assertEqual(r['certs_total'], 10)
        self.assertEqual(r['certs_skipped'], 10, '미점검 인증서 10건이 보고돼야 한다')
        self.assertTrue(r['budget_exceeded'])


class TestSelectorlessNotProbed(unittest.TestCase):
    """★ v1.2.124 사고 — default/kubernetes(apiserver 자신)를 프로브해 503 오탐.

    apiserver Service proxy 로 apiserver 자신을 찌르는 건 구조가 순환이라 건강한
    클러스터에서도 200 이 안 나온다(프록시가 호출자 크리덴셜을 백엔드로 안 넘김).
    selector 가 없으면 추론할 파드가 없어 실패해도 조치 대상이 없으므로 프로브에서 뺀다.
    apiserver 자체의 건강은 /readyz 로 따로 본다.
    """

    def _kubernetes_svc(self):
        return {'namespace': 'default', 'name': 'kubernetes', 'type': 'ClusterIP',
                'cluster_ip': '10.43.0.1', 'selector': None,
                'ports': [{'name': 'https', 'port': 443, 'protocol': 'TCP',
                           'app_protocol': ''}]}

    def test_apiserver_service_is_not_probed(self):
        plan = netscan_plan(inputs(
            [self._kubernetes_svc()],
            endpoints={'default/kubernetes': {'ready': 3, 'not_ready': 0}}))
        self.assertEqual(plan['targets'], [],
                         'apiserver 자기프록시는 항상 실패하므로 프로브 대상이 아니다')
        self.assertIn(SKIP_NO_SELECTOR, reasons(plan, 'kubernetes'))

    def test_selectorless_skip_is_visible_in_report(self):
        """제외는 조용히 사라지지 않고 사유와 함께 남는다."""
        plan = netscan_plan(inputs(
            [self._kubernetes_svc()],
            endpoints={'default/kubernetes': {'ready': 3, 'not_ready': 0}}))
        entry = [s for s in plan['skipped'] if s['name'] == 'kubernetes']
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]['reason'], SKIP_NO_SELECTOR)

    def test_selector_bearing_service_still_probed(self):
        """selector 가 있는 평범한 서비스는 그대로 프로브한다(과잉 제외 방지)."""
        plan = netscan_plan(inputs([svc()]))
        self.assertEqual(len(plan['targets']), 1)


class TestReadyzRule(unittest.TestCase):
    """컨트롤 플레인 준비 상태 (/readyz?verbose) — v1.2.125.

    apiserver 에 붙어 있다는 사실만으로는 '살아 있다'까지만 알 수 있다.
    etcd·informer-sync·poststarthook 단위 실패를 여기서 잡는다.
    """

    BASE = {
        'pods': [], 'nodes': [], 'services': [], 'ingresses': [], 'pvcs': [],
        'pdbs': [], 'storage_classes': [], 'kube_system': {}, 'deployments': [],
        'rbac_risky': [], 'hpa': [], 'hpas': [], 'events': [],
    }

    def _find(self, readyz):
        f = _report_evaluate({**self.BASE, 'readyz': readyz})
        return [x for x in f if x['category'] == 'apiserver']

    def test_healthy_readyz_yields_no_finding(self):
        self.assertEqual(self._find({
            'ok': True, 'status': 200,
            'checks': ['ping', 'etcd', 'informer-sync'], 'failed': [],
            'error': None}), [])

    def test_etcd_failure_is_critical(self):
        f = self._find({'ok': False, 'status': 500, 'checks': ['ping'],
                        'failed': [{'name': 'etcd', 'detail': 'etcd failed: timeout'}],
                        'error': None})
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'critical')
        self.assertIn('etcd', f[0]['detail'])

    def test_other_component_failure_is_high(self):
        f = self._find({'ok': False, 'status': 500, 'checks': ['ping', 'etcd'],
                        'failed': [{'name': 'informer-sync',
                                    'detail': 'informer-sync failed'}],
                        'error': None})
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'high')

    def test_query_failure_is_info_not_alarm(self):
        """조회 자체가 안 되는 건 대개 권한 문제다 — 장애로 단정하지 않는다."""
        f = self._find({'ok': False, 'status': None, 'checks': [], 'failed': [],
                        'error': 'ApiException: 403'})
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'info')

    def test_missing_readyz_key_yields_nothing(self):
        """수집이 안 된 경우(옛 스냅샷 등)에도 조용히 넘어간다."""
        for val in (None, [], 'x'):
            f = _report_evaluate({**self.BASE, 'readyz': val})
            self.assertEqual([x for x in f if x['category'] == 'apiserver'], [],
                             f'readyz={val!r}')
        f = _report_evaluate(dict(self.BASE))
        self.assertEqual([x for x in f if x['category'] == 'apiserver'], [])

    def test_readyz_parser_reads_verbose_body(self):
        """[+]/[-] 형식 파싱 — 500 응답의 body 도 같은 형식으로 온다."""
        from src.reports import _report_fetch_readyz

        class Api:
            class api_client:
                @staticmethod
                def call_api(*a, **kw):
                    raise _ApiErr(500,
                                  '[+]ping ok\n'
                                  '[+]log ok\n'
                                  '[-]etcd failed: reason withheld\n'
                                  '[-]informer-sync failed\n'
                                  'readyz check failed\n')

        class K8s:
            core = Api()

        out = _report_fetch_readyz(K8s())
        self.assertEqual(out['status'], 500)
        self.assertFalse(out['ok'])
        self.assertEqual(out['checks'], ['ping', 'log'])
        self.assertEqual([f['name'] for f in out['failed']],
                         ['etcd', 'informer-sync'])

    def test_readyz_collector_never_raises(self):
        """_report_collect._run 의 폴백이 [] 라서 예외를 밖으로 내면 구분이 사라진다."""
        from src.reports import _report_fetch_readyz

        class Broken:
            core = None

        out = _report_fetch_readyz(Broken())
        self.assertIsInstance(out, dict)
        self.assertFalse(out['ok'])
        self.assertIsNotNone(out['error'])

    def test_area_map_puts_apiserver_under_infra(self):
        """9장 담당 영역 분류 — substring 매칭이라 순서 의존이다."""
        import re
        path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), 'src', 'reports.py')
        with open(path, encoding='utf-8') as fh:
            src = fh.read()
        m = re.search(r"AREA_MAP = \{(.*?)\}", src, re.S)
        self.assertIsNotNone(m)
        self.assertIn("'apiserver': '인프라'", m.group(1))


class TestRedirectIsNotFailure(unittest.TestCase):
    """★ v1.2.123 사고 — 리다이렉트하는 정상 서비스를 '연결 실패'로 신고했다.

    retries=0 (정수) 을 주면 urllib3 이 Retry(total=0) 으로 해석하고 리다이렉트도
    total 에 카운트해서, 리다이렉트 1회만으로 MaxRetryError('too many redirects') 를
    던진다. 그 예외에는 .status 가 없어 '연결 실패'(high)가 됐다.
    Prometheus(/→/graph)·Vault UI(/→/ui/) 가 전부 오탐 — 사용자 클러스터에서 수십 건.

    실측: retries=0 → status=None(오탐) / Retry(total=0, redirect=False) → status=302(정상)
    """

    def test_redirecting_service_is_not_reported_as_failure_end_to_end(self):
        """★ 계약: 302 를 돌려주는 서비스를 프로브해도 '연결 실패'가 나오지 않는다.

        속성(.redirect)을 보는 대신 실제 302 서버를 세워 _no_retry_client + _probe_service
        전체 경로를 통과시킨다 — urllib3 이 redirect=False 를 0 으로 정규화하는 등
        내부 표현이 버전마다 달라도 이 테스트는 흔들리지 않는다.
        """
        try:
            import kubernetes.client as kc
        except ImportError:
            self.skipTest('kubernetes 클라이언트 없음')
        import http.server
        import socket
        from src.netscan import _no_retry_client, _probe_service

        class Redirect302(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header('Location', '/graph')   # Prometheus 가 하는 그대로
                self.end_headers()

            def log_message(self, *a):
                pass

        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()
        srv = http.server.HTTPServer(('127.0.0.1', port), Redirect302)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            cfg = kc.Configuration()
            cfg.host = f'http://127.0.0.1:{port}'
            cfg.verify_ssl = False
            cfg.api_key = {}
            shared = kc.CoreV1Api(kc.ApiClient(cfg))

            class K8s:
                core = shared

            api, closer = _no_retry_client(K8s())
            try:
                r = _probe_service(api, {'namespace': 'ns', 'name': 'prom',
                                         'port': 9090, 'scheme': 'http'})
                self.assertTrue(
                    r['ok'],
                    f"리다이렉트가 실패로 처리됐다 (status={r.get('status')}, "
                    f"error={r.get('error')}) — v1.2.123 오탐 재발")
                self.assertEqual(
                    netscan_findings({'ran': True, 'static': {}, 'certs': [],
                                      'probes': [r]}, _report_finding), [],
                    '리다이렉트는 발견사항이 아니다')
            finally:
                closer()
                shared.api_client.close()
        finally:
            srv.shutdown()
            # shutdown() 은 serve_forever 만 멈춘다 — **듣던 소켓은 server_close()**
            # 라야 닫힌다. 안 닫으면 전체 스위트가 ResourceWarning 을 하나 흘린다
            # (v1.2.125 부터 흘리고 있었다). test_apitest_run 에도 같은 주석이 있다.
            srv.server_close()

    def test_3xx_counts_as_reachable(self):
        """302 는 서비스가 HTTP 응답을 만들어낸 것 = 확실히 살아 있다."""
        from src.netscan import _probe_service

        class Redirecting:
            def connect_get_namespaced_service_proxy(self, name, namespace,
                                                     _request_timeout=None):
                raise _ApiErr(302, 'Found')

        r = _probe_service(Redirecting(), {'namespace': 'app', 'name': 'prom',
                                           'port': 9090, 'scheme': 'http'})
        self.assertTrue(r['ok'], '302 를 실패로 세면 Prometheus·Vault UI 가 오탐된다')
        self.assertEqual(r['status'], 302)
        self.assertEqual(netscan_findings(
            {'ran': True, 'static': {}, 'certs': [], 'probes': [r]},
            _report_finding), [], '리다이렉트는 발견사항이 아니다')

    def test_redirect_flavored_exception_is_not_connection_failure(self):
        """폴백(공유 클라이언트) 경로에서 리다이렉트 한도 초과가 나도 실패가 아니다."""
        from src.netscan import _probe_service

        class TooManyRedirects:
            def connect_get_namespaced_service_proxy(self, name, namespace,
                                                     _request_timeout=None):
                raise RuntimeError(
                    "HTTPSConnectionPool(host='1.2.3.4', port=6443): Max retries "
                    "exceeded with url: /proxy (Caused by ResponseError("
                    "'too many redirects'))")

        r = _probe_service(TooManyRedirects(), {'namespace': 'app', 'name': 'vault',
                                                'port': 8200, 'scheme': 'http'})
        self.assertTrue(r['ok'])
        self.assertTrue(r.get('redirected'))
        self.assertEqual(netscan_findings(
            {'ran': True, 'static': {}, 'certs': [], 'probes': [r]},
            _report_finding), [])

    def test_real_connection_failure_still_reported(self):
        """리다이렉트가 아닌 진짜 연결 실패는 여전히 high 로 잡혀야 한다."""
        from src.netscan import _probe_service

        class Refused:
            def connect_get_namespaced_service_proxy(self, name, namespace,
                                                     _request_timeout=None):
                raise RuntimeError('ConnectionRefusedError: [Errno 111] refused')

        r = _probe_service(Refused(), {'namespace': 'app', 'name': 'dead',
                                       'port': 80, 'scheme': 'http'})
        self.assertFalse(r['ok'])
        f = netscan_findings({'ran': True, 'static': {}, 'certs': [], 'probes': [r]},
                             _report_finding)
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['severity'], 'high')


class _ApiErr(Exception):
    """kubernetes ApiException 흉내 — .status 를 가진 예외."""

    def __init__(self, status, body=''):
        super().__init__(f'({status})')
        self.status = status
        self.body = body


class TestBudgetConsistency(unittest.TestCase):
    """★ 예산·동시성·타임아웃·상한이 서로 모순되지 않는지.

    v1.2.121 초기값(동시 4 · 프로브 8초 · 예산 90초 · 상한 100)은
    100×8÷4 = 200초 > 90초 → 대상 45건만 넘어도 잘림이 확정이었다.
    실제로 사용자 클러스터에서 263초가 걸렸다. 이 테스트가 그 조합을 막는다.
    """

    def test_worst_case_probe_time_fits_in_budget(self):
        from src.netscan import (_DEFAULT_BUDGET_S, _DEFAULT_WORKERS,
                                 _DEFAULT_TARGET_CAP, _PROBE_TIMEOUT_S,
                                 _CERT_TIMEOUT_S)
        probe_worst = _DEFAULT_TARGET_CAP * _PROBE_TIMEOUT_S / _DEFAULT_WORKERS
        # 인증서는 대상 수와 무관하지만 넉넉히 30건 가정
        cert_worst = 30 * _CERT_TIMEOUT_S / _DEFAULT_WORKERS
        total = probe_worst + cert_worst
        self.assertLess(
            total, _DEFAULT_BUDGET_S,
            f'최악 {total:.0f}초 > 예산 {_DEFAULT_BUDGET_S:.0f}초 — 상한까지 채우면 '
            f'반드시 잘린다. 동시성/타임아웃/예산/상한 중 하나를 조정할 것')

    def test_tls_secret_read_deduped_and_system_ns_skipped(self):
        reads = []

        def reader(ns, name):
            reads.append((ns, name))
            return b''      # 파싱 실패 → error 항목

        plan = netscan_plan(inputs([svc()], ingresses=[
            {'namespace': 'app', 'name': 'a', 'hosts': ['a.com'], 'backends': [],
             'default_backend': None, 'tls': [{'secret_name': 'shared', 'hosts': ['a.com']}]},
            {'namespace': 'app', 'name': 'b', 'hosts': ['b.com'], 'backends': [],
             'default_backend': None, 'tls': [{'secret_name': 'shared', 'hosts': ['b.com']}]},
            {'namespace': 'kube-system', 'name': 'sys', 'hosts': [], 'backends': [],
             'default_backend': None, 'tls': [{'secret_name': 'sys-tls', 'hosts': []}]},
        ]))
        r = netscan_run(None, plan, probe=lambda t: {**t, 'ok': True, 'status': 200,
                                                    'latency_ms': 1.0},
                        cert_reader=reader)
        self.assertEqual(reads, [('app', 'shared')],
                         '같은 Secret 은 1회만, 시스템 네임스페이스는 제외')
        self.assertEqual(len(r['certs']), 1)
        self.assertIn('error', r['certs'][0])


# ═════════════════════════════════════════════════════════════════════════════
class TestNoNetscanRegression(unittest.TestCase):
    """★ 최중요 — 옵트인하지 않으면 기존 동작이 한 톨도 안 바뀐다.

    take_snapshot(src/api/snapshots.py)과 비옵트인 health_scan 이 _report_evaluate 를
    공유하므로, 'netscan' 키가 없을 때 network_* 가 0건임을 증명해야 한다.
    """

    BASE = {
        'pods': [{'namespace': 'app', 'name': 'p1', 'restarts': 300,
                  'status': 'Running'}],
        'nodes': [], 'services': [], 'ingresses': [], 'pvcs': [], 'pdbs': [],
        'storage_classes': [], 'kube_system': {}, 'deployments': [],
        'rbac_risky': [], 'hpa': [], 'hpas': [], 'events': [],
    }

    def setUp(self):
        # 기존 규칙이 이 fixture 에서 몇 건을 내는지는 규칙 변경에 따라 달라진다.
        # 하드코딩하면 무관한 규칙을 손댈 때 이 테스트가 깨져 신호가 흐려지므로,
        # 매번 기준선을 측정해 "netscan 이 기준선을 바꾸지 않는다"만 검증한다.
        self.baseline = _report_evaluate(dict(self.BASE))
        self.assertEqual(
            [x for x in self.baseline if x['category'].startswith('network_')], [],
            'fixture 자체에 network_* 가 있으면 이 테스트의 전제가 무너진다')

    def test_without_netscan_key_no_network_findings(self):
        f = _report_evaluate(dict(self.BASE))
        self.assertEqual([x for x in f if x['category'].startswith('network_')], [])
        self.assertEqual(len(f), len(self.baseline))

    def test_netscan_none_or_empty_is_ignored(self):
        for val in (None, {}, {'ran': False}):
            f = _report_evaluate({**self.BASE, 'netscan': val})
            self.assertEqual([x for x in f if x['category'].startswith('network_')], [],
                             f'netscan={val!r}')
            self.assertEqual(len(f), len(self.baseline), f'netscan={val!r}')

    def test_with_netscan_findings_are_appended_not_replacing(self):
        ns = {'ran': True, 'static': {}, 'certs': [], 'probes': [
            {'namespace': 'app', 'name': 'web', 'port': 80, 'ok': False,
             'status': 500, 'latency_ms': 5.0}]}
        f = _report_evaluate({**self.BASE, 'netscan': ns})
        cats = [x['category'] for x in f]
        self.assertIn('pod_restart', cats)   # 기존 발견사항 유지
        self.assertIn('network_reach', cats)
        # 기준선 + network_reach 1건 — 기존 발견사항이 사라지거나 중복되지 않는다
        self.assertEqual(len(f), len(self.baseline) + 1)

    def test_all_categories_are_network_prefixed(self):
        """reports.AREA_MAP 의 'network' substring 매칭에 걸려야 9장 담당영역이 잡힌다."""
        ns = {
            'ran': True, 'permission': 'denied',
            'static': inputs([svc(name='x')],
                             endpoints={'app/x': {'ready': 0, 'not_ready': 0}}),
            'probes': [{'namespace': 'a', 'name': 'b', 'port': 1, 'ok': False,
                        'status': 500}],
            'certs': [{'namespace': 'a', 'ingress': 'i', 'secret': 's',
                       'hosts': ['h'], 'days_left': 3, 'san': ['h'], 'san_ok': True}],
        }
        for f in netscan_findings(ns, _report_finding):
            self.assertTrue(f['category'].startswith('network'),
                            f"{f['category']} 는 network 로 시작해야 함")


# ═════════════════════════════════════════════════════════════════════════════
class TestDocxFormat(unittest.TestCase):
    """보고서 형식 보존 — 10장 조건부 렌더 + 모든 표의 폭 합 16.5cm.

    폭 불변식은 지금까지 손으로만 유지돼 왔다(테스트 없음). 여기서 잠가두면
    이 변경뿐 아니라 앞으로의 모든 표 추가를 보호한다.
    """

    BASE = {
        'nodes': [{'name': 'n1', 'status': 'Ready', 'roles': 'master',
                   'version': 'v1.34', 'cpu': '4', 'memory': '8Gi', 'age': '10d'}],
        'namespaces': [{'name': 'app'}], 'pods': [], 'deployments': [],
        'statefulsets': [], 'daemonsets': [], 'jobs': [], 'cronjobs': [],
        'services': [], 'ingresses': [], 'ingress_classes': [], 'pvcs': [],
        'pvs': [], 'configmaps': [], 'secrets': [], 'helm': [], 'hpa': [],
        'hpas': [], 'pdbs': [], 'network_policies': [], 'storage_classes': [],
        'resource_quotas': [], 'limit_ranges': [], 'rbac': {}, 'rbac_risky': [],
        'kube_system': {}, 'events': [], 'node_metrics': [], 'pod_metrics': [],
        'cluster_version': 'v1.34.8', 'collected_at': '2026-07-29 10:00:00',
    }

    NETSCAN = {
        'ran': True, 'permission': 'ok', 'target_count': 2, 'total_candidates': 5,
        'truncated': True, 'duration_s': 3.1,
        'probes': [
            {'namespace': 'app', 'name': 'web', 'port': 80, 'scheme': 'http',
             'ok': True, 'status': 200, 'latency_ms': 20.0},
            {'namespace': 'app', 'name': 'api', 'port': 8080, 'scheme': 'http',
             'ok': False, 'status': 503, 'latency_ms': 15.0},
        ],
        'certs': [{'namespace': 'app', 'ingress': 'ing', 'secret': 'tls',
                   'hosts': ['a.com'], 'days_left': 5, 'san': ['a.com'],
                   'san_ok': True, 'not_after': '2026-08-03T00:00:00+00:00'}],
        'skipped': [{'namespace': 'kube-system', 'name': 'x', 'port': None,
                     'reason': SKIP_SYSTEM_NS}],
        'static': {'services': [], 'services_ok': True, 'endpoints': {},
                   'endpoints_ok': True, 'ingresses': [], 'ingresses_ok': True},
    }

    def _build(self, data):
        import tempfile
        try:
            from docx import Document
            from docx.shared import Cm
        except ImportError:
            self.skipTest('python-docx 미설치')
        from src.reports import _report_write_docx
        findings = _report_evaluate(data)
        out = os.path.join(tempfile.mkdtemp(), 'r.docx')
        path = _report_write_docx(data, findings, None, out, lambda *_a: None)
        self.assertTrue(path.endswith('.docx'), 'docx 폴백이 아니어야 함')
        return Document(path), Cm

    def test_section10_absent_without_netscan(self):
        doc, _ = self._build(dict(self.BASE))
        texts = [p.text for p in doc.paragraphs]
        self.assertFalse(any('네트워크 스캔' in t for t in texts),
                         '옵트인 안 하면 10장이 아예 없어야 한다')

    def test_section10_present_with_netscan(self):
        doc, _ = self._build({**self.BASE, 'netscan': self.NETSCAN})
        texts = [p.text for p in doc.paragraphs]
        for want in ('10. 네트워크 스캔', '10.1 점검 범위 및 방법',
                     '10.2 도달성 결과', '10.3 TLS 인증서 만료'):
            self.assertTrue(any(want in t for t in texts), f'{want} 누락')
        joined = '\n'.join(texts)
        # 한계 명시와 잘림 경고는 오독 방지를 위한 필수 문구다
        self.assertIn('ClusterIP', joined, '검증되지 않은 경로를 반드시 밝혀야 한다')
        self.assertIn('만 점검했습니다', joined, '잘림 경고가 있어야 한다')
        self.assertIn("'발견 없음'이 '정상'을 뜻하지 않습니다", joined)

    def test_all_tables_sum_to_16_5cm(self):
        for tag, data in (('없음', dict(self.BASE)),
                          ('있음', {**self.BASE, 'netscan': self.NETSCAN})):
            doc, Cm = self._build(data)
            self.assertGreater(len(doc.tables), 0)
            for i, t in enumerate(doc.tables):
                total = sum((c.width.cm if c.width else 0) for c in t.rows[0].cells)
                self.assertAlmostEqual(
                    total, 16.5, places=2,
                    msg=f'netscan {tag} — 표 #{i} 폭 합 {total}cm (16.5 이어야 함)')


if __name__ == '__main__':
    unittest.main()
