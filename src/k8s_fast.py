# -*- coding: utf-8 -*-
"""큰 목록을 **모델 변환 없이** 읽기 (v1.3.42, 성능 P2).

kubernetes 파이썬 클라이언트는 응답 JSON 을 V1Pod 같은 모델 객체로 바꾸는데, 이것이
순수 파이썬 반사(reflection)라 매우 느리다. 실측: 파드 2000개(8.5MB)가 **2285ms**,
같은 JSON 을 `json.loads` 만 하면 **54ms**. 그 동안 GIL 을 쥐고 있어
다른 브리지 호출까지 멈칫한다.

그렇다고 k8s.py 의 행 만드는 코드(수십 곳이 `p.status.container_statuses` 처럼
모델 속성을 읽는다)를 다 dict 용으로 고쳐 쓰면 어긋날 곳이 너무 많다. 그래서
**JSON 을 모델처럼 읽히게** 한다:

  · `obj.pod_ip` → JSON 의 `podIP` (밑줄·대소문자를 무시하고 찾는다 — `external_i_ps`
    ↔ `externalIPs`, `_continue` ↔ `continue` 까지 맞는다)
  · 없는 필드 → None (모델도 설정 안 된 필드는 None)
  · 시각 필드(`*_timestamp`·`*_time`·`started_at`·`finished_at`) → datetime (모델과 같다)
  · labels·annotations 같은 맵 → dict 처럼 `.get()`·`.items()`·`in` 이 된다

모델 경로와 **결과가 같은지는 테스트가 실제 kubernetes 역직렬화와 나란히 돌려 본다**
(tests/test_k8s_fast.py). 새 화면에 쓰려면 그 테스트에 표본을 더할 것.
"""
from __future__ import annotations

import json
from datetime import datetime

# dict 메서드와 이름이 겹치는 쿠버네티스 필드 — 이 이름은 **필드가 있으면 필드**를 준다.
# (LabelSelectorRequirement.values, ConfigMap/Secret 볼륨의 items)
_CONFLICT = ('items', 'values')
_TIME_EXACT = frozenset({'started_at', 'finished_at', 'time'})


def _is_time_field(name: str) -> bool:
    return name.endswith('_timestamp') or name.endswith('_time') or name in _TIME_EXACT


def _parse_time(v):
    if not isinstance(v, str) or not v:
        return v
    try:
        return datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        return v


def _norm(k: str) -> str:
    return k.replace('_', '').lower()


class KObj(dict):
    """JSON 객체를 모델처럼 읽게 해 주는 dict.

    속도: `__getattr__` 은 **없는 속성일 때만** 불린다(dict 메서드·슬롯은 그대로 빠르다).
    한 번 감싼 하위 객체는 제자리에 KObj 로 바꿔 두어 다시 감싸지 않는다 — KObj 도
    dict 라 그대로 JSON 으로 내보낼 수 있다.
    """

    __slots__ = ('_idx',)

    def _find(self, name):
        if dict.__contains__(self, name):
            return name
        try:
            idx = self._idx
        except AttributeError:
            idx = {_norm(k): k for k in dict.keys(self)}
            self._idx = idx
        return idx.get(_norm(name))

    def _field(self, name):
        key = self._find(name)
        if key is None:
            return None
        v = dict.__getitem__(self, key)
        if _is_time_field(name):
            return _parse_time(v)
        if type(v) is dict:
            v = KObj(v)
            dict.__setitem__(self, key, v)
        elif type(v) is list and v and type(v[0]) is dict:
            v = [KObj(x) if type(x) is dict else x for x in v]
            dict.__setitem__(self, key, v)
        return v

    def __getattr__(self, name):
        # `_idx` 는 아직 안 채운 슬롯 — 여기로 오면 필드로 찾지 말고 없다고 해야
        # _find 가 색인을 만든다(안 그러면 무한 재귀)
        if name.startswith('__') or name == '_idx':
            raise AttributeError(name)
        return self._field(name)

    # 맵(labels 등)을 dict 로 쓸 때 중첩 값도 같은 규칙으로
    def get(self, key, default=None):
        return wrap(dict.get(self, key, default))


class _FieldOrMethod:
    """`obj.values` — `values` 필드가 있으면 그 값, 없으면 dict.values 메서드."""

    def __init__(self, name):
        self.name = name
        self.meth = getattr(dict, name)

    def __get__(self, obj, typ=None):
        if obj is None:
            return self
        if obj._find(self.name) is not None:
            return obj._field(self.name)
        return self.meth.__get__(obj, typ)


for _n in _CONFLICT:
    setattr(KObj, _n, _FieldOrMethod(_n))


def wrap(v):
    if isinstance(v, KObj):
        return v
    if isinstance(v, dict):
        return KObj(v)
    if isinstance(v, list):
        return [wrap(x) for x in v]
    return v


class KList:
    """목록 응답 — `.items`(KObj 목록) · `.metadata`(KObj)."""

    __slots__ = ('items', 'metadata')

    def __init__(self, data: dict):
        self.items = [KObj(x) if isinstance(x, dict) else x for x in (data.get('items') or [])]
        self.metadata = KObj(data.get('metadata') or {})


def fast_list(fn, *args, **kwargs) -> KList:
    """`fn(*args, **kwargs)` 를 모델 변환 없이 불러 KList 로.

    fn 은 kubernetes 클라이언트의 list_* 메서드. 오류는 모델 경로와 똑같이 올라온다
    (ApiException 등) — 호출하는 쪽의 예외 처리를 바꿀 필요가 없다.
    """
    kwargs['_preload_content'] = False
    # _preload_content=False 는 k8s_http 가 「스트림」 으로 보고 기본 타임아웃을 건너뛴다.
    # 이건 스트림이 아니라 한 번에 받는 목록이므로 여기서 직접 준다.
    if kwargs.get('_request_timeout') is None:
        from src.k8s_http import DEFAULT_TIMEOUT
        kwargs['_request_timeout'] = DEFAULT_TIMEOUT
    resp = fn(*args, **kwargs)
    try:
        raw = resp.data
    finally:
        try:
            resp.release_conn()
        except Exception:
            pass
    return KList(json.loads(raw or b'{}'))


# ── 메타데이터만 받기 (v1.3.42, 성능 P3) ─────────────────────────────────────
#
# 이름·라벨만 필요한데 **본문 전체**를 받던 곳이 있었다 — 명령 팔레트 검색 인덱스는
# Secret·ConfigMap 을 전부 받았다(helm 릴리스 Secret 은 차트 전체를
# gzip+base64 로 품어 하나에 최대 1MB, 리비전마다 하나).
# API 서버에 `as=PartialObjectMetadataList` 로 요청하면 metadata 만 온다(1.15+).
# 지원하지 않는 서버는 뒤의 `application/json` 으로 전체를 준다 — 그래도 metadata 는 있다.
_META_ACCEPT = ('application/json;as=PartialObjectMetadataList;g=meta.k8s.io;v=v1,'
                'application/json;as=PartialObjectMetadataList;g=meta.k8s.io;v=v1beta1,'
                'application/json')


def list_metadata(api_client, path: str, label_selector: str = None,
                  field_selector: str = None, limit: int = None) -> KList:
    """`path`(예: /api/v1/secrets) 의 목록을 metadata 만 받아 KList 로."""
    from src.k8s_http import DEFAULT_TIMEOUT
    q = []
    if label_selector:
        q.append(('labelSelector', label_selector))
    if field_selector:
        q.append(('fieldSelector', field_selector))
    if limit:
        q.append(('limit', int(limit)))
    resp = api_client.call_api(
        path, 'GET', query_params=q, header_params={'Accept': _META_ACCEPT},
        auth_settings=['BearerToken'], _preload_content=False,
        _return_http_data_only=True, _request_timeout=DEFAULT_TIMEOUT)
    try:
        raw = resp.data
    finally:
        try:
            resp.release_conn()
        except Exception:
            pass
    return KList(json.loads(raw or b'{}'))
