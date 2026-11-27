# -*- coding: utf-8 -*-
"""v1.5.29 업그레이드 사전 점검 — 애드온 공식 호환표로 「먼저 올릴 애드온」 판정.

판정 테스트는 고정한 예시 표로 한다(공식 표가 갱신돼도 흔들리지 않게). 실제 표는 모양만 확인한다."""
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

from src import upgradecheck as UC
from src import upgraderules as UR
from src._k8s_upgrade_data import DATA

ROOT = Path(__file__).resolve().parent.parent

TABLE = {
    'Calico': {'versions': {'3.28': {'k8s': [28, 29, 30], 'min': 28, 'max': 30},
                            '3.29': {'k8s': [29, 30, 31], 'min': 29, 'max': 31},
                            '3.30': {'k8s': [31, 32, 33], 'min': 31, 'max': 33}},
               'url': 'u-calico', 'image': r'calico(?:-|/)node:v?(\d+\.\d+)', 'key': 'minor', 'cni': True},
    'ingress-nginx': {'versions': {'1.10.0': {'k8s': [26, 27, 28, 29], 'min': 26, 'max': 29},
                                   '1.11.2': {'k8s': [26, 27, 28, 29, 30], 'min': 26, 'max': 30}},
                      'url': 'u-ing', 'image': r'ingress-nginx[^:@]*controller[^:@]*:v?(\d+\.\d+\.\d+)', 'key': 'exact', 'cni': False},
    'metrics-server': {'versions': {'0.6': {'k8s': None, 'min': 25, 'max': None}, '0.7': {'k8s': None, 'min': 27, 'max': None}},
                       'url': 'u-ms', 'image': r'metrics-server:v?(\d+\.\d+)', 'key': 'minor', 'cni': False},
    'cert-manager': {'versions': {'1.14': {'k8s': [24, 25, 26, 27, 28, 29], 'min': 24, 'max': 29},
                                  '1.16': {'k8s': [29, 30, 31, 32], 'min': 29, 'max': 32}},
                     'url': 'u-cm', 'image': r'cert-manager-controller:v?(\d+\.\d+)', 'key': 'minor', 'cni': False},
}


def run(images, cur, tgt, version='v1.30.4'):
    d = {'cur_minor': cur, 'target_minor': tgt, 'version': version,
         'apods': [{'images': images, 'namespace': 'x', 'name': 'y', 'claims': [], 'owner': '', 'pull_always': False}]}
    f, p = [], []
    UR.evaluate_addons(d, lambda sev, cat, title, detail='', items=None, action='': f.append(
        {'severity': sev, 'category': cat, 'title': title, 'detail': detail, 'items': items or [], 'action': action}), p)
    return f, p, UR.addon_checklist(d)


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.dict(UR.DATA, {'addons': TABLE})
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_cni_needs_upgrade_first_blocks(self):
        f, p, c = run(['docker.io/calico/node:v3.28.2'], 30, 31)
        x = [y for y in f if 'Calico' in y['title']][0]
        self.assertEqual(x['severity'], 'block', 'CNI 가 맞지 않으면 통신이 끊긴다')
        self.assertIn('3.29', x['title'], '지금(1.30)과 목표(1.31)를 모두 지원하는 가장 낮은 판')
        self.assertTrue(any('먼저' in t and 'Calico' in t for t in c))

    def test_supported_passes(self):
        f, p, c = run(['docker.io/calico/node:v3.29.1'], 30, 31)
        self.assertFalse(f)
        self.assertTrue(any('Calico 3.29' in t and '지원합니다' in t for t in p))
        self.assertEqual(c, [])

    def test_two_step(self):
        f, p, c = run(['docker.io/calico/node:v3.28.2'], 28, 31)          # 1.28 과 1.31 을 함께 지원하는 판이 없다
        x = [y for y in f if 'Calico' in y['title']][0]
        self.assertIn('함께 지원하는 판도 없습니다', x['title'])
        self.assertIn('번갈아', x['action'])

    def test_none_yet(self):
        f, p, c = run(['docker.io/calico/node:v3.30.0'], 33, 34)
        x = [y for y in f if 'Calico' in y['title']][0]
        self.assertIn('아직 없습니다', x['title'])
        self.assertEqual(x['severity'], 'warn', '정보가 없을 뿐 — 막는 문제로 단정하지 않는다')

    def test_exact_version_and_fallback(self):
        f, p, c = run(['registry.k8s.io/ingress-nginx/controller:v1.10.0@sha256:abc'], 29, 30)
        x = [y for y in f if 'ingress-nginx' in y['title']][0]
        self.assertEqual(x['severity'], 'warn')
        self.assertIn('1.11.2', x['title'])
        f, p, c = run(['registry.k8s.io/ingress-nginx/controller:v1.11.5'], 29, 30)
        self.assertTrue(any('ingress-nginx 1.11.5' in t for t in p), '정확한 판이 없으면 같은 주.부 줄로')

    def test_open_range(self):
        f, p, c = run(['registry.k8s.io/metrics-server/metrics-server:v0.7.2'], 33, 34)
        self.assertTrue(any('metrics-server 0.7' in t and '1.27 이상' in t for t in p))

    def test_old_version_not_in_table(self):
        f, p, c = run(['quay.io/jetstack/cert-manager-controller:v1.9.1'], 28, 29)
        x = [y for y in f if 'cert-manager' in y['title']][0]
        self.assertIn('옛 버전', x['title'])

    def test_rke2_bundled_is_info(self):
        f, p, c = run(['rancher/mirrored-calico-node:v3.28.2'], 30, 31, version='v1.30.4+rke2r1')
        x = [y for y in f if 'Calico' in y['title']][0]
        self.assertEqual(x['severity'], 'info', 'RKE2 가 함께 올린다')
        self.assertIn('RKE2', x['detail'])
        self.assertEqual(c, [], '번들은 「먼저 올리기」 순서에 넣지 않는다')

    def test_lowest_of_several_versions(self):
        f, p, c = run(['docker.io/calico/node:v3.29.1', 'docker.io/calico/node:v3.28.0'], 30, 31)
        self.assertTrue(any('지금 3.28' in y['title'] for y in f), '여러 판이 섞이면 낮은 쪽 기준')

    def test_nothing_installed_or_no_target(self):
        self.assertEqual(run(['nginx:1.27'], 30, 31)[:2], ([], []))
        self.assertEqual(run(['docker.io/calico/node:v3.28.2'], 31, 31)[:2], ([], []))


class ChecklistOrderTest(unittest.TestCase):
    def test_after_backup(self):
        with mock.patch.dict(UR.DATA, {'addons': TABLE}):
            d = {'cur_minor': 30, 'target_minor': 31, 'version': 'v1.30.4', 'nodes': [], 'pdbs': [],
                 'apods': [{'images': ['docker.io/calico/node:v3.28.2'], 'namespace': 'x', 'name': 'y', 'claims': [], 'owner': '', 'pull_always': False}]}
            out = UC.checklist(d)
        i = next(i for i, t in enumerate(out) if t.startswith('쿠버네티스보다 먼저'))
        self.assertTrue(out[i - 1].startswith('Velero'), out)
        self.assertLess(i, next(j for j, t in enumerate(out) if t.startswith('노드마다')))


class RealTableTest(unittest.TestCase):
    def test_shape(self):
        A = DATA['addons']
        for name in ('ingress-nginx', 'cert-manager', 'Cilium', 'Calico', 'Argo CD', 'Istio', 'metrics-server', 'Velero'):
            self.assertIn(name, A)
            self.assertTrue(A[name]['versions'], name)
            self.assertTrue(A[name]['url'].startswith('https://'))
            for v, e in A[name]['versions'].items():
                self.assertTrue(e['k8s'] or e['min'], (name, v))
        self.assertTrue(A['Calico']['cni'] and A['Cilium']['cni'])
        self.assertTrue(all(isinstance(e['k8s'], list) for e in A['Argo CD']['versions'].values()), 'v1.34 꼴도 읽는다')


class GeneratorTest(unittest.TestCase):
    def test_minors(self):
        spec = importlib.util.spec_from_file_location('gen', ROOT / 'scripts/gen_k8supgrade.py')
        G = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(G)
        self.assertEqual(G._minors('v1.34, v1.33'), [33, 34])
        self.assertEqual(G._minors('1.36.5 and 1.37.1'), [36, 37])
        self.assertEqual(G._minors('Alpine 3.23.3 · 1.27.1'), [27])


if __name__ == '__main__':
    unittest.main()
