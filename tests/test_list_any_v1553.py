# -*- coding: utf-8 -*-
"""MCP polaris_list_resources — CRD · 단수 표기를 조용히 0건으로 돌려주던 것 (v1.5.53, 사용자 신고).

신고: Claude 가 9개 클러스터의 HelmChartConfig 를 목록으로 보고 「모두 없음」 이라 했는데, 이름으로 직접 보니 있었다.
원인: 목록은 화면용 표(K8sClient.GETTERS 15종)에 없는 종류를 **오류 없이 []** 로 돌려줬다.
재현(2026-11-19, 사내 실험 클러스터 localtest = srv-4 RKE2): list addons.k3s.cattle.io → count 0,
get addons.k3s.cattle.io rke2-canal → 있음. 아래 JSON 은 같은 서버에서 kubectl 로 받은 실제 출력(줄임).
"""
import json
import unittest
from unittest import mock

from src.api import resources as R

REAL_ADDONS = {'apiVersion': 'v1', 'kind': 'List', 'items': [
    {'apiVersion': 'k3s.cattle.io/v1', 'kind': 'Addon',
     'metadata': {'creationTimestamp': '2026-08-13T08:39:43Z', 'name': 'rke2-canal', 'namespace': 'kube-system'},
     'spec': {'checksum': 'a231fb6b', 'source': '/var/lib/rancher/rke2/server/manifests/rke2-canal.yaml'}},
    {'apiVersion': 'k3s.cattle.io/v1', 'kind': 'Addon',
     'metadata': {'creationTimestamp': '2026-08-13T08:39:45Z', 'name': 'rke2-ingress-nginx', 'namespace': 'kube-system'},
     'spec': {'checksum': '561e3eee', 'source': '/var/lib/rancher/rke2/server/manifests/rke2-ingress-nginx.yaml'}},
]}
EMPTY = {'apiVersion': 'v1', 'kind': 'List', 'items': []}


class _K8s:
    kubeconfig = 'kc.yaml'
    GETTERS = {'pods': None, 'deployments': None, 'secrets': None, 'pvcs': None}


class _Api(R.ResourcesMixin):
    def __init__(self):
        self.k8s = _K8s()
        self.calls = []

    def get_resource(self, rtype, ns=''):
        self.calls.append(('api', rtype, ns))
        return [{'name': 'p1'}]


def fake_kubectl(kc, args, timeout=30):
    kind = args[1]
    if kind == 'addons.k3s.cattle.io':
        return json.dumps(REAL_ADDONS), ''
    if kind == 'helmchartconfigs':
        return json.dumps(EMPTY), ''
    if kind == 'secrets.v1.':
        return json.dumps({'items': [{'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': 's', 'namespace': 'a'},
                                      'data': {'password': 'c2VjcmV0'}}]}), ''
    return '', f'error: the server doesn\'t have a resource type "{kind}"'


class ListAny(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(R, '_run_kubectl', fake_kubectl)
        p.start()
        self.addCleanup(p.stop)
        self.api = _Api()

    def test_CRD_를_0건으로_돌려주지_않는다(self):
        r = self.api.list_resources_any('addons.k3s.cattle.io', '')
        self.assertTrue(r['ok'])
        self.assertEqual([x['name'] for x in r['items']], ['rke2-canal', 'rke2-ingress-nginx'])
        self.assertEqual(r['items'][0], {'name': 'rke2-canal', 'namespace': 'kube-system', 'kind': 'Addon',
                                         'apiVersion': 'k3s.cattle.io/v1', 'created': '2026-08-13T08:39:43Z'})
        self.assertEqual(r['via'], 'kubectl')

    def test_정말_없으면_0건(self):
        r = self.api.list_resources_any('helmchartconfigs', 'kube-system')
        self.assertTrue(r['ok'])
        self.assertEqual(r['items'], [])

    def test_모르는_종류는_오류(self):
        r = self.api.list_resources_any('nosuchkinds', '')
        self.assertFalse(r['ok'], '0건으로 보이면 「없다」 고 오판한다')
        self.assertIn('종류가 없습니다', r['error'])

    def test_단수_줄임_표기는_화면_목록으로(self):
        for k, want in (('deployment', 'deployments'), ('Deploy', 'deployments'), ('pod', 'pods'), ('pvc', 'pvcs'), ('pods', 'pods')):
            r = self.api.list_resources_any(k, 'ns1')
            self.assertEqual(r['kind'], want, k)
            self.assertEqual(r['via'], 'api')

    def test_다른_표기의_Secret_도_값은_안_싣는다(self):
        r = self.api.list_resources_any('secrets.v1.', '')
        self.assertTrue(r['ok'])
        self.assertNotIn('data', json.dumps(r))
        self.assertNotIn('c2VjcmV0', json.dumps(r))

    def test_이상한_종류는_kubectl_로_보내지_않는다(self):
        r = self.api.list_resources_any('pods; rm -rf /', '')
        self.assertFalse(r['ok'])
        r = self.api.list_resources_any('x', '../etc')
        self.assertFalse(r['ok'])


class McpTool(unittest.TestCase):
    def test_MCP_가_오류를_그대로_넘긴다(self):
        from src import mcp_server as M

        class _A:
            def list_resources_any(s, kind, ns):
                return {'ok': False, 'error': '이 클러스터에 「x」 종류가 없습니다'} if kind == 'x' else \
                       {'ok': True, 'kind': kind, 'items': [{'name': 'a'}], 'note': '메타데이터만'}
        with mock.patch.object(M, '_get_api', lambda: _A()), \
             mock.patch.object(M, '_ensure_unlocked', lambda api: (True, None)), \
             mock.patch.object(M, '_resolve_cluster', lambda api, c: (True, None)), \
             mock.patch.object(M, '_active_kc', lambda api: 'c1'):
            bad = M._tool_list_resources({'kind': 'x'})
            good = M._tool_list_resources({'kind': 'helmchartconfigs'})
        self.assertFalse(bad['ok'])
        self.assertIn('종류가 없습니다', bad['error'])
        self.assertEqual((good['count'], good['note']), (1, '메타데이터만'))
        desc = {t.name: t for t in M._tool_defs()}['polaris_list_resources'].inputSchema['properties']['kind']['description']
        self.assertIn('helmchartconfigs', desc)


if __name__ == '__main__':
    unittest.main()
