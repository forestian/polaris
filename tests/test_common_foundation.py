import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polaris
import build
from scripts import create_releases


class KubectlParsingTests(unittest.TestCase):
    def test_strips_optional_kubectl_prefix_and_preserves_jsonpath(self):
        args = polaris._parse_kubectl_command(
            'kubectl get pods -A -o jsonpath="{.items[*].metadata.name}"'
        )

        self.assertEqual(
            args,
            ['get', 'pods', '-A', '-o', 'jsonpath={.items[*].metadata.name}'],
        )

    def test_preserves_patch_payload_as_one_argument(self):
        args = polaris._parse_kubectl_command(
            "patch deploy api -p '{\"spec\":{\"replicas\":2}}'"
        )

        self.assertEqual(
            args,
            ['patch', 'deploy', 'api', '-p', '{"spec":{"replicas":2}}'],
        )

    def test_rejects_unclosed_quotes(self):
        with self.assertRaises(ValueError):
            polaris._parse_kubectl_command('get pods -o "unterminated')


class NodeMetricsTests(unittest.TestCase):
    def test_builds_node_metrics_from_metrics_api_items(self):
        items = [{
            'metadata': {'name': 'worker-1'},
            'usage': {'cpu': '250m', 'memory': '1024Mi'},
        }]

        self.assertEqual(
            polaris._build_node_metrics(items),
            [{'name': 'worker-1', 'cpu_m': 250, 'mem_mi': 1024}],
        )

    def test_applies_node_metrics_percentages_to_dashboard_node(self):
        node = {
            'name': 'worker-1',
            'cpu_alloc_m': 2000,
            'mem_alloc_mi': 8192,
        }
        metrics = {'name': 'worker-1', 'cpu_m': 500, 'mem_mi': 1024}

        enriched = polaris._apply_node_metric(node, metrics)

        self.assertEqual(enriched['cpu_used_m'], 500)
        self.assertEqual(enriched['mem_used_mi'], 1024)
        self.assertEqual(enriched['cpu_pct'], 25)
        self.assertEqual(enriched['mem_pct'], 12)
        self.assertTrue(enriched['metrics_available'])

    def test_caps_node_metrics_percentages_at_100(self):
        node = {
            'name': 'worker-1',
            'cpu_alloc_m': 1000,
            'mem_alloc_mi': 512,
        }
        metrics = {'name': 'worker-1', 'cpu_m': 2000, 'mem_mi': 2048}

        enriched = polaris._apply_node_metric(node, metrics)

        self.assertEqual(enriched['cpu_pct'], 100)
        self.assertEqual(enriched['mem_pct'], 100)

    def test_marks_node_metrics_unavailable_when_missing(self):
        node = {
            'name': 'worker-1',
            'cpu_alloc_m': 1000,
            'mem_alloc_mi': 512,
        }

        enriched = polaris._apply_node_metric(node, None)

        self.assertFalse(enriched['metrics_available'])
        self.assertEqual(enriched['cpu_pct'], None)
        self.assertEqual(enriched['mem_pct'], None)


class PodExecCommandTests(unittest.TestCase):
    def test_builds_pod_exec_args_without_container(self):
        self.assertEqual(
            polaris._build_pod_exec_args('default', 'web-7d9'),
            ['exec', '-it', '-n', 'default', 'web-7d9', '--', 'sh'],
        )

    def test_builds_pod_exec_args_with_container(self):
        self.assertEqual(
            polaris._build_pod_exec_args('default', 'web-7d9', 'app'),
            ['exec', '-it', '-n', 'default', 'web-7d9', '-c', 'app', '--', 'sh'],
        )

    def test_rejects_missing_pod_exec_target(self):
        with self.assertRaises(ValueError):
            polaris._build_pod_exec_args('', 'web-7d9')
        with self.assertRaises(ValueError):
            polaris._build_pod_exec_args('default', '')


class LogStreamTargetTests(unittest.TestCase):
    def test_normalizes_log_source_type_aliases(self):
        self.assertEqual(polaris._normalize_log_source_type('pods'), 'pod')
        self.assertEqual(polaris._normalize_log_source_type('deployments'), 'deployment')
        self.assertEqual(polaris._normalize_log_source_type('sts'), 'statefulset')
        self.assertEqual(polaris._normalize_log_source_type('ingress'), 'ingress')

    def test_builds_pod_log_args_with_container_and_follow(self):
        self.assertEqual(
            polaris._build_pod_log_args('default', 'web-7d9', 'app', 500, True),
            ['logs', 'web-7d9', '--tail=500', '-n', 'default', '-c', 'app', '--follow'],
        )

    def test_builds_prefixed_multi_pod_log_args(self):
        self.assertEqual(
            polaris._build_pod_log_args('kube-system', 'ingress-nginx-abc', '', 100, False, all_containers=True),
            ['logs', 'ingress-nginx-abc', '--tail=100', '-n', 'kube-system', '--all-containers=true'],
        )

    def test_detects_ingress_controller_pods(self):
        self.assertTrue(polaris._is_ingress_controller_pod(
            'rke2-ingress-nginx-controller-abc',
            {'app.kubernetes.io/name': 'ingress-nginx'},
        ))
        self.assertTrue(polaris._is_ingress_controller_pod('traefik-xyz', {}))
        self.assertFalse(polaris._is_ingress_controller_pod('nginxplus-api', {}))


class PortForwardTests(unittest.TestCase):
    def test_builds_service_port_forward_spec(self):
        spec = polaris._build_port_forward_spec(
            'services', 'monitoring', 'grafana', '3000', '80'
        )

        self.assertEqual(spec['kind'], 'service')
        self.assertEqual(spec['resource'], 'svc/grafana')
        self.assertEqual(spec['local_port'], 3000)
        self.assertEqual(spec['remote_port'], 80)
        self.assertEqual(
            spec['args'],
            ['-n', 'monitoring', 'port-forward', 'svc/grafana', '3000:80'],
        )

    def test_builds_pod_port_forward_spec_with_default_local_port(self):
        spec = polaris._build_port_forward_spec(
            'pod', 'default', 'api-0', '', 8080
        )

        self.assertEqual(spec['kind'], 'pod')
        self.assertEqual(spec['resource'], 'pod/api-0')
        self.assertEqual(spec['local_port'], 8080)
        self.assertEqual(spec['remote_port'], 8080)
        self.assertEqual(
            spec['args'],
            ['-n', 'default', 'port-forward', 'pod/api-0', '8080:8080'],
        )

    def test_rejects_invalid_port_forward_request(self):
        with self.assertRaises(ValueError):
            polaris._build_port_forward_spec('service', '', 'grafana', 3000, 80)
        with self.assertRaises(ValueError):
            polaris._build_port_forward_spec('service', 'monitoring', '', 3000, 80)
        with self.assertRaises(ValueError):
            polaris._build_port_forward_spec('service', 'monitoring', 'grafana', 0, 80)
        with self.assertRaises(ValueError):
            polaris._build_port_forward_spec('service', 'monitoring', 'grafana', 3000, 70000)

    def test_detects_prefixed_streaming_kubectl_commands(self):
        self.assertTrue(polaris._is_kubectl_streaming_args(
            ['-n', 'default', 'logs', '-f', 'api-0']
        ))
        self.assertTrue(polaris._is_kubectl_streaming_args(
            ['--namespace', 'monitoring', 'port-forward', 'svc/grafana', '3000:80']
        ))
        self.assertTrue(polaris._is_kubectl_streaming_args(
            ['get', 'pods', '--watch']
        ))
        self.assertFalse(polaris._is_kubectl_streaming_args(
            ['get', 'pods']
        ))


class TopologyParityTests(unittest.TestCase):
    def test_builds_cronjob_topology_node(self):
        node = polaris._topo_cronjob_node('batch', 'nightly-backup', 'cj-uid', '0 2 * * *')

        self.assertEqual(node['id'], 'cj/batch/nightly-backup')
        self.assertEqual(node['kind'], 'CronJob')
        self.assertEqual(node['schedule'], '0 2 * * *')

    def test_builds_job_topology_workload_node_with_owner(self):
        node = polaris._topo_job_workload_node(
            'batch', 'nightly-backup-28100100', 'job-uid', 'cj-uid',
            succeeded=1, failed=0, active=0, completions=1,
        )

        self.assertEqual(node['id'], 'wl/batch/Job/nightly-backup-28100100')
        self.assertEqual(node['kind'], 'Job')
        self.assertEqual(node['owner_uid'], 'cj-uid')
        self.assertEqual(node['status'], 'Complete')

    def test_maps_job_owned_pods_to_job_workload(self):
        self.assertEqual(
            polaris._topo_pod_workload_owner('Job', 'nightly-backup-28100100', {}),
            ('Job', 'nightly-backup-28100100'),
        )
        self.assertEqual(
            polaris._topo_pod_workload_owner('ReplicaSet', 'web-7d9', {'web-7d9': 'web'}),
            ('Deployment', 'web'),
        )


class ReportParityTests(unittest.TestCase):
    def test_report_required_datasets_include_v2_parity_inputs(self):
        keys = polaris._report_required_dataset_keys()

        for key in (
            'node_metrics', 'jobs', 'cronjobs', 'limit_ranges',
            'ingress_classes', 'events',
        ):
            self.assertIn(key, keys)

    def test_report_findings_include_recommendation_and_priority_fields(self):
        data = {
            'pods': [{
                'namespace': 'default',
                'name': 'api-0',
                'status': 'CrashLoopBackOff',
                'restarts': 250,
            }],
            'services': [{
                'namespace': 'default',
                'name': 'api-nodeport',
                'type': 'NodePort',
                'ports': '32000/TCP',
            }],
            'nodes': [],
            'deployments': [],
            'pvcs': [],
            'pdbs': [],
            'storage_classes': [],
            'kube_system': {'pods': []},
            'hpa': [],
            'hpas': [],
        }

        findings = polaris._report_evaluate(data)

        restart = next(f for f in findings if f['category'] == 'pod_restart')
        self.assertEqual(restart['level'], 'HIGH')
        self.assertEqual(restart['severity'], 'high')
        self.assertEqual(restart['namespace'], 'default')
        self.assertEqual(restart['name'], 'api-0')
        self.assertIn('권장', restart['message'])
        self.assertIn('kubectl logs', restart['rec'])

    def test_report_priority_summary_groups_immediate_and_short_term_actions(self):
        findings = [
            {
                'level': 'CRITICAL', 'severity': 'critical', 'category': 'node_notready',
                'namespace': 'cluster', 'name': 'worker-1', 'value': 'NotReady',
                'detail': 'Node NotReady', 'rec': '노드 상태 확인',
                'message': 'worker-1 NotReady',
            },
            {
                'level': 'WARNING', 'severity': 'medium', 'category': 'hpa',
                'namespace': 'cluster', 'name': 'HPA', 'value': '0개',
                'detail': 'HPA 부족', 'rec': '주요 서비스 HPA 적용',
                'message': 'HPA 부족',
            },
        ]

        summary = polaris._report_build_priority_summary(findings)

        self.assertEqual(summary['counts']['critical'], 1)
        self.assertEqual(summary['counts']['medium'], 1)
        self.assertEqual(summary['immediate'][0]['target'], 'cluster/worker-1')
        self.assertEqual(summary['short_term'][0]['recommendation'], '주요 서비스 HPA 적용')


class ArgoMultiSourceTests(unittest.TestCase):
    def test_transform_argo_summarizes_multi_source_apps(self):
        app = {
            'metadata': {'name': 'api', 'namespace': 'argocd'},
            'spec': {
                'project': 'default',
                'sources': [
                    {'repoURL': 'https://git.example.com/platform.git', 'path': 'base', 'targetRevision': 'main'},
                    {'repoURL': 'https://git.example.com/values.git', 'path': 'prod', 'targetRevision': 'release'},
                ],
                'destination': {'server': 'https://kubernetes.default.svc', 'namespace': 'api'},
            },
            'status': {'sync': {'status': 'Synced'}, 'health': {'status': 'Healthy'}},
        }

        row = polaris.PolarisAPI._transform_argo(app)

        self.assertEqual(row['source_mode'], 'multi')
        self.assertEqual(row['source_count'], 2)
        self.assertEqual(row['repo_url'], 'https://git.example.com/platform.git')
        self.assertEqual(row['path'], 'base')
        self.assertIn('+1', row['repo'])
        self.assertEqual(row['sources'][1]['path'], 'prod')

    def test_build_argocd_spec_preserves_sources_without_single_source(self):
        sources = [
            {'repoURL': 'https://git.example.com/platform.git', 'path': 'base', 'targetRevision': 'main'},
            {'repoURL': 'https://git.example.com/values.git', 'path': 'prod', 'targetRevision': 'release'},
        ]

        spec = polaris._build_argocd_spec(
            project='default',
            repo_url='',
            path='',
            revision='HEAD',
            dest_ns='api',
            dest_server='https://kubernetes.default.svc',
            sync_policy={},
            sources=sources,
        )

        self.assertIn('sources', spec)
        self.assertNotIn('source', spec)
        self.assertEqual(spec['sources'], sources)

    def test_multi_source_sync_operation_omits_single_revision(self):
        op = polaris._build_argocd_sync_operation(is_multi_source=True)

        self.assertNotIn('revision', op['operation']['sync'])
        self.assertFalse(op['operation']['sync']['prune'])


class ResourceEventFilterTests(unittest.TestCase):
    def test_resource_event_selector_includes_kind_and_name(self):
        self.assertEqual(
            polaris._resource_event_field_selector('pods', 'api-0'),
            'involvedObject.kind=Pod,involvedObject.name=api-0',
        )
        self.assertEqual(
            polaris._resource_event_field_selector('deployments', 'api'),
            'involvedObject.kind=Deployment,involvedObject.name=api',
        )

    def test_resource_event_selector_falls_back_to_name_for_unknown_kind(self):
        self.assertEqual(
            polaris._resource_event_field_selector('customthings', 'api'),
            'involvedObject.name=api',
        )


class ResourceWriteArgsTests(unittest.TestCase):
    def test_scale_args_basic(self):
        self.assertEqual(
            polaris._build_scale_args('deployments', 'default', 'web', 3),
            ['-n', 'default', 'scale', 'deployments', 'web', '--replicas=3'],
        )

    def test_scale_args_alias_and_no_namespace(self):
        self.assertEqual(
            polaris._build_scale_args('sts', '', 'db', 0),
            ['scale', 'statefulsets', 'db', '--replicas=0'],
        )

    def test_scale_args_rejects_non_scalable_kind(self):
        with self.assertRaises(ValueError):
            polaris._build_scale_args('pods', 'ns', 'p', 1)
        with self.assertRaises(ValueError):
            polaris._build_scale_args('services', 'ns', 'svc', 1)

    def test_scale_args_rejects_bad_replicas(self):
        with self.assertRaises(ValueError):
            polaris._build_scale_args('deployments', 'ns', 'w', -1)
        with self.assertRaises(ValueError):
            polaris._build_scale_args('deployments', 'ns', 'w', 99999)
        with self.assertRaises(ValueError):
            polaris._build_scale_args('deployments', 'ns', 'w', 'abc')

    def test_scale_args_rejects_bad_name(self):
        with self.assertRaises(ValueError):
            polaris._build_scale_args('deployments', 'ns', 'Bad_Name!', 1)

    def test_restart_args_basic(self):
        self.assertEqual(
            polaris._build_rollout_restart_args('deployment', 'default', 'web'),
            ['-n', 'default', 'rollout', 'restart', 'deployments/web'],
        )

    def test_restart_args_daemonset_no_namespace(self):
        self.assertEqual(
            polaris._build_rollout_restart_args('ds', '', 'fluentd'),
            ['rollout', 'restart', 'daemonsets/fluentd'],
        )

    def test_restart_args_rejects_non_restartable_kind(self):
        with self.assertRaises(ValueError):
            polaris._build_rollout_restart_args('services', 'ns', 'svc')
        with self.assertRaises(ValueError):
            polaris._build_rollout_restart_args('replicasets', 'ns', 'rs')

    def test_normalize_kubectl_kind(self):
        self.assertEqual(polaris._normalize_kubectl_kind('deploy'), 'deployments')
        self.assertEqual(polaris._normalize_kubectl_kind('sts'), 'statefulsets')
        self.assertEqual(polaris._normalize_kubectl_kind('pvc'), 'persistentvolumeclaims')


class VersionerNoiseTests(unittest.TestCase):
    def test_strips_rke2_versioner_download_log(self):
        sample = (
            'I0529 22:07:37.362514 24732 versioner.go:115] Right kubectl missing, '
            'downloading version 1.32.13+rke2r1 Downloading '
            'https://dl.k8s.io/release/v1.32.13/bin/windows/amd64/kubectl.exe\n'
            'kubectl1.32.13+rke2r1.exe 0% |   | (16 kB/60 MB) [0s:0s]\n'
            'kubectl1.32.13+rke2r1.exe 50% |##| (30/60 MB, 3.8 MB/s) [2s:12s]\n'
            'apiVersion: v1\n'
            'kind: Pod\n'
            'metadata:\n'
            '  name: web\n'
        )
        out = polaris._strip_versioner_noise(sample)
        self.assertNotIn('versioner', out)
        self.assertNotIn('Downloading', out)
        self.assertNotIn('.exe ', out)
        self.assertIn('apiVersion: v1', out)
        self.assertIn('kind: Pod', out)
        self.assertTrue(out.startswith('apiVersion: v1'))

    def test_leaves_clean_output_untouched(self):
        clean = 'apiVersion: v1\nkind: Service\nmetadata:\n  name: svc\n'
        self.assertEqual(polaris._strip_versioner_noise(clean), clean)

    def test_handles_carriage_return_progress(self):
        sample = ('kubectl1.32.exe 10% |#| (6/60 MB)\r'
                  'kubectl1.32.exe 90% |####| (54/60 MB)\r'
                  'kind: Pod\n')
        out = polaris._strip_versioner_noise(sample)
        self.assertIn('kind: Pod', out)
        self.assertNotIn('60 MB', out)


class CrdParsingTests(unittest.TestCase):
    def test_parse_ts_iso_string(self):
        from src.k8s import _parse_ts
        dt = _parse_ts('2024-01-01T00:00:00Z')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)
        self.assertIsNotNone(dt.tzinfo)

    def test_parse_ts_none_and_garbage(self):
        from src.k8s import _parse_ts
        self.assertIsNone(_parse_ts(None))
        self.assertIsNone(_parse_ts('not-a-date'))

    def test_crd_api_methods_exist(self):
        api = polaris.PolarisAPI()
        self.assertTrue(callable(getattr(api, 'get_crds', None)))
        self.assertTrue(callable(getattr(api, 'get_crd_objects', None)))

    def test_jsonpath_simple_dot_paths(self):
        from src.k8s import _jsonpath_get
        obj = {'status': {'phase': 'Ready'}, 'spec': {'replicas': 3, 'paused': False}}
        self.assertEqual(_jsonpath_get(obj, '.status.phase'), 'Ready')
        self.assertEqual(_jsonpath_get(obj, '.spec.replicas'), '3')
        self.assertEqual(_jsonpath_get(obj, '.spec.paused'), 'false')

    def test_jsonpath_missing_and_complex(self):
        from src.k8s import _jsonpath_get
        obj = {'status': {'conditions': [{'type': 'Ready'}]}}
        self.assertEqual(_jsonpath_get(obj, '.missing.path'), '')
        self.assertEqual(_jsonpath_get(obj, '.status.conditions'), '')  # list → ''
        self.assertEqual(_jsonpath_get(obj, ''), '')


class SnapshotDiffTests(unittest.TestCase):
    def _payload(self, deployments, pvcs=None):
        return {'meta': {'id': 'x', 'created_at': '2026-01-01 00:00:00'},
                'data': {'deployments': deployments, 'pvcs': pvcs or []}}

    def test_diff_detects_added_removed_changed(self):
        from src.snapshot import diff_snapshots
        a = self._payload([
            {'namespace': 'default', 'name': 'web', 'ready': 2, 'desired': 2},
            {'namespace': 'default', 'name': 'old', 'ready': 1, 'desired': 1},
        ])
        b = self._payload([
            {'namespace': 'default', 'name': 'web', 'ready': 1, 'desired': 3},
            {'namespace': 'default', 'name': 'new', 'ready': 1, 'desired': 1},
        ])
        d = diff_snapshots(a, b)
        self.assertEqual(d['totals'], {'added': 1, 'removed': 1, 'changed': 1})
        dep = next(k for k in d['kinds'] if k['kind'] == 'Deployment')
        self.assertEqual(dep['added'], ['default/new'])
        self.assertEqual(dep['removed'], ['default/old'])
        self.assertEqual(dep['changed'][0]['key'], 'default/web')
        fields = {f['field'] for f in dep['changed'][0]['fields']}
        self.assertIn('desired', fields)
        self.assertIn('ready', fields)

    def test_diff_ignores_age_field(self):
        from src.snapshot import diff_snapshots
        a = self._payload([{'namespace': 'd', 'name': 'w', 'ready': 1, 'age': '1d'}])
        b = self._payload([{'namespace': 'd', 'name': 'w', 'ready': 1, 'age': '8d'}])
        d = diff_snapshots(a, b)
        self.assertEqual(d['totals']['changed'], 0)   # age 만 바뀐 건 무시

    def test_diff_no_change(self):
        from src.snapshot import diff_snapshots
        a = self._payload([{'namespace': 'd', 'name': 'w', 'ready': 1}])
        d = diff_snapshots(a, a)
        self.assertEqual(d['totals'], {'added': 0, 'removed': 0, 'changed': 0})
        self.assertEqual(d['kinds'], [])

    def test_diff_findings_new_resolved(self):
        from src.snapshot import diff_findings
        fa = [{'category': 'pod_restart', 'namespace': 'n', 'name': 'p1'},
              {'category': 'nodeport', 'namespace': 'n', 'name': 'svc1'}]
        fb = [{'category': 'pod_restart', 'namespace': 'n', 'name': 'p1'},
              {'category': 'pvc', 'namespace': 'n', 'name': 'data'}]
        r = diff_findings(fa, fb)
        self.assertEqual([f['category'] for f in r['new']], ['pvc'])
        self.assertEqual([f['category'] for f in r['resolved']], ['nodeport'])
        self.assertEqual(r['persisting_count'], 1)

    def test_snapshot_api_methods_exist(self):
        api = polaris.PolarisAPI()
        for m in ('take_snapshot', 'list_snapshots', 'delete_snapshot', 'diff_snapshots'):
            self.assertTrue(callable(getattr(api, m, None)), m)


class SnapshotEncryptionTests(unittest.TestCase):
    """v1.2.1 — 스냅샷 파일 암호화 (.enc) 회귀 검증."""

    def setUp(self):
        import tempfile
        import src.snapshot as snap
        from src.vault import HAS_CRYPTO, Vault
        if not HAS_CRYPTO:
            self.skipTest('cryptography 미설치')
        self.snap = snap
        self.tmp = Path(tempfile.mkdtemp(prefix='polaris-snap-enc-'))
        self._orig_dir = snap.SNAPSHOT_DIR
        snap.SNAPSHOT_DIR = self.tmp / 'snaps'
        self.vault = Vault(self.tmp / 'vault.json')
        self.vault.create('test1234')   # 생성 직후 unlocked
        self.data = {
            'cluster_version': 'v1.29.0',
            'pods': [{'namespace': 'ns', 'name': 'secret-pod',
                      'image': 'super-secret-image:1.0'}],
            '_findings': [],
        }

    def tearDown(self):
        import shutil
        self.snap.SNAPSHOT_DIR = self._orig_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_encrypts_and_hides_payload(self):
        r = self.snap.save_snapshot(self.data, 'prod', label='L', vault=self.vault)
        self.assertTrue(r['ok'])
        self.assertTrue(r['encrypted'])
        self.assertTrue(r['path'].endswith('.enc'))
        raw = Path(r['path']).read_text(encoding='utf-8')
        # 민감한 data 는 raw 파일에서 보이면 안 됨
        self.assertNotIn('secret-pod', raw)
        self.assertNotIn('super-secret-image', raw)
        self.assertIn(self.snap._ENC_FORMAT, raw)

    def test_roundtrip_and_lock_behavior(self):
        r = self.snap.save_snapshot(self.data, 'prod', vault=self.vault)
        sid = r['id']
        # 목록은 vault 없이도 meta 표시 (암호화 플래그 포함)
        items = self.snap.list_snapshots()
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]['encrypted'])
        # vault 해제 상태 → 복호화 성공
        loaded = self.snap.load_snapshot(sid, vault=self.vault)
        self.assertEqual(loaded['data']['pods'][0]['name'], 'secret-pod')
        # 잠금 → load None
        self.vault.lock()
        self.assertIsNone(self.snap.load_snapshot(sid, vault=self.vault))
        # vault 없이 .enc load → None
        self.assertIsNone(self.snap.load_snapshot(sid, vault=None))

    def test_save_rejected_when_locked(self):
        self.vault.lock()
        r = self.snap.save_snapshot(self.data, 'prod', vault=self.vault)
        self.assertFalse(r['ok'])   # 평문 저장 금지

    def test_legacy_json_still_readable(self):
        # crypto 없는 경우(vault=None) → 평문 .json 으로 저장되고 다시 읽힘
        r = self.snap.save_snapshot(self.data, 'legacy', vault=None)
        self.assertTrue(r['ok'])
        self.assertFalse(r['encrypted'])
        self.assertTrue(r['path'].endswith('.json'))
        loaded = self.snap.load_snapshot(r['id'], vault=None)
        self.assertEqual(loaded['data']['pods'][0]['name'], 'secret-pod')


class RbacApiTests(unittest.TestCase):
    def test_rbac_api_methods_exist(self):
        api = polaris.PolarisAPI()
        self.assertTrue(callable(getattr(api, 'get_rbac', None)))

    def test_k8smanager_rbac_methods_exist(self):
        from src.k8s import K8sManager
        mgr = K8sManager()
        for m in ('get_rbac_roles', 'get_rbac_bindings', 'get_service_accounts'):
            self.assertTrue(callable(getattr(mgr, m, None)), m)

    def test_rbac_returns_error_when_disconnected(self):
        api = polaris.PolarisAPI()
        r = api.get_rbac()
        self.assertFalse(r.get('ok'))


class RbacRiskyReportTests(unittest.TestCase):
    """v1.2.2 — 과도 권한 SA → 보고서 발견사항."""

    def _mgr(self):
        from src.k8s import K8sManager
        mgr = K8sManager()
        mgr.get_rbac_roles = lambda inc=False: [
            {'kind': 'ClusterRole', 'name': 'cluster-admin', 'namespace': '',
             'rules': [{'verbs': ['*'], 'resources': ['*'], 'apiGroups': ['*']}]},
            {'kind': 'ClusterRole', 'name': 'custom-wild', 'namespace': '',
             'rules': [{'verbs': ['*'], 'resources': ['*'], 'apiGroups': ['*']}]},
            {'kind': 'Role', 'name': 'reader', 'namespace': 'app',
             'rules': [{'verbs': ['get'], 'resources': ['pods'], 'apiGroups': ['']}]},
        ]
        mgr.get_rbac_bindings = lambda inc=False: [
            {'kind': 'ClusterRoleBinding', 'name': 'admin-binding', 'namespace': '',
             'role_ref': {'kind': 'ClusterRole', 'name': 'cluster-admin'},
             'subjects': [{'kind': 'ServiceAccount', 'name': 'ci-deployer', 'namespace': 'ci'},
                          {'kind': 'Group', 'name': 'system:masters', 'namespace': ''}]},
            {'kind': 'RoleBinding', 'name': 'wild-binding', 'namespace': 'app',
             'role_ref': {'kind': 'ClusterRole', 'name': 'custom-wild'},
             'subjects': [{'kind': 'User', 'name': 'alice', 'namespace': ''}]},
            {'kind': 'RoleBinding', 'name': 'reader-binding', 'namespace': 'app',
             'role_ref': {'kind': 'Role', 'name': 'reader'},
             'subjects': [{'kind': 'ServiceAccount', 'name': 'viewer', 'namespace': 'app'}]},
        ]
        return mgr

    def test_detects_admin_and_wildcard_excludes_system_and_normal(self):
        risky = self._mgr().get_rbac_risky_subjects()
        names = sorted(r['name'] for r in risky)
        self.assertEqual(names, ['alice', 'ci-deployer'])   # system:masters / viewer 제외

    def test_evaluate_emits_rbac_findings_with_severity(self):
        from src.reports import _report_evaluate
        risky = self._mgr().get_rbac_risky_subjects()
        findings = _report_evaluate({'rbac_risky': risky})
        rbac = [f for f in findings if f['category'] == 'rbac']
        self.assertEqual(len(rbac), 2)
        by_name = {f['name']: f for f in rbac}
        # ServiceAccount 가 cluster-admin → critical
        self.assertEqual(by_name['ServiceAccount/ci-deployer']['severity'], 'critical')
        self.assertEqual(by_name['User/alice']['severity'], 'high')

    def test_no_risky_no_findings(self):
        from src.reports import _report_evaluate
        findings = _report_evaluate({})
        self.assertEqual([f for f in findings if f['category'] == 'rbac'], [])

    def test_method_exists(self):
        from src.k8s import K8sManager
        self.assertTrue(callable(getattr(K8sManager(), 'get_rbac_risky_subjects', None)))


class K9sLaunchTests(unittest.TestCase):
    def test_k9s_launch_command_uses_windows_terminal_when_available(self):
        original_find = polaris._find_windows_terminal
        original_inject = polaris._inject_wt_polaris_scheme
        try:
            # 헬퍼는 src.tools 모듈에 있으므로 거기에 monkey-patch 해야 함
            import src.tools as src_tools
            src_tools._find_windows_terminal = lambda: r'C:\Users\me\AppData\Local\Microsoft\WindowsApps\wt.exe'
            src_tools._inject_wt_polaris_scheme = lambda: True

            cmd, terminal = polaris._build_k9s_launch_command(
                r'C:\Program Files\k9s\k9s.exe',
                r'C:\Users\me\.kube\prod.yaml',
            )
        finally:
            src_tools._find_windows_terminal = original_find
            src_tools._inject_wt_polaris_scheme = original_inject

        self.assertEqual(terminal, 'Windows Terminal')
        self.assertEqual(cmd[:6], [
            r'C:\Users\me\AppData\Local\Microsoft\WindowsApps\wt.exe',
            'new-tab',
            '--title',
            'Polaris — k9s',
            '--tabColor',
            '#060914',
        ])
        self.assertIn('--colorScheme', cmd)
        self.assertIn('--kubeconfig', cmd)
        self.assertIn(r'C:\Users\me\.kube\prod.yaml', cmd)

    def test_k9s_launch_command_falls_back_to_cmd(self):
        import src.tools as src_tools
        original_find = src_tools._find_windows_terminal
        try:
            src_tools._find_windows_terminal = lambda: None

            cmd, terminal = polaris._build_k9s_launch_command(
                r'C:\Program Files\k9s\k9s.exe',
                r'C:\Users\me\.kube\prod.yaml',
            )
        finally:
            src_tools._find_windows_terminal = original_find

        self.assertEqual(terminal, 'CMD')
        self.assertEqual(cmd[:6], ['cmd.exe', '/c', 'start', 'Polaris k9s', 'cmd.exe', '/k'])
        self.assertIn('--kubeconfig', cmd)
        self.assertIn(r'C:\Users\me\.kube\prod.yaml', cmd)


class OptionalPluginDiscoveryTests(unittest.TestCase):
    """옵셔널 plugin 자동 발견 메커니즘 회귀 테스트.

    v1.0.10 버그: _discover_optional_mixins 가 glob('*.py') 에만 의존했는데
    PyInstaller frozen EXE 는 .py 를 PYZ 아카이브에 패킹하므로 glob 이 빈
    목록을 반환 → plugin 미발견 → 앱 카탈로그 'n[e] is not a function'.
    v1.0.11 수정: pkgutil.iter_modules 를 우선 사용해 frozen 에서도 동작.
    """

    def test_discovery_independent_of_filesystem_glob(self):
        # frozen EXE 시뮬레이션: glob('*.py') 가 아무 파일도 못 찾아도
        # pkgutil.iter_modules 만으로 동일한 plugin 집합을 발견해야 한다.
        # (catalog 가 제거된 variant 빌드에서는 양쪽 다 빈 집합 → 여전히 일치)
        from unittest import mock
        import src.api as api_pkg

        baseline = {fid for fid, _ in api_pkg._discover_optional_mixins()}
        with mock.patch.object(Path, 'glob', return_value=()):
            frozen_like = {fid for fid, _ in api_pkg._discover_optional_mixins()}

        self.assertEqual(
            baseline, frozen_like,
            'glob 없이(frozen EXE) plugin 발견 결과가 달라짐 — '
            'pkgutil.iter_modules 경로가 동작하지 않음',
        )

    def test_enabled_features_reflect_discovery(self):
        # ENABLED_FEATURES 는 발견된 옵셔널 plugin id 와 일치해야 한다.
        import src.api as api_pkg
        discovered = tuple(fid for fid, _ in api_pkg._discover_optional_mixins())
        self.assertEqual(api_pkg.ENABLED_FEATURES, discovered)
        # 발견된 각 plugin 의 메서드가 PolarisAPI 에 실제로 합성됐는지 확인.
        if 'catalog' in api_pkg.ENABLED_FEATURES:
            self.assertTrue(hasattr(api_pkg.PolarisAPI, 'get_catalog'))


class AppLifecycleTests(unittest.TestCase):
    def test_app_uses_polaris_runtime_identity(self):
        # 패치 버전은 작업마다 자동으로 오르고, variant 빌드는 -eN 접미사를 붙이므로
        # 정확한 패치 숫자 대신 형식(major.minor.patch[-variant])을 검증한다.
        self.assertRegex(polaris.VERSION, r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$')
        self.assertIn('.polaris', str(polaris.PolarisAPI._SESSION_PATH))
        self.assertIn('.polaris', str(polaris.PolarisAPI._SETTINGS_PATH))
        self.assertEqual(polaris._WT_SCHEME_NAME, 'Polaris')
        self.assertIn(b'POLARIS', polaris._INSTANCE_SIGNAL)

    def test_selfcheck_reports_infra_api_surface_when_enabled(self):
        # variant 빌드(polaris-free 등 infra 제거)에서는 건너뜀
        from src.api import ENABLED_FEATURES
        if 'infra' not in ENABLED_FEATURES:
            self.skipTest('infra plugin 미포함 (variant 빌드)')

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = polaris._selfcheck()

        self.assertEqual(rc, 0)
        report = json.loads(buf.getvalue())

        self.assertIn('infra', report['enabled_features'])
        for method in ('vault_status', 'list_servers', 'start_ssh_session'):
            self.assertTrue(report['api_methods'].get(method), method)
        self.assertTrue(report['infra_dependencies']['cryptography'])
        self.assertTrue(report['infra_dependencies']['paramiko'])

    def test_settings_persist_known_theme_id(self):
        original_settings_path = polaris.PolarisAPI._SETTINGS_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                polaris.PolarisAPI._SETTINGS_PATH = Path(tmp) / 'settings.json'
                api = polaris.PolarisAPI()

                saved = api.save_settings({
                    'closeBehavior': 'exit',
                    'autoRestore': False,
                    'themeId': 'aurora',
                })

                self.assertTrue(saved['ok'])
                self.assertEqual(saved['settings']['themeId'], 'aurora')
                self.assertEqual(api.get_settings()['themeId'], 'aurora')
        finally:
            polaris.PolarisAPI._SETTINGS_PATH = original_settings_path

    def test_settings_fall_back_to_polaris_for_unknown_theme_id(self):
        original_settings_path = polaris.PolarisAPI._SETTINGS_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                polaris.PolarisAPI._SETTINGS_PATH = Path(tmp) / 'settings.json'
                api = polaris.PolarisAPI()

                saved = api.save_settings({'themeId': 'unknown'})

                self.assertTrue(saved['ok'])
                self.assertEqual(saved['settings']['themeId'], 'polaris')
                self.assertEqual(api.get_settings()['themeId'], 'polaris')
        finally:
            polaris.PolarisAPI._SETTINGS_PATH = original_settings_path

    def test_tray_close_hides_window_without_synchronous_js_notification(self):
        class FakeWindow:
            def __init__(self):
                self.hidden = False

            def hide(self):
                self.hidden = True

        class FakeApi:
            def _load_settings_raw(self):
                return {'closeBehavior': 'tray'}

            def _notify_visibility(self, state):
                raise AssertionError('closing must not call evaluate_js notification')

            def _disconnect_all_clusters(self):
                raise AssertionError('tray close must not disconnect clusters')

        window = FakeWindow()
        result = polaris._handle_window_closing(FakeApi(), window, {'force_quit': False})

        self.assertFalse(result)
        self.assertTrue(window.hidden)

    def test_exit_close_clears_saved_session_before_shutdown(self):
        class FakeWindow:
            def hide(self):
                raise AssertionError('exit close must not hide the window')

        class FakeApi:
            def __init__(self):
                self.cleared = False
                self.disconnected = False
                self.session_blocked = False

            def _load_settings_raw(self):
                return {'closeBehavior': 'exit', 'autoRestore': True}

            def _disable_session_persistence(self):
                self.session_blocked = True

            def clear_session(self):
                self.cleared = True
                return {'ok': True}

            def _disconnect_all_clusters(self):
                self.disconnected = True

        api = FakeApi()
        result = polaris._handle_window_closing(api, FakeWindow(), {'force_quit': False})

        self.assertTrue(result)
        self.assertTrue(api.session_blocked)
        self.assertTrue(api.cleared)
        self.assertTrue(api.disconnected)

    def test_full_quit_clears_saved_session_even_when_auto_restore_enabled(self):
        class FakeWindow:
            def __init__(self):
                self.destroyed = False

            def destroy(self):
                self.destroyed = True

        class FakeApi:
            def __init__(self):
                self.cleared = False
                self.disconnected = False
                self.session_blocked = False

            def _disable_session_persistence(self):
                self.session_blocked = True

            def clear_session(self):
                self.cleared = True
                return {'ok': True}

            def _disconnect_all_clusters(self):
                self.disconnected = True

        api = FakeApi()
        window = FakeWindow()
        tray_state = {'force_quit': False}

        polaris._perform_full_quit(api, window, tray_state)

        self.assertTrue(tray_state['force_quit'])
        self.assertTrue(api.session_blocked)
        self.assertTrue(api.cleared)
        self.assertTrue(api.disconnected)
        self.assertTrue(window.destroyed)

    def test_full_shutdown_blocks_late_session_saves(self):
        original_session_path = polaris.PolarisAPI._SESSION_PATH
        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / 'session.json'
            polaris.PolarisAPI._SESSION_PATH = session_path
            try:
                api = polaris.PolarisAPI()
                self.assertEqual(api.save_session({'version': 1, 'clusters': [{'path': 'old'}]}), {'ok': True})
                self.assertTrue(session_path.exists())

                polaris._prepare_full_shutdown(api)
                self.assertFalse(session_path.exists())
                self.assertEqual(
                    api.save_session({'version': 1, 'clusters': [{'path': 'late'}]}),
                    {'ok': True, 'skipped': True},
                )
                self.assertFalse(session_path.exists())
            finally:
                polaris.PolarisAPI._SESSION_PATH = original_session_path

    def test_queue_lifecycle_action_returns_immediately(self):
        import queue

        actions = queue.Queue()

        self.assertTrue(polaris._queue_lifecycle_action(actions, polaris._LIFECYCLE_OPEN))
        self.assertEqual(actions.get_nowait(), polaris._LIFECYCLE_OPEN)

    def test_existing_instance_notification_requires_ack(self):
        original_connect = polaris.socket.create_connection

        class FakeSocket:
            def __init__(self, response):
                self.response = response
                self.sent = b''

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def settimeout(self, timeout):
                self.timeout = timeout

            def sendall(self, data):
                self.sent += data

            def recv(self, size):
                return self.response

        try:
            polaris.socket.create_connection = lambda addr, timeout: FakeSocket(polaris._INSTANCE_ACK)
            self.assertTrue(polaris._notify_existing_instance())

            polaris.socket.create_connection = lambda addr, timeout: FakeSocket(b'NO\n')
            self.assertFalse(polaris._notify_existing_instance())
        finally:
            polaris.socket.create_connection = original_connect


class BuildToolSelectionTests(unittest.TestCase):
    def test_resolves_windows_cmd_shims_before_subprocess(self):
        resolved = build._resolve_command_path(
            ['corepack', 'npm'],
            which=lambda name: f'C:/Program Files/nodejs/{name}.CMD' if name == 'corepack' else None,
        )

        self.assertEqual(
            resolved,
            ['C:/Program Files/nodejs/corepack.CMD', 'npm'],
        )

    def test_prefers_working_npm(self):
        original = build._command_works
        try:
            build._command_works = lambda cmd: cmd == ['npm']
            self.assertEqual(build._resolve_npm_command(), ['npm'])
        finally:
            build._command_works = original

    def test_falls_back_to_corepack_npm_when_npm_is_broken(self):
        original = build._command_works
        try:
            build._command_works = lambda cmd: cmd == ['corepack', 'npm']
            self.assertEqual(build._resolve_npm_command(), ['corepack', 'npm'])
        finally:
            build._command_works = original

    def test_normalizes_generated_html_to_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'index.html'
            path.write_bytes(b'<html>\r\n<body></body>\r\n</html>\r\n')

            build._normalize_text_file(path)

            self.assertEqual(path.read_bytes(), b'<html>\n<body></body>\n</html>\n')

    def test_detects_missing_direct_node_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            ui_dir = Path(tmp)
            (ui_dir / 'package.json').write_text(
                json.dumps({
                    'dependencies': {
                        '@xterm/xterm': '^6.0.0',
                        'react': '^18.0.0',
                    },
                    'devDependencies': {
                        'vite': '^8.0.0',
                    },
                }),
                encoding='utf-8',
            )
            (ui_dir / 'node_modules' / 'react').mkdir(parents=True)

            missing = build._missing_node_modules_dependencies(ui_dir)

        self.assertIn('@xterm/xterm', missing)
        self.assertIn('vite', missing)
        self.assertNotIn('react', missing)

    def test_reports_missing_pyinstaller_runtime_dependencies(self):
        available = {'docx', 'PyInstaller'}
        checker = getattr(build, '_missing_runtime_imports', None)

        self.assertIsNotNone(checker)

        missing = checker(
            find_spec=lambda name: object() if name in available else None
        )

        self.assertIn(('kubernetes', 'kubernetes'), missing)
        self.assertIn(('webview', 'pywebview'), missing)
        self.assertIn(('pystray', 'pystray'), missing)
        self.assertIn(('PIL', 'Pillow'), missing)
        self.assertIn(('cryptography', 'cryptography'), missing)
        self.assertIn(('paramiko', 'paramiko'), missing)
        self.assertNotIn(('docx', 'python-docx'), missing)
        self.assertNotIn(('PyInstaller', 'pyinstaller'), missing)


class ReleaseScriptTests(unittest.TestCase):
    def test_create_release_links_single_polaris_exe_artifact(self):
        calls = []
        original = create_releases.api_request
        try:
            create_releases.api_request = lambda method, path, body=None: calls.append((method, path, body)) or {'_links': {'self': 'ok'}}

            create_releases.create_release('v1.0.6', '세션 공유 WAS', 'release body')
        finally:
            create_releases.api_request = original

        payload = calls[0][2]
        link = payload['assets']['links'][0]
        self.assertEqual(link['name'], 'polaris.exe')
        self.assertIn('/-/raw/v1.0.6/dist/polaris.exe?inline=false', link['url'])
        self.assertIn('[polaris.exe]', payload['description'])


if __name__ == '__main__':
    unittest.main()
