# -*- coding: utf-8 -*-
"""파드 exec 세션 매니저(src/pod_exec.py) 테스트.

- TestPodExecLogic: 클러스터 불필요 — 버퍼 트림/미존재 세션 가드/목록 등 순수 로직.
- TestPodExecLive : POLARIS_LIVE_CLUSTER=1 일 때만 — 실클러스터(busybox 파드)에 exec 하여
  send→recv→resize→close 왕복 검증. CI/무클러스터에선 자동 skip.
"""
import os
import time
import unittest

from src.pod_exec import PodExecManager, _DEFAULT_SHELL_CMD


class TestPodExecLogic(unittest.TestCase):
    def setUp(self):
        self.mgr = PodExecManager()

    def test_default_shell_probes_bash_then_sh(self):
        joined = ' '.join(_DEFAULT_SHELL_CMD)
        self.assertIn('bash', joined)
        self.assertIn('sh', joined)

    def test_unknown_session_guards(self):
        self.assertFalse(self.mgr.recv('nope')['ok'])
        self.assertFalse(self.mgr.send('nope', 'x')['ok'])
        self.assertFalse(self.mgr.resize('nope', 80, 24)['ok'])
        self.assertFalse(self.mgr.close('nope')['ok'])
        self.assertFalse(self.mgr.snapshot('nope')['ok'])

    def test_list_empty(self):
        self.assertEqual(self.mgr.list(), [])

    def test_start_requires_kubeconfig_and_target(self):
        self.assertFalse(self.mgr.start('', 'default', 'p')['ok'])
        self.assertFalse(self.mgr.start('/x/kubeconfig', '', 'p')['ok'])
        self.assertFalse(self.mgr.start('/x/kubeconfig', 'default', '')['ok'])

    def test_cap_trims_oldest_chunks(self):
        chunks = ['a' * 100, 'b' * 100, 'c' * 100]
        PodExecManager._cap(chunks, 150)     # 150 이하로 앞에서부터 버림
        self.assertLessEqual(sum(len(c) for c in chunks), 150)
        self.assertEqual(chunks[-1], 'c' * 100)   # 최신은 보존
        # 항상 최소 1개는 남긴다 (마지막 청크가 limit 초과여도)
        one = ['z' * 500]
        PodExecManager._cap(one, 100)
        self.assertEqual(len(one), 1)


@unittest.skipUnless(os.environ.get('POLARIS_LIVE_CLUSTER') == '1',
                     'POLARIS_LIVE_CLUSTER=1 아닐 때 skip (실클러스터 필요)')
class TestPodExecLive(unittest.TestCase):
    """실클러스터 exec 왕복. 사전조건: busybox 파드 polaris-exec-test(default) Running,
    기본 kubeconfig current-context 가 그 클러스터를 가리켜야 함."""
    NS = 'default'
    POD = 'polaris-exec-test'

    def setUp(self):
        self.kubeconfig = os.path.expanduser(os.environ.get('KUBECONFIG', '~/.kube/config'))
        self.mgr = PodExecManager()

    def tearDown(self):
        try: self.mgr.close_all()
        except Exception: pass

    def test_exec_roundtrip(self):
        r = self.mgr.start(self.kubeconfig, self.NS, self.POD, shell='/bin/sh', cols=100, rows=30)
        self.assertTrue(r['ok'], r)
        sid = r['session_id']
        self.assertTrue(self.mgr.resize(sid, 120, 40)['ok'])
        self.assertTrue(self.mgr.send(sid, 'echo POLARIS_POD_EXEC_OK\n')['ok'])
        got = ''
        deadline = time.time() + 8
        while time.time() < deadline:
            rec = self.mgr.recv(sid)
            self.assertTrue(rec['ok'])
            got += rec.get('data', '')
            if 'POLARIS_POD_EXEC_OK' in got:
                break
            time.sleep(0.15)
        self.assertIn('POLARIS_POD_EXEC_OK', got)
        # 세션이 아직 목록에 있고 열려 있음
        self.assertTrue(any(s['id'] == sid for s in self.mgr.list()))
        self.assertTrue(self.mgr.close(sid)['ok'])


if __name__ == '__main__':
    unittest.main()
