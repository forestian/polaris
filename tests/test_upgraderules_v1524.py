# -*- coding: utf-8 -*-
"""v1.5.24 업그레이드 사전 점검 — 공식 데이터 표 판정 · 설치된 애플리케이션 점검(예시 클러스터만 — 고객 데이터 금지)."""
import importlib.util
import unittest
from pathlib import Path

from src import upgradecheck as UC
from src import upgraderules as UR
from src._k8s_upgrade_data import DATA

ROOT = Path(__file__).resolve().parent.parent


def evaluate(data):
    found, passed = [], []

    def add(sev, cat, title, detail='', items=None, action=''):
        found.append({'severity': sev, 'category': cat, 'title': title, 'detail': detail, 'items': items or [], 'action': action})
    UR.evaluate_extra(data, add, passed)
    UR.evaluate_apps(data, add, passed)
    return found, passed


def base(cur=33, tgt=34, **kw):
    d = {'cur_minor': cur, 'target_minor': tgt, 'nodes': [], 'components': {}, 'kubelets': [], 'pvs': [], 'pvcs': [],
         'storageclasses': {}, 'csidrivers': [], 'apods': [], 'ingress_hosts': [], 'longhorn_settings': {}, 'proxy_mode': ''}
    d.update(kw)
    return d


def pod(ns, name, images, claims=(), owner='', always=False, node='n1'):
    return {'namespace': ns, 'name': name, 'node': node, 'phase': 'Running', 'owner': owner, 'labels': {}, 'images': list(images),
            'pull_always': always, 'claims': list(claims), 'flex': False, 'selinux': False}


class DataTest(unittest.TestCase):
    def test_generated_table(self):
        self.assertGreater(len(DATA['feature_gates']), 300)
        self.assertGreaterEqual(DATA['latest_minor'], 36)
        self.assertTrue(any(r[2] == 'PodSecurityPolicy' for r in DATA['removed_apis']))
        self.assertFalse(any(r[1].endswith('/v1') and r[1] == r[3] for r in DATA['removed_apis']), '대체 버전을 제거된 것으로 넣지 않는다')
        self.assertEqual(DATA['volume_types']['rbd'], {'state': 'removed', 'since': 31})
        self.assertIn('--pod-infra-container-image', [f['flag'] for f in DATA['releases']['35']['removed_flags'] if f['component'] == 'kubelet'])
        lh = DATA['apps']['longhorn']['releases']
        self.assertTrue(lh['1.7.0']['fast_failover'])
        self.assertIn(2933, [f['issue'] for f in lh['1.9.0']['rwx_fixes']])

    def test_uc_uses_table(self):
        self.assertEqual(UC.REMOVED_APIS, UR.removed_apis())
        self.assertGreaterEqual(UC.TABLE_KNOWN_UNTIL, DATA['latest_minor'])

    def test_static_import(self):
        src = (ROOT / 'src/upgraderules.py').read_text(encoding='utf-8')
        self.assertIn('from src._k8s_upgrade_data import DATA', src, 'PyInstaller 가 찾게 정적 import')


class ParseTest(unittest.TestCase):
    def test_flags(self):
        self.assertEqual(UR.parse_flags(['kube-apiserver', '--a=b', '--c', 'd', '--e', '--f=1']), {'--a': 'b', '--c': 'd', '--e': '', '--f': '1'})
        self.assertEqual(UR.parse_gates('A=true, B=false,C'), {'A': True, 'B': False})

    def test_component(self):
        self.assertEqual(UR.component_of({'metadata': {'namespace': 'kube-system', 'name': 'kube-apiserver-master', 'labels': {}}}), 'kube-apiserver')
        self.assertEqual(UR.component_of({'metadata': {'namespace': 'kube-system', 'name': 'x', 'labels': {'component': 'kube-scheduler'}}}), 'kube-scheduler')
        self.assertEqual(UR.component_of({'metadata': {'namespace': 'default', 'name': 'kube-apiserver-x'}}), '')

    def test_image_host(self):
        self.assertEqual(UR.image_host('harbor.example.com/lib/app:1'), 'harbor.example.com')
        self.assertEqual(UR.image_host('nginx:1.27'), 'docker.io')
        self.assertEqual(UR.image_host('library/nginx'), 'docker.io')


class GateFlagTest(unittest.TestCase):
    def removed_gate(self):
        return next((g, v['removed_in']) for g, v in DATA['feature_gates'].items() if v['removed_in'] and v['removed_in'] >= 30)

    def test_removed_gate_blocks(self):
        g, r = self.removed_gate()
        d = base(r - 1, r, components={'kube-apiserver': [{'node': 'm1', 'flags': {'--feature-gates': f'{g}=true'}, 'pod': 'x'}]})
        f, _ = evaluate(d)
        self.assertTrue(any(x['severity'] == 'block' and '없는 기능 게이트' in x['title'] for x in f), f)

    def test_locked_gate(self):
        g, st = next((g, s) for g, v in DATA['feature_gates'].items() if not v['removed_in']
                     for s in v['stages'] if s['locked'] and s['to'] is None and s['from'])
        d = base(st['from'] - 1, st['from'], kubelets=[{'node': 'n1', 'gates': {g: not st['default']}}])
        f, _ = evaluate(d)
        self.assertTrue(any('고정' in x['title'] for x in f), (g, f))

    def test_unknown_gate_and_clean(self):
        d = base(33, 34, kubelets=[{'node': 'n1', 'gates': {'NoSuchGateXyz': True}}])
        f, _ = evaluate(d)
        self.assertTrue(any('공식 목록에 없는' in x['title'] for x in f))
        f, p = evaluate(base(33, 34))
        self.assertFalse([x for x in f if x['category'] == 'gate' and x['severity'] != 'info'], '설정이 없으면 막는 · 주의 항목 없음')
        kl = [x for x in f if 'kubelet 플래그' in x['title']]
        self.assertTrue(kl and any('--register-schedulable' in i for i in kl[0]['items']))
        self.assertFalse(any('--container-runtime-endpoint' in i for i in kl[0]['items']), 'kubeadm 문장의 /var/lib/kubelet/ 경로를 kubelet 로 잡지 않는다')

    def test_removed_flag(self):
        d = base(36, 37, components={'kube-controller-manager': [{'node': 'm1', 'flags': {'--concurrent-service-syncs': '5'}, 'pod': 'x'}]})
        f, _ = evaluate(d)
        self.assertTrue(any('없어지는 플래그' in x['title'] and x['severity'] == 'block' for x in f), f)
        self.assertTrue(any('kubelet 플래그' in x['title'] for x in f), 'kubelet 은 노드에서 확인하라는 안내')


class StorageTest(unittest.TestCase):
    def test_removed_volume(self):
        d = base(30, 31, pvs=[{'name': 'pv1', 'types': ['rbd'], 'driver': '', 'modes': [], 'claim': 'db/data', 'sc': ''}])
        f, _ = evaluate(d)
        self.assertTrue(any(x['severity'] == 'block' and x['category'] == 'storage' for x in f))

    def test_migrated_needs_csi(self):
        pv = {'name': 'pv1', 'types': ['vsphereVolume'], 'driver': '', 'modes': [], 'claim': '', 'sc': ''}
        f, _ = evaluate(base(33, 34, pvs=[pv]))
        self.assertTrue(any('CSI 드라이버가 없습니다' in x['title'] for x in f))
        f, _ = evaluate(base(33, 34, pvs=[pv], csidrivers=['csi.vsphere.vmware.com']))
        self.assertFalse(any('CSI 드라이버가 없습니다' in x['title'] for x in f))


class NotesTest(unittest.TestCase):
    def test_cgroup_old_kernel_blocks(self):
        nodes = [{'name': 'n1', 'kernel': '3.10.0-1160.el7.x86_64', 'os': 'CentOS Linux 7', 'runtime': 'containerd://1.6.0'}]
        f, _ = evaluate(base(34, 35, nodes=nodes))
        cg = [x for x in f if 'cgroup v1' in x['title']]
        self.assertTrue(cg and cg[0]['severity'] == 'block', f)

    def test_cgroup_new_kernel_is_check(self):
        nodes = [{'name': 'n1', 'kernel': '6.8.0-1', 'os': 'Ubuntu 24.04', 'runtime': 'containerd://2.1'}]
        f, _ = evaluate(base(34, 35, nodes=nodes))
        cg = [x for x in f if 'cgroup v1' in x['title']]
        self.assertTrue(cg and cg[0]['severity'] == 'warn' and 'stat -fc' in cg[0]['items'][0])

    def test_ipvs(self):
        f, _ = evaluate(base(34, 35, proxy_mode='ipvs'))
        self.assertTrue(any('ipvs' in x['title'] for x in f))
        f, _ = evaluate(base(34, 35, proxy_mode='iptables'))
        self.assertFalse(any('ipvs' in x['title'] for x in f))

    def test_notes_differ_by_path(self):
        f1, _ = evaluate(base(34, 35))
        f2, _ = evaluate(base(36, 37))
        t1 = {x['title'] for x in f1 if x['category'] == 'notes'}
        t2 = {x['title'] for x in f2 if x['category'] == 'notes'}
        self.assertTrue(t1 and t2 and t1 != t2, (t1, t2))
        self.assertTrue(any('1.37 공식' in t for t in t2))

    def test_no_target(self):
        f, _ = evaluate(base(35, 35))
        self.assertEqual(f, [])


def incident_cluster(lh='1.4.2', ff=None):
    """장애 보고서와 같은 구조 — Longhorn RWX 위 Harbor · Redis, 이미지는 클러스터 안 Harbor 에서(예시 이름)."""
    pods = [pod('longhorn-system', 'longhorn-manager-x', [f'longhornio/longhorn-manager:v{lh}'], owner='DaemonSet/longhorn-manager'),
            pod('harbor', 'harbor-database-0', ['harbor.example.local/goharbor/harbor-db:v2.8.0'], ['data-harbor-db'], 'StatefulSet/harbor-database'),
            pod('harbor', 'harbor-registry-1', ['harbor.example.local/goharbor/registry-photon:v2.8.0'], ['harbor-registry'], 'ReplicaSet/harbor-registry'),
            pod('app', 'redis-cluster-0', ['harbor.example.local/lib/redis:7.2'], ['redis-data'], 'StatefulSet/redis-cluster'),
            pod('app', 'api-1', ['harbor.example.local/lib/api:1.0'], [], 'ReplicaSet/api', always=True)]
    pvcs = [{'namespace': 'harbor', 'name': 'data-harbor-db', 'modes': ['ReadWriteMany'], 'sc': 'longhorn-rwx', 'volume': 'pv-1'},
            {'namespace': 'harbor', 'name': 'harbor-registry', 'modes': ['ReadWriteMany'], 'sc': 'longhorn-rwx', 'volume': 'pv-2'},
            {'namespace': 'app', 'name': 'redis-data', 'modes': ['ReadWriteMany'], 'sc': 'longhorn-rwx', 'volume': 'pv-3'}]
    nodes = [{'name': f'cp{i}', 'control_plane': True, 'kernel': '6.8', 'os': 'Ubuntu', 'runtime': 'containerd://2.1'} for i in (1, 2, 3)]
    return base(33, 34, apods=pods, pvcs=pvcs, nodes=nodes, storageclasses={'longhorn-rwx': 'driver.longhorn.io'},
                ingress_hosts=['harbor.example.local'], longhorn_settings={} if ff is None else {'rwx-volume-fast-failover': ff})


class AppsTest(unittest.TestCase):
    def test_incident_structure_found(self):
        f, _ = evaluate(incident_cluster())
        lh = [x for x in f if 'Longhorn 공유 볼륨' in x['title']]
        self.assertTrue(lh)
        self.assertEqual(lh[0]['severity'], 'block', 'Harbor 가 RWX 위면 막는 등급(장애 확대)')
        self.assertIn('fast failover', lh[0]['detail'])
        self.assertTrue(any('#2933' in i for i in lh[0]['items']), '이후 판의 공식 수정 목록')
        reg = [x for x in f if '이미지 저장소가 이 클러스터 안' in x['title']]
        self.assertTrue(reg and 'Always' in reg[0]['detail'])
        db = [x for x in f if 'DB' in x['title']]
        self.assertTrue(db and any('redis' in i for i in db[0]['items']))
        self.assertTrue(any('짧은 간격' in x['title'] for x in f))

    def test_new_longhorn_with_ff(self):
        f, _ = evaluate(incident_cluster('1.9.2', 'true'))
        lh = [x for x in f if 'Longhorn 공유 볼륨' in x['title']][0]
        self.assertNotIn('fast failover(공식', lh['detail'])
        f, _ = evaluate(incident_cluster('1.9.2', 'false'))
        lh = [x for x in f if 'Longhorn 공유 볼륨' in x['title']][0]
        self.assertIn('꺼져 있습니다', lh['detail'])

    def test_no_rwx_passes(self):
        d = incident_cluster()
        d['pvcs'] = [dict(c, modes=['ReadWriteOnce']) for c in d['pvcs']]
        f, p = evaluate(d)
        self.assertFalse([x for x in f if 'Longhorn 공유 볼륨' in x['title']])
        self.assertTrue(any('RWX)을 쓰는 PVC 가 없습니다' in x for x in p))

    def test_db_on_nfs_pv(self):
        d = base(33, 34, apods=[pod('db', 'pg-0', ['postgres:16'], ['pgdata'], 'StatefulSet/pg')],
                 pvcs=[{'namespace': 'db', 'name': 'pgdata', 'modes': ['ReadWriteOnce'], 'sc': 'nfs-client', 'volume': 'pv-9'}],
                 pvs=[{'name': 'pv-9', 'types': ['nfs'], 'driver': '', 'modes': ['ReadWriteOnce'], 'claim': 'db/pgdata', 'sc': 'nfs-client'}])
        f, _ = evaluate(d)
        self.assertTrue(any('NFS' in x['title'] and 'db/pgdata' in x['items'][0] for x in f), f)

    def test_plain_cluster_has_no_app_findings(self):
        d = base(33, 34, apods=[pod('web', 'nginx-1', ['nginx:1.27'], owner='ReplicaSet/nginx')])
        f, _ = evaluate(d)
        self.assertFalse([x for x in f if x['category'] == 'app'])

    def test_checklist(self):
        out = UR.extra_checklist(incident_cluster())
        self.assertTrue(any('한 대씩' in t for t in out))
        self.assertTrue(any('share-manager' in t for t in out))
        self.assertTrue(any('미리 받아' in t for t in out))
        self.assertTrue(any('cluster_state' in t for t in out))
        self.assertEqual(UR.extra_checklist(base()), [])


class GeneratorTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('gen', ROOT / 'scripts/gen_k8supgrade.py')
        self.G = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.G)

    def test_bullets_keep_sub_items(self):
        b = self.G._bullets('- ACTION REQUIRED: a\n  - sub one\n  - sub two\n- next\n')
        self.assertEqual(len(b), 2)
        self.assertIn('sub two', b[0])

    def test_clean(self):
        self.assertEqual(self.G._clean('Removed `--x` ([#1](https://github.com/kubernetes/kubernetes/pull/1), [@a](https://github.com/a)) [SIG Node]'),
                         'Removed `--x`')


class EngineHookTest(unittest.TestCase):
    def test_hooked(self):
        src = (ROOT / 'src/upgradecheck.py').read_text(encoding='utf-8')
        self.assertIn('UR.collect_extra(', src)
        self.assertIn('UR.evaluate_extra(data, add, passed)', src)
        self.assertIn('UR.extra_checklist(data)', src)
        ui = (ROOT / 'ui/src/upgradeModel.js').read_text(encoding='utf-8')
        for k in ('gate:', 'storage:', 'notes:', 'app:'):
            self.assertIn(k, ui)


if __name__ == '__main__':
    unittest.main()
