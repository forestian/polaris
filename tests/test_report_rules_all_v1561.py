# -*- coding: utf-8 -*-
"""모든 DOCX 보고서가 같은 양식 규칙을 지키는지 — 한 곳에서 (v1.5.61, 다듬기 ③).

보고서 양식은 이미 공용 모듈(src/docxreport.py)로 모여 있지만, 규칙 검사는 공용 양식 자체와 일부 보고서에만
걸려 있었다. 보고서마다 따로 색 · 서식을 넣으면 아무도 몰랐다. 여기서 **보고서를 만드는 함수 전부**를 표본
데이터로 실제로 돌려, 그동안 사용자가 정한 규칙을 한꺼번에 본다.

  1) 바탕색(w:fill) 없음 — 판정 칸 · 상자 · 머리 행 모두 (v1.4.36 「알록달록해 난잡하다」)
  2) 파란 강조(2563EB) 없음 · 글자색은 검정 · 회색 + 판정 색뿐 (v1.4.36)
  3) 문단 앞 네모 서식(keepNext · keepLines · pageBreakBefore) 없음 (v1.4.12)
  4) 글꼴은 맑은 고딕 + Segoe UI (공용 양식과 같은 모양)

그리고 src 에 **새 보고서 함수가 생기면 여기 표에 넣지 않은 한 실패**한다 — 새 보고서도 자동으로 같은 규칙을 받는다.
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))

NEUTRAL = {'0F172A', '334155', '64748B', '94A3B8', '1E293B', '000000', 'FFFFFF'}
VERDICT = {'B91C1C', 'C2410C', 'A16207', '15803D', '1D4ED8'}
MARKS = ('<w:keepNext', '<w:keepLines', '<w:pageBreakBefore')
FONTS = {'맑은 고딕', 'Segoe UI', 'Consolas', 'D2Coding'}


# ── 표본 만들기 — 보고서 함수마다 하나 ────────────────────────────────────────────

def _upgrade(tmp):
    import test_upgradecheck_v141 as U
    from src.api.upgradecheck import UpgradeCheckMixin

    class A(UpgradeCheckMixin):
        k8s = U.K(U.old_cluster())
        def _cluster_label(self, fallback=''): return 'prod'
    a = A()
    a.upgrade_check('1.26')
    r = a.upgrade_check_save(str(tmp / 'up.docx'))
    assert r['ok'], r
    return r['path']


def _cluster(tmp):
    import test_report_sections as C
    from src.reports import _report_evaluate, _report_write_docx
    data = C._data()
    return _report_write_docx(data, _report_evaluate(data, None), lambda _ctx: 'AI 의견', str(tmp / 'cluster.docx'),
                              lambda *_a, **_k: None, None)


#: src 의 보고서 함수 → 표본. 새 보고서 함수를 만들면 여기에 넣는다(test_빠진_보고서_없음 이 알려 준다)
WRITERS = {
    'upgradecheck.write_docx': _upgrade,
    'reports._report_write_docx': _cluster,
}


def _found_writers():
    out = set()
    for p in (ROOT / 'src').rglob('*.py'):
        for m in re.finditer(r'^def (_?(?:report_)?write\w*docx)\(', p.read_text(encoding='utf-8'), re.M):
            out.add(f'{p.relative_to(ROOT / "src").with_suffix("").as_posix().replace("/", ".")}.{m.group(1)}')
    return out


class Registry(unittest.TestCase):
    def test_빠진_보고서_없음(self):
        found = _found_writers()
        self.assertGreaterEqual(len(found), 2, '보고서 함수를 못 찾았다 — 찾는 정규식을 고칠 것')
        missing = found - set(WRITERS)
        self.assertEqual(missing, set(), '새 보고서 함수 — WRITERS 에 표본을 넣어 양식 규칙 검사를 받게 할 것')


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import docx  # noqa: F401
        except ImportError:
            raise unittest.SkipTest('python-docx 없음')
        from docx import Document
        cls.tmp = Path(tempfile.mkdtemp(prefix='polaris-rules-'))
        cls.docs = {}
        for name, make in WRITERS.items():
            doc = Document(make(cls.tmp))
            body = doc.element.body.xml
            used = {p.style.style_id for p in doc.paragraphs if p.style is not None}
            styles = ''.join(st.element.xml for st in doc.styles if getattr(st, 'style_id', None) in used)
            parts = [body + styles]
            for s in doc.sections:
                for hf in (s.header, s.footer, s.first_page_header, s.first_page_footer):
                    if hf is not None and not hf.is_linked_to_previous:
                        parts.append(hf._element.xml)
            cls.docs[name] = '\n'.join(parts)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(getattr(cls, 'tmp', ''), True)

    def _each(self, check):
        bad = {}
        for name, xml in self.docs.items():
            got = check(xml)
            if got:
                bad[name] = got
        return bad

    def test_바탕색_없음(self):
        bad = self._each(lambda x: sorted({f for f in re.findall(r'w:fill="([0-9A-Fa-f]{6})"', x) if f.upper() not in ('FFFFFF',)}))
        self.assertEqual(bad, {}, '보고서에 바탕색 — 색은 판정 글자에만(v1.4.36)')

    def test_글자색은_검정_회색_판정색뿐(self):
        bad = self._each(lambda x: sorted({c.upper() for c in re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', x)}
                                          - NEUTRAL - VERDICT))
        self.assertEqual(bad, {}, '허용하지 않은 글자색(파란 강조 2563EB 등)')

    def test_문단_앞_네모_서식_없음(self):
        bad = self._each(lambda x: [m for m in MARKS if m in x])
        self.assertEqual(bad, {}, '「다음 문단과 함께」 등 — Word 가 문단 앞에 네모를 그린다(v1.4.12)')

    def test_글꼴(self):
        bad = self._each(lambda x: sorted(set(re.findall(r'w:(?:ascii|eastAsia|hAnsi)="([^"]+)"', x)) - FONTS))
        self.assertEqual(bad, {}, '공용 양식 밖 글꼴')

    def test_판정_글자색은_남는다(self):
        for name, xml in self.docs.items():
            with self.subTest(name):
                self.assertTrue(VERDICT & {c.upper() for c in re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', xml)},
                                '판정 색이 하나도 없다 — 표본이 판정을 못 만들었거나 색이 빠졌다')


if __name__ == '__main__':
    unittest.main()
