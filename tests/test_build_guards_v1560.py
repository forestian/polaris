# -*- coding: utf-8 -*-
"""빌드 전 검사(v1.5.60) — 그동안 사람이 기억해서 하던 것을 build.py 가 한다.

  · ui/__preview* 미리보기 폴더 지우기(빌드에 섞이지 않게)
  · 소스에 CR 이 섞였는지(이 PC 의 autocrlf · 파이썬 write_text · 히어독 \\r)
  · 예전에 사고가 났던 누락을 막는 테스트를 빌드마다 돌리기
"""
import tempfile
import unittest
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parent.parent


class Eol(unittest.TestCase):
    def test_crlf_와_줄_중간_cr_을_가른다(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'src'
            src.mkdir()
            (src / 'ok.py').write_bytes(b'a = 1\nb = 2\n')
            (src / 'win.py').write_bytes(b'a = 1\r\nb = 2\r\n')
            (src / 'heredoc.md').write_bytes('Enter 를 `'.encode() + b'\r' + '` 로\n'.encode())
            (src / 'img.png').write_bytes(b'\r\n')          # 텍스트가 아니면 안 본다
            got = {p.name: k for p, k in build.find_cr_files(d)}
        self.assertEqual(got, {'win.py': 'crlf', 'heredoc.md': 'cr'})

    def test_저장소_소스는_LF(self):
        self.assertEqual([str(p) for p, _ in build.find_cr_files()], [],
                         'CR 이 든 소스 — python build.py --check --fix-eol')

    def test_gitattributes_가_작업_폴더도_LF_로(self):
        a = (ROOT / '.gitattributes').read_text(encoding='utf-8')
        for ext in ('py', 'js', 'jsx', 'mjs', 'md'):
            self.assertRegex(a, rf'\*\.{ext}\s+text eol=lf')
        self.assertRegex(a, r'\*\.bat\s+text eol=crlf')


class Preview(unittest.TestCase):
    def test_미리보기_폴더를_지운다(self):
        with tempfile.TemporaryDirectory() as d:
            ui = Path(d) / 'ui'
            (ui / '__preview_x').mkdir(parents=True)
            (ui / '__preview_x' / 'a.html').write_text('x')
            (ui / 'src').mkdir()
            self.assertEqual(build.clean_preview_dirs(d), ['__preview_x'])
            self.assertTrue((ui / 'src').is_dir())
            self.assertFalse((ui / '__preview_x').exists())


class GuardTests(unittest.TestCase):
    def test_가드_테스트가_다_있다(self):
        for mod in build.GUARD_TESTS:
            self.assertTrue((ROOT / (mod.replace('.', '/') + '.py')).is_file(), mod)

    def test_빌드_처음에_돈다(self):
        b = (ROOT / 'build.py').read_text(encoding='utf-8')
        main = b[b.index('def main'):]
        self.assertLess(main.index('check_source_hygiene('), main.index('run_npm_build()'))
        self.assertLess(main.index('run_guard_tests()'), main.index('if check_only:'), '--check 에서도 돈다')


if __name__ == '__main__':
    unittest.main()
