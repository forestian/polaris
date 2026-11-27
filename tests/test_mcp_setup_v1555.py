# -*- coding: utf-8 -*-
"""MCP 연결 안내 (v1.5.55, 사용자 신고 — 새 PC 에서 안내 문서대로 하면 연결이 안 됨).

문서와 실제가 달랐던 것:
  · 예시 실행 경로 `C:\\Program Files\\Polaris\\polaris.exe` — 설치 프로그램 기본은 %LOCALAPPDATA%\\Programs\\Polaris
  · 감사 로그 `%LOCALAPPDATA%\\Polaris\\logs` — 실제는 ~/.polaris/logs
  · 툴 12종 — 실제 15종
고친 것: 토큰을 발급하면 **이 PC 의 실제 실행 경로**를 함께 돌려줘 화면이 Claude Desktop 설정을 통째로 만든다.
이 파일은 그 경로와 문서의 사실(설치 위치 · 로그 위치 · 툴 수)이 코드와 어긋나지 않게 잡는다.
"""
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


class LaunchCommand(unittest.TestCase):
    def test_설치본은_이_exe(self):
        from src.api.vault import VaultMixin
        with mock.patch.object(sys, 'frozen', True, create=True), \
             mock.patch.object(sys, 'executable', r'C:\Users\kim\AppData\Local\Programs\Polaris\polaris.exe'):
            r = VaultMixin.mcp_launch_command()
        self.assertTrue(r['command'].endswith('polaris.exe'))
        self.assertEqual(r['args'], ['--mcp'])

    def test_개발_실행은_python_polaris_py(self):
        from src.api.vault import VaultMixin
        r = VaultMixin.mcp_launch_command()
        self.assertEqual(r['args'][-1], '--mcp')
        self.assertTrue(Path(r['args'][0]).name == 'polaris.py' and Path(r['args'][0]).exists())

    def test_발급_응답에_실행_경로(self):
        import inspect
        from src.api import vault
        self.assertIn("'launch': self.mcp_launch_command()", inspect.getsource(vault.VaultMixin.vault_issue_mcp_token))


class GuideMatchesCode(unittest.TestCase):
    def setUp(self):
        self.doc = (ROOT / 'docs' / 'mcp.md').read_text(encoding='utf-8')

    def test_설치_위치(self):
        main_rs = (ROOT / 'packaging' / 'setup-tauri' / 'src-tauri' / 'src' / 'main.rs').read_text(encoding='utf-8')
        self.assertIn('\\\\Programs\\\\{}', main_rs, '설치 프로그램 기본 위치')
        self.assertIn('APP_NAME: &str = "Polaris Free"', main_rs)
        self.assertIn(r'%LOCALAPPDATA%\Programs\Polaris Free\polaris.exe', self.doc)
        self.assertNotIn(r'"C:\\Program Files\\Polaris', self.doc, '예시에 Program Files 를 쓰지 않는다')

    def test_감사_로그_위치(self):
        from src import mcp_server as M
        from src import paths
        self.assertEqual(paths.DEFAULT_DIR.name, '.polaris-free')        # 홈 아래 .polaris (홈 경로는 직접 안 가리킨다)
        self.assertIn("polaris_dir() / 'logs'", Path(M.__file__).read_text(encoding='utf-8'))
        self.assertIn(r'%USERPROFILE%\.polaris-free\logs\mcp-audit.log', self.doc)
        self.assertNotIn(r'%LOCALAPPDATA%\Polaris\logs', self.doc)

    def test_툴_수(self):
        from src import mcp_server as M
        n = len(M._tool_defs())
        self.assertIn(f'툴 {n}종', self.doc)
        listed = set(re.findall(r'\| `(polaris_[a-z_]+)` \|', self.doc))
        self.assertEqual(listed, {t.name for t in M._tool_defs()}, '문서 표와 실제 툴 목록이 같다')

    def test_새_PC_안내(self):
        for w in ('토큰은 PC 마다 따로', 'kubeconfig 를 다시 등록', '구성 편집', '트레이', '설정 전체 복사', 'mcp-server-polaris-free.log'):
            self.assertIn(w, self.doc, w)


if __name__ == '__main__':
    unittest.main()
