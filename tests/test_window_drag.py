# -*- coding: utf-8 -*-
"""제목표시줄 드래그 — 최대화 상태에서 끌면 복원 (v1.2.151).

배경: 최대화된 채로 다른 모니터로 옮기면 창은 따라오지만 '최대화' 상태와 복원
기준이 원래 모니터에 남는다. 그 상태에서 최소화하면 처음 모니터로 튀어간다.
브라우저·탐색기처럼 **드래그를 시작하는 순간 복원**해 평범한 창으로 옮기고,
새 모니터에서 최대화를 다시 누르면 그 모니터를 채우게 한다.

좌표 계산이 이 기능의 전부라 여기서 잠근다 — 특히 창이 커서 왼쪽으로 튀는 것.
"""
import unittest

from src.api import PolarisAPI, ENABLED_FEATURES
from src.api.base import MIN_WINDOW_W, MIN_WINDOW_H


class _Api(PolarisAPI):
    """창 좌표만 흉내내는 스텁 — Win32 호출 없이 계산을 검증한다."""

    class _Win:          # window_toggle_maximize 가 창 존재를 확인한다
        def restore(self): pass
        def maximize(self): pass

    def __init__(self, rect, maximized=False, saved=None):
        super().__init__()
        self._rect = dict(rect) if rect else None
        self._maximized = maximized
        self._saved_bounds = saved
        self._window = self._Win()
        self.applied = None

    def _win_get_rect(self):
        return dict(self._rect) if self._rect else None

    def _win_set_pos(self, x, y, w, h):
        self.applied = {'x': x, 'y': y, 'w': w, 'h': h}
        self._rect = {'x': x, 'y': y, 'width': w, 'height': h}
        return True


# 모니터 A 작업영역을 채운 상태
MAXED = {'x': 0, 'y': 0, 'width': 1920, 'height': 1032}
SAVED = {'x': 200, 'y': 120, 'w': 1400, 'h': 900}


class NotMaximizedTests(unittest.TestCase):
    def test_grab_offset_is_cursor_minus_origin(self):
        api = _Api({'x': 300, 'y': 200, 'width': 1400, 'height': 900})
        r = api.window_drag_begin(500, 230)
        self.assertTrue(r['ok'])
        self.assertFalse(r['restored'])
        self.assertEqual((r['grab_x'], r['grab_y']), (200, 30))
        self.assertIsNone(api.applied, '최대화가 아니면 창을 건드릴 이유가 없다')

    def test_no_hwnd_is_reported(self):
        api = _Api(None)
        self.assertFalse(api.window_drag_begin(0, 0)['ok'])


class RestoreOnDragTests(unittest.TestCase):
    def test_maximized_drag_restores_to_saved_size(self):
        api = _Api(MAXED, maximized=True, saved=SAVED)
        r = api.window_drag_begin(960, 20)      # 제목표시줄 가운데를 잡음
        self.assertTrue(r['restored'])
        self.assertEqual((r['width'], r['height']), (1400, 900))
        self.assertEqual(api.applied['w'], 1400)
        self.assertFalse(api._maximized, '복원했으면 최대화 상태가 풀려야 한다')

    def test_cursor_stays_over_the_titlebar(self):
        # 어디를 잡아도 복원 후 커서가 창 가로 범위 안에 있어야 한다
        for cursor_x in (0, 100, 960, 1500, 1919):
            api = _Api(MAXED, maximized=True, saved=SAVED)
            r = api.window_drag_begin(cursor_x, 20)
            self.assertGreaterEqual(r['grab_x'], 0, f'cursor_x={cursor_x}')
            self.assertLess(r['grab_x'], r['width'],
                            f'cursor_x={cursor_x} — 커서가 창 밖이면 창이 옆으로 튄다')
            # 창 좌상단 = 커서 - grab → 커서가 창 안에 들어온다
            self.assertLessEqual(r['x'], cursor_x)
            self.assertGreater(r['x'] + r['width'], cursor_x)

    def test_right_edge_grab_keeps_window_under_cursor(self):
        # 최대화 창의 오른쪽 끝을 잡았을 때가 가장 위험하다 — 비율로 옮기지 않으면
        # 복원 폭(1400)보다 큰 오프셋(≈1900)이 남아 창이 커서 왼쪽으로 사라진다
        api = _Api(MAXED, maximized=True, saved=SAVED)
        r = api.window_drag_begin(1900, 20)
        self.assertLess(r['grab_x'], 1400)
        self.assertAlmostEqual(r['grab_x'] / 1400, 1900 / 1920, delta=0.02,
                               msg='가로 위치를 비율로 유지해야 한다')

    def test_vertical_grab_is_kept_as_is(self):
        # 제목표시줄은 맨 위라 세로는 비율로 줄일 필요가 없다
        api = _Api(MAXED, maximized=True, saved=SAVED)
        r = api.window_drag_begin(960, 18)
        self.assertEqual(r['grab_y'], 18)

    def test_vertical_grab_clamped_to_restored_height(self):
        api = _Api(MAXED, maximized=True, saved={'x': 0, 'y': 0, 'w': 1000, 'h': 300})
        r = api.window_drag_begin(960, 900)
        self.assertLess(r['grab_y'], 300)

    def test_falls_back_to_min_size_without_saved_bounds(self):
        # 앱이 최대화 상태로 시작해 복원 기준이 없을 수도 있다
        api = _Api(MAXED, maximized=True, saved=None)
        r = api.window_drag_begin(960, 20)
        self.assertTrue(r['restored'])
        self.assertGreaterEqual(r['width'], MIN_WINDOW_W)
        self.assertGreaterEqual(r['height'], MIN_WINDOW_H)

    def test_second_drag_does_not_restore_again(self):
        api = _Api(MAXED, maximized=True, saved=SAVED)
        api.window_drag_begin(960, 20)
        again = api.window_drag_begin(500, 20)
        self.assertFalse(again['restored'], '이미 복원된 창을 또 복원하면 안 된다')

    def test_maximize_after_move_uses_the_new_monitor(self):
        """복원 후 다른 모니터에서 최대화하면 그 모니터를 채워야 한다."""
        api = _Api(MAXED, maximized=True, saved=SAVED)
        api.window_drag_begin(960, 20)          # 복원
        api._rect = {'x': 2100, 'y': 100, 'width': 1400, 'height': 900}   # 모니터 B 로 이동

        # 모니터 B 의 작업영역
        api._win_workarea = lambda: (1920, 0, 1920, 1032)
        r = api.window_toggle_maximize()
        self.assertTrue(r['ok'])
        self.assertTrue(r['maximized'])
        self.assertEqual(api.applied['x'], 1920, '이동한 모니터를 채워야 한다')
        self.assertEqual(api.applied['w'], 1920)


def _skip_if_no_infra():
    return 'infra' not in ENABLED_FEATURES


if __name__ == '__main__':
    unittest.main()
