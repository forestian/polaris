# -*- coding: utf-8 -*-
"""저장물에 남는 클러스터 표기가 **보관함 이름**인지 검증 (v1.2.128 회귀).

사고 내용: 스냅샷과 YAML 실험실이 `cluster_info['context']` 를 먼저 썼다. RKE2 가
만드는 kubeconfig 는 context 이름이 죄다 `default` 라, 서로 다른 클러스터의 스냅샷이
전부 `default_20260803-...` 로 저장돼 목록에서 구분이 안 됐다.

올바른 출처는 `display_name` — 사용자가 보관함에서 붙인(그리고 바꿀 수 있는) 이름이며
codebase 다른 곳(catalog·port_forward·notifications)은 이미 이 값을 쓰고 있었다.
"""
import unittest


class _FakeK8s:
    def __init__(self, context='', connected=True):
        self.cluster_info = {'context': context}
        self.connected = connected
        self.kubeconfig = '/tmp/kc'


def _api(display_name='', context='default', connected=True):
    """PolarisAPI.k8s 는 _clusters[_active_id]['mgr'] 에서 파생되는 property 라
    직접 대입할 수 없다 — 클러스터 엔트리째 주입한다."""
    from src.api import PolarisAPI
    api = PolarisAPI()
    api._clusters = {'c1': {
        'display_name': display_name,
        'context':      context,
        'mgr':          _FakeK8s(context, connected),
    }}
    api._active_id = 'c1'
    return api


class TestClusterLabel(unittest.TestCase):
    def test_display_name_beats_context(self):
        """이게 이 버그의 핵심 — context 가 'default' 여도 보관함 이름이 이겨야 한다."""
        self.assertEqual(_api('ollama-k8s', 'default')._cluster_label(), 'ollama-k8s')

    def test_falls_back_to_context_when_no_display_name(self):
        self.assertEqual(_api('', 'prod-ctx')._cluster_label(), 'prod-ctx')

    def test_falls_back_to_default_arg_when_nothing_known(self):
        self.assertEqual(_api('', '')._cluster_label(), 'cluster')
        self.assertEqual(_api('', '')._cluster_label(fallback=''), '')

    def test_renaming_in_vault_changes_future_label(self):
        """보관함에서 이름을 바꾸면 이후 저장물에 새 이름이 붙어야 한다."""
        api = _api('old-name', 'default')
        api._clusters['c1']['display_name'] = 'new-name'
        self.assertEqual(api._cluster_label(), 'new-name')

    def test_helper_lives_on_base_so_every_mixin_can_use_it(self):
        from src.api.base import APIBase
        self.assertTrue(hasattr(APIBase, '_cluster_label'))
        self.assertTrue(hasattr(APIBase, '_active_cluster_name'))


class TestSnapshotUsesVaultName(unittest.TestCase):
    def test_take_snapshot_saves_under_display_name(self):
        import src.api.snapshots as snaps
        seen = {}

        def _fake_save(data, cluster, label='', now=None, vault=None):
            seen['cluster'] = cluster
            return {'ok': True, 'id': f'{cluster}_stamp'}

        orig_save, orig_collect, orig_eval = (
            snaps.save_snapshot, snaps._report_collect, snaps._report_evaluate)
        snaps.save_snapshot = _fake_save
        snaps._report_collect = lambda k8s, log: {'nodes': []}
        snaps._report_evaluate = lambda data: []
        try:
            api = _api('ollama-k8s', 'default')
            api.take_snapshot('라벨')
            self.assertEqual(seen.get('cluster'), 'ollama-k8s',
                             "context('default') 가 아니라 보관함 이름으로 저장돼야 한다")
        finally:
            (snaps.save_snapshot, snaps._report_collect,
             snaps._report_evaluate) = orig_save, orig_collect, orig_eval


class TestYamlLabUsesVaultName(unittest.TestCase):
    def test_lab_cluster_prefers_display_name(self):
        self.assertEqual(_api('ollama-k8s', 'default')._lab_cluster(), 'ollama-k8s')

    def test_lab_cluster_blank_when_nothing_known(self):
        """빈 문자열이어야 목록/내보내기에서 'cluster' 같은 가짜 이름이 안 생긴다."""
        self.assertEqual(_api('', '')._lab_cluster(), '')

    def test_saved_manifest_records_display_name(self):
        import tempfile
        from pathlib import Path
        from src.yamllab import open_db, save_manifest, list_manifests

        api = _api('ollama-k8s', 'default')
        with tempfile.TemporaryDirectory() as td:
            conn = open_db(Path(td) / 'lab.db')
            try:
                save_manifest(conn, None, 'web', 'kind: Pod\n',
                              cluster=api._lab_cluster())
                self.assertEqual(list_manifests(conn)[0]['cluster'], 'ollama-k8s')
            finally:
                conn.close()


if __name__ == '__main__':
    unittest.main()
