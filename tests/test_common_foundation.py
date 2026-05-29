import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polaris
import build
try:
    from scripts import create_releases
    HAS_CREATE_RELEASES = True
except ImportError:
    HAS_CREATE_RELEASES = False


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


class AppLifecycleTests(unittest.TestCase):
    def test_app_uses_polaris_runtime_identity(self):
        self.assertEqual(polaris.VERSION, '1.0.13-e1')
        self.assertIn('.polaris', str(polaris.PolarisAPI._SESSION_PATH))
        self.assertIn('.polaris', str(polaris.PolarisAPI._SETTINGS_PATH))
        self.assertEqual(polaris._WT_SCHEME_NAME, 'Polaris')
        self.assertIn(b'POLARIS', polaris._INSTANCE_SIGNAL)

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
        self.assertNotIn(('docx', 'python-docx'), missing)
        self.assertNotIn(('PyInstaller', 'pyinstaller'), missing)


@unittest.skipUnless(HAS_CREATE_RELEASES, "scripts.create_releases module not found")
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
