# -*- coding: utf-8 -*-
"""앱 창이 **앱 화면 말고 다른 페이지로 넘어가지 못하게** 막는다 (v1.3.39).

pywebview 는 창이 어떤 주소로 넘어가든 새 페이지마다 `window.pywebview.api` 를
다시 심는다(edgechromium `on_navigation_completed` → `inject_pywebview`). 그 API 로
보관함 비밀을 읽고, 클러스터에 YAML 을 적용할 수
있다. 그러니 **창에 남의 페이지가 뜨는 순간 전부 넘어간다.**

실제로 가능한 길: 누군가 보낸 `report.html` 이나 브라우저의 링크를 Polaris 창에
끌어다 놓으면 WebView2 는 그 파일로 이동한다. 화면 쪽(main.jsx)에서도 놓기를
막지만, 그건 화면이 살아 있을 때만 통한다 — 마지막 방어선은 여기, 창 자체다.

허용: 앱 화면이 들어 있는 폴더(`dist/`) 안의 주소, `about:blank`.
그 밖은 전부 취소한다. `#route` 만 바뀌는 이동은 이 이벤트가 오지 않는다.
"""
from __future__ import annotations

from urllib.parse import unquote


def _norm(uri: str) -> str:
    """비교용 정규화 — 퍼센트 인코딩·대소문자·역슬래시·쿼리/조각을 걷어 낸다.

    저장소 경로에 한글이 있어 Python 의 `as_uri()` 와 WebView2 가 알려 주는 주소의
    인코딩이 다를 수 있다. 정규화 없이 앞부분을 비교하면 **앱 자기 화면을 막아
    창이 하얗게 된다** — 그 쪽이 훨씬 나쁜 실패라 여기서 넉넉하게 맞춘다.
    Windows 경로는 대소문자를 가리지 않는다.
    """
    s = str(uri or '').strip()
    for sep in ('#', '?'):
        i = s.find(sep)
        if i >= 0:
            s = s[:i]
    return unquote(s).replace('\\', '/').lower()


def root_of(index_uri: str) -> str:
    """`file:///…/dist/index.html` → `file:///…/dist/` (정규화된 형태)."""
    n = _norm(index_uri)
    return n[:n.rfind('/') + 1] if '/' in n else n


def is_allowed(uri: str, index_uri: str) -> bool:
    n = _norm(uri)
    if n in ('about:blank', ''):
        return True
    root = root_of(index_uri)
    # 루트가 비정상적으로 짧으면(예: 'file:///') 무엇이든 통과해 버린다 —
    # 그럴 바엔 앱 화면 파일 하나만 허용한다.
    if len(root) <= len('file:///'):
        return n == _norm(index_uri)
    return n.startswith(root)


def install(window, index_uri: str, log=None) -> None:
    """창이 뜬 뒤 WebView2 의 `NavigationStarting` 에 검사기를 붙인다.

    첫 이동(앱 화면 자신)은 그 전에 끝나도 상관없다 — 막을 대상이 아니다.
    """
    def _log(msg):
        if log:
            try:
                log(msg)
            except Exception:
                pass

    def _on_start(sender, args):
        try:
            uri = str(args.Uri)
        except Exception:
            return
        if not is_allowed(uri, index_uri):
            try:
                args.Cancel = True
            except Exception:
                pass
            # 주소 전체를 남기면 로컬 파일 경로가 로그에 쌓인다 — 앞부분만
            _log(f'창 이동 차단: {uri[:80]}')

    def _hook():
        form = getattr(window, 'native', None)
        wv = getattr(getattr(form, 'browser', None), 'webview', None)
        if wv is None:
            _log('창 이동 검사기를 붙이지 못함(WebView2 없음)')
            return
        try:
            wv.NavigationStarting += _on_start
            # 델리게이트가 GC 되지 않도록 창에 묶어 둔다
            window._polaris_navguard = _on_start
        except Exception as e:
            _log(f'창 이동 검사기 연결 실패: {e}')

    try:
        window.events.shown += _hook
    except Exception as e:
        _log(f'창 이동 검사기 예약 실패: {e}')
