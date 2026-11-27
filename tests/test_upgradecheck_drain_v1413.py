# -*- coding: utf-8 -*-
"""업그레이드 사전 점검 — 노드 비우기(drain) 안내를 섣불리 하지 않는다 (v1.4.13).

실제 RKE2 1.31 클러스터 점검에서 Longhorn 이 만든 instance-manager PDB(허용 중단 0) 에
「복제본을 늘리거나 PDB 를 잠시 조정하세요」 가 나왔다. 그대로 하면 볼륨의 하나 남은 복제본이 있는
노드를 비울 수 있다. 이 파일이 잠그는 것:
  1) PDB 를 누가 관리하는지(Longhorn · Rook · 다른 오퍼레이터 · 직접) 나눠 안내 — 오퍼레이터 것은 「고치지 마세요」
  2) Longhorn PDB 만 있으면 「주의」 가 아니다(평소 상태) — 대신 업그레이드 순서에 볼륨 상태 확인
  3) 직접 만든 PDB 가 0 이면 원인(준비 안 된 파드 · 설정)을 나눠 적는다
  4) 복제본 1개 워크로드 중 StatefulSet · 볼륨 사용 · Recreate 는 「늘리지 마세요」
"""
import unittest

from src import upgradecheck as U


def _data(pdbs=(), workloads=()):
    return {'version': 'v1.31.5+rke2r1', 'cur_minor': 31, 'target_minor': 32,
            'nodes': [{'name': f'n{i}', 'kubelet': 'v1.31.5+rke2r1', 'runtime': 'containerd://1.7', 'ready': True,
                       'unschedulable': False} for i in range(3)],
            'pods': [], 'pdbs': list(pdbs), 'workloads': list(workloads), 'helm': [], 'images': [],
            'metrics_ok': True, 'readyz': '[+]ping ok'}


def _pdb(ns, name, allowed=0, expected=1, healthy=1, desired=1, labels=None, owners=()):
    return {'namespace': ns, 'name': name, 'allowed': allowed, 'expected': expected, 'healthy': healthy,
            'desired': desired, 'labels': labels or {}, 'owners': list(owners)}


def _find(res, word):
    return [f for f in res['findings'] if word in f['title']]


class DrainTests(unittest.TestCase):
    def test_Longhorn_PDB_는_고치라고_하지_않는다(self):
        res = U.evaluate(_data([_pdb('longhorn-system', f'instance-manager-{i}') for i in range(3)]))
        lh = _find(res, 'Longhorn')
        self.assertEqual(len(lh), 1)
        f = lh[0]
        self.assertEqual(f['severity'], 'info')
        self.assertIn('직접 고치지 마세요', f['title'])
        self.assertNotIn('PDB 를 잠시 조정', f['detail'] + f['action'])
        self.assertIn('Healthy', f['action'])
        self.assertEqual(res['verdict'], 'ready')            # 평소 상태라 「주의」 가 아니다
        self.assertTrue(any('Longhorn' in s for s in res['checklist']))
        self.assertFalse(_find(res, '노드 비우기를 멈추게 할'))

    def test_관리자_구분(self):
        self.assertEqual(U.pdb_manager(_pdb('rook-ceph', 'rook-ceph-osd-0')), 'rook')
        self.assertEqual(U.pdb_manager(_pdb('db', 'pg', owners=['PostgresCluster'])), 'operator')
        self.assertEqual(U.pdb_manager(_pdb('app', 'web', labels={'app.kubernetes.io/managed-by': 'Helm'})), 'user')
        self.assertEqual(U.pdb_manager(_pdb('app', 'web')), 'user')
        self.assertEqual(U.pdb_manager(_pdb('brookfield', 'web')), 'user')

    def test_직접_만든_PDB_는_원인을_나눈다(self):
        res = U.evaluate(_data([_pdb('app', 'web', healthy=1, desired=2), _pdb('app', 'api')]))
        f = _find(res, '노드 비우기를 멈추게 할')[0]
        self.assertEqual(f['severity'], 'warn')
        self.assertIn('준비되지 않은 파드', f['detail'])
        self.assertIn('설정상', f['detail'])
        self.assertIn('담당자', f['action'])
        self.assertIn('원래대로 되돌리세요', f['action'])

    def test_복제본_1개_중_늘리면_안_되는_것(self):
        res = U.evaluate(_data(workloads=[
            {'kind': 'StatefulSet', 'namespace': 'kong', 'name': 'kong-postgresql', 'replicas': 1, 'pvc': True},
            {'kind': 'Deployment', 'namespace': 'shop-api', 'name': 'minio', 'replicas': 1, 'pvc': True},
            {'kind': 'Deployment', 'namespace': 'argocd', 'name': 'argocd-server', 'replicas': 1},
            {'kind': 'Deployment', 'namespace': 'cattle-system', 'name': 'rancher-webhook', 'replicas': 1, 'managed': True},
        ]))
        f = _find(res, '복제본이 1개')[0]
        items = '\n'.join(f['items'])
        self.assertIn('kong/kong-postgresql — 늘리지 마세요(StatefulSet · 볼륨 사용)', items)
        self.assertIn('shop-api/minio — 늘리지 마세요(볼륨 사용)', items)
        self.assertIn('argocd/argocd-server', items)
        self.assertNotIn('argocd-server — 늘리지', items)
        self.assertIn('오퍼레이터가 관리', items)
        self.assertIn('2개는 단일 DB', f['detail'])

    def test_모으기_요약(self):
        p = U._pdb_brief({'metadata': {'namespace': 'longhorn-system', 'name': 'instance-manager-x',
                                       'ownerReferences': [{'kind': 'InstanceManager'}]},
                          'spec': {'minAvailable': 1},
                          'status': {'disruptionsAllowed': 0, 'expectedPods': 1, 'currentHealthy': 1, 'desiredHealthy': 1}})
        self.assertEqual((p['allowed'], p['owners'], p['min_available']), (0, ['InstanceManager'], 1))
        w = U._workload_brief({'metadata': {'namespace': 'a', 'name': 'b'},
                               'spec': {'replicas': 1, 'strategy': {'type': 'Recreate'},
                                        'template': {'spec': {'volumes': [{'name': 'd', 'persistentVolumeClaim': {'claimName': 'x'}}]}}}},
                              'Deployment')
        self.assertTrue(w['pvc'] and w['recreate'])
        self.assertFalse(w['managed'])


class OtherJudgmentTests(unittest.TestCase):
    """v1.4.13 — 업그레이드 사전 점검의 다른 섣부른 판정"""

    def test_cri_dockerd_는_막지_않는다(self):
        d = _data()
        d['nodes'][0]['runtime'] = 'docker://24.0.7'                 # kubelet 1.31 — 이미 cri-dockerd
        res = U.evaluate(d)
        self.assertFalse([f for f in res['findings'] if f['severity'] == 'block'])
        self.assertTrue(_find(res, 'cri-dockerd'))
        d['nodes'][1].update(kubelet='v1.23.17', runtime='docker://20.10.7')   # 이 노드는 dockershim
        res = U.evaluate(d)
        self.assertEqual(_find(res, 'Docker 엔진')[0]['severity'], 'block')

    def test_kubelet_차이_안내는_API_서버_버전_이하로(self):
        d = _data()
        d['cur_minor'], d['target_minor'] = 31, 32
        d['nodes'][0]['kubelet'] = 'v1.28.9'
        f = _find(U.evaluate(d), '차이가 큰 노드')[0]
        self.assertIn('1.31) 이하로', f['detail'])

    def test_API_지표_통과는_범위를_밝힌다(self):
        res = U.evaluate(_data())
        self.assertTrue(any('인스턴스가 시작된 뒤 기준' in p for p in res['passed']))

    def test_readyz_500_본문을_판정에_쓴다(self):
        class E(Exception):
            status, body = 500, b'[+]ping ok\n[-]etcd failed: reason withheld\nreadyz check failed'

        class Api:
            def call_api(self, *a, **k):
                raise E()
        orig = U._get
        U._get = lambda api, path, **k: (_ for _ in ()).throw(E()) if path == '/readyz' else orig(api, path, **k)
        try:
            data, errors = {}, []
            try:
                data['readyz'] = U._get(Api(), '/readyz')
            except Exception as e:
                body = e.body.decode() if isinstance(e.body, bytes) else e.body
                data['readyz'] = body if '[-]' in body else None
        finally:
            U._get = orig
        d = _data()
        d['readyz'] = data['readyz']
        self.assertEqual(_find(U.evaluate(d), 'readyz')[0]['severity'], 'block')
        src = open(U.__file__, encoding='utf-8').read()
        self.assertIn("'[-]' in str(body)", src)


if __name__ == '__main__':
    unittest.main()
