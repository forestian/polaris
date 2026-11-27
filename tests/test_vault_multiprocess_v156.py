# -*- coding: utf-8 -*-
"""보안 보관함을 두 프로세스가 같이 쓴다 (v1.5.6, 2026-11-05 신고).

Polaris 창과 MCP 서버(polaris.exe --mcp)는 다른 프로세스다. 예전 Vault 는 연 뒤 한 번 읽은 내용을 끝까지 들고 있어서
  · 창에서 새로 저장한 서버 비밀번호를 이미 떠 있는 MCP 가 못 봤다 → has_password false · 「비밀이 저장돼 있지 않습니다」
  · 한쪽이 저장하면 자기 옛 사본을 통째로 써서, 다른 쪽이 그사이 넣은 비밀이 지워질 수 있었다
  · 창에서 폐기한 MCP 토큰을, 이미 그 토큰으로 열어 둔 MCP 가 계속 썼다
두 Vault 객체 = 두 프로세스로 흉내 낸다(같은 파일). 사용자의 실제 vault 는 쓰지 않는다(임시 폴더).
"""
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from src.vault import Vault, VaultError


class TwoProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='polaris-vault2-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = self.tmp / 'vault.json'
        self.gui = Vault(self.path)
        self.gui.create('master-pw')
        self.gui.store('server.srv-4.password', 'old-pw')
        self.mcp = Vault(self.path)                 # MCP 서버 — 창보다 먼저 떠서 지금 내용을 들고 있다
        self.mcp.unlock_master('master-pw')
        self.assertTrue(self.mcp.has('server.srv-4.password'))

    def bump(self):
        # 같은 1초 안에 두 번 쓰면 mtime 이 같을 수 있다 — 크기도 보지만 확실히 다르게
        time.sleep(0.01)

    def test_창에서_저장한_비밀번호를_떠_있는_MCP_가_본다(self):
        self.bump()
        self.gui.store('server.srv-169.password', 'new-pw')
        self.assertTrue(self.mcp.has('server.srv-169.password'))
        self.assertEqual(self.mcp.retrieve('server.srv-169.password'), 'new-pw')
        self.assertIn('server.srv-169.password', self.mcp.list_keys())

    def test_한쪽_저장이_다른_쪽_비밀을_지우지_않는다(self):
        self.bump()
        self.gui.store('server.srv-168.password', 'a')
        self.bump()
        self.mcp.store('server.srv-999.sudo', 'b')           # MCP 는 168 을 넣기 전 사본을 들고 있었다
        fresh = Vault(self.path)
        fresh.unlock_master('master-pw')
        self.assertEqual(fresh.retrieve('server.srv-168.password'), 'a')
        self.assertEqual(fresh.retrieve('server.srv-999.sudo'), 'b')
        self.assertEqual(fresh.retrieve('server.srv-4.password'), 'old-pw')

    def test_지우기도_다른_쪽에_보인다(self):
        self.bump()
        self.gui.delete('server.srv-4.password')
        self.assertFalse(self.mcp.has('server.srv-4.password'))

    def test_마스터_비밀번호를_바꿔도_다른_쪽이_계속_읽는다(self):
        self.bump()
        self.gui.change_master_password('master-pw', 'new-master')
        self.bump()
        self.gui.store('server.x.password', 'p')
        self.assertEqual(self.mcp.retrieve('server.x.password'), 'p', 'DEK 는 그대로 — 재래핑만')
        again = Vault(self.path)
        again.unlock_master('new-master')
        self.assertEqual(again.retrieve('server.srv-4.password'), 'old-pw')

    def test_창에서_폐기한_토큰은_떠_있는_MCP_에서도_못_연다(self):
        tok = self.gui.issue_mcp_token('t', scope='write')
        tid = tok.split('_')[2]
        mcp = Vault(self.path)
        self.assertIsNotNone(mcp.unlock_token(tok))
        self.bump()
        self.gui.revoke_mcp_token(tid)
        mcp2_view = [t['id'] for t in mcp.list_mcp_tokens()]
        self.assertNotIn(tid, mcp2_view, '목록도 다시 읽는다')
        mcp.lock()
        self.assertIsNone(mcp.unlock_token(tok))

    def test_토큰으로_열_때_쓰는_사용시각이_다른_비밀을_지우지_않는다(self):
        tok = self.gui.issue_mcp_token('t')
        mcp = Vault(self.path)
        mcp.has_dpapi                                 # 읽기만 — _data 는 아직 없다
        self.bump()
        self.gui.store('server.later.password', 'x')
        self.assertIsNotNone(mcp.unlock_token(tok))   # 열면서 last_used_at 을 쓴다
        self.assertEqual(mcp.retrieve('server.later.password'), 'x')
        fresh = Vault(self.path)
        fresh.unlock_master('master-pw')
        self.assertTrue(fresh.has('server.later.password'))

    def test_파일_잠금(self):
        """다른 프로세스가 쓰는 중이면 기다렸다가 쓴다 · 너무 오래면 알아듣는 오류."""
        hold = threading.Event()
        release = threading.Event()

        def holder():
            with self.gui._file_lock():
                hold.set()
                release.wait(5)
        t = threading.Thread(target=holder)
        t.start()
        hold.wait(5)
        threading.Timer(0.3, release.set).start()
        t0 = time.monotonic()
        self.mcp.store('server.wait.password', 'w')
        self.assertGreater(time.monotonic() - t0, 0.2, '잠금이 풀릴 때까지 기다렸다')
        t.join()
        self.assertEqual(self.gui.retrieve('server.wait.password'), 'w')
        # 오래 잡혀 있으면
        hold.clear(); release.clear()
        t = threading.Thread(target=holder)
        t.start()
        hold.wait(5)
        orig = Vault._file_lock
        with mock.patch.object(Vault, '_file_lock', lambda self, timeout=10.0: orig(self, 0.2)):
            with self.assertRaises(VaultError) as cm:
                self.mcp.store('server.wait.password', 'z')
        self.assertIn('쓰는 중', str(cm.exception))
        release.set()
        t.join()

    def test_파일은_한_벌_잠금_파일은_옆에(self):
        self.gui.store('a.b', 'c')
        self.assertTrue(self.path.exists())
        self.assertFalse(self.path.with_suffix('.json.tmp').exists())


class McpRevokeTests(unittest.TestCase):
    def test_열어_둔_뒤_폐기되면_MCP_가_닫는다(self):
        import src.mcp_server as m

        class Fake:
            locked = 0
            tokens = [{'id': 'aaaa1111', 'expired': False}]

            def vault_status(self):
                return {'available': True, 'exists': True, 'unlocked': True}

            def vault_unlock_token(self, token):
                return {'ok': True, 'token': {'id': 'aaaa1111', 'scope': 'write'}}

            def vault_list_mcp_tokens(self):
                return {'ok': True, 'tokens': self.tokens}

            def vault_lock(self):
                self.locked += 1
                return {'ok': True}
        api = Fake()
        old = m._token_meta
        self.addCleanup(setattr, m, '_token_meta', old)
        with mock.patch.dict(os.environ, {'POLARIS_MCP_TOKEN': 'plrs_mcp_aaaa1111_' + 'C' * 43}):
            m._token_meta = None
            self.assertEqual(m._ensure_unlocked(api), (True, None))
            self.assertEqual(m._ensure_unlocked(api), (True, None), '살아 있는 토큰은 그대로')
            api.tokens = []                                  # 창에서 폐기
            ok, err = m._ensure_unlocked(api)
            self.assertFalse(ok)
            self.assertEqual(api.locked, 1)
            self.assertIsNone(m._token_meta)


if __name__ == '__main__':
    unittest.main()
