# -*- coding: utf-8 -*-
"""설정 창(SettingsModal)이 보내는 키가 백엔드 화이트리스트를 통과하는지 (v1.5.60).

설정 정규화는 화이트리스트라, 화면에만 키를 넣고 base.py 를 빠뜨리면 저장이 **조용히** 실패한다
(v1.2.160 · v1.2.166 · v1.2.167 세 번). 여기서는 설정 창의 키(맨 위 키 · 알림)를 소스에서 뽑아 대조한다. 그리고 저장할 때 버린 키를
돌려주는지(dropped) 본다.
"""
import re
import unittest
from pathlib import Path

from src.api import PolarisAPI

ROOT = Path(__file__).resolve().parent.parent
MODAL = ROOT / 'ui' / 'src' / 'components' / 'SettingsModal.jsx'


def _keys(block):
    lines = [ln for ln in block.splitlines() if not ln.strip().startswith('//')]
    return set(re.findall(r'^\s*([A-Za-z_]\w*)\s*:', '\n'.join(lines), re.M))


def _front():
    src = MODAL.read_text(encoding='utf-8')
    m = re.search(r'function normalizeSettings\(settings\)\s*\{\s*return \{(.*?)\n  \}\n\}', src, re.S)
    assert m, 'SettingsModal 의 normalizeSettings 를 못 찾음 — 이름이나 모양이 바뀌었는지 확인'
    body = m.group(1)
    n = re.search(r'notifications:\s*\{(.*?)\n    \},', body, re.S)
    assert n, 'normalizeSettings 의 notifications 블록을 못 찾음'
    top = _keys(re.sub(r'\{.*?\n    \}', '{}', body, flags=re.S))
    return top, _keys(n.group(1))


# 키마다 타입 검증이 있어 타입에 맞는 값을 넣어야 「버렸다」 로 오판하지 않는다
_PROBE_TOP = {'closeBehavior': 'exit', 'autoRestore': False, 'themeId': 'dark',
              'customTheme': {}, 'notifications': {}}
_PROBE_NOTI = {'webhookUrl': 'https://example.invalid/hook'}


class SettingsSync(unittest.TestCase):
    def test_맨_위_키(self):
        top, _ = _front()
        self.assertIn('notifications', top)
        out = PolarisAPI._normalize_settings({k: _PROBE_TOP.get(k, True) for k in top})
        self.assertEqual(top - set(out), set(), '설정 창에는 있는데 _normalize_settings 가 버리는 키')

    def test_알림_키(self):
        _, noti = _front()
        self.assertIn('webhookUrl', noti)
        out = PolarisAPI._normalize_notifications({k: _PROBE_NOTI.get(k, True) for k in noti})
        self.assertEqual(noti - set(out), set(), '설정 창에는 있는데 _normalize_notifications 가 버리는 키')

    def test_버린_키를_알린다(self):
        f = PolarisAPI._dropped_settings_keys
        clean = PolarisAPI._normalize_settings({})
        self.assertEqual(f({'closeBehavior': 'tray', 'newThing': 1}, clean), ['newThing'])
        self.assertEqual(f({'notifications': {'tray': True, 'newSub': True}}, clean), ['notifications.newSub'])
        self.assertEqual(f({}, clean), [])


if __name__ == '__main__':
    unittest.main()
