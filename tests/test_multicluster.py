# -*- coding: utf-8 -*-
"""멀티클러스터 집계(BaseMixin.get_multicluster_summary) 테스트 — 클러스터 불필요.

가짜 매니저를 _clusters 에 주입해 병렬 집계·합계·정렬·오류 처리를 검증한다.
(각 매니저의 get_nodes/get_pods 는 기존 검증된 메서드라 여기선 대역으로 대체)
"""
import unittest


class _FakeMgr:
    def __init__(self, connected, nodes, pods, raise_on=None):
        self.connected = connected
        self._nodes = nodes
        self._pods = pods
        self._raise = raise_on

    def get_nodes(self, _=None):
        if self._raise == 'nodes':
            raise RuntimeError('boom-nodes')
        return self._nodes

    def get_pods(self, ns=None):
        if self._raise == 'pods':
            raise RuntimeError('boom-pods')
        return self._pods


def _mk(name, ctx, mgr):
    return {'mgr': mgr, 'display_name': name, 'context': ctx,
            'version': 'v1.30', 'path': '', 'kc_name': name}


class TestMultiClusterSummary(unittest.TestCase):
    def setUp(self):
        from src.api import PolarisAPI
        self.api = PolarisAPI()

    def test_empty(self):
        self.api._clusters = {}
        s = self.api.get_multicluster_summary()
        self.assertTrue(s['ok'])
        self.assertEqual(s['clusters'], [])
        self.assertEqual(s['totals']['clusters'], 0)
        self.assertEqual(s['totals']['nodes'], 0)

    def test_aggregate_and_totals(self):
        self.api._clusters = {
            'a': _mk('alpha', 'ctx-a', _FakeMgr(True,
                     [{'status': 'Ready'}, {'status': 'NotReady'}],
                     [{'status': 'Running'}, {'status': 'Pending'}])),
            'b': _mk('beta', 'ctx-b', _FakeMgr(False, [], [])),
            'c': _mk('gamma', 'ctx-c', _FakeMgr(True,
                     [{'status': 'Ready'}], [{'status': 'Running'}])),
        }
        self.api._active_id = 'c'
        s = self.api.get_multicluster_summary()
        t = s['totals']
        self.assertEqual(t['clusters'], 3)
        self.assertEqual(t['connected'], 2)
        self.assertEqual(t['nodes'], 3)          # 2 + 0(미연결) + 1
        self.assertEqual(t['nodes_ready'], 2)    # 1 + 0 + 1
        self.assertEqual(t['pods'], 3)           # 2 + 0 + 1
        self.assertEqual(t['pods_not_ready'], 1) # Pending 1개
        # 활성 클러스터(gamma)가 맨 앞
        self.assertEqual(s['clusters'][0]['id'], 'c')
        self.assertTrue(s['clusters'][0]['active'])
        # 미연결 클러스터는 error 표시 + 카운트 0
        beta = next(r for r in s['clusters'] if r['id'] == 'b')
        self.assertFalse(beta['connected'])
        self.assertIn('error', beta)

    def test_manager_exception_captured(self):
        self.api._clusters = {
            'x': _mk('x', 'cx', _FakeMgr(True, [{'status': 'Ready'}], [], raise_on='pods')),
        }
        self.api._active_id = 'x'
        s = self.api.get_multicluster_summary()
        row = s['clusters'][0]
        self.assertIn('error', row)
        self.assertIn('boom-pods', row['error'])
        # 예외가 나도 전체 호출은 성공(ok=True), 크래시 없음
        self.assertTrue(s['ok'])


if __name__ == '__main__':
    unittest.main()
