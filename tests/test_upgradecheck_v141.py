# -*- coding: utf-8 -*-
"""K8s 업그레이드 사전 점검 (v1.4.1) — src/upgradecheck.py · src/api/upgradecheck.py.

잠그는 것(가짜 API 서버로 실제 수집 경로를 돌린다):
  · 사라지는 API — API 서버 지표 · managedFields · kubectl last-applied · Helm 최신 리비전 매니페스트
  · 지표의 removed_release 가 이번 경로 밖이면 「참고」 로만
  · 여러 단계 건너뛰기 · kubelet 3단계 차이 · Docker 런타임(1.24+) · NotReady · readyz 실패 · 노드 1대
  · drain 방해: 허용 중단 0 PDB · 단독 파드(미러 파드 제외) · 복제본 1 · emptyDir
  · Helm 을 못 읽으면(403) 「문제 없음」 으로 말하지 않는다
  · GET 만 한다(가짜 클라이언트가 GET 외 요청을 거부)
  · 실제 srv-4 RKE2(v1.35.7) 응답으로도 확인했다 — 개인 정보가 섞일 수 있어 고정 자료로는 넣지 않았다
"""
import base64
import gzip
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src import upgradecheck as UC


def helm_secret(manifest, name='app', chart='demo', ver='1.0.0'):
    rel = {'name': name, 'manifest': manifest, 'chart': {'metadata': {'name': chart, 'version': ver}}}
    inner = base64.b64encode(gzip.compress(json.dumps(rel).encode())).decode()
    return {'data': {'release': base64.b64encode(inner.encode()).decode()}}


def node(name, kubelet, ready=True, runtime='containerd://1.7.0', cp=False):
    return {'metadata': {'name': name, 'labels': {'node-role.kubernetes.io/control-plane': 'true'} if cp else {}},
            'status': {'nodeInfo': {'kubeletVersion': kubelet, 'containerRuntimeVersion': runtime, 'osImage': 'Ubuntu'},
                       'conditions': [{'type': 'Ready', 'status': 'True' if ready else 'False'}]}}


def pod(ns, name, owner='ReplicaSet', mirror=False, emptydir=False, phase='Running', ready=True, image='nginx:1.25'):
    md = {'namespace': ns, 'name': name}
    if owner:
        md['ownerReferences'] = [{'kind': owner}]
    if mirror:
        md['annotations'] = {'kubernetes.io/config.mirror': 'x'}
    return {'metadata': md, 'spec': {'nodeName': 'n1', 'containers': [{'image': image}],
                                     'volumes': [{'name': 'tmp', 'emptyDir': {}}] if emptydir else []},
            'status': {'phase': phase, 'containerStatuses': [{'ready': ready}]}}


class _E(Exception):
    def __init__(self, status):
        self.status = status


class _R:
    def __init__(self, data):
        self.data = data if isinstance(data, bytes) else data.encode()

    def release_conn(self):
        pass


class FakeAPI:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def call_api(self, path, method, query_params=None, **kw):
        assert method == 'GET', '사전 점검은 조회만 한다'
        self.calls.append(path)
        v = self.routes.get(path)
        if v is None:
            raise _E(404)
        if isinstance(v, Exception):
            raise v
        return _R(v if isinstance(v, (str, bytes)) else json.dumps(v))


class K:
    kubeconfig = 'x'

    def __init__(self, routes):
        self._api_client = FakeAPI(routes)


def old_cluster():
    """1.24 클러스터 — 1.25/1.26 에서 사라지는 것을 곳곳에 심어 둔다"""
    cj = {'metadata': {'namespace': 'batch', 'name': 'nightly',
                       'managedFields': [{'manager': 'argocd', 'apiVersion': 'batch/v1beta1'}]}}
    hpa = {'metadata': {'namespace': 'web', 'name': 'web',
                        'annotations': {'kubectl.kubernetes.io/last-applied-configuration':
                                        json.dumps({'apiVersion': 'autoscaling/v2beta2', 'kind': 'HorizontalPodAutoscaler'})}}}
    manifest = ('---\napiVersion: policy/v1beta1\nkind: PodDisruptionBudget\nmetadata:\n  name: app-pdb\n'
                '---\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app\n')
    return {
        '/version': {'gitVersion': 'v1.24.17'},
        '/api/v1/nodes': {'items': [node('cp1', 'v1.24.17', cp=True), node('w1', 'v1.21.14', runtime='docker://20.10.7'),
                                    node('w2', 'v1.24.17', ready=False)]},
        '/readyz': '[+]ping ok\n[-]etcd failed: reason withheld\nreadyz check failed\n',
        '/metrics': ('# HELP x\napiserver_requested_deprecated_apis{group="batch",removed_release="1.25",resource="cronjobs",'
                     'subresource="",version="v1beta1"} 1\n'
                     'apiserver_requested_deprecated_apis{group="",removed_release="",resource="endpoints",subresource="",version="v1"} 1\n'
                     'apiserver_requested_deprecated_apis{group="x.io",removed_release="1.30",resource="things",subresource="",version="v1beta1"} 1\n'),
        '/apis/batch/v1/cronjobs': {'items': [cj]},
        '/apis/autoscaling/v2/horizontalpodautoscalers': {'items': [hpa]},
        '/api/v1/secrets': {'items': [
            {'metadata': {'namespace': 'web', 'name': 'sh.helm.release.v1.app.v1', 'labels': {'name': 'app', 'version': '1', 'status': 'superseded'}}},
            {'metadata': {'namespace': 'web', 'name': 'sh.helm.release.v1.app.v2', 'labels': {'name': 'app', 'version': '2', 'status': 'deployed'}}},
        ]},
        '/api/v1/namespaces/web/secrets/sh.helm.release.v1.app.v2': helm_secret(manifest),
        '/apis/policy/v1/poddisruptionbudgets': {'items': [
            {'metadata': {'namespace': 'db', 'name': 'pg'}, 'status': {'disruptionsAllowed': 0, 'expectedPods': 1}},
            {'metadata': {'namespace': 'web', 'name': 'ok'}, 'status': {'disruptionsAllowed': 1, 'expectedPods': 3}}]},
        '/api/v1/pods': {'items': [
            pod('default', 'debug', owner=None), pod('kube-system', 'kube-apiserver-cp1', owner=None, mirror=True),
            pod('web', 'cache-1', emptydir=True), pod('kube-system', 'coredns-x', ready=False, image='rancher/hardened-coredns:v1.11.1'),
            pod('ingress', 'ctl', image='registry.k8s.io/ingress-nginx/controller:v1.9.4')]},
        '/apis/apps/v1/deployments': {'items': [{'metadata': {'namespace': 'web', 'name': 'api'}, 'spec': {'replicas': 1}},
                                                {'metadata': {'namespace': 'kube-system', 'name': 'coredns'}, 'spec': {'replicas': 1}}]},
        '/apis/apps/v1/statefulsets': {'items': []},
        '/apis/apiextensions.k8s.io/v1/customresourcedefinitions': {'items': [
            {'metadata': {'name': 'widgets.x.io'}, 'spec': {'versions': [
                {'name': 'v1beta1', 'served': True, 'deprecated': True}, {'name': 'v1', 'served': True, 'storage': True}]}}]},
    }


class OldClusterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = K(old_cluster())
        cls.data = UC.collect(cls.k, '1.26')
        cls.r = UC.evaluate(cls.data)
        cls.by = {f['title']: f for f in cls.r['findings']}

    def find(self, word, sev=None):
        hits = [f for t, f in self.by.items() if word in t and (sev is None or f['severity'] == sev)]
        self.assertTrue(hits, f'{word} ({sev}) 가 없다: {list(self.by)}')
        return hits[0]

    def test_판정은_막힘(self):
        self.assertEqual(self.r['verdict'], 'blocked')
        self.assertEqual(self.r['findings'][0]['severity'], 'block', '먼저 해결이 맨 위')

    def test_두_단계(self):
        f = self.find('한 단계씩', 'warn')
        self.assertEqual(f['items'], ['1.24 → 1.25', '1.25 → 1.26'])

    def test_지표_요청_기록(self):
        f = self.find('요청한 기록', 'block')
        self.assertEqual(f['items'], ['batch/v1beta1 cronjobs — 1.25 에서 제거'])
        later = self.find('권장하지 않는 API 요청', 'info')
        self.assertTrue(any('endpoints — 제거 일정 없음' in x for x in later['items']))
        self.assertTrue(any('1.30 에서 제거 예정' in x for x in later['items']))

    def test_써_넣은_흔적(self):
        f = self.find('작성된 오브젝트', 'warn')
        joined = '\n'.join(f['items'])
        self.assertIn('CronJob batch/nightly — batch/v1beta1 (managedFields, argocd)', joined)
        self.assertIn('HorizontalPodAutoscaler web/web — autoscaling/v2beta2 (kubectl apply)', joined)

    def test_helm_최신_리비전만(self):
        f = self.find('Helm 릴리스가', 'block')
        self.assertEqual(len(f['items']), 1)
        self.assertIn('PodDisruptionBudget app-pdb: policy/v1beta1 → policy/v1', f['items'][0])
        self.assertNotIn('/api/v1/namespaces/web/secrets/sh.helm.release.v1.app.v1', self.k._api_client.calls)

    def test_버전_차이_런타임(self):
        self.assertIn('w1 — kubelet v1.21.14', self.find('차이가 큰 노드', 'block')['items'])
        self.assertIn('w1 — docker://20.10.7', self.find('Docker 엔진', 'block')['items'])
        self.assertIn('섞여', ' '.join(self.by))

    def test_지금_상태(self):
        self.assertEqual(self.find('NotReady', 'block')['items'], ['w2'])
        self.assertTrue(any('etcd failed' in x for x in self.find('readyz', 'block')['items']))
        self.assertTrue(any('coredns' in x for x in self.find('kube-system 파드', 'warn')['items']))

    def test_drain_방해(self):
        self.assertEqual(self.find('PodDisruptionBudget', 'warn')['items'], ['db/pg (허용 중단 0 · 파드 1)'])
        self.assertEqual(self.find('컨트롤러 없이', 'warn')['items'], ['default/debug'], '미러(스태틱) 파드는 뺀다')
        self.assertEqual(self.find('복제본이 1개', 'info')['items'], ['Deployment web/api'], 'kube-system 은 뺀다')
        self.assertEqual(self.find('emptyDir', 'info')['items'], ['web/cache-1'])

    def test_crd_애드온(self):
        self.assertIn('widgets.x.io', self.find('CRD', 'info')['items'][0])
        add = '\n'.join(self.find('애드온', 'info')['items'])
        self.assertIn('ingress-nginx — v1.9.4', add)
        self.assertIn('CoreDNS — v1.11.1', add)

    def test_순서_안내(self):
        self.assertTrue(any('etcdctl snapshot' in t for t in self.r['checklist']))


class EdgeTests(unittest.TestCase):
    def test_정상_클러스터_한단계(self):
        routes = {'/version': {'gitVersion': 'v1.35.7+rke2r1'},
                  '/api/v1/nodes': {'items': [node('a', 'v1.35.7+rke2r1', cp=True), node('b', 'v1.35.7+rke2r1')]},
                  '/readyz': '[+]ping ok\nreadyz check passed\n', '/metrics': '',
                  '/api/v1/secrets': {'items': []}, '/api/v1/pods': {'items': [pod('kube-system', 'x', image='rancher/hardened-coredns:v1.14')]},
                  '/apis/policy/v1/poddisruptionbudgets': {'items': []}, '/apis/apps/v1/deployments': {'items': []},
                  '/apis/apps/v1/statefulsets': {'items': []}, '/apis/apiextensions.k8s.io/v1/customresourcedefinitions': {'items': []}}
        r = UC.evaluate(UC.collect(K(routes), '1.36'))
        self.assertEqual(r['verdict'], 'ready', r['findings'])
        self.assertTrue(r['rke2'])
        self.assertTrue(any('rke2 etcd-snapshot' in t for t in r['checklist']))
        self.assertTrue(any('API 서버 지표' in p for p in r['passed']))
        self.assertTrue(any('Helm 릴리스 0개' in p for p in r['passed']))

    def test_helm_못_읽으면_문제없다고_말하지_않는다(self):
        routes = old_cluster()
        routes['/api/v1/secrets'] = _E(403)
        r = UC.evaluate(UC.collect(K(routes), '1.25'))
        self.assertFalse(any('Helm 릴리스' in p for p in r['passed']))
        scope = next(f for f in r['findings'] if f['category'] == 'scope')
        self.assertTrue(any('권한 없음(403)' in x for x in scope['items']))

    def test_노드_1대(self):
        routes = {'/version': {'gitVersion': 'v1.30.1'}, '/api/v1/nodes': {'items': [node('solo', 'v1.30.1', cp=True)]}}
        r = UC.evaluate(UC.collect(K(routes), '1.31'))
        self.assertTrue(any(f['title'] == '노드가 1대뿐입니다' for f in r['findings']))

    def test_도구(self):
        self.assertEqual(UC.minor_of('v1.35.7+rke2r1'), (1, 35))
        self.assertIsNone(UC.minor_of('abc'))
        self.assertEqual({r[2] for r in UC.removed_between(24, 25)} >= {'CronJob', 'PodDisruptionBudget'}, True)
        self.assertEqual(UC.removed_between(32, 36), [])
        self.assertEqual(UC.manifest_kinds('apiVersion: v1\nkind: Service\nmetadata:\n  labels:\n    a: b\n  name: svc\n'),
                         [('v1', 'Service', 'svc')])
        self.assertIsNone(UC.decode_helm_release('###'))

    def test_api_mixin(self):
        from src.api.upgradecheck import UpgradeCheckMixin

        class A(UpgradeCheckMixin):
            k8s = K(old_cluster())
        a = A()
        v = a.upgrade_check_versions()
        self.assertEqual(v['minor'], '1.24')
        self.assertEqual([t['value'] for t in v['targets']], ['1.25', '1.26', '1.27'])
        self.assertIn('권장', v['targets'][0]['label'])
        self.assertFalse(a.upgrade_check('')['ok'])
        r = a.upgrade_check('1.25')
        self.assertTrue(r['ok'])
        self.assertEqual(r['target'], '1.25')

        class B(UpgradeCheckMixin):
            class k8s:
                kubeconfig = None
        self.assertFalse(B().upgrade_check('1.25')['ok'])

    def test_보고서(self):
        from docx import Document
        from src.api.upgradecheck import UpgradeCheckMixin
        tmp = Path(tempfile.mkdtemp(prefix='polaris-upg-'))
        self.addCleanup(shutil.rmtree, tmp, True)

        class A(UpgradeCheckMixin):
            k8s = K(old_cluster())
            def _cluster_label(self, fallback=''): return 'prod/east'
        a = A()
        self.assertFalse(a.upgrade_check_save(str(tmp / 'x.docx'))['ok'], '점검 전에는 거절')
        a.upgrade_check('1.26')
        self.assertEqual(a.upgrade_check_filename()[:23], 'Polaris-upgrade-check-p')
        self.assertNotIn('/', a.upgrade_check_filename(), '파일 이름에 못 쓰는 글자는 뺀다')
        r = a.upgrade_check_save(str(tmp / 'u.docx'))
        self.assertTrue(r['ok'], r)
        doc = Document(r['path'])
        text = '\n'.join(p.text for p in doc.paragraphs)
        cells = [c.text for t in doc.tables for row in t.rows for c in row.cells]
        for h in ('1. 점검 요약', '2. 발견사항', '3. 확인 완료', '4. 업그레이드 순서', '부록. 점검 방법과 기준'):
            self.assertIn(h, text)
        self.assertIn('먼저 해결', cells)
        self.assertIn('1.24 → 1.25 → 1.26', cells)
        self.assertIn('batch/v1beta1', cells, '이번 경로에서 제거되는 API 표')
        self.assertIn('prod/east', cells)
        self.assertTrue(any('판정: 업그레이드 전에 먼저 해결해야 할 문제' in x for x in cells + text.split('\n')))

    def test_코어_등록(self):
        from src.api import _CORE_MODULE_NAMES, PolarisAPI
        self.assertIn('upgradecheck', _CORE_MODULE_NAMES)
        self.assertTrue(hasattr(PolarisAPI, 'upgrade_check'))


if __name__ == '__main__':
    unittest.main()
