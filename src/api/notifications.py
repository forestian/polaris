# -*- coding: utf-8 -*-
"""NotificationsMixin — 이벤트→트레이/웹훅 알림 백그라운드 감시 + 설정 테스트.

알림 설정 자체(enabled/tray/webhookUrl)는 기존 설정 저장소(settings.json,
base.py _normalize_settings 의 'notifications' 키)를 그대로 쓴다 — 별도 파일 없음.
"""
from src.notifications import NotificationWatcher, send_test_webhook


class NotificationsMixin:
    def _notif_watcher(self) -> NotificationWatcher:
        if not hasattr(self, '_polaris_notif_watcher'):
            self._polaris_notif_watcher = NotificationWatcher(self)
        return self._polaris_notif_watcher

    def start_notification_watcher(self) -> dict:
        """runtime.py 가 실제 GUI 앱 기동 시 1회 호출. 유닛 테스트/헤드리스(MCP 등)
        인스턴스는 이 메서드를 부르지 않는 한 백그라운드 스레드가 생기지 않는다."""
        self._notif_watcher().start()
        return {'ok': True}

    def test_webhook(self, url: str) -> dict:
        """설정 화면 '테스트 전송' — 즉시 결과 반환(백그라운드 큐 안 씀)."""
        return send_test_webhook(url)
