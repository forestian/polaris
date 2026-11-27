# -*- coding: utf-8 -*-
"""S1 (v1.3.39) — 창이 앱 화면 밖으로 넘어가지 않는다.

pywebview 는 창이 어느 주소로 가든 새 페이지마다 js_api 를 다시 심는다. 창에
끌어다 놓은 `report.html` 한 장이 보관함과 모든 SSH 서버를 가져갈 수 있었다.
코어 기능이라 변형 빌드에서도 도는 파일에 둔다.
"""
import unittest
from pathlib import Path


class NavGuardTests(unittest.TestCase):
    """S1 — 창에 남의 페이지가 뜨면 그 페이지가 js_api 를 통째로 얻는다."""

    # 저장소 경로에 한글이 있다 — Python as_uri() 는 퍼센트 인코딩한다
    INDEX = Path(r'C:\Users\u\클로드\클러스터관리\ui\dist\index.html').as_uri()

    def setUp(self):
        from src import navguard
        self.ok = lambda u: navguard.is_allowed(u, self.INDEX)

    def test_앱_화면과_그_폴더_안은_허용(self):
        self.assertTrue(self.ok(self.INDEX))
        self.assertTrue(self.ok(self.INDEX + '#cmdlog'))
        self.assertTrue(self.ok(self.INDEX.replace('index.html', 'assets/x.js')))
        self.assertTrue(self.ok('about:blank'))

    def test_인코딩_대소문자가_달라도_자기_화면은_막지_않는다(self):
        # 여기서 틀리면 앱이 하얀 화면이 된다 — 막는 것보다 훨씬 나쁜 실패
        raw = 'file:///c:/Users/u/클로드/클러스터관리/ui/dist/index.html'
        self.assertTrue(self.ok(raw))
        self.assertTrue(self.ok(raw.replace('/', '\\').replace('file:\\\\\\', 'file:///')))

    def test_폴더_밖_파일과_웹페이지는_막는다(self):
        for u in ('file:///C:/Users/u/Downloads/report.html',
                  'file:///C:/Users/u/%ED%81%B4%EB%A1%9C%EB%93%9C/other/index.html',
                  'https://example.com/', 'http://10.0.0.1/', 'data:text/html,<b>x</b>',
                  'file://attacker/share/x.html',
                  # 이름이 앞부분만 같은 옆 폴더
                  self.INDEX.replace('/dist/index.html', '/dist-evil/index.html')):
            self.assertFalse(self.ok(u), u)

    def test_루트가_비정상이면_앱_파일_하나만_허용(self):
        from src import navguard
        self.assertFalse(navguard.is_allowed('file:///C:/Windows/x.html', 'file:///x.html'))

    def test_본창에_붙인다(self):
        rt = Path('src/runtime.py').read_text(encoding='utf-8')
        self.assertIn('navguard.install(window', rt)

    def test_화면쪽_놓기_차단이_있다(self):
        js = Path('ui/src/main.jsx').read_text(encoding='utf-8')
        self.assertIn("addEventListener('drop'", js)
        self.assertIn("addEventListener('dragover'", js)


if __name__ == '__main__':
    unittest.main()
