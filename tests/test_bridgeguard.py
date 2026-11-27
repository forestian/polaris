# -*- coding: utf-8 -*-
"""JS → Python 다리 문지기 (v1.5.28 보안 검토).

  1) 밑줄로 시작하는 내부 함수(_unlock_dpapi_now 등) · 점으로 들어가는 내부 객체(_polaris_vault.retrieve ·
     k8s.connect)는 화면에서 부를 수 없다 — pywebview 의 실제 디스패치(js_bridge_call)를 통해 확인
  2) 공개 메서드 · pywebview 내부 신호는 그대로 된다
  3) 새 창 주소는 http(s) 만 — file: · UNC · 프로토콜 처리기는 버린다
  4) 화면 코드(ui/src)는 밑줄 · 점 이름을 부르지 않는다 — 막아도 깨지는 화면이 없다
  5) 앱 시작이 창을 만들기 전에 문지기를 건다
"""
import re
import time
import unittest
from pathlib import Path
from unittest import mock

from src import bridgeguard as BG

ROOT = Path(__file__).resolve().parent.parent


class Api:
    def __init__(self):
        self.calls = []
        self.k8s = Inner(self.calls)
        self._polaris_vault = Inner(self.calls)

    def get_status(self):
        self.calls.append('get_status')
        return {'ok': True}

    def _unlock_dpapi_now(self):
        self.calls.append('_unlock_dpapi_now')
        return True


class Inner:
    def __init__(self, calls):
        self.calls = calls

    def connect(self, *a):
        self.calls.append('inner.connect')

    def retrieve(self, *a):
        self.calls.append('inner.retrieve')
        return 'SECRET'


class Window:
    def __init__(self, api):
        self._js_api = api
        self._functions = {}
        self.evaluated = []

    def evaluate_js(self, s):
        self.evaluated.append(s)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(BG.install())
        import webview.util as util
        self.call = util.js_bridge_call
        self.api = Api()
        self.w = Window(self.api)

    def _go(self, name):
        self.call(self.w, name, [], '1')
        time.sleep(0.2)                         # pywebview 는 스레드로 부른다

    def test_막는_이름(self):
        for name in ('_unlock_dpapi_now', '_polaris_vault.retrieve', 'k8s.connect', '__class__', 'k8s', '', None):
            self._go(name)
        self.assertEqual(self.api.calls, [], '내부 함수 · 내부 객체 · 공개 속성 객체가 불렸다')

    def test_공개_메서드는_된다(self):
        self._go('get_status')
        self.assertEqual(self.api.calls, ['get_status'])
        self.assertTrue(self.w.evaluated, '결과를 화면에 돌려준다')

    def test_판정(self):
        self.assertTrue(BG.allowed(self.w, 'get_status'))
        self.assertTrue(BG.allowed(self.w, 'pywebviewMoveWindow'))
        self.w._functions['exposed_fn'] = lambda: 1
        self.assertTrue(BG.allowed(self.w, 'exposed_fn'))
        for bad in ('_unlock_dpapi_now', 'k8s.connect', 'k8s', 'nope', 'get_status.__globals__'):
            self.assertFalse(BG.allowed(self.w, bad), bad)

    def test_플랫폼_모듈도_바뀐다(self):
        import webview.util as util
        from webview.platforms import edgechromium as ec
        self.assertIs(ec.js_bridge_call, util.js_bridge_call)
        self.assertTrue(getattr(ec.EdgeChrome, '_polaris_guarded', False))

    def test_새_창_주소(self):
        for ok in ('https://gitlab.example.com/x', 'http://10.0.0.1:8080/'):
            self.assertTrue(BG.external_url_ok(ok), ok)
        for bad in ('file:///C:/Windows/System32/cmd.exe', '\\\\attacker\\share\\x.exe', '//attacker/share',
                    'search-ms:query=x', 'ms-settings:', 'javascript:alert(1)', 'https://user:pw@evil/', '', None):
            self.assertFalse(BG.external_url_ok(bad), bad)

    def test_새_창_요청_처리(self):
        from webview.platforms import edgechromium as ec

        class Args:
            def __init__(self, uri):
                self.uri, self.handled = uri, False

            def set_Handled(self, v):
                self.handled = v

            def get_Uri(self):
                return self.uri
        with mock.patch('webbrowser.open') as op:
            a = Args('file:///C:/Windows/System32/cmd.exe')
            ec.EdgeChrome.on_new_window_request(None, None, a)
            self.assertTrue(a.handled)
            op.assert_not_called()
            ec.EdgeChrome.on_new_window_request(None, None, Args('https://example.com/'))
            op.assert_called_once_with('https://example.com/')


class UiDoesNotNeedPrivateNames(unittest.TestCase):
    def test_화면은_밑줄_점_이름을_부르지_않는다(self):
        bad = []
        for f in (ROOT / 'ui' / 'src').rglob('*.js*'):
            if f.name.endswith('.test.mjs'):
                continue
            text = f.read_text(encoding='utf-8')
            for m in re.finditer(r"call(?:Safe)?\('([^']+)'", text):
                if m.group(1).startswith('_') or '.' in m.group(1):
                    bad.append((f.name, m.group(1)))
            for m in re.finditer(r'pywebview\.api\.([A-Za-z_][\w.]*)\(', text):
                if m.group(1).startswith('_') or '.' in m.group(1):
                    bad.append((f.name, m.group(1)))
        self.assertEqual(bad, [])

    def test_창을_만들기_전에_건다(self):
        src = (ROOT / 'src' / 'runtime.py').read_text(encoding='utf-8')
        self.assertLess(src.index('bridgeguard.install()'), src.index('window = webview.create_window('))


if __name__ == '__main__':
    unittest.main()
