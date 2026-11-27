# -*- coding: utf-8 -*-
"""보고서 색 정리 (v1.4.36).

알록달록해서 난잡하다는 의견 — 보고서에서 색을 모두 빼고 **판정 · 등급 글자색만** 남긴다.

  1) 바탕색(w:fill)이 한 곳도 없다 — 판정 칸 · 요약 카드 · 안내 상자 · 코드 상자 · 표 머리 행 · 줄무늬
  2) 파란 강조(2563EB)가 없다 — 머리글 「POLARIS」 · 장 번호 · 글머리표 · 점검표 분류 · AI 한 마디
  3) 글자색은 검정 · 회색 + 판정 색(긴급 · 높음 · 중간 · 낮음/양호 · 참고)뿐이다
  4) 판정 글자색은 그대로 남는다
서버 · 패치 · DB · 업그레이드 보고서(공용 양식 src/docxreport.py)와 클러스터 보고서(src/reports.py) 둘 다.
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NEUTRAL = {'0F172A', '334155', '64748B', '94A3B8', '1E293B'}              # 검정 · 회색 글자
VERDICT = {'B91C1C', 'C2410C', 'A16207', '15803D', '1D4ED8'}               # 긴급 · 높음 · 중간 · 낮음/양호 · 참고


def _colors(xml):
    return set(re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', xml))


def _all_xml(doc):
    parts = [doc.element.body.xml]
    for s in doc.sections:
        parts += [s.header._element.xml, s.footer._element.xml,
                  s.first_page_header._element.xml, s.first_page_footer._element.xml]
    return '\n'.join(parts)


class CheckTemplateTests(unittest.TestCase):
    def setUp(self):
        try:
            import docx  # noqa: F401
        except ImportError:
            self.skipTest('python-docx 없음')
        self.tmp = Path(tempfile.mkdtemp(prefix='polaris-mono-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _doc(self):
        from docx import Document
        from src.docxreport import Report, Sev
        r = Report('서버 운영 점검 보고서', org='테스트')
        r.cover('서버 1대', [('점검일', '2026-11-03')], verdict='high', verdict_text='높음',
                kpis=[('점검 서버', '1 대'), ('발견사항', '3 건', 'high')])
        r.h1('1. 점검 요약')
        r.h2('서버별 요약')
        r.bullet('글머리표')
        r.callout('안내 문장', 'critical', '긴급')
        r.callout('참고 문장', 'info')
        r.code(['SELECT 1;'])
        r.table(['서버', '판정'], [('web-01', Sev('critical')), ('web-02', Sev('ok'))])
        r.kv([('이름', '값')])
        r.counts_table({'critical': 1, 'high': 0, 'medium': 2, 'low': 0})
        r.checklist([{'cat': '계정', 'name': 'root 원격 로그인', 'value': 'yes', 'sev': 'high', 'detail': 'd', 'action': 'a'},
                     {'cat': '계정', 'name': '빈 비밀번호', 'value': '없음', 'sev': 'ok', 'help': 'h'}])
        p = self.tmp / 'r.docx'
        r.doc.save(str(p))
        return Document(str(p))

    def test_바탕색이_없다(self):
        self.assertNotIn('w:fill=', _all_xml(self._doc()))

    def test_파란_강조가_없다(self):
        xml = _all_xml(self._doc())
        self.assertNotIn('2563EB', xml.upper())

    def test_글자색은_검정_회색_판정색뿐(self):
        cols = {c.upper() for c in _colors(_all_xml(self._doc()))}
        self.assertLessEqual(cols, NEUTRAL | VERDICT, cols - NEUTRAL - VERDICT)

    def test_판정_글자색은_남는다(self):
        cols = {c.upper() for c in _colors(self._doc().element.body.xml)}
        self.assertIn('B91C1C', cols)          # 긴급
        self.assertIn('C2410C', cols)          # 높음
        self.assertIn('15803D', cols)          # 양호

    def test_색_막대_없이_테두리는_회색(self):
        xml = self._doc().element.body.xml
        for c in re.findall(r'<w:(?:top|left|bottom|right) w:val="single"[^>]*w:color="([0-9A-Fa-f]{6})"', xml):
            self.assertIn(c.upper(), {'E2E8F0', 'CBD5E1', '94A3B8'}, c)
        self.assertNotRegex(xml, r'w:sz="18"')     # 요약 카드 위쪽 굵은 색 줄


class ClusterReportTests(unittest.TestCase):
    def setUp(self):
        try:
            import docx  # noqa: F401
        except ImportError:
            self.skipTest('python-docx 없음')
        self.tmp = Path(tempfile.mkdtemp(prefix='polaris-mono-k8s-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _doc(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        import test_report_sections as C
        from docx import Document
        from src.reports import _report_evaluate, _report_write_docx
        data = C._data()
        path = _report_write_docx(data, _report_evaluate(data, None), lambda _ctx: 'AI 의견', str(self.tmp / 'c.docx'),
                                  lambda *_a, **_k: None, None)
        return Document(path)

    def test_바탕색이_없다(self):
        self.assertNotIn('w:fill=', _all_xml(self._doc()))

    def test_파란_강조가_없고_글자색은_검정_회색_판정색뿐(self):
        xml = _all_xml(self._doc())
        self.assertNotIn('2563EB', xml.upper())
        cols = {c.upper() for c in _colors(xml)}
        self.assertLessEqual(cols, NEUTRAL | VERDICT | {'FFFFFF'}, cols - NEUTRAL - VERDICT)

    def test_판정_글자색은_남는다(self):
        cols = {c.upper() for c in _colors(self._doc().element.body.xml)}
        self.assertTrue(cols & {'B91C1C', 'C2410C', 'A16207', '15803D'}, cols)

    def test_HTML_보고서도_색_머리_행이_없다(self):
        src = (ROOT / 'src' / 'reports.py').read_text(encoding='utf-8')
        html = src[src.index('<title>Polaris 클러스터 보고서</title>'):]
        self.assertNotIn('#1e3a5f', html)
        self.assertNotIn('#1e40af', html)
        self.assertNotIn('#bfdbfe', html)


if __name__ == '__main__':
    unittest.main()
