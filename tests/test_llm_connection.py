# -*- coding: utf-8 -*-
"""LLM 연결 테스트(AIOpsMixin.test_llm_connection) — 로컬 모델 UX.

- 항상: URL 스킴/빈값 가드 + 도달 불가(닫힌 포트) 처리. 네트워크 없이도 빠르게 끝난다
  (127.0.0.1:9 = discard 포트, 즉시 refused).
- opt-in(POLARIS_LIVE_LLM=1): 실제 OpenAI 호환 서버(LM Studio 등) /v1/models 조회.
"""
import os
import unittest


class TestLlmConnection(unittest.TestCase):
    def setUp(self):
        from src.api import PolarisAPI
        self.api = PolarisAPI()

    def test_empty_url(self):
        r = self.api.test_llm_connection('')
        self.assertFalse(r['ok'])

    def test_rejects_non_http_scheme(self):
        for bad in ('file:///etc/passwd', 'ftp://x/y', 'not-a-url'):
            r = self.api.test_llm_connection(bad)
            self.assertFalse(r['ok'], bad)

    def test_unreachable_reports_not_reachable(self):
        r = self.api.test_llm_connection('http://127.0.0.1:9', timeout=3)
        self.assertFalse(r['ok'])
        self.assertFalse(r.get('reachable'))
        self.assertIn('error', r)

    def test_timeout_clamped(self):
        # 잘못된 timeout 값이 와도 예외 없이 처리(내부 clamp)
        r = self.api.test_llm_connection('http://127.0.0.1:9', timeout='oops')
        self.assertFalse(r['ok'])


class TestLlmTimeoutReachesSocket(unittest.TestCase):
    """타임아웃이 **실제로 urlopen 까지 도달**하는지 본다.

    v1.2.123 교훈 — 상수만 바꾸고 라이브러리가 안 지키면 의미가 없다(그때는 urllib3 가
    float 를 per-phase 상한으로 안 썼다). 그래서 '값이 선언돼 있다'가 아니라 호출
    인자를 직접 가로채 확인한다.
    """

    def _captured_timeout(self, call):
        import json as _json
        import urllib.request

        seen = {}

        class _Resp:
            def read(self):
                return _json.dumps(
                    {'choices': [{'message': {'content': 'ok'}}]}).encode('utf-8')

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def _fake_urlopen(req, timeout=None, **kw):
            seen['timeout'] = timeout
            return _Resp()

        orig = urllib.request.urlopen
        urllib.request.urlopen = _fake_urlopen
        try:
            call()
        finally:
            urllib.request.urlopen = orig
        return seen.get('timeout')

    def test_llm_ask_default_is_the_shared_constant(self):
        from src.reports import _llm_ask, _LLM_TIMEOUT_S
        got = self._captured_timeout(
            lambda: _llm_ask('http://127.0.0.1:1234', 'm', 'hi'))
        self.assertEqual(got, _LLM_TIMEOUT_S)

    def test_llm_ask_explicit_timeout_wins(self):
        from src.reports import _llm_ask
        got = self._captured_timeout(
            lambda: _llm_ask('http://127.0.0.1:1234', 'm', 'hi', timeout=42))
        self.assertEqual(got, 42)

    def test_chat_path_shares_the_same_default(self):
        """첫 진단(_llm_ask)은 되는데 후속 대화만 끊기는 비대칭이 생기면 실패."""
        from src.reports import _LLM_TIMEOUT_S
        from src.api.aiops import _aiops_post_chat
        got = self._captured_timeout(
            lambda: _aiops_post_chat('http://127.0.0.1:1234', 'm',
                                     [{'role': 'user', 'content': 'hi'}]))
        self.assertEqual(got, _LLM_TIMEOUT_S)

    def test_budget_covers_slow_local_model(self):
        """실측 근거를 숫자로 잠근다 — 누가 값을 줄이면 여기서 걸린다.

        bonsai-27b 8 t/s 실측: reasoning 936 + 답변으로 max_tokens=2600 을 다 쓰면
        2600/8 = 325초. 이보다 짧으면 답변이 끝나기 전에 끊긴다.
        """
        from src.reports import _LLM_TIMEOUT_S
        self.assertGreaterEqual(
            _LLM_TIMEOUT_S, 325,
            '8 t/s 로컬 모델이 max_tokens=2600 을 끝내려면 최소 325초 필요')

    def test_connection_test_stays_short(self):
        """도달성 확인은 생성과 달리 짧아야 한다 — 죽은 서버에 10분 매달리면 안 됨."""
        import inspect
        from src.api.aiops import AIOpsMixin
        default = inspect.signature(
            AIOpsMixin.test_llm_connection).parameters['timeout'].default
        self.assertLessEqual(default, 60)


@unittest.skipUnless(os.environ.get('POLARIS_LIVE_LLM') == '1',
                     'POLARIS_LIVE_LLM=1 아닐 때 skip (실 LLM 서버 필요)')
class TestLlmConnectionLive(unittest.TestCase):
    def setUp(self):
        from src.api import PolarisAPI
        self.api = PolarisAPI()
        self.url = os.environ.get('POLARIS_LLM_URL', 'http://localhost:1234')

    def test_lists_models(self):
        r = self.api.test_llm_connection(self.url, timeout=5)
        self.assertTrue(r['ok'], r)
        self.assertTrue(r.get('reachable'))
        self.assertIsInstance(r.get('models'), list)


if __name__ == '__main__':
    unittest.main()
