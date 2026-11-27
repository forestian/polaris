# -*- coding: utf-8 -*-
"""JS → Python 다리(js_api) 문지기 (v1.5.28 보안 검토).

pywebview 는 창에 넘긴 js_api 객체의 **공개 메서드 목록**만 화면에 알려 주지만, 실제로 호출을 처리하는
`webview.util.js_bridge_call` 은 화면이 보낸 이름을 `getattr` 로 점(.)을 따라 그대로 찾아 부른다
(pywebview 6.2.1 확인 — 밑줄 검사도, 허용 목록도 없다). 그래서 화면 안에서 스크립트를 돌릴 수 있으면
  · `_unlock_dpapi_now` 처럼 밑줄로 시작하는 내부 함수(Windows Hello 확인을 건너뛰고 보관함 열기)
  · `_polaris_vault.retrieve` 처럼 내부 객체를 타고 들어가 비밀을 평문으로 읽기
  · `k8s.connect` 처럼 공개 속성 객체의 메서드(API 층의 검사를 거치지 않는다)
를 부를 수 있었다. 여기서 그 이름들을 막는다 — 점이 들어 있거나, 밑줄로 시작하거나, js_api 의 **바로 위**에
있는 호출 가능한 메서드가 아니면 부르지 않는다. pywebview 자체의 내부 신호(pywebviewMoveWindow 등)는 그대로 둔다.

화면 코드(ui/src)는 밑줄 · 점 이름을 부르지 않는다(tests/test_bridgeguard.py 가 확인한다).
"""
from __future__ import annotations

import logging

logger = logging.getLogger('polaris.bridgeguard')

# pywebview 가 스스로 쓰는 신호 — js_api 의 메서드가 아니다
_PYWEBVIEW_INTERNAL = frozenset({
    'pywebviewMoveWindow', 'pywebviewEventHandler', 'pywebviewAsyncCallback',
    'pywebviewStateUpdate', 'pywebviewStateDelete',
})

_installed = False


def allowed(window, func_name) -> bool:
    """이 이름을 화면이 불러도 되는가."""
    if not isinstance(func_name, str) or not func_name:
        return False
    if func_name in _PYWEBVIEW_INTERNAL:
        return True
    if '.' in func_name or func_name.startswith('_'):
        return False
    # window.expose() 로 따로 내놓은 함수
    funcs = getattr(window, '_functions', None) or {}
    if func_name in funcs:
        return True
    api = getattr(window, '_js_api', None)
    if api is None:
        return False
    # 클래스에 정의된 메서드만 — 인스턴스 속성(객체 · dict 등)은 메서드가 아니다
    attr = getattr(type(api), func_name, None)
    return callable(attr)


def install() -> bool:
    """pywebview 의 다리 호출을 감싼다. 창을 만들기 **전에** 한 번 부른다. 여러 번 불러도 된다."""
    global _installed
    if _installed:
        return True
    try:
        import webview.util as util
    except Exception:
        return False
    original = util.js_bridge_call

    def guarded_js_bridge_call(window, func_name, param, value_id):
        if not allowed(window, func_name):
            logger.warning('다리 호출 거부: %r', str(func_name)[:120])
            return None
        return original(window, func_name, param, value_id)

    guarded_js_bridge_call.__wrapped__ = original
    util.js_bridge_call = guarded_js_bridge_call
    # 각 플랫폼 모듈은 `from webview.util import js_bridge_call` 로 **이름을 복사해** 쓴다 — 그쪽도 바꿔야 한다
    import importlib
    for mod in ('webview.platforms.edgechromium', 'webview.platforms.winforms', 'webview.platforms.cef',
                'webview.platforms.mshtml'):
        try:
            m = importlib.import_module(mod)
        except Exception:
            continue
        if getattr(m, 'js_bridge_call', None) is original:
            m.js_bridge_call = guarded_js_bridge_call
    _guard_new_window()
    _installed = True
    return True


def external_url_ok(uri) -> bool:
    """새 창(target=_blank · window.open)으로 열어도 되는 주소 — http(s) 만, 사용자 정보(id:pw@) 없이."""
    from urllib.parse import urlsplit
    try:
        u = urlsplit(str(uri or '').strip())
    except Exception:
        return False
    return u.scheme in ('http', 'https') and bool(u.hostname) and not u.username and not u.password


def _guard_new_window() -> None:
    """새 창 요청을 거른다(v1.5.28 보안 검토).

    pywebview 는 화면이 새 창을 열려 하면(target=_blank 링크 · window.open) 주소를 따지지 않고
    `webbrowser.open(주소)` 로 넘긴다 — Windows 에서는 os.startfile 이라 `file:///C:/…/cmd.exe` ·
    `\\\\서버\\공유\\x.exe` · `search-ms:` · `ms-*:` 같은 주소가 그대로 프로그램을 띄운다. 창 이동 검사(navguard)는
    새 창 요청을 보지 않는다. http(s) 만 기본 브라우저로 열고 나머지는 버린다."""
    try:
        from webview.platforms import edgechromium as ec
    except Exception:
        return
    cls = getattr(ec, 'EdgeChrome', None)
    if cls is None or getattr(cls, '_polaris_guarded', False):
        return

    def on_new_window_request(self, sender, args):
        try:
            args.set_Handled(True)
        except Exception:
            try:
                args.Handled = True
            except Exception:
                pass
        try:
            uri = str(args.get_Uri())
        except Exception:
            try:
                uri = str(args.Uri)
            except Exception:
                return
        if external_url_ok(uri):
            import webbrowser
            webbrowser.open(uri)
        else:
            logger.warning('새 창 주소 거부: %r', uri[:120])

    cls.on_new_window_request = on_new_window_request
    cls._polaris_guarded = True
