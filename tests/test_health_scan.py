# -*- coding: utf-8 -*-
"""건강 스캔(ReportsMixin.health_scan) 테스트.

- 항상: 미연결 가드.
- opt-in(POLARIS_LIVE_CLUSTER=1): 실클러스터 스캔이 구조화된 결과(counts/그룹)를 반환.
  (평가 규칙 자체는 보고서 테스트가 커버 — 여기선 health_scan 래핑/구조를 확인)
"""
import os
import unittest


class TestHealthScanGuard(unittest.TestCase):
    def test_not_connected(self):
        from src.api import PolarisAPI
        api = PolarisAPI()
        r = api.health_scan()
        self.assertFalse(r['ok'])
        self.assertIn('연결', r['error'])

    def test_netscan_is_fourth_positional_and_gated_by_connection(self):
        """v1.2.121 — netscan 은 4번째 위치 인자여야 한다.

        ui/src/api.js 의 healthScan 이 positional 호출이므로 순서가 계약이다.
        또 연결 확인보다 먼저 프로브가 나가면 안 되므로, 미연결 시 옵트인해도
        네트워크 접근 없이 곧바로 에러가 나와야 한다.
        """
        import inspect
        from src.api import PolarisAPI
        params = list(inspect.signature(PolarisAPI.health_scan).parameters)
        self.assertEqual(params[1:5], ['explain', 'llm_url', 'llm_model', 'netscan'])

        api = PolarisAPI()
        r = api.health_scan(False, '', 'local-model', True)   # positional 4개
        self.assertFalse(r['ok'])
        self.assertIn('연결', r['error'])
        self.assertNotIn('netscan', r)


@unittest.skipUnless(os.environ.get('POLARIS_LIVE_CLUSTER') == '1',
                     'POLARIS_LIVE_CLUSTER=1 아닐 때 skip (실클러스터 필요)')
class TestHealthScanLive(unittest.TestCase):
    def setUp(self):
        from src.api import PolarisAPI
        from src.k8s import K8sManager
        self.api = PolarisAPI()
        mgr = K8sManager()
        mgr.connect(path=os.path.expanduser(os.environ.get('KUBECONFIG', '~/.kube/config')))
        self.api._clusters['c1'] = {'mgr': mgr, 'display_name': 'rd',
                                    'context': 'rancher-desktop', 'version': 'v?',
                                    'path': '', 'kc_name': 'rd'}
        self.api._active_id = 'c1'

    def test_scan_structure(self):
        r = self.api.health_scan(explain=False)
        self.assertTrue(r['ok'], r)
        self.assertIn('counts', r)
        self.assertIn('immediate', r)
        self.assertIn('short_term', r)
        self.assertIn('backlog', r)
        self.assertIsInstance(r['total'], int)
        # immediate 는 critical/high 만 포함
        for it in r['immediate']:
            self.assertIn(it['severity'], ('critical', 'high'))


if __name__ == '__main__':
    unittest.main()
