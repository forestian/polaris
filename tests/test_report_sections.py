# -*- coding: utf-8 -*-
"""보고서 섹션 선택 — RBAC 제외 (v1.2.153).

RBAC 권한 정리는 단기간에 끝나는 일이 아니라 매 보고서마다 확인할 정보가 아니다.
체크를 풀면 **RBAC 관련 내용이 보고서 어디에도 남지 않아야** 한다 — 구성 표뿐
아니라 발견 사항·우선순위 요약·개선 작업·점검 범위까지.

핵심 설계: RBAC 경고를 _report_evaluate 단계에서 아예 만들지 않는다. 발견 사항
표·우선순위·개선 작업이 모두 findings 에서 파생되므로 한 곳만 막으면 전부 사라진다.
"""
import pathlib
import tempfile
import unittest

import docx

from src.reports import _section_on, _report_evaluate, _report_write_docx


def _data():
    return {
        'cluster_version': 'v1.34.8', 'collected_at': '2026-09-04',
        'nodes': [], 'pods': [], 'deployments': [], 'services': [], 'events': [],
        'rbac': {'cluster_roles': 71, 'cluster_role_bindings': 55, 'roles': 12,
                 'role_bindings': 18, 'service_accounts': 40},
        'rbac_risky': [
            {'subject_kind': 'ServiceAccount', 'name': 'ci-runner', 'namespace': 'ci',
             'reason': 'cluster-admin 바인딩', 'binding_kind': 'ClusterRoleBinding',
             'binding': 'ci-admin', 'role_kind': 'ClusterRole', 'role': 'cluster-admin'},
            {'subject_kind': 'Group', 'name': 'dev-team', 'namespace': '',
             'reason': '와일드카드 권한', 'binding_kind': 'ClusterRoleBinding',
             'binding': 'dev-all', 'role_kind': 'ClusterRole', 'role': 'wildcard'},
        ],
        'network_policies': [],
    }


def _docx_text(path):
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.append(' | '.join(c.text for c in row.cells))
    return '\n'.join(parts)


class SectionGateTests(unittest.TestCase):
    def test_none_includes_everything(self):
        # 이 인자를 넘기지 않던 기존 호출이 그대로 동작해야 한다
        self.assertTrue(_section_on(None, 'rbac'))

    def test_membership(self):
        self.assertTrue(_section_on({'nodes', 'rbac'}, 'rbac'))
        self.assertFalse(_section_on({'nodes', 'pods'}, 'rbac'))
        self.assertFalse(_section_on(set(), 'rbac'))


class EvaluateTests(unittest.TestCase):
    @staticmethod
    def _rbac(findings):
        return [f for f in findings if f.get('category') == 'rbac']

    def test_rbac_findings_present_by_default(self):
        self.assertEqual(len(self._rbac(_report_evaluate(_data()))), 2)

    def test_rbac_findings_present_when_selected(self):
        self.assertEqual(len(self._rbac(_report_evaluate(_data(), {'rbac'}))), 2)

    def test_rbac_findings_dropped_when_deselected(self):
        self.assertEqual(self._rbac(_report_evaluate(_data(), {'nodes'})), [])

    def test_other_findings_survive(self):
        # RBAC 만 빠져야 한다 — 다른 발견 사항까지 사라지면 보고서가 비어버린다
        # v1.4.13 — 예전에는 늘 켜지던 HPA 경고가 「다른 발견 사항」 역할을 했다. 그 규칙을 고쳐
        # fixture 에 RBAC 외 발견 사항이 없어졌으므로 하나(Lost PVC)를 직접 넣는다
        def _d():
            d = _data()
            d['pvcs'] = [{'namespace': 'app', 'name': 'data', 'status': 'Lost'}]
            return d
        full = _report_evaluate(_d())
        cut = _report_evaluate(_d(), {'nodes'})
        self.assertEqual(len(full) - len(cut), 2)
        self.assertGreater(len(cut), 0)


class DocxOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='polaris-report-sec-'))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build(self, sections, name):
        data = _data()
        findings = _report_evaluate(data, sections)
        path = _report_write_docx(data, findings, None, str(self.tmp / name),
                                  lambda *_a, **_k: None, sections)
        return _docx_text(path)

    def test_included_report_has_rbac_section(self):
        text = self._build(None, 'inc.docx')
        self.assertIn('7.1 RBAC 구성', text)
        self.assertIn('7.2 NetworkPolicy', text)
        self.assertIn('ClusterRoleBinding', text)

    def test_excluded_report_has_no_rbac_anywhere(self):
        """★ 이 테스트가 요청의 핵심 — 어디에도 남으면 안 된다."""
        text = self._build({'nodes', 'pods'}, 'exc.docx')
        upper = text.upper()
        self.assertNotIn('RBAC', upper, 'RBAC 글자가 보고서에 남아 있다')
        self.assertNotIn('CLUSTERROLE', upper, 'RBAC 구성 표가 남아 있다')
        self.assertNotIn('CLUSTER-ADMIN', upper, '권한 경고가 발견 사항에 남아 있다')

    def test_excluded_report_renumbers_networkpolicy(self):
        # 7.1 이 비고 7.2 부터 시작하면 빠진 장이 있는 문서로 읽힌다
        text = self._build({'nodes'}, 'renum.docx')
        self.assertIn('7.1 NetworkPolicy', text)
        self.assertNotIn('7.2 NetworkPolicy', text)

    def test_excluded_report_drops_rbac_from_scope(self):
        # 점검 범위에 적어놓고 내용이 없으면 누락된 보고서로 읽힌다
        text = self._build({'nodes'}, 'scope.docx')
        self.assertIn('보안 위험 항목 (NetworkPolicy)', text)

    def test_excluded_report_still_has_other_sections(self):
        text = self._build({'nodes'}, 'rest.docx')
        for heading in ('1. 점검 개요', '7. 보안', '8. 발견 사항 및 권고'):
            self.assertIn(heading, text)


class FrontendContractTests(unittest.TestCase):
    """UI 가 보내는 키와 백엔드가 보는 키가 어긋나면 체크박스가 조용히 무시된다."""

    def test_report_page_offers_rbac_checkbox(self):
        src = (pathlib.Path(__file__).resolve().parents[1]
               / 'ui' / 'src' / 'pages' / 'ReportPage.jsx').read_text(encoding='utf-8')
        self.assertIn("key: 'rbac'", src)

    def test_api_passes_sections_into_report(self):
        src = (pathlib.Path(__file__).resolve().parents[1]
               / 'src' / 'api' / 'reports.py').read_text(encoding='utf-8')
        self.assertIn('_report_evaluate(data, _sections)', src)
        self.assertIn('log_fn, _sections)', src)
        # 클러스터 스캔은 보고서와 별개 — 항상 전부 본다
        self.assertIn('findings = _report_evaluate(data)', src)


class ReportFilenameTests(unittest.TestCase):
    """기본 파일명에 클러스터 별명 넣기 (v1.2.154).

    파일명만 보고 어느 클러스터 보고서인지 알 수 있어야 한다. 별명 선택은
    _cluster_label 이 하며 display_name 을 우선한다 — RKE2 kubeconfig 는 context 가
    죄다 'default' 라 context 를 쓰면 클러스터가 몇 개든 전부 같은 이름이 된다.
    """

    def setUp(self):
        from src.api import PolarisAPI
        self.api = PolarisAPI()

    def _connect(self, display_name, context='default'):
        class M:
            connected = True
            cluster_info = {'context': context}
        self.api._clusters['c1'] = {'mgr': M(), 'display_name': display_name,
                                     'context': context, 'version': 'v1.34', 'path': ''}
        self.api._active_id = 'c1'

    def test_includes_cluster_alias(self):
        self._connect('o2meet')
        name = self.api.default_report_filename()
        self.assertTrue(name.startswith('Polaris-report-o2meet-'), name)
        self.assertTrue(name.endswith('.docx'), name)

    def test_falls_back_without_cluster(self):
        # 미연결이면 예전 형식 그대로 — 이름에 빈 칸이 생기면 안 된다
        name = self.api.default_report_filename()
        self.assertRegex(name, r'^Polaris-report-\d{4}-\d{2}-\d{2}\.docx$')

    def test_keeps_korean_alias(self):
        # 스냅샷의 _safe_name 은 ASCII 만 남겨 한글이 통째로 '-' 가 된다.
        # 보고서 파일명은 사람이 읽는 것이라 한글을 살린다.
        self._connect('운영 클러스터')
        self.assertIn('운영-클러스터', self.api.default_report_filename())

    def test_strips_filesystem_reserved_chars(self):
        self._connect('a/b:c*d?e"f<g>h|i')
        name = self.api.default_report_filename()
        for ch in r'\/:*?"<>|':
            self.assertNotIn(ch, name, f'{ch!r} 가 파일명에 남으면 저장이 실패한다')

    def test_caps_length(self):
        self._connect('x' * 100)
        self.assertLessEqual(len(self.api.default_report_filename()), 80)

    def test_display_name_wins_over_context(self):
        self._connect('o2meet', context='default')
        self.assertIn('o2meet', self.api.default_report_filename())

    def test_frontend_asks_backend_for_the_name(self):
        # 프론트가 자체 규칙으로 만들면 별명 선택 로직이 두 곳으로 갈라진다
        src = (pathlib.Path(__file__).resolve().parents[1]
               / 'ui' / 'src' / 'pages' / 'ReportPage.jsx').read_text(encoding='utf-8')
        self.assertIn('api.defaultReportFilename()', src)
        apijs = (pathlib.Path(__file__).resolve().parents[1]
                 / 'ui' / 'src' / 'api.js').read_text(encoding='utf-8')
        self.assertIn("callSafe('default_report_filename')", apijs)


if __name__ == "__main__":
    unittest.main()
