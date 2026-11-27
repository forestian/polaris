# -*- coding: utf-8 -*-
"""클러스터 점검 보고서 판정 — 서두른 판단 고치기 (v1.4.13).

사용자가 보고서 권고(Longhorn 이 관리하는 PDB 를 「조정」 하라)를 따랐다면 장애가 났을
상황에서 시작했다. 같은 성격 — 「못 본 것을 정상으로 적기」 · 「제품이 요구하는 설정을
고치라고 하기」 · 「phase 만 보고 판정하기」 — 을 항목별로 잠근다.

실제 사용자 데이터 폴더를 건드리지 않는다: 데이터는 test_report_sections._data() 를
늘려 쓰고, 클러스터 대신 가짜 API 객체를 쓴다.
"""
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_report_sections as C                                   # noqa: E402
from src.reports import (                                         # noqa: E402
    _report_evaluate, _report_write_docx, _report_collect, _call_collect,
    _COLLECT_FAIL_TEXT,
)

try:
    import docx  # noqa: F401
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

COLLECTED = '2026-10-22 10:00:00'


def _data(**extra):
    d = C._data()
    d['collected_at'] = COLLECTED
    d['rbac_risky'] = []
    d.update(extra)
    return d


def _cat(findings, cat):
    return [f for f in findings if f.get('category') == cat]


def _iso(days_ago):
    ref = datetime.fromisoformat(COLLECTED).astimezone()
    return (ref - timedelta(days=days_ago)).astimezone(timezone.utc).isoformat()


@unittest.skipUnless(HAS_DOCX, 'python-docx 미설치')
class _DocxCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='polaris-judg-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _text(self, data, sections=None, name='r.docx'):
        findings = _report_evaluate(data, sections)
        path = _report_write_docx(data, findings, None, str(self.tmp / name),
                                  lambda *_a, **_k: None, sections)
        self.assertTrue(path.endswith('.docx'))
        self.last_path = path
        return C._docx_text(path)


# ── 1. 수집 실패 ──────────────────────────────────────────────────────────────
class CollectFailureEvaluateTests(unittest.TestCase):
    def test_failed_sections_become_info_findings(self):
        f = _report_evaluate(_data(collect_errors=['pods', 'pvcs', 'helm']))
        col = _cat(f, 'collect')
        self.assertEqual(sorted(x['name'] for x in col), ['Helm 릴리스', 'PVC', '파드'])
        for x in col:
            self.assertEqual(x['severity'], 'info')
            self.assertIn('확인 불가 — ', x['detail'])
            self.assertIn('을(를) 수집하지 못해 판단하지 않았습니다', x['detail'])

    def test_rbac_failure_hidden_when_rbac_section_excluded(self):
        f = _report_evaluate(_data(collect_errors=['rbac_risky', 'pods']), {'nodes'})
        self.assertEqual([x['name'] for x in _cat(f, 'collect')], ['파드'])

    def test_old_data_without_key_has_no_collect_findings(self):
        self.assertEqual(_cat(_report_evaluate(_data()), 'collect'), [])


class CollectFailureCollectorTests(unittest.TestCase):
    """연결 안 된 K8sManager — getter 가 전부 실패한다. 반환값은 예전 그대로([] / {})여야 하고,
    보고서 수집만 실패를 안다."""

    def test_unconnected_manager_marks_sections_failed(self):
        from src.k8s import K8sManager
        mgr = K8sManager()
        data = _report_collect(mgr, lambda *_a: None, extras=True)
        failed = set(data['collect_errors'])
        for key in ('pods', 'nodes', 'deployments', 'pvcs', 'helm', 'pdbs', 'hpa',
                    'network_policies', 'ingresses', 'services', 'kube_system', 'events'):
            self.assertIn(key, failed, key)
        self.assertEqual(data['pods'], [])
        self.assertEqual(data['kube_system'], {})

    def test_getter_return_values_unchanged_for_other_callers(self):
        from src.k8s import K8sManager
        mgr = K8sManager()
        self.assertEqual(mgr.get_pods(), [])
        self.assertEqual(mgr.get_pdbs(), [])
        self.assertEqual(mgr.get_kube_system_info(), {})
        errs = []
        self.assertEqual(mgr.get_pods(None, errors=errs), [])
        self.assertEqual(len(errs), 1)

    def test_snapshot_path_keeps_diffed_shapes(self):
        """take_snapshot 경로(extras 없음)는 Ingress · Deployment 를 예전 키워드로 부른다."""
        calls = {}

        class Fake:
            cluster_info = {'version': 'v1'}

            def __getattr__(self, name):
                def fn(*a, **kw):
                    calls[name] = kw
                    return []
                return fn
        _report_collect(Fake(), lambda *_a: None)
        self.assertNotIn('tls', calls['get_ingresses'])
        self.assertNotIn('meta', calls['get_deployments_extended'])
        self.assertNotIn('get_cni_network_policy_counts', calls)

    def test_call_collect_skips_unknown_keywords(self):
        def old_getter(ns=None):
            return [ns]
        self.assertEqual(_call_collect(old_getter, [], 'x', detail=True), ['x'])


class CollectFailureDocxTests(_DocxCase):
    def test_failed_sections_do_not_print_normal(self):
        text = self._text(_data(collect_errors=['pods', 'pvcs', 'helm', 'kube_system']))
        self.assertIn(_COLLECT_FAIL_TEXT, text)
        for bad in ('✓ 비정상 파드 없음', '전체 PVC가 정상 Bound', 'Helm 릴리스 0개 모두 정상',
                    'kube-system 파드 정상 운영 중', '클러스터 상태가 양호합니다'):
            self.assertNotIn(bad, text, bad)

    def test_no_good_health_line_when_only_failures(self):
        d = _data(collect_errors=['rbac_risky'])
        text = self._text(d, {'nodes'}, 'x.docx')
        self.assertNotIn('클러스터 상태가 양호합니다', text)
        self.assertNotIn('RBAC', text.upper())


# ── 2. 파드 상태 ─────────────────────────────────────────────────────────────
class PodHealthTests(unittest.TestCase):
    def _f(self, pods, jobs=None, ks=None):
        return _report_evaluate(_data(pods=pods, jobs=jobs or [],
                                      kube_system=ks or {}))

    def test_crashloop_with_running_phase_is_caught(self):
        f = self._f([{'namespace': 'app', 'name': 'web-1', 'status': 'Running',
                      'reason': 'CrashLoopBackOff', 'restarts': '3'}])
        st = _cat(f, 'pod_state')
        self.assertEqual(len(st), 1)
        self.assertEqual(st[0]['severity'], 'high')
        self.assertEqual(st[0]['value'], 'CrashLoopBackOff')

    def test_evicted_is_low_cleanup(self):
        f = self._f([{'namespace': 'app', 'name': 'web-x', 'status': 'Failed', 'reason': 'Evicted'}])
        st = _cat(f, 'pod_state')
        self.assertEqual(st[0]['severity'], 'low')
        self.assertIn('정리 대상(남은 기록) — 서비스 영향 없음', st[0]['detail'])

    def test_failed_attempt_of_succeeded_job_is_skipped(self):
        pods = [{'namespace': 'kube-system', 'name': 'helm-install-rke2-ingress-nginx-abcde',
                 'status': 'Failed', 'reason': 'Error',
                 'owner_kind': 'Job', 'owner_name': 'helm-install-rke2-ingress-nginx'}]
        jobs = [{'namespace': 'kube-system', 'name': 'helm-install-rke2-ingress-nginx',
                 'status': 'Complete'}]
        f = self._f(pods, jobs)
        self.assertEqual(_cat(f, 'pod_state') + _cat(f, 'kube_system'), [])

    def test_failed_attempt_guessed_by_name_on_old_data(self):
        pods = [{'namespace': 'kube-system', 'name': 'helm-install-rke2-coredns-x1y2z',
                 'status': 'Failed'}]
        jobs = [{'namespace': 'kube-system', 'name': 'helm-install-rke2-coredns', 'status': 'Complete'}]
        self.assertEqual(_cat(self._f(pods, jobs), 'kube_system'), [])

    def test_failed_job_still_failing_is_reported(self):
        pods = [{'namespace': 'app', 'name': 'batch-abcde', 'status': 'Failed', 'reason': 'Error',
                 'owner_kind': 'Job', 'owner_name': 'batch'}]
        f = self._f(pods, [{'namespace': 'app', 'name': 'batch', 'status': 'Failed'}])
        self.assertEqual(_cat(f, 'pod_state')[0]['severity'], 'high')

    def test_pending_is_medium(self):
        f = self._f([{'namespace': 'app', 'name': 'p', 'status': 'Pending', 'reason': ''}])
        self.assertEqual(_cat(f, 'pod_state')[0]['severity'], 'medium')

    def test_kube_system_counted_once(self):
        pods = [{'namespace': 'kube-system', 'name': 'coredns-1', 'status': 'Running',
                 'reason': 'CrashLoopBackOff', 'restarts': '2'}]
        ks = {'pods': [{'name': 'coredns-1', 'status': 'Running', 'restarts': 2}]}
        f = self._f(pods, ks=ks)
        self.assertEqual(_cat(f, 'pod_state'), [])
        ksf = _cat(f, 'kube_system')
        self.assertEqual(len(ksf), 1)
        self.assertEqual(ksf[0]['severity'], 'critical')

    def test_kube_system_fallback_when_pods_failed(self):
        ks = {'pods': [{'name': 'etcd-x', 'status': 'Pending', 'restarts': 0}]}
        f = _report_evaluate(_data(collect_errors=['pods'], kube_system=ks))
        ksf = _cat(f, 'kube_system')
        self.assertEqual(len(ksf), 1)
        self.assertEqual(ksf[0]['severity'], 'high')      # phase 만으로 긴급 단정하지 않는다

    def test_get_pods_owner_field(self):
        import src.k8s as km
        from src.k8s import K8sManager
        cs = NS(ready=False, restart_count=4,
                state=NS(waiting=NS(reason='CrashLoopBackOff'), terminated=None, running=None),
                last_state=NS(terminated=NS(finished_at=datetime(2026, 10, 20, tzinfo=timezone.utc))))
        pod = NS(metadata=NS(name='w-abcde', namespace='app', creation_timestamp=None,
                             owner_references=[NS(kind='Job', name='w', controller=True)]),
                 spec=NS(containers=[NS()], node_name='n1'),
                 status=NS(phase='Running', reason=None, container_statuses=[cs],
                           init_container_statuses=None))
        mgr = K8sManager()
        mgr.core = NS(list_pod_for_all_namespaces=lambda **kw: NS(items=[pod]))
        old = km._FAST_LISTS
        km._FAST_LISTS = False
        try:
            plain = mgr.get_pods(None)
            full = mgr.get_pods(None, detail=True, owner=True)
        finally:
            km._FAST_LISTS = old
        self.assertNotIn('owner_kind', plain[0])
        self.assertNotIn('reason', plain[0])
        self.assertEqual((full[0]['owner_kind'], full[0]['owner_name']), ('Job', 'w'))
        self.assertEqual(full[0]['reason'], 'CrashLoopBackOff')


class PodHealthDocxTests(_DocxCase):
    def test_evicted_not_shown_as_urgent(self):
        text = self._text(_data(pods=[{'namespace': 'app', 'name': 'evicted-pod',
                                       'status': 'Failed', 'reason': 'Evicted', 'restarts': '0'}]))
        row = next(l for l in text.splitlines() if 'evicted-pod' in l)
        self.assertIn('낮음', row)
        self.assertNotIn('긴급', row)
        self.assertIn('서비스 영향은 없습니다', text)


# ── 3. RBAC ─────────────────────────────────────────────────────────────────
def _risky(kind, name, ns, binding='b'):
    return {'subject_kind': kind, 'name': name, 'namespace': ns, 'reason': 'cluster-admin 바인딩',
            'binding_kind': 'ClusterRoleBinding', 'binding': binding,
            'role_kind': 'ClusterRole', 'role': 'cluster-admin'}


class RbacTests(unittest.TestCase):
    def test_platform_subjects_are_info(self):
        risky = [_risky('ServiceAccount', 'rancher', 'cattle-system'),
                 _risky('ServiceAccount', 'fleet-agent', 'cattle-fleet-system'),
                 _risky('ServiceAccount', 'helm-rke2-ingress-nginx', 'kube-system',
                        'helm-kube-system-rke2-ingress-nginx'),
                 _risky('ServiceAccount', 'argocd-application-controller', 'argocd'),
                 _risky('ServiceAccount', 'longhorn-service-account', 'longhorn-system'),
                 _risky('ServiceAccount', 'cert-manager', 'cert-manager'),
                 _risky('ServiceAccount', 'rook-ceph-system', 'rook-ceph'),
                 _risky('ServiceAccount', 'kube-prometheus-stack-operator', 'monitoring')]
        f = _cat(_report_evaluate(_data(rbac_risky=risky)), 'rbac')
        self.assertEqual(len(f), len(risky))
        for x in f:
            self.assertEqual(x['severity'], 'info', x['name'])
            self.assertEqual(x['rec'], '제품이 요구하는 권한입니다 — 바인딩을 지우거나 줄이지 마세요')

    def test_other_sa_is_high_with_caution(self):
        f = _cat(_report_evaluate(_data(rbac_risky=[_risky('ServiceAccount', 'ci-runner', 'ci')])), 'rbac')
        self.assertEqual(f[0]['severity'], 'high')
        self.assertIn('이 계정을 쓰는 프로그램을 확인하세요', f[0]['rec'])
        self.assertNotIn('전용 Role 로 필요한 권한만', f[0]['rec'])

    def test_never_critical(self):
        f = _report_evaluate(C._data())
        self.assertFalse([x for x in _cat(f, 'rbac') if x['severity'] == 'critical'])


class RbacDocxTests(_DocxCase):
    def test_no_security_incident_callout(self):
        d = _data(rbac_risky=[_risky('ServiceAccount', 'ci-runner', 'ci')],
                  pvcs=[{'namespace': 'a', 'name': 'p', 'status': 'Lost'}])
        text = self._text(d)
        self.assertNotIn('보안 사고 가능성이 높습니다', text)
        self.assertIn('바로 지우면 그 컨트롤러가 멈춥니다', text)


# ── 4 · 10. Limit · LimitRange · 메모리 상위 ─────────────────────────────────
class LimitDocxTests(_DocxCase):
    def test_limit_wording_and_limitrange_caveat(self):
        metrics = [{'namespace': 'app', 'name': f'cpu-{i}', 'cpu_m': 1000 - i, 'mem_mi': 10 + i}
                   for i in range(12)]
        metrics.append({'namespace': 'app', 'name': 'mem-hog', 'cpu_m': 1, 'mem_mi': 9000})
        text = self._text(_data(pod_metrics=metrics, limit_ranges=[]))
        self.assertNotIn('Limit 미설정 시 OOMKill', text)
        self.assertIn('Limit 에 도달하는 순간', text)
        for ns in ('kube-system', 'longhorn-system', 'rook-ceph', 'cattle-*', 'cert-manager', 'monitoring'):
            self.assertIn(ns, text)
        self.assertIn('적용하지 마세요', text)
        self.assertIn('mem-hog', text, '메모리 순으로 정렬한 뒤 잘라야 한다')


# ── 5. NetworkPolicy ─────────────────────────────────────────────────────────
class NetworkPolicyDocxTests(_DocxCase):
    def test_cilium_policies_counted(self):
        text = self._text(_data(network_policies=[],
                                cni_network_policies={'CiliumNetworkPolicy': 3}))
        self.assertNotIn('트래픽 제한이 없습니다', text)
        self.assertIn('CiliumNetworkPolicy 3개', text)

    def test_unknown_cni_is_not_zero(self):
        text = self._text(_data(network_policies=[]))          # 키 없음 = 확인하지 않음
        self.assertNotIn('트래픽 제한이 없습니다', text)
        self.assertIn('단정할 수 없습니다', text)
        text = self._text(_data(network_policies=[],
                                cni_network_policies={'CiliumNetworkPolicy': None}), name='b.docx')
        self.assertIn('단정할 수 없습니다', text)

    def test_none_anywhere_and_default_deny_caveat(self):
        text = self._text(_data(network_policies=[], cni_network_policies={}))
        self.assertIn('트래픽 제한이 없습니다', text)
        self.assertIn('DNS(53)', text)
        self.assertIn('한 네임스페이스에서 먼저 시험', text)


class CniCountTests(unittest.TestCase):
    def test_counts_absent_and_unknown(self):
        from src.k8s import K8sManager

        class Err(Exception):
            def __init__(self, status):
                super().__init__(f'HTTP {status}')
                self.status = status

        def lister(group, version, plural, limit):
            if plural == 'ciliumnetworkpolicies':
                return {'items': [{}], 'metadata': {'remainingItemCount': 4}}
            if plural == 'ciliumclusterwidenetworkpolicies':
                return {'items': [], 'metadata': {}}
            if plural == 'networkpolicies':
                raise Err(404)
            raise Err(403)
        mgr = K8sManager()
        mgr.custom = NS(list_cluster_custom_object=lister)
        errs = []
        out = mgr.get_cni_network_policy_counts(errors=errs)
        self.assertEqual(out['CiliumNetworkPolicy'], 5)
        self.assertEqual(out['CiliumClusterwideNetworkPolicy'], 0)
        self.assertNotIn('Calico NetworkPolicy', out)              # CRD 없음
        self.assertIsNone(out['Calico GlobalNetworkPolicy'])       # 확인 불가 ≠ 0
        self.assertEqual(len(errs), 1)


# ── 6. PVC ───────────────────────────────────────────────────────────────────
class PvcTests(unittest.TestCase):
    def test_pending_vs_lost(self):
        f = _cat(_report_evaluate(_data(pvcs=[
            {'namespace': 'a', 'name': 'wait', 'status': 'Pending'},
            {'namespace': 'a', 'name': 'gone', 'status': 'Lost'}])), 'pvc')
        by = {x['name']: x for x in f}
        self.assertIn(by['wait']['severity'], ('low', 'info'))
        self.assertIn('WaitForFirstConsumer', by['wait']['detail'])
        self.assertEqual(by['gone']['severity'], 'critical')
        self.assertIn('삭제하지 마세요', by['gone']['rec'])
        self.assertIn('claimRef', by['gone']['rec'])


class PvcDocxTests(_DocxCase):
    def test_no_safe_delete_advice(self):
        text = self._text(_data(pvcs=[{'namespace': 'a', 'name': 'wait', 'status': 'Pending'},
                                      {'namespace': 'a', 'name': 'gone', 'status': 'Lost'}]))
        self.assertNotIn('안전 삭제', text)
        self.assertNotIn('PV 소실', text)
        self.assertIn('WaitForFirstConsumer', text)
        row = next(l for l in text.splitlines() if l.startswith('a | wait'))
        self.assertNotIn('긴급', row)


# ── 7. PDB ───────────────────────────────────────────────────────────────────
def _pdb(ns, name, curr, desired, allowed, **kw):
    return {'namespace': ns, 'name': name, 'current_healthy': curr, 'desired_healthy': desired,
            'disruptions_allowed': allowed, 'min_available': 1, **kw}


class PdbTests(unittest.TestCase):
    def test_operator_pdbs_are_info(self):
        pdbs = [_pdb('longhorn-system', 'instance-manager-abc', 1, 1, 0),
                _pdb('rook-ceph', 'rook-ceph-osd', 3, 3, 0),
                _pdb('db', 'pg-primary', 1, 1, 0, owners=['Cluster'])]
        f = _cat(_report_evaluate(_data(pdbs=pdbs)), 'pdb')
        self.assertEqual(len(f), 3)
        for x in f:
            self.assertEqual(x['severity'], 'info')
            self.assertIn('수정 · 삭제하지 마세요', x['rec'])
            self.assertNotIn('워크로드 복구 후', x['rec'])

    def test_user_pdb_cause_split(self):
        f = _cat(_report_evaluate(_data(pdbs=[_pdb('app', 'unready', 1, 2, 0),
                                              _pdb('app', 'tight', 2, 2, 0)])), 'pdb')
        by = {x['name']: x for x in f}
        self.assertEqual(by['unready']['severity'], 'medium')
        self.assertEqual(by['tight']['severity'], 'medium')
        self.assertIn('준비된 파드가 부족', by['unready']['detail'])
        self.assertIn('설정상', by['tight']['detail'])


class PdbDocxTests(_DocxCase):
    def test_operator_pdb_callout(self):
        text = self._text(_data(pdbs=[_pdb('longhorn-system', 'instance-manager-abc', 1, 1, 0)]))
        self.assertIn('제품이 관리하는 PDB', text)
        self.assertIn('Longhorn', text)


# ── 8. HPA ───────────────────────────────────────────────────────────────────
def _dep(ns, name, desired, **kw):
    return {'namespace': ns, 'name': name, 'desired': desired, 'ready': desired, **kw}


class HpaTests(unittest.TestCase):
    def test_no_finding_without_user_candidates(self):
        deps = [_dep('kube-system', 'coredns', 2), _dep('cattle-system', 'rancher', 3),
                _dep('app', 'single', 1), _dep('app', 'gitops', 3, argocd=True),
                _dep('app', 'op', 3, owners=['Kafka'])]
        self.assertEqual(_cat(_report_evaluate(_data(deployments=deps, hpa=[])), 'hpa'), [])

    def test_fires_for_user_workload_without_hpa(self):
        deps = [_dep('app', 'api', 3), _dep('app', 'web', 2)]
        hpa = [{'namespace': 'app', 'name': 'web', 'reference': 'Deployment/web'}]
        f = _cat(_report_evaluate(_data(deployments=deps, hpa=hpa)), 'hpa')
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]['value'], '1개')
        self.assertIn('HPA 를 붙이지 마세요', f[0]['rec'])


class HpaDocxTests(_DocxCase):
    def test_sentence_is_data_driven(self):
        deps = [_dep('app', 'api', 3), _dep('app', 'gitops', 3, argocd=True),
                _dep('kube-system', 'coredns', 2)]
        text = self._text(_data(deployments=deps, hpa=[]))
        self.assertNotIn('대부분의 워크로드', text)
        self.assertIn('사용자 Deployment 2개', text)
        self.assertIn('Argo CD가 관리 — HPA 를 붙이지 마세요', text)
        self.assertFalse([l for l in text.splitlines() if l.startswith('kube-system | coredns')])


# ── 9. TLS ───────────────────────────────────────────────────────────────────
class TlsDocxTests(_DocxCase):
    def test_tls_from_spec(self):
        ing = [{'namespace': 'a', 'name': 'secure', 'class': 'nginx', 'hosts': 'a.com',
                'address': '1.2.3.4', 'tls': ['a-tls']}]
        text = self._text(_data(ingresses=ing, namespaces=[{'name': 'cert-manager'}]))
        self.assertNotIn('TLS 설정이 없는 Ingress', text)
        self.assertNotIn('HTTPS 미적용', text)
        self.assertIn('cert-manager 네임스페이스가 있습니다', text)
        self.assertNotIn('운영 중입니다', text)

    def test_missing_tls_flagged_only_when_known(self):
        ing = [{'namespace': 'a', 'name': 'plain', 'class': 'nginx', 'hosts': 'a.com',
                'address': '1.2.3.4', 'tls': []}]
        self.assertIn('TLS 설정이 없는 Ingress 1개', self._text(_data(ingresses=ing)))
        old = [{'namespace': 'a', 'name': 'plain', 'class': 'nginx', 'hosts': 'a.com',
                'address': '1.2.3.4'}]
        self.assertNotIn('TLS 설정이 없는 Ingress', self._text(_data(ingresses=old), name='o.docx'))

    def test_get_ingresses_tls_field_is_opt_in(self):
        import src.k8s as km
        from src.k8s import K8sManager
        ing = NS(metadata=NS(name='i', namespace='a', creation_timestamp=None),
                 spec=NS(rules=[NS(host='a.com')], ingress_class_name='nginx',
                         tls=[NS(secret_name='a-tls', hosts=['a.com'])]),
                 status=NS(load_balancer=None))
        mgr = K8sManager()
        mgr.net = NS(list_ingress_for_all_namespaces=lambda **kw: NS(items=[ing]))
        self.assertNotIn('tls', mgr.get_ingresses(None)[0])
        self.assertEqual(mgr.get_ingresses(None, tls=True)[0]['tls'], ['a-tls'])


# ── 11. StorageClass ─────────────────────────────────────────────────────────
class StorageClassTests(unittest.TestCase):
    def test_text(self):
        f = _cat(_report_evaluate(_data(storage_classes=[{'name': 'nfs', 'is_default': 'false'}])),
                 'storageclass')
        self.assertNotIn('동적 PVC 프로비저닝 불가', f[0]['detail'])
        self.assertIn('storageClassName 을 적지 않은 PVC 는 프로비저닝되지 않습니다', f[0]['detail'])
        self.assertIn('정적 PV 대신 새 볼륨이 만들어질 수 있습니다', f[0]['detail'])


# ── 12. NodePort ─────────────────────────────────────────────────────────────
class NodePortTests(unittest.TestCase):
    SVCS = [{'namespace': 'ingress-nginx', 'name': 'ingress-nginx-controller', 'type': 'NodePort',
             'ports': '80:30080/TCP'},
            {'namespace': 'app', 'name': 'api', 'type': 'NodePort', 'ports': '80:32000/TCP'}]

    def test_no_port_list_and_controller_excluded(self):
        by = {x['name']: x for x in _cat(_report_evaluate(_data(services=self.SVCS)), 'nodeport')}
        self.assertEqual(by['api']['severity'], 'medium')      # 32000 이라고 높음이 되지 않는다
        self.assertEqual(by['ingress-nginx-controller']['severity'], 'info')
        self.assertIn('전환할 대상이 아닙니다', by['ingress-nginx-controller']['rec'])


class NodePortDocxTests(_DocxCase):
    def test_docx_uses_evaluator_severity(self):
        text = self._text(_data(services=NodePortTests.SVCS))
        row = next(l for l in text.splitlines() if l.startswith('app | api'))
        self.assertIn('중간', row)
        self.assertNotIn('높음', row)
        self.assertNotIn('민감 서비스', text)


# ── 13. 재시작 ───────────────────────────────────────────────────────────────
class RestartTests(unittest.TestCase):
    def test_stale_restarts_lowered(self):
        pods = [{'namespace': 'a', 'name': 'old', 'status': 'Running', 'restarts': '1500',
                 'restarted_at': _iso(30)},
                {'namespace': 'a', 'name': 'new', 'status': 'Running', 'restarts': '1500',
                 'restarted_at': _iso(1)},
                {'namespace': 'a', 'name': 'unknown', 'status': 'Running', 'restarts': '1500'}]
        by = {x['name']: x for x in _cat(_report_evaluate(_data(pods=pods)), 'pod_restart')}
        self.assertEqual(by['old']['severity'], 'low')
        self.assertIn('최근 7일 동안 재시작이 없습니다', by['old']['detail'])
        self.assertEqual(by['new']['severity'], 'critical')
        self.assertEqual(by['unknown']['severity'], 'critical')


class RestartDocxTests(_DocxCase):
    def test_docx_same_thresholds(self):
        pods = [{'namespace': 'a', 'name': 'few', 'status': 'Running', 'restarts': '8'},
                {'namespace': 'a', 'name': 'stale', 'status': 'Running', 'restarts': '300',
                 'restarted_at': _iso(20)}]
        text = self._text(_data(pods=pods))
        rows = text.splitlines()          # _docx_text 는 문단 뒤에 표 행을 「a | b | …」 로 붙인다
        self.assertFalse([l for l in rows if l.startswith('a | few')],
                         '10회 이하는 발견 사항에도 없다 — 표에도 없어야 한다')
        row = next(l for l in rows if l.startswith('a | stale'))
        self.assertIn('낮음', row)
        self.assertNotIn('긴급', row)


# ── 표 폭 불변식 — 새로 넣은 표 · 열도 16.5cm ────────────────────────────────
class TableWidthTests(_DocxCase):
    def test_rich_report_tables_sum_to_16_5(self):
        from docx import Document
        d = _data(
            pods=[{'namespace': 'app', 'name': 'w', 'status': 'Running', 'reason': 'CrashLoopBackOff',
                   'restarts': '300', 'restarted_at': _iso(1)},
                  {'namespace': 'kube-system', 'name': 'k', 'status': 'Failed', 'reason': 'Error'}],
            deployments=[_dep('app', 'api', 3)], hpa=[],
            pdbs=[_pdb('longhorn-system', 'instance-manager-a', 1, 1, 0)],
            pvcs=[{'namespace': 'a', 'name': 'gone', 'status': 'Lost'}],
            services=NodePortTests.SVCS,
            ingresses=[{'namespace': 'a', 'name': 'i', 'class': 'nginx', 'hosts': 'a.com', 'tls': []}],
            rbac_risky=[_risky('ServiceAccount', 'ci', 'ci')],
            collect_errors=['events'],
        )
        self._text(d)
        doc = Document(self.last_path)
        for i, t in enumerate(doc.tables):
            total = sum((c.width.cm if c.width else 0) for c in t.rows[0].cells)
            self.assertAlmostEqual(total, 16.5, places=2, msg=f'표 #{i} 폭 합 {total}cm')


if __name__ == '__main__':
    unittest.main()
