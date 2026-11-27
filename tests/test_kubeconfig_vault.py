"""kubeconfig vault 이름 동기화 + 단일 context minify 테스트 (v1.2.6).

- rename_kubeconfig: 이름 변경 = 기존 데이터를 새 이름으로 이전(덮어쓰기) + 옛 키 제거,
  충돌 시 거부.
- _minify_kubeconfig: 멀티 context kubeconfig 에서 선택한 context 하나만 추출.
"""
import sys
import tempfile
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vault import Vault, HAS_CRYPTO
from src.api.vault import VaultMixin
import src.api.base as base


def _make_unlocked_vault():
    d = tempfile.mkdtemp(prefix='polaris-kctest-')
    v = Vault(pathlib.Path(d) / 'vault.json')
    v.create('testpw1234')
    return v


class _VaultHost(VaultMixin):
    def __init__(self, vault):
        self._polaris_vault = vault


@unittest.skipUnless(HAS_CRYPTO, 'cryptography 필요')
class VaultKubeconfigRename(unittest.TestCase):
    def setUp(self):
        self.t = _VaultHost(_make_unlocked_vault())

    def test_rename_roundtrip_overwrites_name(self):
        self.assertTrue(self.t.store_kubeconfig('default (2)', 'CONTENT-A')['ok'])
        r = self.t.rename_kubeconfig('default (2)', 'prod')
        self.assertTrue(r['ok'], r)
        self.assertEqual(self.t.list_kubeconfigs()['items'], ['prod'])
        self.assertEqual(self.t.get_kubeconfig('prod')['content'], 'CONTENT-A')
        # 옛 이름은 제거되어야 함 (이전/덮어쓰기)
        self.assertFalse(self.t.get_kubeconfig('default (2)')['ok'])

    def test_rename_conflict_rejected(self):
        self.t.store_kubeconfig('a', 'A')
        self.t.store_kubeconfig('b', 'B')
        r = self.t.rename_kubeconfig('b', 'a')
        self.assertFalse(r['ok'])
        self.assertTrue(r.get('conflict'))
        # 둘 다 그대로 유지
        self.assertEqual(self.t.get_kubeconfig('a')['content'], 'A')
        self.assertEqual(self.t.get_kubeconfig('b')['content'], 'B')

    def test_rename_missing(self):
        r = self.t.rename_kubeconfig('nope', 'x')
        self.assertFalse(r['ok'])
        self.assertTrue(r.get('missing'))

    def test_rename_same_name_noop(self):
        self.t.store_kubeconfig('x', 'X')
        self.assertTrue(self.t.rename_kubeconfig('x', 'x')['ok'])
        self.assertEqual(self.t.get_kubeconfig('x')['content'], 'X')


class MinifyKubeconfig(unittest.TestCase):
    KC = (
        "apiVersion: v1\nkind: Config\n"
        "clusters:\n"
        "- {name: c1, cluster: {server: 'https://1.1.1.1:6443'}}\n"
        "- {name: c2, cluster: {server: 'https://2.2.2.2:6443'}}\n"
        "users:\n"
        "- {name: u1, user: {token: t1}}\n"
        "- {name: u2, user: {token: t2}}\n"
        "contexts:\n"
        "- {name: ctx1, context: {cluster: c1, user: u1}}\n"
        "- {name: ctx2, context: {cluster: c2, user: u2}}\n"
        "current-context: ctx1\n"
    )

    def _write(self):
        p = pathlib.Path(tempfile.mkdtemp(prefix='polaris-kctest-')) / 'multi.yaml'
        p.write_text(self.KC, encoding='utf-8')
        return str(p)

    def test_minify_selected_context_python_fallback(self):
        # kubectl 경로 무력화 → 순수 파이썬 minify 강제 (CI/무 kubectl 환경 결정적 검증)
        import src.tools as tools
        orig = tools._find_kubectl
        tools._find_kubectl = lambda *a: None
        try:
            inst = base.APIBase.__new__(base.APIBase)
            out = inst._minify_kubeconfig(self._write(), 'ctx2')
        finally:
            tools._find_kubectl = orig
        self.assertTrue(out)
        import yaml
        m = yaml.safe_load(out)
        self.assertEqual([c['name'] for c in m['contexts']], ['ctx2'])
        self.assertEqual([c['name'] for c in m['clusters']], ['c2'])
        self.assertEqual([u['name'] for u in m['users']], ['u2'])
        self.assertEqual(m['current-context'], 'ctx2')
        self.assertNotIn('1.1.1.1', out)   # 선택 안 한 context/cluster 는 제외


class _FakeMgr:
    """K8sManager 대체 — 실제 클러스터 없이 연결 성공 + context 보고."""
    def __init__(self):
        self.connected = False
        self.cluster_info = {}
        self.kubeconfig = None
    def connect(self, path=None, context=None, content=None):
        self.connected = True
        self.cluster_info = {'version': 'v1.30.0', 'context': context or 'default'}
        return True, '연결 성공'
    def disconnect(self):
        self.connected = False


class _API(base.APIBase, VaultMixin):
    # remove_cluster 가 호출하는 다른 mixin 메서드 스텁 (테스트엔 port-forward/kubectl 스트림 불필요)
    def _stop_port_forward_jobs_for_cluster(self, cid):
        pass
    def _stop_kubectl_stream_procs_for_cluster(self, cid):
        pass


@unittest.skipUnless(HAS_CRYPTO, 'cryptography 필요')
class ReconnectFromVaultName(unittest.TestCase):
    """보관본으로 재연결해도 사용자가 지정한 이름(vault 키)이 표시되어야 한다.
    (context 'default' 로 재유도하면 'default (2)' 로 되돌아가는 버그 회귀)"""

    def _api(self):
        api = _API()
        api._polaris_vault = _make_unlocked_vault()
        # context 는 'default' 이지만 사용자가 'lgons' 라는 이름으로 보관
        api.store_kubeconfig('lgons', 'apiVersion: v1\nkind: Config\ncurrent-context: default\n')
        return api

    def test_vault_connect_uses_saved_name(self):
        orig = base.K8sManager
        base.K8sManager = _FakeMgr
        try:
            api = self._api()
            r = api.add_cluster_from_vault('lgons')
            self.assertTrue(r['ok'], r)
            self.assertEqual(r['display_name'], 'lgons')   # 'default' 아님
            self.assertEqual(r['kc_name'], 'lgons')
        finally:
            base.K8sManager = orig

    def test_disconnect_then_reconnect_keeps_name(self):
        orig = base.K8sManager
        base.K8sManager = _FakeMgr
        try:
            api = self._api()
            r1 = api.add_cluster_from_vault('lgons')
            self.assertEqual(r1['display_name'], 'lgons')
            api.remove_cluster(r1['cluster_id'])           # 연결 끊기
            r2 = api.add_cluster_from_vault('lgons')        # 다시 연결
            self.assertEqual(r2['display_name'], 'lgons')   # 'default (2)' 로 되돌아가면 안 됨
        finally:
            base.K8sManager = orig

    def test_same_vault_connect_twice_reuses(self):
        """v1.5.23 — OPS 설정 변경에서 연결한 뒤 K8s 탭에서 또 연결해도 「lgons (2)」 가 생기지 않는다."""
        orig = base.K8sManager
        base.K8sManager = _FakeMgr
        try:
            api = self._api()
            r1 = api.add_cluster_from_vault('lgons')
            r2 = api.add_cluster_from_vault('lgons')
            self.assertEqual(r2['cluster_id'], r1['cluster_id'])
            self.assertTrue(r2.get('reused'))
            self.assertEqual(len(api._clusters), 1)
            self.assertEqual(r2['display_name'], 'lgons')
            # context 를 따로 고르면 다른 연결이다(같은 파일의 여러 context — 세션 복원과 같은 키)
            r3 = api.add_cluster_from_vault('lgons', 'other')
            self.assertNotEqual(r3['cluster_id'], r1['cluster_id'])
            # 끊긴 연결은 다시 쓰지 않는다
            api._clusters[r1['cluster_id']]['mgr'].connected = False
            r4 = api.add_cluster_from_vault('lgons')
            self.assertNotEqual(r4['cluster_id'], r1['cluster_id'])
        finally:
            base.K8sManager = orig


if __name__ == '__main__':
    unittest.main()
