# -*- coding: utf-8 -*-
"""알림(src/notifications.py, src/api/notifications.py) 테스트.

- TestNormalizeNotifications: 설정 검증(base.py) — 잘못된 URL 은 저장 안 됨.
- TestWatcherLogic: 클러스터 불필요 — 가짜 api 객체로 baseline→신규만 알림 계약,
  같은 이슈 반복 시 재알림 안 함, enabled=False/클러스터 미연결 시 조용히 스킵.
- TestWebhookRealHttp: 진짜 로컬 HTTP 서버로 실제 POST 왕복 확인(외부 의존성 없음,
  항상 실행) — send_test_webhook 과 NotificationWatcher 의 실제 웹훅 발사 둘 다.
"""
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.notifications import NotificationWatcher, send_test_webhook, _valid_webhook_url


# ── 로컬 웹훅 수신 서버 (진짜 HTTP, 외부 네트워크 불필요) ────────────────────────
class _CapturingHandler(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            _CapturingHandler.received.append(json.loads(body.decode('utf-8')))
        except Exception:
            _CapturingHandler.received.append({'_raw': body})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')

    def log_message(self, *args):
        pass   # 테스트 출력 조용히


class _LocalWebhookServer:
    def __enter__(self):
        _CapturingHandler.received = []
        self.httpd = HTTPServer(('127.0.0.1', 0), _CapturingHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}/hook'

    def wait_for(self, count, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if len(_CapturingHandler.received) >= count:
                return _CapturingHandler.received
            time.sleep(0.05)
        return _CapturingHandler.received


class TestNormalizeNotifications(unittest.TestCase):
    def setUp(self):
        from src.api.base import APIBase
        self.norm = APIBase._normalize_notifications

    def test_defaults(self):
        r = self.norm(None)
        self.assertEqual(r, {
            'enabled': False, 'tray': True, 'webhookUrl': '',
        })

    def test_valid_url_kept(self):
        r = self.norm({'enabled': True, 'webhookUrl': 'https://hooks.slack.com/x'})
        self.assertTrue(r['enabled'])
        self.assertEqual(r['webhookUrl'], 'https://hooks.slack.com/x')

    def test_invalid_url_dropped(self):
        for bad in ('not-a-url', 'ftp://x/y', 'javascript:alert(1)', '  '):
            r = self.norm({'webhookUrl': bad})
            self.assertEqual(r['webhookUrl'], '', bad)

    def test_full_settings_roundtrip_includes_notifications(self):
        from src.api.base import APIBase
        s = APIBase._normalize_settings({'notifications': {'enabled': True, 'tray': False}})
        self.assertIn('notifications', s)
        self.assertTrue(s['notifications']['enabled'])
        self.assertFalse(s['notifications']['tray'])


class _FakeApi:
    """NotificationWatcher.tick() 이 참조하는 최소 표면적만 흉내."""
    def __init__(self, events, enabled=True, cluster_name='rd'):
        self._active_id = 'c1'
        self._clusters = {'c1': {'display_name': cluster_name}}
        self._settings = {'notifications': {'enabled': enabled, 'tray': True, 'webhookUrl': ''}}
        self._events = events

    def _load_settings_raw(self):
        return self._settings

    def get_cluster_events(self, ns, limit, types):
        return {'ok': True, 'events': self._events}


def _warn(ns, kind, name, reason, msg='x'):
    return {'namespace': ns, 'kind': kind, 'obj_name': name, 'obj': f'{kind}/{name}',
            'reason': reason, 'message': msg, 'type': 'Warning'}


class TestWatcherLogic(unittest.TestCase):
    def test_first_tick_is_baseline_no_fire(self):
        api = _FakeApi([_warn('default', 'Pod', 'a', 'BackOff')])
        w = NotificationWatcher(api)
        fired = []
        w._fire = lambda cfg, cname, e: fired.append(e)
        w.tick()
        self.assertEqual(fired, [])
        self.assertIn('c1', w._seen)

    def test_second_tick_fires_only_for_new_event(self):
        api = _FakeApi([_warn('default', 'Pod', 'a', 'BackOff')])
        w = NotificationWatcher(api)
        fired = []
        w._fire = lambda cfg, cname, e: fired.append(e)
        w.tick()   # baseline
        api._events = [_warn('default', 'Pod', 'a', 'BackOff'),
                       _warn('default', 'Pod', 'b', 'FailedScheduling')]
        w.tick()
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0]['obj_name'], 'b')

    def test_repeated_same_issue_does_not_refire(self):
        events = [_warn('default', 'Pod', 'a', 'BackOff', msg='count=1')]
        api = _FakeApi(events)
        w = NotificationWatcher(api)
        fired = []
        w._fire = lambda cfg, cname, e: fired.append(e)
        w.tick()   # baseline
        # 같은 namespace/kind/name/reason 이지만 count/message 만 바뀐 "반복" 이벤트
        api._events = [_warn('default', 'Pod', 'a', 'BackOff', msg='count=7')]
        w.tick()
        w.tick()
        self.assertEqual(fired, [])   # 재알림 없음

    def test_disabled_skips(self):
        api = _FakeApi([_warn('default', 'Pod', 'a', 'BackOff')], enabled=False)
        w = NotificationWatcher(api)
        fired = []
        w._fire = lambda cfg, cname, e: fired.append(e)
        w.tick()
        api._events.append(_warn('default', 'Pod', 'b', 'X'))
        w.tick()
        self.assertEqual(fired, [])   # enabled=False → 아예 baseline 도 안 잡음

    def test_no_active_cluster_skips(self):
        api = _FakeApi([_warn('default', 'Pod', 'a', 'BackOff')])
        api._active_id = None
        w = NotificationWatcher(api)
        w.tick()
        self.assertEqual(w._seen, {})

    def test_forget_cluster_resets_baseline(self):
        api = _FakeApi([_warn('default', 'Pod', 'a', 'BackOff')])
        w = NotificationWatcher(api)
        w.tick()
        self.assertIn('c1', w._seen)
        w.forget_cluster('c1')
        self.assertNotIn('c1', w._seen)

    def test_tray_notify_calls_icon(self):
        api = _FakeApi([])
        calls = []
        api._tray_state = {'icon': type('I', (), {'notify': staticmethod(
            lambda msg, title: calls.append((title, msg)))})()}
        w = NotificationWatcher(api)
        w._tray_notify('제목', '본문')
        self.assertEqual(calls, [('제목', '본문')])

    def test_tray_notify_noop_without_icon(self):
        api = _FakeApi([])
        w = NotificationWatcher(api)
        w._tray_notify('제목', '본문')   # api._tray_state 없음 — 예외 없이 조용히 통과


class TestWebhookRealHttp(unittest.TestCase):
    """실제 로컬 HTTP 서버로 웹훅 POST 왕복을 검증 — 외부 네트워크/클러스터 불필요."""

    def test_send_test_webhook_reaches_server(self):
        with _LocalWebhookServer() as srv:
            r = send_test_webhook(srv.url)
            self.assertTrue(r['ok'], r)
            got = srv.wait_for(1)
            self.assertEqual(len(got), 1)
            self.assertIn('Polaris', got[0]['title'])

    def test_send_test_webhook_rejects_bad_url(self):
        r = send_test_webhook('not-a-url')
        self.assertFalse(r['ok'])

    def test_send_test_webhook_reports_connection_error(self):
        r = send_test_webhook('http://127.0.0.1:9/hook')   # 닫힌 포트
        self.assertFalse(r['ok'])
        self.assertIn('error', r)

    def test_watcher_fires_real_webhook_on_new_event(self):
        with _LocalWebhookServer() as srv:
            api = _FakeApi([_warn('default', 'Pod', 'a', 'BackOff', msg='첫 발생')])
            api._settings['notifications']['webhookUrl'] = srv.url
            w = NotificationWatcher(api)
            w.tick()   # baseline — 웹훅 없음
            self.assertEqual(srv.wait_for(1, timeout=1), [])

            api._events.append(_warn('default', 'Pod', 'new-pod', 'FailedScheduling', msg='스케줄 실패'))
            w.tick()   # 신규 1건 → 웹훅 발사(별도 스레드, fire-and-forget)
            got = srv.wait_for(1, timeout=5)
            self.assertEqual(len(got), 1)
            payload = got[0]
            self.assertEqual(payload['name'], 'new-pod')
            self.assertEqual(payload['reason'], 'FailedScheduling')
            self.assertEqual(payload['cluster'], 'rd')
            self.assertIn('스케줄 실패', payload['message'])


class TestApiNoSideEffectsAtConstruction(unittest.TestCase):
    """PolarisAPI() 생성만으로는 백그라운드 스레드가 뜨지 않아야 한다 — 헤드리스(MCP)/
    유닛테스트 인스턴스 안전. start_notification_watcher() 를 명시 호출해야 시작."""

    def test_no_watcher_thread_until_explicit_start(self):
        from src.api import PolarisAPI
        api = PolarisAPI()
        self.assertFalse(hasattr(api, '_polaris_notif_watcher'))
        r = api.start_notification_watcher()
        self.assertTrue(r['ok'])
        self.assertTrue(api._polaris_notif_watcher._thread.is_alive())
        api._polaris_notif_watcher.stop()


if __name__ == '__main__':
    unittest.main()
