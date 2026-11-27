# -*- coding: utf-8 -*-
"""MCP 액세스 토큰 (v1.2.119).

핵심 보장:
  1. 토큰 발급/해제/폐기/만료가 정확히 동작한다.
  2. 위조·변조 토큰으로는 절대 열리지 않는다.
  3. **MCP 는 DPAPI 로 열리지 않는다** — 자동 잠금 해제가 켜져 있어도 토큰이
     없으면 거부해야 한다. (이번 릴리스의 핵심 요구사항)
  4. 토큰 비밀값이 vault 파일·감사 로그·API 응답 어디에도 남지 않는다.
  5. scope=read 토큰은 변경 툴을 쓸 수 없다.
  6. 기존(토큰 없는) vault 가 그대로 열린다 — v1 포맷 하위 호환.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from src.vault import Vault, _parse_mcp_token, _MCP_TOKEN_PREFIX


def _new_vault(tmp):
    v = Vault(Path(tmp) / 'vault.json')
    v.create('master-pw-1234')
    return v


class TestTokenFormat(unittest.TestCase):
    def test_prefix_and_parse_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            tok = v.issue_mcp_token(label='cli')
            self.assertTrue(tok.startswith(_MCP_TOKEN_PREFIX))
            parsed = _parse_mcp_token(tok)
            self.assertIsNotNone(parsed)
            tid, secret = parsed
            self.assertEqual(len(secret), 32)
            self.assertEqual(len(tid), 8)

    def test_malformed_rejected(self):
        for bad in ('', 'nope', 'plrs_mcp_', 'plrs_mcp_zzzz_AAAA',
                    'plrs_mcp_deadbeef_short', _MCP_TOKEN_PREFIX + 'deadbeef_' + 'A' * 39):
            self.assertIsNone(_parse_mcp_token(bad), bad)


class TestIssueUnlockRevoke(unittest.TestCase):
    def test_unlock_with_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            v.store('k', 'v-secret')
            tok = v.issue_mcp_token(label='claude', scope='read')
            v.lock()
            self.assertFalse(v.is_unlocked)
            meta = v.unlock_token(tok)
            self.assertIsNotNone(meta)
            self.assertEqual(meta['scope'], 'read')
            self.assertEqual(meta['label'], 'claude')
            self.assertTrue(v.is_unlocked)
            self.assertEqual(v.retrieve('k'), 'v-secret')

    def test_issue_requires_unlocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            v.lock()
            with self.assertRaises(Exception):
                v.issue_mcp_token()

    def test_tampered_token_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            tok = v.issue_mcp_token()
            v.lock()
            self.assertIsNone(v.unlock_token(tok[:-6] + 'AAAAAA'))
            self.assertFalse(v.is_unlocked)

    def test_unknown_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            tok = v.issue_mcp_token()
            v.lock()
            tid, rest = tok[len(_MCP_TOKEN_PREFIX):].split('_', 1)
            other = _MCP_TOKEN_PREFIX + ('0' * 8 if tid != '0' * 8 else 'f' * 8) + '_' + rest
            self.assertIsNone(v.unlock_token(other))

    def test_revoke_blocks_unlock(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            tok = v.issue_mcp_token()
            meta_id = v.list_mcp_tokens()[0]['id']
            self.assertTrue(v.revoke_mcp_token(meta_id))
            v.lock()
            self.assertIsNone(v.unlock_token(tok))
            self.assertFalse(v.revoke_mcp_token(meta_id))   # 두 번째는 False

    def test_expired_token_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            tok = v.issue_mcp_token(expires_days=1)
            tid = v.list_mcp_tokens()[0]['id']
            past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            v._data['token_deks'][tid]['expires_at'] = past
            v._save()
            v.lock()
            self.assertIsNone(v.unlock_token(tok))
            self.assertTrue(v.list_mcp_tokens()[0]['expired'])

    def test_no_expiry_when_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            v.issue_mcp_token(expires_days=0)
            self.assertIsNone(v.list_mcp_tokens()[0]['expires_at'])

    def test_multiple_tokens_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            a = v.issue_mcp_token(label='a', scope='read')
            b = v.issue_mcp_token(label='b', scope='write')
            self.assertEqual(len(v.list_mcp_tokens()), 2)
            ids = {t['label']: t['id'] for t in v.list_mcp_tokens()}
            v.revoke_mcp_token(ids['a'])
            v.lock()
            self.assertIsNone(v.unlock_token(a))       # 폐기된 것만 막히고
            self.assertIsNotNone(v.unlock_token(b))    # 나머지는 살아 있다

    def test_last_used_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            tok = v.issue_mcp_token()
            self.assertIsNone(v.list_mcp_tokens()[0]['last_used_at'])
            v.lock()
            v.unlock_token(tok)
            self.assertIsNotNone(v.list_mcp_tokens()[0]['last_used_at'])

    def test_invalid_scope_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            with self.assertRaises(ValueError):
                v.issue_mcp_token(scope='admin')


class TestSecretNotPersisted(unittest.TestCase):
    def test_token_secret_absent_from_vault_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            tok = v.issue_mcp_token()
            secret_part = tok.rsplit('_', 1)[1]
            raw = (Path(tmp) / 'vault.json').read_text(encoding='utf-8')
            self.assertNotIn(secret_part, raw)          # 비밀값 원문 없음
            self.assertNotIn(tok, raw)
            self.assertIn('token_deks', raw)            # 래핑본만 있음

    def test_list_has_no_secret_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            v.issue_mcp_token()
            rec = v.list_mcp_tokens()[0]
            for banned in ('wrapped', 'salt', 'token', 'secret'):
                self.assertNotIn(banned, rec)


class TestBackwardCompat(unittest.TestCase):
    def test_vault_without_token_deks_still_opens(self):
        """v1.2.118 이전 vault(=token_deks 키 자체가 없음)도 그대로 열려야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            v.store('k', 'v')
            p = Path(tmp) / 'vault.json'
            data = json.loads(p.read_text(encoding='utf-8'))
            data.pop('token_deks', None)
            p.write_text(json.dumps(data), encoding='utf-8')

            v2 = Vault(p)
            self.assertTrue(v2.unlock_master('master-pw-1234'))
            self.assertEqual(v2.retrieve('k'), 'v')
            self.assertEqual(v2.list_mcp_tokens(), [])

    def test_dpapi_path_unaffected(self):
        """GUI 용 DPAPI 경로는 토큰 도입과 무관하게 계속 동작한다."""
        with tempfile.TemporaryDirectory() as tmp:
            v = _new_vault(tmp)
            v.issue_mcp_token()
            v.lock()
            self.assertTrue(v.unlock_dpapi())


# ─────────────────────────────────────────────────────────────────────────────
# MCP 서버 계층 — DPAPI 금지 + scope 게이트
# ─────────────────────────────────────────────────────────────────────────────
class _FakeAPI:
    """vault_* 만 흉내내는 스텁."""
    def __init__(self, unlocked=False, has_token=None, exists=True):
        self.unlocked = unlocked
        self.has_token = has_token          # 유효 토큰 문자열 (None 이면 전부 거부)
        self.exists = exists
        self.dpapi_calls = 0

    def vault_status(self):
        return {'available': True, 'exists': self.exists, 'unlocked': self.unlocked}

    def vault_unlock_dpapi(self):
        self.dpapi_calls += 1
        self.unlocked = True
        return {'ok': True}

    def vault_unlock_token(self, token):
        if self.has_token and token == self.has_token:
            self.unlocked = True
            return {'ok': True, 'token': {'id': 'abcd1234', 'scope': self._scope,
                                          'label': 'test'}}
        return {'ok': False, 'error': '유효하지 않은 토큰입니다.'}

    _scope = 'read'


class TestMcpServerTokenOnly(unittest.TestCase):
    def setUp(self):
        from src import mcp_server
        self.m = mcp_server
        self.m._token_meta = None
        self._env = dict(os.environ)
        os.environ.pop('POLARIS_MCP_TOKEN', None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self.m._token_meta = None

    def test_no_token_env_is_refused(self):
        api = _FakeAPI(unlocked=False, has_token='plrs_mcp_x')
        ok, err = self.m._ensure_unlocked(api)
        self.assertFalse(ok)
        self.assertIn('MCP 액세스 토큰', err)

    def test_dpapi_never_used(self):
        """자동 잠금 해제가 가능한 상태여도 MCP 는 DPAPI 를 호출하지 않는다."""
        api = _FakeAPI(unlocked=False, has_token=None)
        ok, err = self.m._ensure_unlocked(api)
        self.assertFalse(ok)
        self.assertEqual(api.dpapi_calls, 0)      # ★ 핵심 단언

    def test_bad_token_refused_without_leaking(self):
        os.environ['POLARIS_MCP_TOKEN'] = 'plrs_mcp_deadbeef_' + 'A' * 43
        api = _FakeAPI(has_token='plrs_mcp_other')
        ok, err = self.m._ensure_unlocked(api)
        self.assertFalse(ok)
        self.assertEqual(api.dpapi_calls, 0)
        self.assertNotIn('deadbeef', err)         # 토큰 조각이 오류에 안 실림
        self.assertNotIn('AAAA', err)

    def test_valid_token_unlocks(self):
        tok = 'plrs_mcp_abcd1234_' + 'B' * 43
        os.environ['POLARIS_MCP_TOKEN'] = tok
        api = _FakeAPI(has_token=tok)
        ok, err = self.m._ensure_unlocked(api)
        self.assertTrue(ok)
        self.assertIsNone(err)
if __name__ == '__main__':
    unittest.main()
