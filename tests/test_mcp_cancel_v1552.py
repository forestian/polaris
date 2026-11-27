# -*- coding: utf-8 -*-
"""MCP 서버 — 클라이언트가 툴 호출을 취소해도 서버가 죽지 않는다 (v1.5.52, 사용자 신고).

신고: Claude Desktop 에서 Polaris MCP 를 쓰다가 「Failed to execute script 'polaris' … unhandled errors in a TaskGroup …
AssertionError: Request already responded to」 로 서버가 죽고, 그 뒤 모든 호출이 응답 없음.
원인: 오래 걸린 툴 호출을 클라이언트가 취소 → SDK 가 그 요청에 오류로 대신 답함 → 끊을 수 없는 툴 스레드가 끝난 뒤
우리 핸들러가 정상 반환 → SDK 가 같은 요청에 또 답하려다 AssertionError 로 TaskGroup 째 무너짐.

이 파일은 **실제 SDK(mcp)** 에 JSON-RPC 를 그대로 흘려 그 순서를 재현한다: 느린 툴 호출 → 취소 알림 → 다음 요청이 답을 받는가.
"""
import json
import time
import unittest
from unittest import mock

import anyio

from src import mcp_server as M


def _slow_tool(args):
    time.sleep(float(args.get('secs', 0.6)))          # 끊을 수 없는 스레드 일(SSH 명령 대신)
    return {'ok': True, 'slept': True}


async def _exchange(cancel: bool, harden: bool = True):
    """서버에 메시지를 흘리고 받은 응답을 모은다 → (응답들, 서버 오류)"""
    from mcp.shared.message import SessionMessage
    import mcp.types as types

    c2s_send, c2s_recv = anyio.create_memory_object_stream(100)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(100)
    out, err = [], []

    with mock.patch.dict(M._TOOLS, {'polaris_test_slow': _slow_tool}), \
         mock.patch.object(M, '_audit', lambda rec: None), \
         mock.patch.object(M, '_harden_sdk', M._harden_sdk if harden else (lambda: None)):
        server = M.build_server()

        async def send(obj):
            try:
                await c2s_send.send(SessionMessage(types.JSONRPCMessage.model_validate(obj)))
            except (anyio.BrokenResourceError, anyio.ClosedResourceError):
                pass                                        # 서버가 무너져 받는 쪽이 닫혔다 — err 에 원인이 남는다

        async def serve():
            try:
                await server.run(c2s_recv, s2c_send, server.create_initialization_options())
            except BaseException as e:                      # noqa: BLE001 — 무너졌는지 본다
                err.append(e)

        async def collect():
            async for m in s2c_recv:
                out.append(m.message.model_dump(by_alias=True, exclude_none=True))

        async with anyio.create_task_group() as tg:
            tg.start_soon(serve)
            tg.start_soon(collect)
            await send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '0'}}})
            await anyio.sleep(0.2)
            await send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            await send({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                        'params': {'name': 'polaris_test_slow', 'arguments': {'secs': 0.6}}})
            await anyio.sleep(0.15)
            if cancel:
                await send({'jsonrpc': '2.0', 'method': 'notifications/cancelled', 'params': {'requestId': 2, 'reason': 'timeout'}})
            await anyio.sleep(1.0)                          # 툴 스레드가 끝나고 핸들러가 돌아올 때까지
            await send({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list'})
            await anyio.sleep(0.4)
            await c2s_send.aclose()
            await anyio.sleep(0.2)
            tg.cancel_scope.cancel()
    return out, err


def _by_id(msgs):
    d = {}
    for m in msgs:
        mid = m.get('id')
        if mid is not None:
            d.setdefault(mid, []).append(m)
    return d


class CancelTests(unittest.TestCase):
    def test_취소돼도_서버가_살아서_다음_요청에_답한다(self):
        out, err = anyio.run(_exchange, True)
        self.assertEqual([e for e in err if 'already responded' in repr(e)], [], '서버가 무너지면 안 된다')
        by = _by_id(out)
        self.assertEqual(len(by.get(2, [])), 1, f'취소된 요청에는 한 번만 답한다: {by.get(2)}')
        self.assertIn(3, by, '취소 뒤에도 다음 요청(tools/list)에 답한다')
        self.assertIn('tools', by[3][0]['result'])

    def test_취소_안_하면_결과를_받는다(self):
        out, err = anyio.run(_exchange, False)
        by = _by_id(out)
        res = json.loads(by[2][0]['result']['content'][0]['text'])
        self.assertTrue(res['slept'])
        self.assertIn(3, by)

    def test_안전망만으로도_무너지지_않는다(self):
        """checkpoint 를 지나쳐 두 번째 응답이 와도(예: 다른 경로) 버리고 계속 간다"""
        from mcp.shared import session as S
        M._harden_sdk()
        self.assertTrue(getattr(S.RequestResponder.respond, '_polaris_guard', False))

        class _R:
            _completed = True
            request_id = 9
        called = []

        async def go():
            await S.RequestResponder.respond(_R(), {'x': 1})
        with mock.patch.object(M, '_audit', lambda rec: called.append(rec)):
            anyio.run(go)
        self.assertEqual(called[0]['event'], 'mcp_duplicate_response_dropped')
    def test_SDK_내부가_그대로인지(self):
        """안전망은 SDK 의 비공개 속성(_completed)에 기댄다 — 판이 바뀌어 이름이 달라지면 여기서 알린다"""
        import inspect
        from mcp.shared import session as S
        src = inspect.getsource(S.RequestResponder.__init__)
        self.assertIn('self._completed = False', src)


if __name__ == '__main__':
    unittest.main()
