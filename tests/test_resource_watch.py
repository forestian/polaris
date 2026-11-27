# -*- coding: utf-8 -*-
"""ResourceWatchManager(src/k8s_watch.py) 테스트 — 파드 실시간 갱신(watch API).

- TestResourceWatchLogic: 클러스터 불필요 — 미지원 kind 가드, 빈 kubeconfig 가드,
  세션 없는 recv/close 가드, 매퍼 함수(_map_pod) 단위, 버퍼 upsert/delete 병합 로직
  (프론트 applyWatchEvents 와 동일한 계약을 파이썬 쪽에서 재현해 검증).
- TestResourceWatchLive: POLARIS_LIVE_CLUSTER=1 일 때만 — 실클러스터에 파드를
  만들고/지우면서 watch 버퍼에 ADDED/DELETED 이벤트가 실제로 도착하는지 확인
  (진짜 "실시간" 이라는 근거).
"""
import os
import time
import types
import unittest

from src.k8s_watch import ResourceWatchManager, _map_pod


class _FakePod:
    """kubernetes V1Pod 최소 대역 — _map_pod 단위 테스트용."""
    def __init__(self, name, ns, phase='Running', ready=True, restarts=0, node='n1'):
        Meta = types.SimpleNamespace
        cs = types.SimpleNamespace(ready=ready, restart_count=restarts)
        self.metadata = Meta(name=name, namespace=ns, creation_timestamp=None)
        self.spec = Meta(containers=[object()], node_name=node)
        self.status = Meta(phase=phase, container_statuses=[cs])


class TestResourceWatchLogic(unittest.TestCase):
    def setUp(self):
        self.mgr = ResourceWatchManager()

    def test_supported_kinds(self):
        self.assertEqual(ResourceWatchManager.supported_kinds(), ['pods'])

    def test_unsupported_kind_rejected(self):
        r = self.mgr.start('/x/kubeconfig', 'deployments', '')
        self.assertFalse(r['ok'])
        self.assertIn('watch 미지원', r['error'])

    def test_empty_kubeconfig_rejected(self):
        r = self.mgr.start('', 'pods', '')
        self.assertFalse(r['ok'])

    def test_recv_unknown_session(self):
        r = self.mgr.recv('nope')
        self.assertFalse(r['ok'])

    def test_close_unknown_session(self):
        r = self.mgr.close('nope')
        self.assertFalse(r['ok'])

    def test_map_pod_shape(self):
        row = _map_pod(_FakePod('web-1', 'default', phase='Running', ready=True, restarts=2))
        self.assertEqual(row['name'], 'web-1')
        self.assertEqual(row['namespace'], 'default')
        self.assertEqual(row['ready'], '1/1')
        self.assertEqual(row['status'], 'Running')
        self.assertEqual(row['restarts'], '2')
        self.assertEqual(row['_kind'], 'pod')

    def test_buffer_append_and_drain(self):
        from src.k8s_watch import _WatchSession
        import threading
        sess = _WatchSession(id='s1', kind='pods', namespace='', watch=None)
        self.mgr._sessions['s1'] = sess
        self.mgr._append(sess, {'type': 'ADDED', 'row': {'name': 'a'}})
        self.mgr._append(sess, {'type': 'MODIFIED', 'row': {'name': 'a'}})
        r = self.mgr.recv('s1')
        self.assertTrue(r['ok'])
        self.assertEqual(len(r['events']), 2)
        # 두 번째 recv 는 비어있어야 함(버퍼 비움)
        r2 = self.mgr.recv('s1')
        self.assertEqual(r2['events'], [])

    def test_merge_semantics_upsert_and_delete(self):
        """프론트 applyWatchEvents 와 동일한 namespace::name 키 upsert/delete 계약을
        파이썬으로 재현 — 이벤트 순서에 따른 최종 rows 상태가 기대와 같은지 확인."""
        def apply_events(rows, events):
            m = {f"{r['namespace']}::{r['name']}": r for r in rows}
            for ev in events:
                key = f"{ev['row']['namespace']}::{ev['row']['name']}"
                if ev['type'] == 'DELETED':
                    m.pop(key, None)
                else:
                    m[key] = ev['row']
            return list(m.values())

        rows = [{'namespace': 'default', 'name': 'a', 'status': 'Running'}]
        events = [
            {'type': 'ADDED', 'row': {'namespace': 'default', 'name': 'b', 'status': 'Pending'}},
            {'type': 'MODIFIED', 'row': {'namespace': 'default', 'name': 'a', 'status': 'CrashLoopBackOff'}},
        ]
        rows = apply_events(rows, events)
        by_name = {r['name']: r for r in rows}
        self.assertEqual(set(by_name.keys()), {'a', 'b'})
        self.assertEqual(by_name['a']['status'], 'CrashLoopBackOff')

        events2 = [{'type': 'DELETED', 'row': {'namespace': 'default', 'name': 'b'}}]
        rows = apply_events(rows, events2)
        self.assertEqual({r['name'] for r in rows}, {'a'})


@unittest.skipUnless(os.environ.get('POLARIS_LIVE_CLUSTER') == '1',
                     'POLARIS_LIVE_CLUSTER=1 아닐 때 skip (실클러스터 필요)')
class TestResourceWatchLive(unittest.TestCase):
    """실클러스터(Rancher Desktop)에 파드를 만들고 지우며 watch 가 실제로
    ADDED/DELETED 이벤트를 실시간으로 넘겨주는지 end-to-end 로 확인."""
    NS = 'default'
    POD = 'polaris-watch-test'

    def setUp(self):
        self.kubeconfig = os.path.expanduser(os.environ.get('KUBECONFIG', '~/.kube/config'))
        self.mgr = ResourceWatchManager()

    def tearDown(self):
        try: self.mgr.close_all()
        except Exception: pass
        try:
            from kubernetes import client, config
            config.load_kube_config(config_file=self.kubeconfig)
            client.CoreV1Api().delete_namespaced_pod(self.POD, self.NS)
        except Exception:
            pass

    def _wait_for(self, watch_id, predicate, timeout=20):
        deadline = time.time() + timeout
        seen = []
        while time.time() < deadline:
            r = self.mgr.recv(watch_id)
            self.assertTrue(r['ok'], r)
            seen.extend(r['events'])
            if predicate(seen):
                return seen
            time.sleep(0.3)
        self.fail(f'timeout — 조건 미충족. 수신된 이벤트: {seen}')

    def test_watch_sees_add_and_delete_in_real_time(self):
        from kubernetes import client, config
        config.load_kube_config(config_file=self.kubeconfig)
        core = client.CoreV1Api()
        try:
            core.delete_namespaced_pod(self.POD, self.NS, grace_period_seconds=0)
            time.sleep(2)
        except Exception:
            pass

        r = self.mgr.start(self.kubeconfig, 'pods', self.NS)
        self.assertTrue(r['ok'], r)
        wid = r['watch_id']

        # 파드 생성 → ADDED 이벤트 기대
        body = client.V1Pod(
            metadata=client.V1ObjectMeta(name=self.POD),
            spec=client.V1PodSpec(containers=[client.V1Container(
                name='c', image='busybox:1.36', command=['sleep', '3600'])]))
        core.create_namespaced_pod(self.NS, body)
        self._wait_for(wid, lambda evs: any(
            e['type'] == 'ADDED' and e['row']['name'] == self.POD for e in evs))

        # 파드 삭제(즉시 강제 종료 — 기본 유예시간 30s 를 기다리지 않고 빠르게 검증) → DELETED 기대
        core.delete_namespaced_pod(self.POD, self.NS, grace_period_seconds=0)
        self._wait_for(wid, lambda evs: any(
            e['type'] == 'DELETED' and e['row']['name'] == self.POD for e in evs))

        self.mgr.close(wid)


if __name__ == '__main__':
    unittest.main()
