# -*- coding: utf-8 -*-
"""v1.3.41 성능 점검 — 코어 쪽.

  P1  kubernetes 호출에 타임아웃이 없어 응답 없는 클러스터 하나에 84초(실측)
  P12 이벤트 `limit=500` 은 최신 500개가 아니었다 → 알림이 새 경고를 놓칠 수 있었다
"""
import unittest
from types import SimpleNamespace as NS


class DefaultTimeoutTests(unittest.TestCase):
    """P1 — 따로 정하지 않은 호출에만 기본값. 스트림·직접 지정한 호출은 그대로."""

    def setUp(self):
        # v1.3.73 부터 kubernetes 는 처음 쓸 때 불러오고, 그 순간 기본값이 입혀진다
        import src.k8s
        src.k8s.preload_k8s()
        from kubernetes.client import rest
        self.rest = rest

    def _call(self, **kw):
        """감싼 request 가 원래 함수에 넘기는 인자를 본다."""
        from src import k8s_http
        self.assertTrue(getattr(self.rest.RESTClientObject.request, k8s_http._MARK, False),
                        'src.k8s 를 import 하면 기본값이 입혀져 있어야 한다')
        seen = {}
        wrapped = k8s_http.wrap_request(lambda self, method, url, **k: seen.update(k))
        wrapped(object(), 'GET', 'https://x/api', **kw)
        return seen

    def test_지정_안_한_호출은_기본_타임아웃(self):
        from src.k8s_http import DEFAULT_TIMEOUT
        self.assertEqual(self._call()['_request_timeout'], DEFAULT_TIMEOUT)
        self.assertIsInstance(DEFAULT_TIMEOUT, tuple, 'float 은 클라이언트가 조용히 무시한다')

    def test_직접_준_값은_그대로(self):
        self.assertEqual(self._call(_request_timeout=10)['_request_timeout'], 10)
        self.assertEqual(self._call(_request_timeout=(1, 2))['_request_timeout'], (1, 2))

    def test_스트림은_건드리지_않는다(self):
        # watch · 로그 follow 는 원래 오래 열려 있다 — 타임아웃을 주면 끊긴다
        self.assertIsNone(self._call(_preload_content=False)['_request_timeout'])

    def test_재시도는_설정에_값이_없을_때만(self):
        from kubernetes import client
        import urllib3
        cfg = client.Configuration()
        cfg.host = 'https://127.0.0.1:1'
        self.rest.RESTClientObject(cfg)
        self.assertIsInstance(cfg.retries, urllib3.Retry)
        self.assertEqual(cfg.retries.connect, 1)
        self.assertGreaterEqual(cfg.retries.read, 1,
                                '0 이면 서버가 닫아 둔 keep-alive 연결 재사용이 곧 오류가 된다')
        mine = urllib3.Retry(total=7)
        cfg2 = client.Configuration()
        cfg2.host = 'https://127.0.0.1:1'
        cfg2.retries = mine
        self.rest.RESTClientObject(cfg2)
        self.assertIs(cfg2.retries, mine)

    def test_두번_입혀도_한_번만(self):
        from src import k8s_http
        before = self.rest.RESTClientObject.request
        k8s_http.install()
        self.assertIs(self.rest.RESTClientObject.request, before)


# ── P12 ──────────────────────────────────────────────────────────────────────
def _ev(name, ns, typ, ts):
    from datetime import datetime, timezone
    t = datetime.fromtimestamp(ts, tz=timezone.utc)
    return NS(metadata=NS(name=name, namespace=ns, creation_timestamp=t),
              type=typ, reason='R', message=name, count=1,
              first_timestamp=t, last_timestamp=t, event_time=None,
              involved_object=NS(kind='Pod', name=name, namespace=ns),
              source=NS(component='c', host=None), reporting_component=None)


class _Core:
    """키(이름) 순서로 페이지를 돌려주는 가짜 core API — 실제 쿠버네티스와 같은 순서."""

    def __init__(self, events, forbid_all=False):
        self.events = sorted(events, key=lambda e: (e.metadata.namespace, e.metadata.name))
        self.forbid_all = forbid_all
        self.calls = []

    def _page(self, evs, limit, _continue=None, field_selector=None):
        if field_selector:
            want = field_selector.split('=', 1)[1]
            evs = [e for e in evs if e.type == want]
        start = int(_continue or 0)
        chunk = evs[start:start + limit]
        nxt = start + limit
        return NS(items=chunk, metadata=NS(_continue=str(nxt) if nxt < len(evs) else None))

    def list_event_for_all_namespaces(self, limit=None, _continue=None, field_selector=None):
        self.calls.append(('all', field_selector))
        if self.forbid_all:
            e = Exception('(403)\nReason: Forbidden')
            e.status = 403
            raise e
        return self._page(self.events, limit, _continue, field_selector)

    def list_namespaced_event(self, namespace, limit=None, _continue=None, field_selector=None):
        self.calls.append(('ns', namespace))
        return self._page([e for e in self.events if e.metadata.namespace == namespace],
                          limit, _continue, field_selector)

    def list_namespace(self):
        names = sorted({e.metadata.namespace for e in self.events})
        return NS(items=[NS(metadata=NS(name=n)) for n in names])


class EventsNewestTests(unittest.TestCase):
    def setUp(self):
        # 가짜 core 는 모델 흉내 객체를 돌려준다 — 모델 경로로 고정(빠른 길은 test_k8s_fast)
        import src.k8s as km
        km._FAST_LISTS = False
        self.addCleanup(setattr, km, '_FAST_LISTS', True)

    def _api(self, core):
        from src.api import PolarisAPI
        api = PolarisAPI.__new__(PolarisAPI)
        api._active_id = 'c1'
        type(api).k8s = property(lambda s: NS(core=core, custom=None))
        self.addCleanup(lambda: delattr(type(api), 'k8s'))
        return api

    def test_최신_경고가_목록에_든다(self):
        # 이름이 'a…' 인 오래된 이벤트 1200개 + 이름이 'z' 인 **방금** 생긴 경고 하나.
        # 예전 limit=500 한 번이면 키 순서 앞쪽 500개만 와서 z 가 빠졌다.
        old = [_ev(f'a{i:04d}', 'default', 'Warning', 1000 + i) for i in range(1200)]
        new = _ev('zzz-new', 'default', 'Warning', 999999)
        api = self._api(_Core(old + [new]))
        r = api.get_cluster_events('', 500, ['Warning'])
        self.assertTrue(r['ok'], r)
        self.assertEqual(len(r['events']), 500)
        self.assertEqual(r['events'][0]['obj_name'], 'zzz-new', '가장 최근 것이 맨 앞')

    def test_종류가_하나면_서버에서_거른다(self):
        core = _Core([_ev('a', 'x', 'Warning', 1), _ev('b', 'x', 'Normal', 2)])
        api = self._api(core)
        r = api.get_cluster_events('', 500, ['Warning'])
        self.assertEqual(core.calls[0], ('all', 'type=Warning'))
        self.assertEqual([e['obj_name'] for e in r['events']], ['a'])
        core.calls.clear()
        api.get_cluster_events('', 500, None)
        self.assertEqual(core.calls[0], ('all', None), '전부 볼 때는 거르지 않는다')

    def test_권한이_없으면_기억하고_바로_네임스페이스별로(self):
        core = _Core([_ev('a', 'n1', 'Warning', 1), _ev('b', 'n2', 'Warning', 2)], forbid_all=True)
        api = self._api(core)
        r1 = api.get_cluster_events('', 500, ['Warning'])
        self.assertEqual(r1['source'], 'per-ns')
        self.assertEqual(len(r1['events']), 2)
        core.calls.clear()
        r2 = api.get_cluster_events('', 500, ['Warning'])
        self.assertEqual(r2['source'], 'per-ns')
        self.assertNotIn('all', [c[0] for c in core.calls], '두 번째부터는 거절당하러 가지 않는다')

    def test_네임스페이스_하나도_최신순(self):
        old = [_ev(f'a{i:04d}', 'ns', 'Warning', i) for i in range(700)]
        api = self._api(_Core(old + [_ev('zz', 'ns', 'Warning', 99999)]))
        r = api.get_cluster_events('ns', 100, ['Warning'])
        self.assertEqual(len(r['events']), 100)
        self.assertEqual(r['events'][0]['obj_name'], 'zz')


if __name__ == '__main__':
    unittest.main()
