# -*- coding: utf-8 -*-
"""대시보드 「주의가 필요한 파드」 선별 + 컨트롤 플레인 카드 (v1.2.129).

여기서 잠그는 두 가지:

1) **한 번도 못 뜬 파드가 기간 필터에 걸려 사라지지 않는지.**
   ImagePullBackOff·Pending 파드는 restartCount 가 0 이고 재시작 시각도 없다.
   '3일 내 재시작'으로만 거르면 정작 가장 급한 파드가 목록에서 빠진다.

2) **readyz 조회 실패를 장애로 표시하지 않는지 (fail-open).**
   클러스터 정책상 403/404 일 수 있는데, 그걸 빨간불로 띄우면 멀쩡한 클러스터를
   장애라고 신고하게 된다.
"""
import unittest
from datetime import datetime, timedelta, timezone

from src.k8s import (
    select_attention_pods, _pod_problem_reason, _pod_last_restart_at,
    _pod_is_abnormal, _parse_iso,
)

NOW = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)


def _ago(days=0, hours=0):
    return (NOW - timedelta(days=days, hours=hours)).isoformat()


def _pod(name, status='Running', restarts='0', abnormal=False, reason='',
         restarted_at='', ns='demo'):
    return {'name': name, 'namespace': ns, 'status': status, 'restarts': restarts,
            'abnormal': abnormal, 'reason': reason, 'restarted_at': restarted_at,
            'node': 'n1'}


class TestSelectAttentionPods(unittest.TestCase):
    def test_never_started_pod_is_kept_despite_no_restart_history(self):
        """이 테스트가 이 기능의 핵심 — 시간 필터만 걸면 사라지던 파드다."""
        pods = [_pod('img', status='Pending', abnormal=True, reason='ImagePullBackOff')]
        r = select_attention_pods(pods, now=NOW, days=3)
        self.assertEqual([i['name'] for i in r['items']], ['img'])
        self.assertEqual(r['abnormal_count'], 1)
        self.assertEqual(r['restart_count'], 0)   # 재시작 이력은 없다

    def test_old_restarts_are_dropped(self):
        """재시작 999회지만 반년 전이면 지금 문제로 볼 근거가 없다."""
        pods = [_pod('old', restarts='999', restarted_at=_ago(days=180))]
        r = select_attention_pods(pods, now=NOW, days=3)
        self.assertEqual(r['items'], [])
        self.assertEqual(r['total'], 0)

    def test_recent_restart_of_healthy_pod_is_kept(self):
        pods = [_pod('recent', restarts='2', restarted_at=_ago(days=1))]
        r = select_attention_pods(pods, now=NOW, days=3)
        self.assertEqual([i['name'] for i in r['items']], ['recent'])
        self.assertTrue(r['items'][0]['recent_restart'])

    def test_boundary_just_inside_and_outside_window(self):
        inside = _pod('in', restarts='1', restarted_at=_ago(days=2, hours=23))
        outside = _pod('out', restarts='1', restarted_at=_ago(days=3, hours=1))
        r = select_attention_pods([inside, outside], now=NOW, days=3)
        self.assertEqual([i['name'] for i in r['items']], ['in'])

    def test_healthy_pods_excluded(self):
        pods = [_pod('fine'), _pod('job', status='Succeeded')]
        self.assertEqual(select_attention_pods(pods, now=NOW)['items'], [])

    def test_abnormal_sorted_before_recent_restart(self):
        pods = [
            _pod('recent', restarts='1', restarted_at=_ago(hours=1)),
            _pod('broken', status='Pending', abnormal=True, reason='ImagePullBackOff'),
        ]
        r = select_attention_pods(pods, now=NOW, days=3)
        self.assertEqual([i['name'] for i in r['items']], ['broken', 'recent'])

    def test_truncation_reports_total(self):
        """limit 으로 조용히 자르면 '10개뿐'으로 오독된다 — total 이 남아야 한다."""
        pods = [_pod(f'p{i}', status='Pending', abnormal=True, reason='X')
                for i in range(25)]
        r = select_attention_pods(pods, now=NOW, days=3, limit=10)
        self.assertEqual(len(r['items']), 10)
        self.assertEqual(r['total'], 25)
        self.assertTrue(r['truncated'])

    def test_not_truncated_when_under_limit(self):
        pods = [_pod('a', status='Pending', abnormal=True)]
        r = select_attention_pods(pods, now=NOW, days=3, limit=10)
        self.assertFalse(r['truncated'])

    def test_internal_sort_key_not_leaked(self):
        pods = [_pod('a', restarts='1', restarted_at=_ago(hours=2))]
        self.assertNotIn('_restart_dt', select_attention_pods(pods, now=NOW)['items'][0])

    def test_empty_and_garbage_input(self):
        self.assertEqual(select_attention_pods([], now=NOW)['total'], 0)
        self.assertEqual(select_attention_pods(None, now=NOW)['total'], 0)
        # 깨진 restarted_at 이 예외로 번지지 않아야 한다
        r = select_attention_pods([_pod('x', restarted_at='not-a-date')], now=NOW)
        self.assertEqual(r['items'], [])

    def test_window_days_reported(self):
        r = select_attention_pods([], now=NOW, days=7)
        self.assertEqual(r['window_days'], 7)


class TestParseIso(unittest.TestCase):
    def test_z_suffix_and_naive_treated_as_utc(self):
        self.assertEqual(_parse_iso('2026-08-03T12:00:00Z').tzinfo, timezone.utc)
        self.assertEqual(_parse_iso('2026-08-03T12:00:00').tzinfo, timezone.utc)

    def test_invalid_returns_none(self):
        for bad in ('', None, 'nope', '2026-13-45'):
            self.assertIsNone(_parse_iso(bad), bad)


# ── 파드 객체 → 사유/재시작시각 추출 (k8s 클라이언트 객체 모사) ────────────────
class _S:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _cs(ready=True, restart_count=0, waiting=None, terminated=None,
        last_terminated=None, running_at=None):
    state = _S(waiting=_S(reason=waiting) if waiting else None,
               terminated=_S(reason=terminated) if terminated else None,
               running=_S(started_at=running_at) if running_at else None)
    last = _S(terminated=_S(reason='Error', finished_at=last_terminated)
              if last_terminated else None)
    return _S(ready=ready, restart_count=restart_count, state=state, last_state=last)


def _fake_pod(phase='Running', reason=None, css=None, init_css=None):
    return _S(status=_S(phase=phase, reason=reason,
                        container_statuses=css or [],
                        init_container_statuses=init_css or []))


class TestPodReasonExtraction(unittest.TestCase):
    def test_crashloop_is_detected_even_though_phase_is_running(self):
        """CrashLoopBackOff 파드의 phase 는 Running 이다 — phase 만 보면 정상으로 분류된다."""
        pod = _fake_pod('Running', css=[_cs(ready=False, restart_count=9,
                                           waiting='CrashLoopBackOff')])
        self.assertEqual(_pod_problem_reason(pod), 'CrashLoopBackOff')
        self.assertTrue(_pod_is_abnormal(pod, ready=0, total=1))

    def test_container_creating_is_not_a_problem(self):
        pod = _fake_pod('Pending', css=[_cs(ready=False, waiting='ContainerCreating')])
        self.assertEqual(_pod_problem_reason(pod), '')

    def test_completed_terminated_is_not_a_problem(self):
        pod = _fake_pod('Succeeded', css=[_cs(ready=False, terminated='Completed')])
        self.assertEqual(_pod_problem_reason(pod), '')
        self.assertFalse(_pod_is_abnormal(pod, ready=0, total=1))

    def test_pod_level_reason_wins(self):
        pod = _fake_pod('Failed', reason='Evicted')
        self.assertEqual(_pod_problem_reason(pod), 'Evicted')

    def test_init_container_failure_detected(self):
        pod = _fake_pod('Pending',
                        init_css=[_cs(ready=False, waiting='CreateContainerConfigError')])
        self.assertEqual(_pod_problem_reason(pod), 'CreateContainerConfigError')

    def test_running_but_not_all_ready_is_abnormal(self):
        pod = _fake_pod('Running', css=[_cs(ready=True), _cs(ready=False)])
        self.assertTrue(_pod_is_abnormal(pod, ready=1, total=2))

    def test_fully_ready_running_is_normal(self):
        pod = _fake_pod('Running', css=[_cs(ready=True)])
        self.assertFalse(_pod_is_abnormal(pod, ready=1, total=1))

    def test_last_restart_uses_finished_at(self):
        t = NOW - timedelta(hours=3)
        pod = _fake_pod('Running', css=[_cs(restart_count=2, last_terminated=t)])
        self.assertEqual(_pod_last_restart_at(pod), t.isoformat())

    def test_last_restart_falls_back_to_started_at(self):
        t = NOW - timedelta(hours=5)
        pod = _fake_pod('Running', css=[_cs(restart_count=1, running_at=t)])
        self.assertEqual(_pod_last_restart_at(pod), t.isoformat())

    def test_no_restart_means_no_timestamp(self):
        pod = _fake_pod('Running', css=[_cs(restart_count=0, running_at=NOW)])
        self.assertEqual(_pod_last_restart_at(pod), '')

    def test_latest_restart_across_containers_wins(self):
        older, newer = NOW - timedelta(days=2), NOW - timedelta(hours=1)
        pod = _fake_pod('Running', css=[_cs(restart_count=1, last_terminated=older),
                                       _cs(restart_count=1, last_terminated=newer)])
        self.assertEqual(_pod_last_restart_at(pod), newer.isoformat())


class TestGetPodsDetailIsOptIn(unittest.TestCase):
    def test_detail_fields_absent_by_default(self):
        """get_pods 는 8곳이 공유한다 — 기본 반환 형태가 바뀌면 엉뚱한 화면에 열이 샌다."""
        import inspect
        from src.k8s import K8sManager
        sig = inspect.signature(K8sManager.get_pods)
        self.assertIn('detail', sig.parameters)
        self.assertIs(sig.parameters['detail'].default, False)


class TestReadyzFailOpen(unittest.TestCase):
    """조회 실패를 장애로 표시하면 멀쩡한 클러스터를 문제라고 신고한다."""

    def _api(self, fake_readyz, connected=True):
        import src.reports as reports
        from src.api import PolarisAPI

        class _K:
            def __init__(self):
                self.connected = connected
                self.cluster_info = {}
        api = PolarisAPI()
        api._clusters = {'c1': {'display_name': 'c1', 'context': 'c1', 'mgr': _K()}}
        api._active_id = 'c1'
        self._orig = reports._report_fetch_readyz
        reports._report_fetch_readyz = lambda k8s: fake_readyz
        return api

    def tearDown(self):
        import src.reports as reports
        if hasattr(self, '_orig'):
            reports._report_fetch_readyz = self._orig

    def test_403_is_unavailable_not_failure(self):
        api = self._api({'ok': False, 'status': 403, 'checks': [], 'failed': [],
                         'error': None})
        r = api._dashboard_readyz()
        self.assertFalse(r['available'])
        self.assertNotIn('failed', r)       # 실패 항목으로 보고하지 않는다
        self.assertIn('403', r['reason'])

    def test_no_response_is_unavailable(self):
        api = self._api({'ok': False, 'status': None, 'checks': [], 'failed': [],
                         'error': 'ConnectionError: nope'})
        r = api._dashboard_readyz()
        self.assertFalse(r['available'])
        self.assertIn('ConnectionError', r['reason'])

    def test_healthy_reports_counts(self):
        api = self._api({'ok': True, 'status': 200,
                         'checks': ['etcd', 'scheduler', 'controller-manager'],
                         'failed': [], 'error': None})
        r = api._dashboard_readyz()
        self.assertTrue(r['available'])
        self.assertTrue(r['ok'])
        self.assertEqual((r['passed'], r['total']), (3, 3))

    def test_real_failure_is_reported(self):
        api = self._api({'ok': False, 'status': 200, 'checks': ['etcd'],
                         'failed': [{'name': 'scheduler', 'detail': 'scheduler down'}],
                         'error': None})
        r = api._dashboard_readyz()
        self.assertTrue(r['available'])
        self.assertFalse(r['ok'])
        self.assertEqual(r['failed'][0]['name'], 'scheduler')
        self.assertEqual((r['passed'], r['total']), (1, 2))

    def test_disconnected_is_unavailable(self):
        api = self._api({}, connected=False)
        r = api._dashboard_readyz()
        self.assertFalse(r['available'])


if __name__ == '__main__':
    unittest.main()
