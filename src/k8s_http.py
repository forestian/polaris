# -*- coding: utf-8 -*-
"""kubernetes 클라이언트의 **기본 타임아웃·재시도** (v1.3.41, 성능 P1).

kubernetes 파이썬 클라이언트는 호출에 `_request_timeout` 을 주지 않으면 **타임아웃이
없다.** 게다가 urllib3 기본값대로 연결 실패를 3번 더 시도한다. 응답 없는 클러스터
하나에 윈도우 TCP 연결 대기(약 21초) × 4번 = **84초** 가 걸렸다(실측).

그 84초가 쌓이는 자리가 여럿이다:
  · 세션 복원은 저장된 클러스터를 **하나씩** 다시 연결한다 — 죽은 클러스터마다 84초
  · 알림 감시 스레드가 같은 호출에서 멈춘다
  · MCP 모드는 이 동안 전역 잠금을 쥐고 있어 다른 도구까지 모두 기다린다

그래서 **따로 정하지 않은 호출에만** 기본값을 준다:
  · 타임아웃 (연결 5초, 응답 120초). 응답 쪽을 넉넉히 둔 것은 큰 목록·서버 측
    apply 가 느린 망에서 수십 초 걸릴 수 있어서다 — 느린 것과 죽은 것을 가른다.
  · 재시도는 연결 1번, 응답 1번 (아래 _default_retries 설명).

건드리지 않는 것:
  · `_request_timeout` 을 직접 준 호출 (netscan·yamllab 등 — 각자 이유가 있다)
  · `_preload_content=False` 스트림 (watch · 로그 follow) — 원래 오래 열려 있는 연결이다
  · exec/attach 웹소켓 — 이 경로를 지나지 않는다

주의: kubernetes 클라이언트는 `_request_timeout` 이 **float 이면 조용히 무시한다**
(int 또는 (연결, 응답) 튜플만 본다, v1.2.123 에서 겪었다). 그래서 기본값은 튜플이다.
"""
from __future__ import annotations

DEFAULT_TIMEOUT = (5, 120)          # (연결, 응답) 초 — 튜플이어야 한다(위 주의)
_MARK = '_polaris_default_timeout'


def _default_retries():
    import urllib3
    # connect=1 — 죽은 클러스터는 (5초 × 2번) 이면 포기한다(예전 84초).
    # read=1 — 0 으로 두면 안 된다. 서버가 먼저 닫아 둔 keep-alive 연결을 다시 쓰다
    #   끊기는 것(RemoteDisconnected)을 urllib3 는 read 오류로 센다. 기본 재시도가 이것을
    #   조용히 흡수해 왔으므로 한 번은 남긴다. (POST/PATCH 는 원래 read 재시도를 안 한다.)
    return urllib3.Retry(total=3, connect=1, read=1, status=0, other=0, redirect=2,
                         raise_on_redirect=False)


def wrap_request(orig_request):
    """RESTClientObject.request 를 감싼다 — 따로 정하지 않은 호출에만 기본 타임아웃."""
    def request(self, method, url, query_params=None, headers=None,
                body=None, post_params=None, _preload_content=True,
                _request_timeout=None):
        if _request_timeout is None and _preload_content:
            _request_timeout = DEFAULT_TIMEOUT
        return orig_request(self, method, url, query_params=query_params,
                            headers=headers, body=body, post_params=post_params,
                            _preload_content=_preload_content,
                            _request_timeout=_request_timeout)
    setattr(request, _MARK, True)
    return request


def wrap_init(orig_init):
    """RESTClientObject.__init__ 을 감싼다 — 설정에 재시도 값이 없을 때만 기본값."""
    def __init__(self, configuration, *a, **kw):
        try:
            if getattr(configuration, 'retries', None) is None:
                configuration.retries = _default_retries()
        except Exception:
            pass
        orig_init(self, configuration, *a, **kw)
    setattr(__init__, _MARK, True)
    return __init__


def install() -> bool:
    """RESTClientObject 에 기본값을 한 번 입힌다. 이미 입혔으면 아무것도 안 한다."""
    try:
        from kubernetes.client import rest
    except Exception:
        return False
    cls = rest.RESTClientObject
    if getattr(cls.request, _MARK, False):
        return True
    cls.__init__ = wrap_init(cls.__init__)
    cls.request = wrap_request(cls.request)
    return True
