# -*- coding: utf-8 -*-
"""v1.5.30 업그레이드 사전 점검 — RKE2 업그레이드 경로(공식 릴리스 노트 표).

판정 테스트는 고정한 예시 표로 한다(공식 표가 갱신돼도 흔들리지 않게). 실제 표는 모양만 확인한다."""
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

from src import upgradecheck as UC
from src import upgraderules as UR
from src._k8s_upgrade_data import DATA

ROOT = Path(__file__).resolve().parent.parent


def rel(k8s, etcd, ctd, charts=None, notes=(), prime=False, pulled=False, ingress=True):
    c = {'Kubernetes': k8s, 'Etcd': etcd, 'Containerd': ctd, 'Runc': 'v1.2.0', 'CoreDNS': 'v1.12.0',
         'Canal': 'Flannel v0.26.0 + Calico v3.29.0', 'Traefik': 'v3.5.0'}
    if ingress:
        c['Ingress-Nginx'] = 'v1.12.0-hardened1'
    return {'components': c, 'charts': charts or {}, 'notes': list(notes), 'prime_only': prime, 'pulled': pulled, 'date': ''}


TABLE = {'releases': {
    'v1.32.5+rke2r1': rel('v1.32.5', 'v3.5.19-k3s1', 'v2.0.4-k3s2', {'rke2-traefik': '34.0.0'}),
    'v1.32.11+rke2r3': rel('v1.32.11', 'v3.5.26-k3s1', 'v2.0.7-k3s1', notes=['RKE2 v1.34 and higher include etcd 3.6. There is no safe path ...']),
    'v1.33.10+rke2r1': rel('v1.33.10', 'v3.5.26-k3s1', 'v2.1.0-k3s1'),
    'v1.33.13+rke2r3': rel('v1.33.13', 'v3.5.26-k3s1', 'v2.1.0-k3s1', prime=True),
    'v1.34.2+rke2r1': rel('v1.34.2', 'v3.6.5-k3s1', 'v2.1.4-k3s1', {'rke2-traefik': '37.0.0', 'rke2-canal': 'v3.30.0-build1'},
                          notes=['This release upgrades Traefik chart to v40.x which includes a breaking change',
                                 'Canal must be restarted after upgrade because flannel changed']),
    'v1.34.3+rke2r1': rel('v1.34.3', 'v3.6.6-k3s1', 'v2.1.5-k3s1', pulled=True,
                          notes=['we have removed this RKE2 release from the channel server. Please use r2']),
    'v1.27.1+rke2r1': rel('v1.27.1', 'v3.5.7-k3s1', 'v1.7.0-k3s1'),
    'v1.28.2+rke2r1': rel('v1.28.2', 'v3.5.9-k3s1', 'v2.0.0-k3s1', ingress=False),
}, 'etcd_bridges': [{'from': '3.5', 'to': '3.6', 'min': '3.5.26'}], 'url': 'u-rke2'}


def data(ver, tgt, helm=None, etcd_img=None, runtime='', configs=(), plans=()):
    return {'version': ver, 'cur_minor': int(ver.split('.')[1]), 'target_minor': tgt, 'pdbs': [],
            'nodes': [{'name': 'n1', 'runtime': runtime, 'control_plane': True}] if runtime else [],
            'helm': None if helm is None else [{'namespace': 'kube-system', 'release': r, 'chart': f'{r}-{v}'} for r, v in helm.items()],
            'apods': [{'images': [f'rancher/hardened-etcd:{etcd_img}-k3s1-build1'] if etcd_img else [], 'namespace': 'kube-system',
                       'name': 'p', 'claims': [], 'owner': '', 'pull_always': False}],
            'rke2_configs': list(configs), 'rke2_plans': list(plans)}


def run(d):
    f, p = [], []
    UR.evaluate_rke2(d, lambda sev, cat, title, detail='', items=None, action='': f.append(
        {'severity': sev, 'category': cat, 'title': title, 'detail': detail, 'items': items or [], 'action': action}), p)
    return f, p


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.dict(UR.DATA, {'rke2': TABLE})
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_path_skips_prime_and_pulled(self):
        p = UR.rke2_plan(data('v1.32.11+rke2r3', 34))
        self.assertEqual(p['path'], ['v1.33.10+rke2r1', 'v1.34.2+rke2r1'], 'Prime 전용 · 회수된 판은 고르지 않는다')

    def test_etcd_bridge_first(self):
        d = data('v1.32.5+rke2r1', 34, helm={'rke2-canal': 'v3.29.0-build1'})
        p = UR.rke2_plan(d)
        self.assertEqual(p['bridge']['via'], 'v1.32.11+rke2r3', 'etcd 3.5.26 을 담은 가장 이른 판')
        self.assertEqual(p['path'][0], 'v1.32.11+rke2r3')
        f, _ = run(d)
        x = [y for y in f if 'etcd 3.5 → 3.6' in y['title']][0]
        self.assertEqual(x['severity'], 'warn')
        self.assertTrue(any('v1.32.11+rke2r3' in t and '먼저' in t for t in UR.rke2_checklist(d)))

    def test_no_bridge_when_etcd_already_safe(self):
        p = UR.rke2_plan(data('v1.33.10+rke2r1', 34, etcd_img='v3.5.26'))
        self.assertIsNone(p['bridge'])

    def test_cluster_values_override_table(self):
        p = UR.rke2_plan(data('v1.33.10+rke2r1', 34, etcd_img='v3.5.20', runtime='containerd://2.1.0-k3s1'))
        self.assertEqual(p['bridge']['etcd'], 'v3.5.20', '클러스터의 etcd 이미지가 표보다 우선')

    def test_component_diff_only_installed(self):
        p = UR.rke2_plan(data('v1.33.10+rke2r1', 34, helm={'rke2-canal': 'v3.29.0-build1'}, etcd_img='v3.5.26'))
        names = [n for n, a, b in p['diff']]
        self.assertIn('Etcd', names)
        self.assertNotIn('Traefik', names, '쓰지 않는 번들 구성 요소는 비교하지 않는다')

    def test_notes_filtered_by_installed(self):
        p = UR.rke2_plan(data('v1.33.10+rke2r1', 34, helm={'rke2-canal': 'v3.29.0-build1'}, etcd_img='v3.5.26'))
        texts = [n for t, n in p['notes']]
        self.assertTrue(any('Canal must' in n for n in texts))
        self.assertFalse(any('Traefik' in n for n in texts), 'Traefik 을 안 쓰면 Traefik 안내는 빼다')
        self.assertFalse(any('channel server' in n for n in texts), '회수된 판의 안내는 빼다')

    def test_etcd_bridge_text_not_repeated(self):
        p = UR.rke2_plan(data('v1.32.5+rke2r1', 33, etcd_img='v3.5.19'))
        self.assertIsNone(p['bridge'], '1.33 까지는 etcd 3.6 으로 가지 않는다')
        self.assertFalse(any('safe path' in n for t, n in p['notes']), 'etcd 다리 원문은 따로 판정하므로 일반 안내에 넣지 않는다')

    def test_helmchartconfig_major_change(self):
        f, p = run(data('v1.33.10+rke2r1', 34, helm={'rke2-traefik': '34.0.0'}, etcd_img='v3.5.26', configs=['rke2-traefik']))
        x = [y for y in f if 'HelmChartConfig' in y['title']][0]
        self.assertIn('rke2-traefik: 34.0.0 → 37.0.0', x['items'])

    def test_ingress_nginx_missing_blocks(self):
        f, _ = run(data('v1.27.1+rke2r1', 28, helm={'rke2-ingress-nginx': '4.6.0'}))
        self.assertTrue(any(y['severity'] == 'block' and 'ingress-nginx' in y['title'] for y in f))

    def test_containerd_major(self):
        f, _ = run(data('v1.27.1+rke2r1', 28, helm={}, runtime='containerd://2.0.0-k3s1'))
        self.assertTrue(any('containerd 메이저' in y['title'] for y in f), '판을 아는 RKE2 는 표의 containerd(1.7)로')
        f, _ = run(data('v1.27.9+rke2r1', 28, helm={}, runtime='containerd://1.7.5-k3s1'))
        self.assertTrue(any('containerd 메이저' in y['title'] for y in f), '표에 없는 판은 노드 값으로')

    def test_checklist_plan_vs_script(self):
        d = data('v1.33.10+rke2r1', 34, etcd_img='v3.5.26')
        self.assertTrue(any('INSTALL_RKE2_VERSION=v1.34.2+rke2r1' in t for t in UR.rke2_checklist(d)))
        d['rke2_plans'] = [{'name': 'server-plan', 'version': 'v1.33.10+rke2r1', 'channel': '', 'namespace': 's', 'concurrency': 1}]
        c = UC.checklist(d)
        self.assertTrue(any('server Plan' in t and 'v1.34.2+rke2r1' in t for t in c))
        self.assertFalse(any('INSTALL_RKE2_VERSION 을 지정해' in t for t in c), '일반 안내는 실제 경로로 바뀐다')

    def test_not_rke2_or_missing_minor(self):
        self.assertIsNone(UR.rke2_plan(data('v1.33.10', 34)))
        f, _ = run(data('v1.34.2+rke2r1', 36))
        self.assertTrue(any('1.35' in y['title'] and '없습니다' in y['title'] for y in f))

    def test_addon_bundle_text_uses_target(self):
        with mock.patch.dict(UR.DATA, {'addons': {'Calico': {'versions': {'3.29': {'k8s': [31, 32, 33], 'min': 31, 'max': 33}},
                                                             'url': 'u', 'image': r'calico(?:-|/)node:v?(\d+\.\d+)', 'key': 'minor', 'cni': True}}}):
            d = data('v1.33.10+rke2r1', 34, etcd_img='v3.5.26')
            d['apods'][0]['images'] = ['rancher/mirrored-calico-node:v3.29.0']
            f = []
            UR.evaluate_addons(d, lambda sev, cat, title, detail='', items=None, action='': f.append(detail), [])
        self.assertTrue(any('v1.34.2+rke2r1' in t and 'Calico v3.29.0' in t for t in f), f)


class GeneratorTest(unittest.TestCase):
    BODY = '''<!-- v1.36.0+rke2r1 -->
> [!WARNING]
> **Ingress change**
> Traefik is now the default for new clusters starting in v1.36 (existing clusters keep their ingress).

This release updates Kubernetes to v1.36.0.

**Important Note**

If your server (control-plane) nodes were not started with the `--token` CLI flag or config file key, a randomized token was generated.

You may retrieve the token value from any server already joined to the cluster:
```bash
cat /var/lib/rancher/rke2/server/token
```

## Changes since v1.35.0+rke2r1:

* Change default ingress controller to traefik [(#1)](https://github.com/rancher/rke2/pull/1)
  * The default ingress-controller is now traefik. Clusters with ingress-nginx keep it.
  * Fix race condition that would fail to start pods
* Bump something [(#2)](https://github.com/rancher/rke2/pull/2)

## Charts Versions
| Component | Version |
| --- | --- |
| rke2-traefik | [39.0.702](https://example.invalid/a.tgz) |
| rancher-vsphere-csi | [3.8.0](https://example.invalid/b.tgz) |

## Packaged Component Versions
| Component | Version |
| --- | --- |
| Kubernetes | [v1.36.0](https://example.invalid/k) |
| Etcd | [v3.6.9-k3s1](https://example.invalid/e) |

### Available CNIs
| Component | Version | FIPS Compliant |
| --- | --- | --- |
| Canal (Default) | [Flannel v0.28.4](https://example.invalid/f)<br/>[Calico v3.32.0](https://example.invalid/c) | Yes |

## Helpful Links
- x
'''

    def gen(self):
        spec = importlib.util.spec_from_file_location('gen', ROOT / 'scripts/gen_k8supgrade.py')
        G = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(G)
        return G

    def test_parse(self):
        e = self.gen().parse_rke2_release('v1.36.0+rke2r1', self.BODY)
        self.assertEqual(e['components']['Etcd'], 'v3.6.9-k3s1')
        self.assertEqual(e['components']['Canal'], 'Flannel v0.28.4 + Calico v3.32.0')
        self.assertEqual(e['components']['Flannel'], 'v0.28.4')
        self.assertEqual(e['charts'], {'rke2-traefik': '39.0.702'}, 'rke2- 차트만')
        n = ' | '.join(e['notes'])
        self.assertIn('Traefik is now the default', n)
        self.assertIn('The default ingress-controller is now traefik', n)
        self.assertNotIn('token', n.lower(), '매번 같은 토큰 안내는 뺀다')
        self.assertNotIn('Fix race', n, '고친 것 알림은 할 일이 아니다')

    def test_bridge_and_flags(self):
        raw = [{'tag_name': 'v1.33.7+rke2r3', 'prerelease': False, 'published_at': '2026-01-10T00:00:00Z',
                'body': 'there is NO safe path from etcd 3.5 to 3.6 except by upgrading to v3.5.26 first.\n> `v1.33.7+rke2r3` is a Prime-only release.'},
               {'tag_name': 'v1.33.7-rc1+rke2r3', 'prerelease': True, 'published_at': '', 'body': ''}]
        r = self.gen().rke2_releases(raw)
        self.assertEqual(r['etcd_bridges'], [{'from': '3.5', 'to': '3.6', 'min': '3.5.26'}])
        self.assertEqual(list(r['releases']), ['v1.33.7+rke2r3'], 'rc 는 뺀다')
        self.assertTrue(r['releases']['v1.33.7+rke2r3']['prime_only'])


class RealTableTest(unittest.TestCase):
    def test_shape(self):
        R = DATA['rke2']
        self.assertGreater(len(R['releases']), 100)
        for tag, e in R['releases'].items():
            self.assertRegex(tag, r'^v1\.\d+\.\d+\+rke2r\d+$')
            self.assertIn('Kubernetes', e['components'], tag)
        self.assertTrue(any(b['from'] == '3.5' for b in R['etcd_bridges']))
        self.assertTrue(UR.rke2_latest(DATA['latest_minor'] - 1))


if __name__ == '__main__':
    unittest.main()
