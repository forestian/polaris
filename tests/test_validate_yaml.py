# -*- coding: utf-8 -*-
"""YAML 스키마 검증(ResourcesMixin.validate_resource_yaml) 테스트.

- TestValidateLogic: 클러스터 불필요 — 미연결/빈 입력 가드 + stderr 파서.
- TestValidateLive : POLARIS_LIVE_CLUSTER=1 일 때만 — 실클러스터 dry-run 으로
  유효 YAML 통과 / 잘못된 필드 거부. (아무것도 실제로 생성하지 않음)
"""
import os
import unittest


class TestValidateLogic(unittest.TestCase):
    def setUp(self):
        from src.api import PolarisAPI
        self.api = PolarisAPI()   # 클러스터 미연결 상태

    def test_not_connected(self):
        r = self.api.validate_resource_yaml('kind: ConfigMap')
        self.assertFalse(r['ok'])

    def test_empty_text(self):
        # kubeconfig 를 임의값으로 세팅해도 빈 텍스트는 먼저 걸러진다
        self.api.k8s.kubeconfig = 'X'
        r = self.api.validate_resource_yaml('   ')
        self.assertFalse(r['ok'])
        self.assertIn('비어', r['error'])

    def test_split_kubectl_errors_filters_noise(self):
        split = self.api._split_kubectl_errors
        stderr = ('Downloading kubectl v1.30...\n'
                  '\n'
                  'error: error validating "STDIN": ValidationError(Deployment.spec):\n'
                  'unknown field "spec.replicasX"\n')
        out = split(stderr)
        self.assertTrue(all('downloading' not in l.lower() for l in out))
        self.assertTrue(any('unknown field' in l for l in out))
        self.assertNotIn('', out)   # 빈 줄 제거

    def test_split_caps_at_40(self):
        many = '\n'.join(f'error line {i}' for i in range(100))
        self.assertLessEqual(len(self.api._split_kubectl_errors(many)), 40)


@unittest.skipUnless(os.environ.get('POLARIS_LIVE_CLUSTER') == '1',
                     'POLARIS_LIVE_CLUSTER=1 아닐 때 skip (실클러스터 필요)')
class TestValidateLive(unittest.TestCase):
    def setUp(self):
        from src.api import PolarisAPI
        self.api = PolarisAPI()
        self.api.k8s.kubeconfig = os.path.expanduser(
            os.environ.get('KUBECONFIG', '~/.kube/config'))

    def test_valid_configmap_passes(self):
        good = ('apiVersion: v1\nkind: ConfigMap\n'
                'metadata:\n  name: polaris-validate-ut\n  namespace: default\n'
                'data:\n  a: b\n')
        r = self.api.validate_resource_yaml(good)
        self.assertTrue(r['ok'], r)
        self.assertTrue(r['valid'], r)

    def test_invalid_field_rejected(self):
        bad = ('apiVersion: apps/v1\nkind: Deployment\n'
               'metadata:\n  name: polaris-bad-ut\n  namespace: default\n'
               'spec:\n  replicasX: 2\n  selector:\n    matchLabels: {app: x}\n'
               '  template:\n    metadata: {labels: {app: x}}\n'
               '    spec:\n      containers:\n      - name: c\n        image: nginx\n')
        r = self.api.validate_resource_yaml(bad)
        self.assertTrue(r['ok'], r)
        self.assertFalse(r['valid'], r)
        self.assertTrue(r.get('errors') or r.get('detail'))


if __name__ == '__main__':
    unittest.main()
