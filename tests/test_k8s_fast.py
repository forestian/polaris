# -*- coding: utf-8 -*-
"""P2 (v1.3.42) — 모델 변환 없는 목록이 **모델 경로와 똑같은 행**을 만드는가.

k8s_fast 는 JSON 을 모델처럼 읽히게 할 뿐이다. 어긋나면(필드 이름·시각·빈 값)
화면에 조용히 다른 값이 나온다. 그래서 같은 JSON 을 **진짜 kubernetes 역직렬화**와
fast 경로로 각각 읽어 k8s.py 의 행 만드는 코드를 그대로 돌리고 결과를 비교한다.
"""
import json
import time
import unittest
from types import SimpleNamespace as NS

T0 = '2026-09-20T01:02:03Z'
T1 = '2026-09-27T10:11:12Z'
TM = '2026-09-27T10:11:12.123456Z'   # MicroTime


def _cs(name, ready=True, restarts=0, state=None, last=None, image='img:1'):
    d = {'name': name, 'ready': ready, 'restartCount': restarts, 'image': image,
         'imageID': 'sha256:x', 'containerID': 'containerd://abc', 'started': ready,
         'state': state or {'running': {'startedAt': T1}}}
    if last:
        d['lastState'] = last
    return d


def _pod(name, ns='default', phase='Running', statuses=None, init=None, reason=None,
         deleting=False, node='n1', containers=1):
    meta = {'name': name, 'namespace': ns, 'uid': f'u-{name}', 'creationTimestamp': T0,
            'labels': {'app': name, 'values': 'x'}, 'annotations': {'a': 'b'},
            'ownerReferences': [{'apiVersion': 'apps/v1', 'kind': 'ReplicaSet',
                                 'name': f'{name}-rs', 'uid': 'r', 'controller': True}]}
    if deleting:
        meta['deletionTimestamp'] = T1
    st = {'phase': phase, 'podIP': '10.0.0.1', 'hostIP': '192.168.0.1', 'startTime': T0,
          'podIPs': [{'ip': '10.0.0.1'}],
          'conditions': [{'type': 'Ready', 'status': 'True', 'lastTransitionTime': T1}]}
    if statuses is not None:
        st['containerStatuses'] = statuses
    if init is not None:
        st['initContainerStatuses'] = init
    if reason:
        st['reason'] = reason
    spec = {'nodeName': node,
            'containers': [{'name': f'c{i}', 'image': 'img:1'} for i in range(containers)]}
    return {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': meta, 'spec': spec, 'status': st}


PODS = [
    _pod('ok', statuses=[_cs('c0')]),
    _pod('crash', statuses=[_cs('c0', ready=False, restarts=7,
                                state={'waiting': {'reason': 'CrashLoopBackOff', 'message': 'back-off'}},
                                last={'terminated': {'exitCode': 1, 'reason': 'Error',
                                                     'startedAt': T0, 'finishedAt': T1}})]),
    _pod('pull', phase='Pending', statuses=[_cs('c0', ready=False,
                                                state={'waiting': {'reason': 'ImagePullBackOff'}})]),
    _pod('init-stuck', phase='Pending', statuses=[],
         init=[_cs('i0', ready=False, state={'waiting': {'reason': 'PodInitializing'}}),
               _cs('i1', ready=False, restarts=2,
                   state={'terminated': {'exitCode': 2, 'reason': 'Error', 'finishedAt': T1}})]),
    _pod('evicted', phase='Failed', reason='Evicted', statuses=None),
    _pod('done', phase='Succeeded', statuses=[_cs('c0', ready=False,
                                                  state={'terminated': {'exitCode': 0,
                                                                        'reason': 'Completed'}})]),
    _pod('restarted-running', statuses=[_cs('c0', restarts=3,
                                            state={'running': {'startedAt': TM}})]),
    _pod('half-ready', containers=2, statuses=[_cs('c0'), _cs('c1', ready=False)]),
    _pod('pending-nothing', phase='Pending', statuses=None, node=None),
    _pod('terminating', deleting=True, statuses=[_cs('c0')], ns='kube-system'),
]


def _event(name, typ, ts_field='lastTimestamp', ns='default'):
    e = {'metadata': {'name': name, 'namespace': ns, 'creationTimestamp': T0},
         'involvedObject': {'kind': 'Pod', 'name': f'p-{name}', 'namespace': ns},
         'reason': 'BackOff', 'message': f'msg {name}', 'type': typ, 'count': 3,
         'source': {'component': 'kubelet', 'host': 'n1'},
         'firstTimestamp': T0}
    if ts_field == 'eventTime':
        e['eventTime'] = TM
        e['reportingComponent'] = 'kubelet'
        e.pop('firstTimestamp')
    else:
        e[ts_field] = T1
    return e


EVENTS = [_event('a', 'Warning'), _event('b', 'Normal'),
          _event('c', 'Warning', 'eventTime'), _event('d', 'Warning', ns='kube-system')]


class _Resp:
    def __init__(self, obj):
        self.data = json.dumps(obj).encode()

    def release_conn(self):
        pass


def _typed(obj, kind):
    from kubernetes import client
    return client.ApiClient().deserialize(_Resp(obj), kind)


class _Core:
    """_preload_content 에 따라 모델(느린 길) 또는 원본 JSON(빠른 길)을 돌려준다."""

    def __init__(self, pods=None, events=None):
        self.pods = {'kind': 'PodList', 'apiVersion': 'v1', 'metadata': {}, 'items': pods or []}
        self.events = {'kind': 'EventList', 'apiVersion': 'v1', 'metadata': {},
                       'items': events or []}

    fast_calls = 0

    def _ret(self, obj, kind, kw):
        if kw.get('_preload_content') is False:
            self.fast_calls += 1
            return _Resp(obj)
        return _typed(obj, kind)

    def list_pod_for_all_namespaces(self, **kw):
        return self._ret(self.pods, 'V1PodList', kw)

    def list_namespaced_pod(self, ns, **kw):
        sub = dict(self.pods, items=[p for p in self.pods['items']
                                     if p['metadata']['namespace'] == ns])
        return self._ret(sub, 'V1PodList', kw)

    def list_event_for_all_namespaces(self, **kw):
        return self._ret(self.events, 'CoreV1EventList', kw)


def _strip_age(rows):
    # age 는 지금 시각 기준이라 두 번 부르는 사이 바뀔 수 있다 — 같은 시각에서 비교
    return [{k: v for k, v in r.items() if k != 'age'} for r in rows]


class EquivalenceTests(unittest.TestCase):
    def test_파드_행이_모델_경로와_같다(self):
        from src import k8s as k8s_mod
        from src.k8s import K8sManager
        mgr = K8sManager.__new__(K8sManager)
        mgr.core = _Core(PODS)

        k8s_mod._FAST_LISTS = False
        try:
            slow = mgr.get_pods(None, detail=True)
        finally:
            k8s_mod._FAST_LISTS = True
        self.assertEqual(mgr.core.fast_calls, 0, '끈 상태에서는 모델 경로여야 비교가 된다')
        fast = mgr.get_pods(None, detail=True)
        self.assertEqual(mgr.core.fast_calls, 1, '빠른 길을 실제로 탔어야 한다 — 안 타면 이 비교는 헛돈다')
        self.assertEqual(len(slow), len(PODS))
        self.assertEqual(_strip_age(fast), _strip_age(slow))
        self.assertEqual([r['age'] for r in fast], [r['age'] for r in slow])
        # 표본이 제 역할을 하는지 — 비정상 사유가 실제로 여러 갈래로 나와야 한다
        reasons = {r['name']: r['reason'] for r in fast}
        self.assertEqual(reasons['crash'], 'CrashLoopBackOff')
        self.assertEqual(reasons['evicted'], 'Evicted')
        self.assertEqual(reasons['init-stuck'], 'Error')
        self.assertTrue(any(r['restarted_at'] for r in fast))

    def test_네임스페이스_지정도_같다(self):
        from src import k8s as k8s_mod
        from src.k8s import K8sManager
        mgr = K8sManager.__new__(K8sManager)
        mgr.core = _Core(PODS)
        k8s_mod._FAST_LISTS = False
        try:
            slow = mgr.get_pods('kube-system')
        finally:
            k8s_mod._FAST_LISTS = True
        self.assertEqual(_strip_age(mgr.get_pods('kube-system')), _strip_age(slow))

    def test_이벤트_행이_모델_경로와_같다(self):
        from src.api import PolarisAPI
        slow_items = _typed(_Core(events=EVENTS).events, 'CoreV1EventList').items
        from src.k8s_fast import KList
        fast_items = KList(_Core(events=EVENTS).events).items
        f = PolarisAPI._format_events_core
        self.assertEqual(f(fast_items, None), f(slow_items, None))
        self.assertEqual(f(fast_items, {"Warning"}), f(slow_items, {"Warning"}))


class KObjTests(unittest.TestCase):
    def test_이름_규칙(self):
        from src.k8s_fast import KObj
        o = KObj({'podIP': '1', 'externalIPs': ['a'], 'continue': 'tok', 'apiVersion': 'v1'})
        self.assertEqual(o.pod_ip, '1')
        self.assertEqual(o.external_i_ps, ['a'])
        self.assertEqual(o._continue, 'tok')
        self.assertEqual(o.api_version, 'v1')
        self.assertIsNone(o.missing_field)

    def test_맵은_dict_로_쓸_수_있다(self):
        from src.k8s_fast import KObj
        m = KObj({'metadata': {'labels': {'app': 'x'}}}).metadata.labels
        self.assertEqual(m.get('app'), 'x')
        self.assertEqual(dict(m.items()), {'app': 'x'})
        self.assertIn('app', m)

    def test_dict_메서드와_겹치는_필드(self):
        from src.k8s_fast import KObj
        req = KObj({'key': 'k', 'operator': 'In', 'values': ['a', 'b']})
        self.assertEqual(req.values, ['a', 'b'], 'LabelSelectorRequirement.values')
        plain = KObj({'app': 'x'})
        self.assertEqual(list(plain.values()), ['x'], '필드가 없으면 dict 메서드')

    def test_빈_JSON_도_된다(self):
        from src.k8s_fast import KList
        lst = KList({})
        self.assertEqual(lst.items, [])
        self.assertIsNone(lst.metadata._continue)


class SpeedTests(unittest.TestCase):
    def test_모델_경로보다_훨씬_빠르다(self):
        from src.k8s_fast import KList
        big = {'items': [_pod(f'p{i}', statuses=[_cs('c0', restarts=i % 3)]) for i in range(1500)],
               'metadata': {}}
        raw = json.dumps(big).encode()
        t = time.perf_counter()
        _typed(big, 'V1PodList')
        slow = time.perf_counter() - t
        t = time.perf_counter()
        items = KList(json.loads(raw)).items
        _ = [p.status.container_statuses[0].restart_count for p in items]
        fast = time.perf_counter() - t
        self.assertLess(fast * 5, slow, f'fast={fast*1000:.0f}ms slow={slow*1000:.0f}ms')


class EventsEndToEndTests(unittest.TestCase):
    """get_cluster_events 전체 경로(페이지 넘김 포함)도 두 길이 같은 결과."""

    def test_같다(self):
        import src.k8s as km
        from src.api import PolarisAPI
        core = _Core(events=EVENTS)
        api = PolarisAPI.__new__(PolarisAPI)
        api._active_id = 'c1'
        type(api).k8s = property(lambda s: NS(core=core, custom=None))
        self.addCleanup(lambda: delattr(type(api), 'k8s'))
        km._FAST_LISTS = False
        try:
            slow = api.get_cluster_events('', 500, None)
        finally:
            km._FAST_LISTS = True
        before = core.fast_calls
        fast = api.get_cluster_events('', 500, None)
        self.assertGreater(core.fast_calls, before, '빠른 길을 실제로 탔어야 한다')
        self.assertEqual(fast['events'], slow['events'])
        self.assertEqual(len(fast['events']), len(EVENTS))


class _MetaClient:
    """call_api 를 흉내 — Accept 헤더와 경로를 기록하고 metadata 만 돌려준다."""

    def __init__(self, items=None, fail=False):
        self.calls, self.items, self.fail = [], items or [], fail

    def call_api(self, path, method, query_params=None, header_params=None, **kw):
        self.calls.append((path, dict(query_params or []), (header_params or {}).get('Accept', '')))
        if self.fail:
            raise RuntimeError('metadata 요청 미지원')
        return _Resp({'kind': 'PartialObjectMetadataList', 'metadata': {},
                      'items': [{'metadata': m} for m in self.items]})


class MetadataOnlyTests(unittest.TestCase):
    """P3 — 이름·라벨만 필요한 곳은 본문을 받지 않는다."""

    def test_요청이_metadata_전용이다(self):
        from src.k8s_fast import list_metadata
        c = _MetaClient([{'name': 'a', 'namespace': 'n'}])
        out = list_metadata(c, '/api/v1/secrets', label_selector='owner=helm')
        path, q, accept = c.calls[0]
        self.assertEqual(path, '/api/v1/secrets')
        self.assertIn('as=PartialObjectMetadataList', accept)
        self.assertEqual(q, {'labelSelector': 'owner=helm'})
        self.assertEqual(out.items[0].metadata.name, 'a')

    def test_helm_라벨_조회는_본문을_받지_않는다(self):
        from src.k8s import K8sManager
        mgr = K8sManager.__new__(K8sManager)
        mgr._api_client = _MetaClient([
            {'name': 'sh.helm.release.v1.velero.v1', 'namespace': 'velero',
             'labels': {'owner': 'helm', 'name': 'velero', 'version': '1',
                        'polaris-catalog': 'true', 'polaris-catalog-app-id': 'velero'}},
            {'name': 'sh.helm.release.v1.velero.v2', 'namespace': 'velero',
             'labels': {'owner': 'helm', 'name': 'velero', 'version': '2',
                        'polaris-catalog': 'true', 'polaris-catalog-app-id': 'velero'}},
        ])

        class Core:
            def list_secret_for_all_namespaces(self, **kw):
                raise AssertionError('본문 전체 목록을 부르면 안 된다')

        mgr.core = Core()
        got = mgr.get_helm_releases_by_label('polaris-catalog', 'true',
                                             extra_meta_key='polaris-catalog-app-id')
        self.assertEqual(got, {('velero', 'velero'): 'velero'})
        _, q, _ = mgr._api_client.calls[0]
        self.assertEqual(q['fieldSelector'], 'type=helm.sh/release.v1')

    def test_metadata_요청이_안_되는_서버는_예전_경로(self):
        from src.k8s import K8sManager
        mgr = K8sManager.__new__(K8sManager)
        mgr._api_client = _MetaClient(fail=True)
        called = []

        class Core:
            def list_secret_for_all_namespaces(self, **kw):
                called.append(kw)
                return NS(items=[])

        mgr.core = Core()
        self.assertEqual(mgr.helm_release_secrets_meta(), [])
        self.assertEqual(called[0]['field_selector'], 'type=helm.sh/release.v1')

    def test_velero_판정은_라벨_하나로(self):
        from src.api import PolarisAPI
        if not hasattr(PolarisAPI, 'velero_status'):
            self.skipTest('카탈로그 플러그인 없음')
        seen = []

        class Mgr:
            connected = True

            def helm_release_secrets_meta(self, extra=''):
                seen.append(extra)
                return [NS(metadata=NS(namespace='backup', labels={'name': 'velero', 'version': '3'}))]

        api = PolarisAPI.__new__(PolarisAPI)
        type(api).k8s = property(lambda s: Mgr())
        self.addCleanup(lambda: delattr(type(api), 'k8s'))
        api.get_installed_catalog_apps = lambda: self.fail('전체 앱 목록을 만들면 안 된다')
        r = api.velero_status()
        self.assertEqual(r, {'ok': True, 'installed': True, 'namespace': 'backup', 'release': 'velero'})
        self.assertIn('polaris-catalog-app-id=velero', seen[0])

    def test_검색_인덱스는_metadata_만(self):
        from src.api import PolarisAPI
        c = _MetaClient([{'name': 'x', 'namespace': 'n'}])

        class Mgr:
            connected = True
            _api_client = c

            def get_resources(self, rtype, ns):
                raise AssertionError('본문 목록으로 돌아가면 안 된다')

        api = PolarisAPI.__new__(PolarisAPI)
        api._active_id = 'c1'
        idx = api.get_search_index(force=True, _cluster_id='c1', _mgr=Mgr())
        self.assertEqual(len(idx), len(PolarisAPI._SEARCH_KINDS))
        self.assertTrue(all('as=PartialObjectMetadataList' in a for _, _, a in c.calls))
        self.assertIn('/api/v1/secrets', [p for p, _, _ in c.calls])


if __name__ == '__main__':
    unittest.main()
