# -*- coding: utf-8 -*-
"""「생각하는」 LLM 의 빈 답 (v1.5.62, 사용자 신고).

Qwen3.5-9B 를 llama.cpp(localhost:8080)로 띄우니 AI 진단 답 칸이 비었다. 실측:
  기본 요청   → content '' · reasoning_content 에 추론 300토큰 · finish_reason 'length'
  enable_thinking=false → content '2' · 2토큰 · finish 'stop'
그래서 요청마다 생각을 끄고, 그 필드를 거절하는 서버면 빼고 다시 보내고, 그래도 비면 이유를 알린다.
"""
import io
import json
import unittest
import urllib.error
from unittest import mock

from src import reports as R


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _ok(content, reasoning='', finish='stop'):
    return _Resp(json.dumps({'choices': [{'finish_reason': finish, 'message': {
        'role': 'assistant', 'content': content, 'reasoning_content': reasoning}}]}).encode())


class Thinking(unittest.TestCase):
    def setUp(self):
        self.sent = []

    def _urlopen(self, replies):
        it = iter(replies)

        def f(req, timeout=None):
            self.sent.append(json.loads(req.data))
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return r
        return mock.patch('urllib.request.urlopen', f)

    def test_생각을_끄라고_보낸다(self):
        with self._urlopen([_ok('2')]):
            self.assertEqual(R._llm_ask('http://h:8080', 'm', '1+1?'), '2')
        self.assertEqual(self.sent[0]['chat_template_kwargs'], {'enable_thinking': False})

    def test_모르는_필드를_거절하면_빼고_다시(self):
        err = urllib.error.HTTPError('http://h/v1/chat/completions', 400, 'Unrecognized request argument', {}, io.BytesIO(b''))
        with self._urlopen([err, _ok('답')]):
            self.assertEqual(R._llm_ask('http://h:8080', 'm', 'q'), '답')
        self.assertNotIn('chat_template_kwargs', self.sent[1])

    def test_다른_오류는_그대로(self):
        err = urllib.error.HTTPError('http://h/v1/chat/completions', 500, 'boom', {}, io.BytesIO(b''))
        with self._urlopen([err]), self.assertRaises(urllib.error.HTTPError):
            R._llm_ask('http://h:8080', 'm', 'q')
        self.assertEqual(len(self.sent), 1)

    def test_답_안의_think_는_뗀다(self):
        with self._urlopen([_ok('<think>음… 계산하면</think>\n2')]):
            self.assertEqual(R._llm_ask('http://h:8080', 'm', 'q'), '2')

    def test_생각만_하다_끝나면_이유를_알린다(self):
        with self._urlopen([_ok('', reasoning='Thinking Process: ...', finish='length')]):
            with self.assertRaises(RuntimeError) as cm:
                R._llm_ask('http://h:8080', 'm', 'q')
        self.assertIn('생각', str(cm.exception))

    def test_content_가_null_이어도(self):
        with self._urlopen([_Resp(json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': None}}]}).encode())]):
            with self.assertRaises(RuntimeError) as cm:
                R._llm_ask('http://h:8080', 'm', 'q')
        self.assertIn('빈 답', str(cm.exception))

    def test_대화도_같은_길로(self):
        from src.api.aiops import _aiops_post_chat
        with self._urlopen([_ok('<think>x</think>답')]):
            self.assertEqual(_aiops_post_chat('http://h:8080', 'm', [{'role': 'user', 'content': 'q'}]), '답')
        self.assertEqual(self.sent[0]['chat_template_kwargs'], {'enable_thinking': False})


if __name__ == '__main__':
    unittest.main()
