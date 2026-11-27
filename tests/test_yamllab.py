# -*- coding: utf-8 -*-
"""YAML 실험실 — 순수 함수 + SQLite 저장소 회귀 테스트 (클러스터 불필요).

특히 두 가지를 잠근다:
  - plan_export 가 **남의 파일을 덮어쓰거나 선택 폴더 밖으로 나가지 않는지**
  - _run_kubectl_rc 가 종료코드를 **실제로 전달하는지** (v1.2.123 교훈 — 값을 선언만
    하고 실제로는 안 지켜지는 부류의 버그를 잡기 위해 도달 여부를 본다)
"""
import tempfile
import unittest
from pathlib import Path

from src.yamllab import (
    open_db, list_manifests, get_manifest, get_version_content,
    save_manifest, delete_manifest, record_apply, export_items,
    parse_targets, target_namespaces, scan_secrets,
    version_diff, scope_diff, plan_export, join_documents, safe_filename,
)

_DEPLOY = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: demo
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: web
          image: nginx:1.27
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: demo
spec:
  ports:
    - port: 80
"""


class TestParseTargets(unittest.TestCase):
    def test_multi_document(self):
        t = parse_targets(_DEPLOY)
        self.assertEqual([x['kind'] for x in t], ['Deployment', 'Service'])
        self.assertTrue(all(x['namespace'] == 'demo' for x in t))

    def test_missing_namespace_is_blank_not_guessed(self):
        t = parse_targets('kind: Pod\nmetadata:\n  name: p\n')
        self.assertEqual(t[0]['namespace'], '')

    def test_garbage_does_not_raise(self):
        self.assertEqual(parse_targets('%%%not yaml%%%\n\t- ['), [])
        self.assertEqual(parse_targets(''), [])

    def test_scalar_document_skipped(self):
        self.assertEqual(parse_targets('just a string\n'), [])


class TestTargetNamespaces(unittest.TestCase):
    def test_default_filled_for_namespaced(self):
        t = [{'kind': 'Pod', 'namespace': '', 'name': 'p'}]
        self.assertEqual(target_namespaces(t), ['default'])

    def test_cluster_scoped_not_given_default(self):
        """Namespace·PV 같은 클러스터 스코프에 default 를 붙이면 엉뚱한 ns 를 관찰하게 된다."""
        t = [{'kind': 'Namespace', 'namespace': '', 'name': 'demo'},
             {'kind': 'PersistentVolume', 'namespace': '', 'name': 'pv1'}]
        self.assertEqual(target_namespaces(t), [])

    def test_dedup_and_order(self):
        t = [{'kind': 'Pod', 'namespace': 'b', 'name': '1'},
             {'kind': 'Pod', 'namespace': 'a', 'name': '2'},
             {'kind': 'Pod', 'namespace': 'b', 'name': '3'}]
        self.assertEqual(target_namespaces(t), ['b', 'a'])


class TestScanSecrets(unittest.TestCase):
    def test_detects_env_name_value_pair(self):
        """컨테이너 env 는 대부분 이 형태 — 이걸 놓치면 사실상 아무것도 못 잡는다."""
        y = 'env:\n  - name: DB_PASSWORD\n    value: hunter2\n'
        hits = scan_secrets(y)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['key'], 'DB_PASSWORD')
        self.assertEqual(hits[0]['line'], 2)   # value 줄이 아니라 name 줄을 가리켜야 유용

    def test_compound_keys_are_caught(self):
        """\\b 경계를 쓰면 밑줄·camelCase 합성어를 전부 놓친다 — 그 회귀를 잠근다."""
        for key in ('DB_PASSWORD', 'apiToken', 'api_key', 'privateKey', 'clientSecret'):
            self.assertEqual(len(scan_secrets(f'{key}: literal-value\n')), 1, key)

    def test_reference_style_keys_not_flagged(self):
        """secretName(Ingress TLS)·secretKeyRef 는 올바른 사용법이다."""
        for key in ('secretName', 'secretKeyRef', 'tokenPath'):
            self.assertEqual(scan_secrets(f'{key}: something\n'), [], key)

    def test_detects_inline_token_key(self):
        hits = scan_secrets('apiToken: abc123def\n')
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['line'], 1)

    def test_value_from_is_not_flagged(self):
        """secretKeyRef 로 참조하는 건 올바른 방식 — 경고하면 노이즈다."""
        y = ('env:\n  - name: DB_PASSWORD\n    valueFrom:\n'
             '      secretKeyRef:\n        name: db\n        key: password\n')
        self.assertEqual(scan_secrets(y), [])

    def test_placeholder_is_not_flagged(self):
        for v in ('{{ .Values.pw }}', '${DB_PASS}', '<채워넣기>', '""'):
            self.assertEqual(scan_secrets(f'password: {v}\n'), [], v)

    def test_base64_secret_data_block_not_flagged(self):
        """kind: Secret 의 data 블록은 어차피 적용이 차단된다 — 여기서 또 경고하지 않는다."""
        y = ('apiVersion: v1\nkind: Secret\nmetadata:\n  name: s\n'
             'data:\n  password: aHVudGVyMg==\n  token: eHl6\n')
        self.assertEqual(scan_secrets(y), [])

    def test_comment_ignored(self):
        self.assertEqual(scan_secrets('# password: hunter2\n'), [])


class TestPlanExport(unittest.TestCase):
    def test_collision_does_not_overwrite(self):
        """같은 이름 3건이 서로를 덮어쓰면 사용자가 조용히 데이터를 잃는다."""
        items = [{'name': 'web', 'cluster': 'c1', 'content': 'a'},
                 {'name': 'web', 'cluster': 'c1', 'content': 'b'},
                 {'name': 'web', 'cluster': 'c1', 'content': 'c'}]
        paths = [e['rel_path'] for e in plan_export(items, by_cluster=True)]
        self.assertEqual(len(set(paths)), 3, paths)
        self.assertEqual(paths[0], 'c1/web.yaml')
        self.assertEqual(paths[1], 'c1/web-2.yaml')

    def test_same_name_different_cluster_keeps_both(self):
        items = [{'name': 'web', 'cluster': 'c1', 'content': 'a'},
                 {'name': 'web', 'cluster': 'c2', 'content': 'b'}]
        paths = [e['rel_path'] for e in plan_export(items, by_cluster=True)]
        self.assertEqual(paths, ['c1/web.yaml', 'c2/web.yaml'])

    def test_by_cluster_off_flattens(self):
        items = [{'name': 'web', 'cluster': 'c1', 'content': 'a'}]
        self.assertEqual(plan_export(items, by_cluster=False)[0]['rel_path'], 'web.yaml')

    def test_path_traversal_neutralised(self):
        """이름에 경로 구분자·.. 가 섞여도 선택 폴더 밖으로 나가면 안 된다."""
        items = [{'name': '../../etc/passwd', 'cluster': '../..', 'content': 'x'}]
        rel = plan_export(items, by_cluster=True)[0]['rel_path']
        self.assertNotIn('..', rel)
        self.assertFalse(Path(rel).is_absolute())
        # 실제로 합쳐도 root 안에 머무는지
        root = Path(tempfile.gettempdir()).resolve() / 'lab-root'
        self.assertIn(root, (root / rel).resolve().parents)

    def test_content_gets_trailing_newline(self):
        e = plan_export([{'name': 'a', 'cluster': '', 'content': 'x'}], by_cluster=False)[0]
        self.assertTrue(e['content'].endswith('\n'))

    def test_empty_name_falls_back(self):
        e = plan_export([{'name': '', 'cluster': '', 'content': 'x'}], by_cluster=False)[0]
        self.assertEqual(e['rel_path'], 'manifest.yaml')


class TestSafeFilename(unittest.TestCase):
    def test_strips_separators(self):
        for bad in ('a/b', 'a\\b', '../a', 'a:b'):
            self.assertNotRegex(safe_filename(bad), r'[/\\:.]{2}|[/\\:]')


class TestJoinDocuments(unittest.TestCase):
    def test_separator_and_header(self):
        text = join_documents([{'name': 'a', 'cluster': 'c1', 'content': 'x: 1'},
                               {'name': 'b', 'cluster': '', 'content': 'y: 2'}])
        self.assertIn('\n---\n', text)
        self.assertIn('# a', text)
        self.assertIn('tested on: c1', text)

    def test_empty_returns_empty(self):
        self.assertEqual(join_documents([]), '')


class TestVersionDiff(unittest.TestCase):
    def test_detects_change(self):
        d = version_diff('replicas: 1\n', 'replicas: 3\n')
        self.assertIn('-replicas: 1', d)
        self.assertIn('+replicas: 3', d)

    def test_identical_is_empty(self):
        self.assertEqual(version_diff('a\n', 'a\n'), '')


class TestScopeDiff(unittest.TestCase):
    def test_added_removed_changed(self):
        before = {'pods': [{'namespace': 'demo', 'name': 'old', 'phase': 'Running'},
                           {'namespace': 'demo', 'name': 'keep', 'phase': 'Running'}]}
        after = {'pods': [{'namespace': 'demo', 'name': 'keep', 'phase': 'Pending'},
                          {'namespace': 'demo', 'name': 'new', 'phase': 'Running'}]}
        r = scope_diff(before, after)
        pods = next(k for k in r['kinds'] if k['kind'] == 'Pod')
        self.assertEqual(pods['added'], ['demo/new'])
        self.assertEqual(pods['removed'], ['demo/old'])
        self.assertEqual(pods['changed'][0]['key'], 'demo/keep')
        self.assertEqual(r['totals'], {'added': 1, 'removed': 1, 'changed': 1})

    def test_no_change_gives_empty_kinds(self):
        same = {'pods': [{'namespace': 'd', 'name': 'p', 'phase': 'Running'}]}
        r = scope_diff(same, same)
        self.assertEqual(r['kinds'], [])
        self.assertEqual(r['totals'], {'added': 0, 'removed': 0, 'changed': 0})

    def test_replicaset_is_covered(self):
        """_DIFF_KINDS 에는 없는 kind — Deployment 적용 시 가장 보고 싶은 파급이다."""
        r = scope_diff({'replicasets': []},
                       {'replicasets': [{'namespace': 'd', 'name': 'web-abc', 'desired': 1}]})
        self.assertEqual(r['kinds'][0]['kind'], 'ReplicaSet')


class TestStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = open_db(Path(self._tmp.name) / 'lab.db')

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_save_creates_then_versions(self):
        r1 = save_manifest(self.conn, None, 'web', _DEPLOY, cluster='c1')
        self.assertTrue(r1['ok'])
        mid = r1['id']
        r2 = save_manifest(self.conn, mid, 'web', _DEPLOY.replace('replicas: 1', 'replicas: 3'),
                           cluster='c1')
        self.assertTrue(r2['new_version'])
        item = get_manifest(self.conn, mid)
        self.assertEqual(len(item['versions']), 2)
        self.assertIn('replicas: 3', item['content'])   # 최신이 앞

    def test_identical_content_does_not_add_version(self):
        """저장 버튼 연타로 이력이 쓰레기로 차면 안 된다."""
        mid = save_manifest(self.conn, None, 'web', _DEPLOY)['id']
        r = save_manifest(self.conn, mid, 'web', _DEPLOY)
        self.assertFalse(r['new_version'])
        self.assertEqual(len(get_manifest(self.conn, mid)['versions']), 1)

    def test_namespace_extracted_from_yaml(self):
        mid = save_manifest(self.conn, None, 'web', _DEPLOY)['id']
        self.assertEqual(get_manifest(self.conn, mid)['namespace'], 'demo')

    def test_save_returns_secret_warnings(self):
        r = save_manifest(self.conn, None, 'x', 'apiToken: abc123\n')
        self.assertTrue(r['ok'])
        self.assertTrue(r['warnings'])   # 경고는 하되 저장은 성공

    def test_fts_finds_by_body(self):
        save_manifest(self.conn, None, '아무이름', _DEPLOY)
        self.assertEqual(len(list_manifests(self.conn, 'nginx')), 1)
        self.assertEqual(len(list_manifests(self.conn, '존재하지않는문자열')), 0)

    def test_search_by_name_and_tag(self):
        save_manifest(self.conn, None, 'web-front', _DEPLOY, tags='운영,테스트')
        self.assertEqual(len(list_manifests(self.conn, 'front')), 1)
        self.assertEqual(len(list_manifests(self.conn, '운영')), 1)

    def test_fts_special_chars_do_not_crash(self):
        save_manifest(self.conn, None, 'web', _DEPLOY)
        for q in ('"', 'a AND', 'x*(', "it's"):
            self.assertIsInstance(list_manifests(self.conn, q), list)

    def test_delete_cascades(self):
        mid = save_manifest(self.conn, None, 'web', _DEPLOY)['id']
        vid = get_manifest(self.conn, mid)['current_version_id']
        record_apply(self.conn, vid, 'c1', True, 'created', {'totals': {}})
        self.assertTrue(delete_manifest(self.conn, mid))
        self.assertEqual(get_manifest(self.conn, mid), {})
        self.assertEqual(get_version_content(self.conn, vid), '')
        left = self.conn.execute('SELECT COUNT(*) c FROM applies').fetchone()['c']
        self.assertEqual(left, 0, 'ON DELETE CASCADE 가 안 걸렸다 (PRAGMA foreign_keys)')

    def test_apply_history_recorded(self):
        mid = save_manifest(self.conn, None, 'web', _DEPLOY)['id']
        vid = get_manifest(self.conn, mid)['current_version_id']
        record_apply(self.conn, vid, 'c1', True, 'deployment/web created', {})
        item = get_manifest(self.conn, mid)
        self.assertEqual(len(item['applies']), 1)
        self.assertEqual(item['applies'][0]['ok'], 1)

    def test_export_items_returns_latest_version(self):
        mid = save_manifest(self.conn, None, 'web', 'v: 1\n', cluster='c1')['id']
        save_manifest(self.conn, mid, 'web', 'v: 2\n', cluster='c1')
        items = export_items(self.conn, [mid])
        self.assertEqual(items[0]['content'], 'v: 2\n')
        self.assertEqual(items[0]['cluster'], 'c1')

    def test_export_items_empty_ids(self):
        self.assertEqual(export_items(self.conn, []), [])


class TestRunKubectlRcPropagates(unittest.TestCase):
    """종료코드가 **실제로 호출자까지 도달하는지** 본다.

    kubectl diff 는 차이가 있으면 exit 1 이다. 여기서 코드가 유실되면 정상 diff 를
    오류로 신고하게 된다 — 선언이 아니라 도달을 확인해야 하는 이유.
    """

    def _fake_run(self, rc):
        class _R:
            returncode = rc
            stdout = 'OUT'
            stderr = 'ERR'
        return lambda *a, **kw: _R()

    def test_each_exit_code_reaches_caller(self):
        import src.tools as tools
        orig_run, orig_find = tools.subprocess.run, tools._find_kubectl
        tools._find_kubectl = lambda *a: 'kubectl'
        try:
            for rc in (0, 1, 2, 127):
                tools.subprocess.run = self._fake_run(rc)
                got, out, err = tools._run_kubectl_rc('kc', ['diff', '-f', '-'])
                self.assertEqual(got, rc)
                self.assertEqual((out, err), ('OUT', 'ERR'))
        finally:
            tools.subprocess.run, tools._find_kubectl = orig_run, orig_find

    def test_missing_kubectl_is_minus_one(self):
        import src.tools as tools
        orig = tools._find_kubectl
        tools._find_kubectl = lambda *a: None
        try:
            rc, _out, err = tools._run_kubectl_rc('kc', ['diff'])
            self.assertEqual(rc, -1)
            self.assertIn('kubectl', err)
        finally:
            tools._find_kubectl = orig

    def test_original_run_kubectl_signature_unchanged(self):
        """기존 함수는 호출부가 많다 — 2-튜플 계약을 깨면 안 된다."""
        import src.tools as tools
        orig = tools._find_kubectl
        tools._find_kubectl = lambda *a: None
        try:
            self.assertEqual(len(tools._run_kubectl('kc', ['get', 'pods'])), 2)
        finally:
            tools._find_kubectl = orig


if __name__ == '__main__':
    unittest.main()
