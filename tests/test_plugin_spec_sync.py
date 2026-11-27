# -*- coding: utf-8 -*-
"""옵셔널 plugin(src/api/ 의 비-코어 *.py) 이 PyInstaller spec 의 _PLUGINS 등록
목록과 어긋나지 않는지 정적으로 검증.

배경(회귀): v1.2.113 에서 src/api/notifications.py 를 추가했지만
packaging/specs/Polaris.spec 의 _PLUGINS 에 등록하지 않아, frozen EXE 에서
_discover_optional_mixins() 의 동적 import 를 PyInstaller 정적 분석이 놓쳐
plugin 이 조용히(에러도 없이) 통째로 빠졌다 — 개발 환경 테스트는 전부 통과했지만
frozen 빌드에서만 'PolarisAPI' object has no attribute 'start_notification_watcher'
크래시가 났다. 이 테스트는 클러스터/빌드 없이도 그 실수를 즉시 잡아낸다.
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / 'packaging' / 'specs' / 'Polaris.spec'
API_DIR = ROOT / 'src' / 'api'


def _actual_optional_plugin_probes():
    from src.api import _CORE_MODULE_NAMES
    return {
        f'src/api/{f.name}'
        for f in API_DIR.glob('*.py')
        if f.stem not in _CORE_MODULE_NAMES and not f.stem.startswith('_')
    }


def _spec_registered_probes():
    text = SPEC.read_text(encoding='utf-8')
    m = re.search(r'_PLUGINS\s*=\s*(\[.*?\n\])', text, re.S)
    assert m, 'Polaris.spec 에서 _PLUGINS 리스트를 찾지 못함 — 파싱 로직 또는 spec 구조 확인 필요'
    plugins = ast.literal_eval(m.group(1))
    return {probe for probe, _mods, _data in plugins}


class TestPluginSpecSync(unittest.TestCase):
    def test_every_optional_plugin_registered_in_spec(self):
        actual = _actual_optional_plugin_probes()
        registered = _spec_registered_probes()
        missing = actual - registered
        self.assertEqual(
            missing, set(),
            f'src/api/ 에 있지만 packaging/specs/Polaris.spec 의 _PLUGINS 에 '
            f'등록 안 된 plugin: {missing} — frozen EXE 에서 조용히 누락되어 '
            f'AttributeError 를 일으킨다. spec 의 _PLUGINS 에 한 줄 추가할 것.'
        )

    def test_spec_has_no_stale_plugin_entries(self):
        actual = _actual_optional_plugin_probes()
        registered = _spec_registered_probes()
        stale = registered - actual
        self.assertEqual(
            stale, set(),
            f'packaging/specs/Polaris.spec 의 _PLUGINS 에 등록돼 있지만 '
            f'실제로는 src/api/ 에 없는(삭제된) plugin: {stale} — spec 에서 정리할 것.'
        )


if __name__ == '__main__':
    unittest.main()
