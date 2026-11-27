# -*- coding: utf-8 -*-
"""NotificationWatcher — 클러스터 Warning 이벤트 → 트레이 알림 / 웹훅.

설계:
  - 폴링 방식(기본 15초) — 이미 검증된 get_cluster_events() 를 그대로 재사용.
    watch API(src/k8s_watch.py)와 달리 이벤트는 이미 REST list 로도 충분히
    가볍고, 여러 리소스 kind 를 아우르는 단일 스트림이 없어 REST 폴링이 더 단순.
  - 클러스터별 baseline: 감시가 그 클러스터에서 처음 도는 회차는 알림을 보내지
    않고 '이미 있던' Warning 을 기준선으로만 기록한다. 다음 회차부터 새로 나타난
    (namespace, kind, name, reason) 조합만 알림 — 같은 이슈가 반복(count 증가)돼도
    재알림하지 않아 알림 폭주를 막는다.
  - 웹훅은 짧은 별도 스레드에서 fire-and-forget(5초 타임아웃, 실패는 조용히 무시).
    설정 화면의 '테스트 전송' 버튼(test_webhook)으로 사전에 연결을 확인할 수 있다.
  - 트레이 알림은 runtime.py 가 쥔 pystray.Icon 객체를 API 인스턴스에 주입받아
    사용(api._tray_state) — 트레이가 없는 헤드리스 실행에선 조용히 건너뛴다.
"""
import json
import threading
import urllib.request
from urllib.parse import urlparse

_POLL_INTERVAL = 15.0
_HTTP_TIMEOUT = 5.0


def _valid_webhook_url(url: str) -> bool:
    p = urlparse(url or '')
    return p.scheme in ('http', 'https') and bool(p.netloc)


def _post_json(url: str, payload: dict, timeout: float = _HTTP_TIMEOUT):
    """공용 JSON POST 전송. 반환: (ok, status_or_error)."""
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return True, resp.status


def send_test_webhook(url: str) -> dict:
    """설정 화면 '테스트 전송' — 즉시 결과를 반환(백그라운드 아님)."""
    url = (url or '').strip()
    if not _valid_webhook_url(url):
        return {'ok': False, 'error': 'http:// 또는 https:// 로 시작하는 URL만 사용할 수 있습니다.'}
    try:
        ok, status = _post_json(url, {
            'title': 'Polaris 테스트 알림',
            'message': '웹훅 연결이 정상입니다.',
            'text': 'Polaris 테스트 알림 — 웹훅 연결이 정상입니다.',
        }, timeout=8.0)
        return {'ok': True, 'status': status}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


class NotificationWatcher:
    """앱 전체에 하나만 존재 — PolarisAPI 인스턴스가 소유(start_notification_watcher).

    유닛 테스트/헤드리스(MCP 등) 인스턴스는 명시적으로 start() 를 부르지 않는 한
    스레드가 생기지 않는다(생성만으로는 부작용 없음).
    """

    def __init__(self, api):
        self._api = api
        self._seen = {}   # cluster_id -> set(dedupe_key) | None(=아직 baseline 전)
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name='polaris-notify')
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                pass
            self._stop.wait(_POLL_INTERVAL)

    def tick(self):
        """한 회차 점검. 테스트에서 직접 호출하기 쉽도록 루프 본체와 분리."""
        api = self._api
        try:
            cfg = (api._load_settings_raw().get('notifications') or {})
        except Exception:
            return
        if not cfg.get('enabled'):
            return
        cid = getattr(api, '_active_id', None)
        clusters = getattr(api, '_clusters', {}) or {}
        if not cid or cid not in clusters:
            return
        try:
            r = api.get_cluster_events('', 500, ['Warning'])
        except Exception:
            return
        if not r.get('ok'):
            return
        events = r.get('events') or []
        keys = {self._key(e) for e in events}
        prev = self._seen.get(cid)
        if prev is None:
            self._seen[cid] = keys   # baseline — 이번 회차는 알림 없음
            return
        new_keys = keys - prev
        self._seen[cid] = keys
        if not new_keys:
            return
        cluster_name = clusters.get(cid, {}).get('display_name', cid)
        for e in events:
            if self._key(e) in new_keys:
                self._fire(cfg, cluster_name, e)

    def forget_cluster(self, cid):
        """클러스터 연결 해제/삭제 시 baseline 정리(재연결 시 다시 기준선부터)."""
        self._seen.pop(cid, None)

    @staticmethod
    def _key(e):
        return f"{e.get('namespace','')}::{e.get('kind','')}::{e.get('obj_name','')}::{e.get('reason','')}"

    def _fire(self, cfg, cluster_name, e):
        title = f"[{cluster_name}] {e.get('reason') or 'Warning'}"
        obj = e.get('obj') or e.get('obj_name') or ''
        message = f"{e.get('namespace','')}/{obj}: {e.get('message','')}"[:300]
        if cfg.get('tray', True):
            self._tray_notify(title, message)
        url = (cfg.get('webhookUrl') or '').strip()
        if url and _valid_webhook_url(url):
            threading.Thread(target=self._send_webhook,
                             args=(url, title, message, cluster_name, e), daemon=True).start()

    def _tray_notify(self, title, message):
        try:
            tray_state = getattr(self._api, '_tray_state', None)
            icon = tray_state.get('icon') if tray_state else None
            if icon is not None:
                icon.notify(message, title)
        except Exception:
            pass

    @staticmethod
    def _send_webhook(url, title, message, cluster_name, e):
        try:
            _post_json(url, {
                'title': title, 'message': message, 'cluster': cluster_name,
                'namespace': e.get('namespace', ''), 'kind': e.get('kind', ''),
                'name': e.get('obj_name', ''), 'reason': e.get('reason', ''),
                'text': f'{title}\n{message}',   # Slack/Discord 등 incoming-webhook 호환용
            })
        except Exception:
            pass
