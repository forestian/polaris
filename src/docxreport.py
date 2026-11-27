# -*- coding: utf-8 -*-
"""CHECK 탭 보고서 공용 DOCX 템플릿 (v1.4.4 신설 · v1.4.5 새 디자인).

서버 보고서 · 패치 현황 · DB 점검 · 업그레이드 사전 점검이 **같은 모양**이 되도록 표지 · 머리글/바닥글 · 제목 ·
표 · 판정 칸 · 요약 카드 · 점검표 · 안내 상자를 한 곳에서 만든다.

디자인(v1.4.36): **색은 판정 · 등급 글자에만** 쓴다 — 바탕색 · 색 막대 · 파란 강조를 모두 걷어냈다(알록달록해
난잡하다는 의견). 나머지는 검정 · 회색 글자와 회색 선뿐이다. 표는 가로줄만(세로줄 없음), 머리 행은 굵은 글자 + 아래 진한 줄,
요약 카드 · 안내 상자 · 코드 상자는 회색 테두리 상자. 글꼴은 맑은 고딕(한글) + Segoe UI(영문 · 숫자).
python-docx 가 없는 빌드면 ImportError — 호출하는 쪽이 사용자 문구로 바꾼다.
"""
from __future__ import annotations

import re
from datetime import datetime

FONT_KO = '맑은 고딕'
FONT_EN = 'Segoe UI'
FONT = FONT_KO                                  # 예전 이름(다른 모듈 호환)

# 색 — 글자 · 선 · 바탕
INK = (0x0F, 0x17, 0x2A)          # 제목
TEXT = (0x33, 0x41, 0x55)         # 본문
MUTED = (0x64, 0x74, 0x8B)        # 설명 · 머리글
ACCENT = INK                      # 예전 이름 — 파란 강조는 쓰지 않는다(v1.4.36)
LINE_HEX = 'E2E8F0'
RULE_HEX = '94A3B8'               # 표 머리 행 아래 · 상자 테두리(회색)
BOX_HEX = 'CBD5E1'
HEAD_BG = 'F1F5F9'
SOFT_BG = 'F8FAFC'
BAND_HEX = '0F172A'
NAVY_HEX = BAND_HEX               # 예전 이름(호환)

SEV_KO = {'critical': '긴급', 'high': '높음', 'medium': '중간', 'low': '낮음', 'ok': '양호', 'info': '참고',
          'unknown': '확인 불가', 'na': '해당 없음',
          'block': '먼저 해결', 'warn': '주의', 'blocked': '막힘', 'caution': '주의', 'ready': '준비됨'}
_SEV_RGB = {'critical': (0xB9, 0x1C, 0x1C), 'high': (0xC2, 0x41, 0x0C), 'medium': (0xA1, 0x62, 0x07), 'low': (0x15, 0x80, 0x3D),
            'ok': (0x15, 0x80, 0x3D), 'info': (0x1D, 0x4E, 0xD8), 'unknown': (0x64, 0x74, 0x8B), 'na': (0x94, 0xA3, 0xB8),
            'block': (0xB9, 0x1C, 0x1C), 'warn': (0xC2, 0x41, 0x0C), 'blocked': (0xB9, 0x1C, 0x1C), 'caution': (0xC2, 0x41, 0x0C),
            'ready': (0x15, 0x80, 0x3D)}
PROBLEM = ('critical', 'high', 'medium', 'low')
CONTENT_CM = 17.0                 # A4 - 좌우 여백 2cm
KPI_GAP_CM = 0.25                 # 요약 카드 사이 틈


class Sev(str):
    """표 칸에 넣으면 판정 칸이 되는 값 — Sev('high'), 글자를 바꾸려면 Sev('high', '중요')"""

    def __new__(cls, key, label=None):
        o = super().__new__(cls, key)
        o.label = label
        return o


STALE_DAYS = 7                    # 이보다 오래된 점검 결과는 보고서에 「오래된 결과」 로 알린다


def local_time(iso) -> str:
    """저장된 시각(ISO) → 이 PC 의 시각 「2026-10-22 12:00」. 없으면 「—」"""
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(iso)).astimezone().strftime('%Y-%m-%d %H:%M')
    except (TypeError, ValueError):
        return '—'


def checked_span(isos) -> str:
    """여러 대상의 점검 시각 → 「2026-10-21 10:00」 또는 「2026-10-15 09:00 ~ 2026-10-21 10:00」 (v1.4.10)"""
    ts = sorted(t for t in (local_time(i) for i in isos or []) if t != '—')
    if not ts:
        return '—'
    return ts[0] if ts[0] == ts[-1] else f'{ts[0]} ~ {ts[-1]}'


def oldest_days(isos, now=None):
    """가장 오래된 점검이 며칠 전인가(없으면 None)"""
    from datetime import datetime, timezone
    now = now or datetime.now(timezone.utc)
    ages = []
    for i in isos or []:
        try:
            t = datetime.fromisoformat(str(i))
        except (TypeError, ValueError):
            continue
        if t.tzinfo is None:
            t = t.astimezone()
        ages.append((now - t).total_seconds() / 86400)
    return max(ages) if ages else None


def health_score(counts: dict) -> int:
    """발견사항 건수 → 100점 만점(긴급 25 · 높음 10 · 중간 4 · 낮음 1 감점). 보고서 표지의 한눈 지표."""
    pen = 25 * counts.get('critical', 0) + 10 * counts.get('high', 0) + 4 * counts.get('medium', 0) + counts.get('low', 0)
    return max(0, 100 - pen)


_XML_BAD = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _xml_safe(s):
    """DOCX(XML)에 넣을 수 없는 글자 — 색 코드 · 제어 문자를 뺀다. 하나만 섞여도 보고서 저장이 통째로 실패했다(v1.4.24)"""
    return _XML_BAD.sub('', s) if isinstance(s, str) else s


def _install_xml_safe():
    """python-docx 의 add_run 한 곳에 건다 — 표 칸(cell.text)도 결국 여기로 들어온다"""
    from docx.text.paragraph import Paragraph
    if getattr(Paragraph.add_run, '_polaris_xml_safe', False):
        return
    orig = Paragraph.add_run

    def add_run(self, text=None, style=None):
        return orig(self, _xml_safe(text), style)
    add_run._polaris_xml_safe = True
    Paragraph.add_run = add_run


class Report:
    def __init__(self, title: str, header: str | None = None, footer: str = '', org: str = ''):
        from docx import Document
        from docx.shared import Cm
        _install_xml_safe()
        self._m = _mods()
        self.doc = Document()
        for s in self.doc.sections:
            s.page_width, s.page_height = Cm(21.0), Cm(29.7)
            s.top_margin, s.bottom_margin, s.left_margin, s.right_margin = Cm(2.2), Cm(2.0), Cm(2.0), Cm(2.0)
            s.header_distance, s.footer_distance = Cm(1.0), Cm(1.0)
            s.different_first_page_header_footer = True          # 표지에는 머리글 · 바닥글 없음
        self.title = title
        self._compat15()
        self._base_style()
        self._header(header or title, footer, org)

    # ── 바탕 ─────────────────────────────────────────────────────────────
    def _compat15(self):
        """Word 2013 이후 배치 — 옛 호환 모드는 표를 칸 여백만큼 왼쪽으로 밀어 표지 띠 · 카드 · 표의 가장자리가 어긋났다"""
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        st = self.doc.settings.element
        compat = st.find(qn('w:compat'))
        if compat is None:
            compat = OxmlElement('w:compat'); st.append(compat)
        for old in compat.findall(qn('w:compatSetting')):
            if old.get(qn('w:name')) == 'compatibilityMode':
                compat.remove(old)
        cs = OxmlElement('w:compatSetting')
        cs.set(qn('w:name'), 'compatibilityMode'); cs.set(qn('w:uri'), 'http://schemas.microsoft.com/office/word'); cs.set(qn('w:val'), '15')
        compat.append(cs)

    def _base_style(self):
        Pt, qn = self._m['Pt'], self._m['qn']
        st = self.doc.styles['Normal']
        st.font.name, st.font.size = FONT_EN, Pt(10)
        st.font.color.rgb = self._m['RGBColor'](*TEXT)
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn('w:rFonts'))
        if rf is None:
            rf = self._m['OxmlElement']('w:rFonts'); rpr.insert(0, rf)
        for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
            rf.set(qn(a), FONT_EN)
        rf.set(qn('w:eastAsia'), FONT_KO)
        pf = st.paragraph_format
        pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(3), 1.18

    def _font(self, run, size=10, bold=False, color=None, italic=False, spacing=None):
        Pt, qn, OxmlElement, RGBColor = self._m['Pt'], self._m['qn'], self._m['OxmlElement'], self._m['RGBColor']
        run.font.name, run.font.size, run.font.bold, run.font.italic = FONT_EN, Pt(size), bold, italic
        rpr = run._r.get_or_add_rPr()
        rf = rpr.find(qn('w:rFonts'))
        if rf is None:
            rf = OxmlElement('w:rFonts')
            rpr.insert(0, rf)
        for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
            rf.set(qn(a), FONT_EN)
        rf.set(qn('w:eastAsia'), FONT_KO)
        if spacing is not None:                                   # 자간(1/20pt)
            sp = OxmlElement('w:spacing'); sp.set(qn('w:val'), str(int(spacing))); rpr.append(sp)
        c = TEXT if color is None else color
        run.font.color.rgb = c if isinstance(c, RGBColor) else RGBColor(*c)

    def _shade(self, el, hexc):
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        pr = el._tc.get_or_add_tcPr() if hasattr(el, '_tc') else el._p.get_or_add_pPr()
        for old in pr.findall(qn('w:shd')):
            pr.remove(old)
        sh = OxmlElement('w:shd')
        sh.set(qn('w:val'), 'clear'); sh.set(qn('w:color'), 'auto'); sh.set(qn('w:fill'), hexc)
        pr.append(sh)

    def _pborder(self, p, side, hexc, sz=6, space=4):
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        ppr = p._p.get_or_add_pPr()
        b = ppr.find(qn('w:pBdr'))
        if b is None:
            b = OxmlElement('w:pBdr'); ppr.append(b)
        e = OxmlElement(f'w:{side}')
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(sz)); e.set(qn('w:space'), str(space)); e.set(qn('w:color'), hexc)
        b.append(e)

    def _cell_borders(self, cell, **sides):
        """sides: top/bottom/left/right = (hex, sz) 또는 None(없음)"""
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        tcpr = cell._tc.get_or_add_tcPr()
        b = tcpr.find(qn('w:tcBorders'))
        if b is None:
            b = OxmlElement('w:tcBorders'); tcpr.append(b)
        for side, v in sides.items():
            e = OxmlElement(f'w:{side}')
            if v is None:
                e.set(qn('w:val'), 'nil')
            else:
                e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(v[1])); e.set(qn('w:color'), v[0]); e.set(qn('w:space'), '0')
            b.append(e)

    def _cell_margins(self, cell, top=60, bottom=60, left=100, right=100):
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        tcpr = cell._tc.get_or_add_tcPr()
        m = OxmlElement('w:tcMar')
        for side, v in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
            e = OxmlElement(f'w:{side}'); e.set(qn('w:w'), str(v)); e.set(qn('w:type'), 'dxa'); m.append(e)
        tcpr.append(m)

    def _valign(self, cell, val='center'):
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        v = OxmlElement('w:vAlign'); v.set(qn('w:val'), val)
        cell._tc.get_or_add_tcPr().append(v)

    def _table_base(self, t, lines=True, pad=70):
        """가로줄만 있는 표 — 세로줄 없음, 칸 여백 넉넉히"""
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        tblpr = t._tbl.tblPr
        b = OxmlElement('w:tblBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            e = OxmlElement(f'w:{side}')
            if lines and side in ('top', 'bottom', 'insideH'):
                e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '4'); e.set(qn('w:color'), LINE_HEX); e.set(qn('w:space'), '0')
            else:
                e.set(qn('w:val'), 'nil')
            b.append(e)
        tblpr.append(b)
        mar = OxmlElement('w:tblCellMar')
        for side, v in (('top', pad), ('bottom', pad), ('left', 110), ('right', 110)):
            e = OxmlElement(f'w:{side}'); e.set(qn('w:w'), str(v)); e.set(qn('w:type'), 'dxa'); mar.append(e)
        tblpr.append(mar)
        lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblpr.append(lay)
        ind = OxmlElement('w:tblInd'); ind.set(qn('w:w'), '0'); ind.set(qn('w:type'), 'dxa'); tblpr.append(ind)   # 표 가장자리를 본문 여백에 맞춘다

    def _header(self, text, footer, org):
        WD = self._m['WD_ALIGN_PARAGRAPH']
        Cm = self._m['Cm']
        for s in self.doc.sections:
            hp = s.header.paragraphs[0]
            self._tabs(hp)
            self._font(hp.add_run('POLARIS'), 7.5, True, INK, spacing=30)
            self._font(hp.add_run(f'   {text}'), 8, False, MUTED)
            if org:
                self._font(hp.add_run(f'\t{org}'), 8, False, MUTED)
            self._pborder(hp, 'bottom', LINE_HEX, 4, 6)
            fp = s.footer.paragraphs[0]
            self._tabs(fp)
            if footer:
                self._font(fp.add_run(footer), 7.5, False, MUTED)
            self._font(fp.add_run('\t'), 7.5, False, MUTED)
            self._field(fp, 'PAGE', 7.5, TEXT, True)
            self._font(fp.add_run(' / '), 7.5, False, MUTED)
            self._field(fp, 'NUMPAGES', 7.5, MUTED)
            fp.alignment = WD.LEFT

    def _tabs(self, p):
        """머리글 · 바닥글 스타일의 기본 탭(가운데 8.25cm · 오른쪽 16.5cm)을 지우고 본문 오른쪽 끝에 하나만"""
        from docx.shared import Twips
        ts = p.paragraph_format.tab_stops
        for pos in (4680, 9360):
            ts.add_tab_stop(Twips(pos), self._m['WD_TAB'].CLEAR)
        ts.add_tab_stop(self._m['Cm'](CONTENT_CM), self._m['WD_TAB'].RIGHT)

    def _field(self, p, code, size, color, bold=False):
        """PAGE · NUMPAGES 필드 — 글꼴이 본문과 같도록 run 을 만들어 그 안에 필드를 넣는다"""
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        for kind, txt in (('begin', None), (None, f' {code} '), ('separate', None), (None, '1'), ('end', None)):
            run = p.add_run()
            self._font(run, size, bold, color)
            if kind:
                fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'), kind); run._r.append(fc)
            elif txt.strip() == code:
                it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = txt; run._r.append(it)
            else:
                run.text = txt

    _page_field = lambda self, p: self._field(p, 'PAGE', 7.5, TEXT)   # 예전 이름

    # ── 표지 ─────────────────────────────────────────────────────────────
    def cover(self, subtitle: str, rows: list[tuple[str, str]], verdict: str | None = None, verdict_text: str = '',
              kpis: list | None = None, kicker: str = '점검 보고서', note: str = ''):
        """제목(바탕 없음) → 판정 + 요약 카드 → 머리 정보 표 → 안내 한 줄.
        v1.4.9 — 어두운 띠를 걷어냈다(인쇄 · 복사에 무겁고 낡아 보인다는 의견). 제목 아래 가는 줄 하나로 나눈다"""
        Pt = self._m['Pt']
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18); p.paragraph_format.space_after = Pt(10)
        self._font(p.add_run(f'POLARIS  ·  {kicker}'), 8.5, True, MUTED, spacing=40)
        p = self.doc.add_paragraph()
        self._font(p.add_run(self.title), 24, True, INK)
        p.paragraph_format.space_after = Pt(4); p.paragraph_format.line_spacing = 1.05
        if subtitle:
            p = self.doc.add_paragraph()
            self._font(p.add_run(subtitle), 11, False, MUTED)
        p.paragraph_format.space_after = Pt(0)
        self._pborder(p, 'bottom', LINE_HEX, 8, 12)
        self._gap(18)

        cards = []
        if verdict:
            vt = re.sub(r'^(종합\s*)?판정\s*[:：]\s*', '', verdict_text or '') or SEV_KO.get(verdict, verdict)
            cards.append(('종합 판정', vt, verdict, None))
        cards += list(kpis or [])
        if cards:
            self.kpis(cards, first_wide=bool(verdict))
            self._gap(10)

        t = self.doc.add_table(rows=0, cols=2)
        self._table_base(t)
        for k, v in rows:
            cells = t.add_row().cells
            cells[0].text = cells[1].text = ''
            self._font(cells[0].paragraphs[0].add_run(k), 9, False, MUTED)
            self._font(cells[1].paragraphs[0].add_run(str(v or '—')), 10, False, INK)
        self._widths(t, [3.6, CONTENT_CM - 3.6])
        self._gap(18)
        self.para(note or '이 보고서는 Polaris 가 대상 시스템에 조회만 해서 만들었습니다 — 설정 · 데이터는 변경하지 않았습니다.',
                  8.5, color=MUTED)
        self.page_break()

    def stale_note(self, isos, what: str = '대상'):
        """오래된 점검 결과가 섞여 있으면 요약 맨 앞에 알린다 — 지금 상태로 착각하지 않게(v1.4.10)"""
        d = oldest_days(isos)
        if d is None or d < STALE_DAYS:
            return None
        old = sum(1 for i in isos if (oldest_days([i]) or 0) >= STALE_DAYS)
        return self.callout(f'{old}개 {what}의 점검 결과가 {STALE_DAYS}일 넘게 지났습니다(가장 오래된 것 {int(d)}일 전). '
                            '지금 상태와 다를 수 있으니 점검 시각을 확인하고, 필요하면 다시 점검하세요.',
                            'medium', '오래된 점검 결과')

    def kpis(self, cards: list, first_wide: bool = False):
        """요약 카드 한 줄 — cards = [(이름, 값, 판정키 또는 None, 작은 설명 또는 None)]"""
        Pt, Cm = self._m['Pt'], self._m['Cm']
        n = len(cards)
        gap = KPI_GAP_CM
        t = self.doc.add_table(rows=1, cols=2 * n - 1)       # 카드 · 틈 · 카드 · 틈 …
        self._table_base(t, lines=False)
        room = CONTENT_CM - gap * (n - 1)
        if first_wide and n > 1:
            w0 = min(6.0, room * 0.34)
            cw = [w0] + [(room - w0) / (n - 1)] * (n - 1)
        else:
            cw = [room / n] * n
        widths = []
        for i, w in enumerate(cw):
            widths += [w] if i == 0 else [gap, w]
        for i in range(1, n):                                  # 틈 칸 — 바탕 · 테두리 · 여백 없음
            g = t.rows[0].cells[2 * i - 1]
            self._cell_borders(g, top=None, left=None, bottom=None, right=None)
            self._cell_margins(g, 0, 0, 0, 0)
        for i, card in enumerate(cards):
            label, value, sev, sub = (list(card) + [None, None])[:4]
            c = t.rows[0].cells[2 * i]
            c.text = ''
            # 바탕색 · 위쪽 색 줄 없이 회색 테두리 상자 — 판정은 값 글자색으로만(v1.4.36)
            box = (BOX_HEX, 4)
            self._cell_borders(c, top=box, left=box, bottom=box, right=box)
            self._cell_margins(c, 150, 150, 180, 120)
            p = c.paragraphs[0]
            self._font(p.add_run(label), 8, False, MUTED)
            p.paragraph_format.space_after = Pt(2)
            p = c.add_paragraph()
            self._font(p.add_run(str(value)), 17 if len(str(value)) <= 12 else 13, True,
                       _SEV_RGB.get(sev, INK) if sev else INK)
            p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
            if sub:
                p = c.add_paragraph()
                self._font(p.add_run(str(sub)), 7.5, False, MUTED)
        self._widths(t, widths)
        return t

    # ── 제목 · 글 ────────────────────────────────────────────────────────
    def h1(self, text, new_page: bool = False):
        Pt = self._m['Pt']
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before, pf.space_after = Pt(6 if new_page else 20), Pt(10)
        if new_page:
            self.break_before(p)
        m = re.match(r'^(\d+\.|부록\.)\s*(.*)$', text)
        if m:
            self._font(p.add_run(m.group(1) + ' '), 15, True, INK)
            self._font(p.add_run(m.group(2)), 15, True, INK)
        else:
            self._font(p.add_run(text), 15, True, INK)
        self._pborder(p, 'bottom', LINE_HEX, 6, 6)
        return p

    def h2(self, text, sub: str = ''):
        Pt = self._m['Pt']
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(12), Pt(5)
        self._font(p.add_run(text), 11.5, True, INK)
        if sub:
            self._font(p.add_run(f'   {sub}'), 9, False, MUTED)
        return p

    def h3(self, text):
        Pt = self._m['Pt']
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(8), Pt(3)
        self._font(p.add_run(text), 9.5, True, TEXT)
        return p

    def para(self, text, size=10, bold=False, color=None, align=None, space=2):
        Pt = self._m['Pt']
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space); p.paragraph_format.space_after = Pt(space + 1)
        if align is not None:
            p.alignment = align
        self._font(p.add_run(text), size, bold, color)
        return p

    def bullet(self, text, size=9.5):
        Cm, Pt = self._m['Cm'], self._m['Pt']
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent, pf.first_line_indent = Cm(0.6), Cm(-0.35)
        pf.space_before, pf.space_after = Pt(1), Pt(2)
        self._font(p.add_run('•  '), size, True, MUTED)
        self._font(p.add_run(text), size)
        return p

    def callout(self, text, sev='info', title: str = ''):
        """안내 상자 — 판정 한 줄 · 주의 사항. 회색 테두리만 두고 등급은 글자색으로 나타낸다(v1.4.36 — 바탕색도 걷어냈다)"""
        Pt, Cm = self._m['Pt'], self._m['Cm']
        t = self.doc.add_table(rows=1, cols=1)
        self._table_base(t, lines=False)
        c = t.rows[0].cells[0]
        c.width = Cm(CONTENT_CM)
        box = (BOX_HEX, 4)
        self._cell_borders(c, left=box, top=box, bottom=box, right=box)
        self._cell_margins(c, 110, 110, 180, 140)
        p = c.paragraphs[0]
        if title:
            self._font(p.add_run(title + '  '), 10, True, _SEV_RGB.get(sev, INK))
        self._font(p.add_run(text), 10, bool(not title), _SEV_RGB.get(sev, INK) if not title else INK)
        self._gap(6)
        return t

    def code(self, lines, size=8.5):
        """고정폭 글꼴 상자 — SQL · 명령 예시"""
        Pt, Cm = self._m['Pt'], self._m['Cm']
        t = self.doc.add_table(rows=1, cols=1)
        self._table_base(t, lines=False)
        c = t.rows[0].cells[0]
        c.width = Cm(CONTENT_CM)
        box = (BOX_HEX, 4)
        self._cell_borders(c, left=box, top=box, bottom=box, right=box)       # 바탕색 없이 회색 테두리만(v1.4.36)
        self._cell_margins(c, 100, 100, 180, 120)
        for i, ln in enumerate(lines):
            p = c.paragraphs[0] if i == 0 else c.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(ln)
            self._font(r, size, False, INK)
            r.font.name = 'Consolas'
            rf = r._r.get_or_add_rPr().find(self._m['qn']('w:rFonts'))
            for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
                rf.set(self._m['qn'](a), 'Consolas')
        self._gap(6)
        return t

    def _gap(self, pt=6):
        Pt = self._m['Pt']
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0); p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = Pt(max(1, pt))
        return p

    # ── 표 ───────────────────────────────────────────────────────────────
    def table(self, headers, rows, widths=None, font_size=9):
        """rows 의 칸이 Sev(...) 면 판정 칸으로 칠한다. 빈 rows 면 「(해당 없음)」"""
        if not rows:
            self.para('(해당 없음)', 9, color=MUTED)
            return None
        t = self.doc.add_table(rows=1, cols=len(headers))
        self._table_base(t, pad=25 if font_size <= 8 else 70)       # 긴 목록(작은 글씨)은 촘촘하게
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]; c.text = ''
            self._font(c.paragraphs[0].add_run(h), font_size - 0.5, True, INK)
            self._cell_borders(c, bottom=(RULE_HEX, 8))
        self._repeat_header(t.rows[0])
        for ri, row in enumerate(rows):
            tr = t.add_row()
            self._cant_split(tr)
            cells = tr.cells
            for i, v in enumerate(row):
                c = cells[i]; c.text = ''
                p = c.paragraphs[0]
                if isinstance(v, Sev):
                    self._sev_cell(c, v, font_size)
                else:
                    lines = ('' if v is None else str(v)).split('\n')
                    self._font(p.add_run(lines[0]), font_size, False, INK if i == 0 else TEXT)
                    for extra in lines[1:]:                     # 둘째 줄부터는 작은 회색 글씨(주소 · 버전 등)
                        q = c.add_paragraph()
                        self._font(q.add_run(extra), font_size - 1, False, MUTED)
        if widths:
            self._widths(t, widths)
        self._gap(8)
        return t

    def _sev_cell(self, c, v, font_size):
        key = str(v)
        p = c.paragraphs[0]
        self._font(p.add_run(v.label or SEV_KO.get(key, key)), font_size, True, _SEV_RGB.get(key, TEXT))

    def kv(self, pairs, widths=(4.5, 12.5)):
        """이름 · 값 두 칸 표(머리 행 없음)"""
        rows = [(k, v) for k, v in pairs]
        if not rows:
            return None
        t = self.doc.add_table(rows=0, cols=2)
        self._table_base(t)
        for k, v in rows:
            cells = t.add_row().cells
            cells[0].text = cells[1].text = ''
            self._font(cells[0].paragraphs[0].add_run(str(k)), 9, False, MUTED)
            lines = ('—' if v in (None, '') else str(v)).split('\n')
            self._font(cells[1].paragraphs[0].add_run(lines[0]), 9.5, False, INK)
            for extra in lines[1:]:
                q = cells[1].add_paragraph(); self._font(q.add_run(extra), 8.5, False, MUTED)
        self._widths(t, list(widths))
        self._gap(8)
        return t

    def counts_table(self, counts: dict, keys=('critical', 'high', 'medium', 'low'), meaning=None):
        """등급별 건수 — 카드 한 줄로"""
        meaning = meaning or {'critical': '즉시 조치', 'high': '빠른 시일 안에', 'medium': '정기 작업에서', 'low': '참고 · 계획',
                              'block': '업그레이드 전에 반드시', 'warn': '작업 중 중단 위험', 'info': '참고'}
        return self.kpis([(SEV_KO.get(k, k), f'{counts.get(k, 0)}건', k if counts.get(k) else None, meaning.get(k, ''))
                          for k in keys])

    def checklist(self, items: list, show_ok_detail: bool = True, font_size=8.5):
        """점검표 — 분류마다 묶음 행 + 항목(점검 항목 · 결과 · 판정 · 설명/권고).

        items = [{cat, name, value, sev, detail, action, help}] — sev 가 ok/info/unknown 이어도 모두 싣는다
        (보고서가 「무엇을 봤는지」 를 보여 주도록). 정상 항목은 설명 칸에 왜 보는지(help)를 짧게.
        """
        if not items:
            self.para('(점검 항목 없음)', 9, color=MUTED)
            return None
        Cm = self._m['Cm']
        widths = [4.0, 3.8, 1.7, CONTENT_CM - 9.5]
        t = self.doc.add_table(rows=1, cols=4)
        self._table_base(t)
        for i, h in enumerate(('점검 항목', '결과', '판정', '설명 · 권고')):
            c = t.rows[0].cells[i]; c.text = ''
            self._font(c.paragraphs[0].add_run(h), font_size, True, INK)
            self._cell_borders(c, bottom=(RULE_HEX, 8))
        self._repeat_header(t.rows[0])
        cur = None
        for it in items:
            if it.get('cat') != cur:
                cur = it.get('cat')
                row = t.add_row()
                self._cant_split(row)
                merged = row.cells[0].merge(row.cells[3])
                merged.text = ''
                p = merged.paragraphs[0]
                p.paragraph_format.space_before = self._m['Pt'](4)
                self._font(p.add_run(str(cur or '')), font_size + 0.5, True, INK)
            tr = t.add_row()
            self._cant_split(tr)
            cells = tr.cells
            for c in cells:
                c.text = ''
            self._font(cells[0].paragraphs[0].add_run(str(it.get('name', ''))), font_size, False, INK)
            self._font(cells[1].paragraphs[0].add_run(str(it.get('value') if it.get('value') not in (None, '') else '—')), font_size)
            sev = it.get('sev') or 'info'
            self._sev_cell(cells[2], Sev(sev), font_size)
            note = it.get('detail') or ''
            if sev in PROBLEM:
                if it.get('action'):
                    note = (note + ' — ' if note else '') + it['action']
            elif show_ok_detail and not note:
                note = it.get('help') or ''
            p = cells[3].paragraphs[0]
            self._font(p.add_run(note), font_size - 0.5, False, TEXT if sev in PROBLEM else MUTED)
        self._widths(t, widths)
        self._gap(8)
        return t

    def page_break(self):
        self.doc.add_page_break()

    def break_before(self, p):
        """p 를 새 쪽에서 시작 — 문단 앞에 페이지 나누기를 넣는다(v1.4.12).
        「앞에서 페이지 나누기」 · 「다음 문단과 함께」 서식은 Word 편집 기호에서 문단 앞 네모(▪)로 보여
        모두 쓰지 않는다. 표 행은 쪽에서 쪼개지지 않게(cantSplit) · 머리 행은 다음 쪽에 반복한다"""
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        r = OxmlElement('w:r'); br = OxmlElement('w:br'); br.set(qn('w:type'), 'page'); r.append(br)
        ppr = p._p.find(qn('w:pPr'))
        if ppr is not None:
            ppr.addnext(r)
        else:
            p._p.insert(0, r)
        return p

    def _cant_split(self, row):
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        e = OxmlElement('w:cantSplit'); e.set(qn('w:val'), 'true'); row._tr.get_or_add_trPr().append(e)

    def _repeat_header(self, row):
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        trPr = row._tr.get_or_add_trPr()
        h = OxmlElement('w:tblHeader'); h.set(qn('w:val'), 'true'); trPr.append(h)

    def _widths(self, t, widths):
        Cm = self._m['Cm']
        qn, OxmlElement = self._m['qn'], self._m['OxmlElement']
        total = sum(widths)
        scale = CONTENT_CM / total if total > CONTENT_CM + 0.05 else 1.0   # 본문 폭을 넘지 않게
        ws = [w * scale for w in widths]
        grid = t._tbl.tblGrid
        cols = grid.findall(qn('w:gridCol'))
        for i, w in enumerate(ws):
            if i < len(cols):
                cols[i].set(qn('w:w'), str(int(w * 567)))              # cm → twip
        for row in t.rows:
            tcs = row._tr.findall(qn('w:tc'))
            if len(tcs) != len(ws):                                    # 합친 행(점검표 분류 행)
                if tcs:
                    tcs[0].get_or_add_tcPr()
                    row.cells[0].width = Cm(sum(ws))
                continue
            for i, w in enumerate(ws):
                row.cells[i].width = Cm(w)

    def save(self, path: str) -> str:
        self.doc.save(path)
        return path


def _mods():
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    return {'Pt': Pt, 'Cm': Cm, 'RGBColor': RGBColor, 'WD_ALIGN_PARAGRAPH': WD_ALIGN_PARAGRAPH, 'WD_TAB': WD_TAB_ALIGNMENT,
            'OxmlElement': OxmlElement, 'qn': qn}


def meta_defaults(version: str = '') -> dict:
    """보고서 공통 머리 정보 — 작성 시각 · Polaris 버전 · 조직(풀패키지일 때만)"""
    try:
        from polaris import VERSION
    except Exception:
        VERSION = version or ''
    try:
        from src.reports import _report_org
        org = _report_org() or ''
    except Exception:
        org = ''
    return {'when': datetime.now().strftime('%Y-%m-%d %H:%M'), 'version': f'v{VERSION}' if VERSION else '', 'org': org}
