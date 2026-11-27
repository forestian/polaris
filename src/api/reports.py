"""ReportsMixin — 파일 다이얼로그 + 보고서 생성 (DOCX/TXT).
"""
import os
import threading
import uuid
from pathlib import Path

from src.k8s import HAS_K8S
from src.reports import (
    _report_collect, _report_collect_ext, _report_evaluate,
    _report_build_priority_summary,
    _llm_ask, _report_write_docx, _report_write_txt,
)
from src._state import _report_jobs


class ReportsMixin:
    # 파일명에 쓸 수 없는 문자만 걸러낸다. 스냅샷의 _safe_name 은 ASCII 만 남겨
    # 한글 클러스터명이 통째로 '-' 가 되는데, 보고서 파일명은 사람이 읽는 것이라
    # 한글·유니코드를 살린다(Windows 파일명은 아래 문자만 금지).
    _FNAME_BAD = r'[\\/:*?"<>|]'

    @classmethod
    def _fname_part(cls, s: str, limit: int = 40) -> str:
        import re
        s = re.sub(cls._FNAME_BAD, '', str(s or ''))
        s = re.sub(r'[\x00-\x1f]', '', s)
        s = re.sub(r'\s+', '-', s).strip('-. ')   # 공백→'-', 끝의 점/공백은 Windows 가 싫어함
        return s[:limit]

    def default_report_filename(self) -> str:
        """저장 대화상자에 채워 넣을 기본 파일명.

        클러스터 별명을 끼워 어느 클러스터 보고서인지 파일명만 보고 알 수 있게 한다
        (Polaris-report-o2meet-2026-09-04.docx). 별명은 _cluster_label 이 고른다 —
        display_name 우선이라 RKE2 처럼 context 가 죄다 'default' 인 경우에도 구분된다.
        """
        from datetime import datetime
        stamp = datetime.now().strftime('%Y-%m-%d')
        try:
            label = self._fname_part(self._cluster_label(fallback=''))
        except Exception:
            label = ''
        return f'Polaris-report-{label}-{stamp}.docx' if label else f'Polaris-report-{stamp}.docx'

    def open_save_dialog(self, filename: str = 'Polaris-report.docx'):
        if not self._window:
            return None
        try:
            import webview
            try:
                dialog_type = webview.FileDialog.SAVE
            except AttributeError:
                dialog_type = webview.SAVE_DIALOG  # < 6.x
            # 확장자별 필터
            if str(filename).endswith('.docx'):
                file_types = ('Word 문서 (*.docx)', 'All files (*.*)')
            elif str(filename).endswith('.zip'):
                file_types = ('ZIP 압축 파일 (*.zip)', 'All files (*.*)')
            elif str(filename).endswith('.log'):
                file_types = ('로그 파일 (*.log)', 'All files (*.*)')
            else:
                file_types = ('HTML files (*.html)', 'All files (*.*)')
            result = self._window.create_file_dialog(
                dialog_type,
                save_filename=filename,
                file_types=file_types,
            )
            # pywebview 는 tuple/list 를 반환 → 첫 번째 경로 문자열만 반환
            if not result:
                return None
            return result[0] if isinstance(result, (list, tuple)) else result
        except Exception:
            return None


    def save_text_file(self, content: str, filename: str = 'polaris-export.txt') -> dict:
        """텍스트 내용을 네이티브 SAVE 다이얼로그로 저장.

        pywebview 환경에서 브라우저식 Blob 다운로드는 불안정하므로, 백엔드에서
        저장 다이얼로그를 띄우고 직접 파일을 기록한다. 로그뷰어/이벤트 등
        텍스트 export 공용 메서드.

        반환: {ok:True, path} / {ok:False, canceled:True} / {ok:False, error}
        """
        if not self._window:
            return {'ok': False, 'error': '윈도우가 준비되지 않았습니다.'}
        try:
            import webview
            try:
                dialog_type = webview.FileDialog.SAVE
            except AttributeError:
                dialog_type = webview.SAVE_DIALOG  # < 6.x
            ext = Path(filename).suffix.lower()
            if ext in ('.csv', '.tsv'):
                file_types = ('CSV/TSV (*.csv;*.tsv)', 'All files (*.*)')
            elif ext == '.log':
                file_types = ('로그 파일 (*.log)', 'Text 파일 (*.txt)', 'All files (*.*)')
            elif ext in ('.yaml', '.yml'):
                file_types = ('YAML (*.yaml;*.yml)', 'All files (*.*)')
            else:
                file_types = ('Text 파일 (*.txt)', 'All files (*.*)')
            result = self._window.create_file_dialog(
                dialog_type, save_filename=filename, file_types=file_types,
            )
            if not result:
                return {'ok': False, 'canceled': True}
            path = result[0] if isinstance(result, (list, tuple)) else result
            Path(path).write_text('' if content is None else str(content), encoding='utf-8')
            return {'ok': True, 'path': str(path)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def generate_report(self, cfg: dict):
        """하위 호환 — start_report 로 위임."""
        return self.start_report(cfg)


    def start_report(self, cfg: dict):
        """백그라운드 스레드로 DOCX 보고서 생성. {ok, job_id} 반환."""
        if not self.k8s.connected:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        save_path = cfg.get('save_path', '')
        if not save_path:
            return {'ok': False, 'error': '저장 경로가 지정되지 않았습니다.'}
        if not str(Path(save_path).name).lower().endswith('.docx'):
            return {'ok': False, 'error': '저장 파일은 .docx 형식이어야 합니다.'}
        try:
            save_path = str(Path(save_path).resolve())
        except Exception:
            return {'ok': False, 'error': '저장 경로가 올바르지 않습니다.'}

        import uuid
        job_id = str(uuid.uuid4())
        _report_jobs[job_id] = {'status': 'running', 'logs': [], 'path': None, 'error': None}

        k8s_ref = self.k8s   # 스레드가 캡처

        def run():
            job = _report_jobs[job_id]

            def log_fn(msg):
                job['logs'].append(msg)

            try:
                # cfg['namespace'] 와 sections 의 나머지 키(nodes·pods…)는 UI 가 보내지만
                # DOCX 경로에서 쓰이지 않는다 — 옛 HTML 보고서용이라 DOCX 의 9개 장 구성과
                # 매핑이 없다. 반면 'netscan' 과 sections 의 'rbac' 는 **실제로 읽어서
                # 동작을 바꾼다** — 장식이 아니므로 지우지 말 것.
                _netscan = bool(cfg.get('netscan'))
                # sections 를 아예 안 보내던 옛 호출은 None → 전부 포함(기존 동작 유지)
                _sections = cfg.get('sections')
                _sections = set(_sections) if isinstance(_sections, (list, tuple, set)) else None
                if _sections is not None and 'rbac' not in _sections:
                    log_fn('  RBAC 섹션 제외 — 구성 표와 권한 경고를 모두 생략합니다')
                log_fn('[1/5] 클러스터 데이터 수집 중...'
                       + (' (네트워크 스캔 포함)' if _netscan else ''))
                data = _report_collect_ext(k8s_ref, log_fn, netscan=_netscan)

                log_fn('[2/5] 발견 사항 평가 중...')
                findings = _report_evaluate(data, _sections)
                log_fn(f'  발견 이슈 {len(findings)}개')

                llm_fn = None
                if cfg.get('use_ai') and cfg.get('llm_url'):
                    _ai_url   = cfg['llm_url']
                    _ai_model = cfg.get('llm_model', 'local-model')
                    def llm_fn(prompt):
                        try:
                            return _llm_ask(_ai_url, _ai_model, prompt)
                        except Exception as _e:
                            log_fn(f'  [경고] AI 호출 실패: {_e}')
                            return ''
                    log_fn('[3/5] AI 분석 활성화 (섹션별)')
                else:
                    log_fn('[3/5] AI 분석 건너뜀')

                log_fn('[4/5] DOCX 보고서 작성 중...')
                actual_path = _report_write_docx(data, findings, llm_fn, save_path, log_fn, _sections)

                log_fn(f'[5/5] 완료 → {actual_path}')
                job['status'] = 'done'
                job['path']   = actual_path

            except Exception as e:
                import traceback, logging
                job['status'] = 'error'
                job['error']  = str(e)
                job['logs'].append(f'[오류] 보고서 생성 실패: {e}')
                logging.exception('[보고서 생성 오류]')

        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'job_id': job_id}


    def health_scan(self, explain: bool = False, llm_url: str = '',
                    llm_model: str = 'local-model', netscan: bool = False) -> dict:
        """규칙 기반 클러스터 스캔 (온디맨드, 파일 생성 없음).

        보고서와 동일한 수집·평가 규칙(_report_collect/_report_evaluate)을 재사용해
        즉석에서 발견사항을 반환한다. explain=True + llm_url 이면 로컬 LLM 으로 우선
        조치 요약을 덧붙인다(발견사항 근거로만; 크리덴셜 미취급).

        netscan=True 면 네트워크 스캐닝(선택 점검)을 함께 수행한다 — 클러스터에 아무것도
        배포하지 않고 API 서버 경유로만 확인한다. False 면 data 에 'netscan' 키가 없어
        네트워크 규칙이 한 건도 발동하지 않는다(기존 동작과 동일).

        ※ netscan 은 반드시 **4번째 위치 인자**여야 한다 — ui/src/api.js 의 healthScan 이
          positional 로 호출하므로 중간에 끼워넣으면 인자가 잘못 결합된다.

        반환: {ok, total, counts, immediate, short_term, backlog, explanation?, netscan?}
        """
        if not getattr(self.k8s, 'kubeconfig', None):
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        try:
            data = _report_collect_ext(self.k8s, lambda *_a, **_k: None,
                                       netscan=bool(netscan))
            # 클러스터 스캔은 보고서와 별개다 — 여기서는 RBAC 을 포함해 전부 본다
            findings = _report_evaluate(data)
            summary = _report_build_priority_summary(findings)
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        result = {
            'ok': True, 'total': len(findings),
            'counts': summary.get('counts', {}),
            'immediate': summary.get('immediate', []),
            'short_term': summary.get('short_term', []),
            'backlog': summary.get('backlog', []),
        }
        ns = data.get('netscan')
        if ns:
            # 점검 범위 요약만 프론트로 — probes/certs 원본은 보내지 않는다(용량·불필요)
            result['netscan'] = {
                'target_count': ns.get('target_count', 0),
                'probed_count': len(ns.get('probes') or []),
                'total_candidates': ns.get('total_candidates', 0),
                'skipped_count': len(ns.get('skipped') or []),
                'cert_count': len(ns.get('certs') or []),
                'certs_total': ns.get('certs_total', 0),
                'certs_skipped': ns.get('certs_skipped', 0),
                'truncated': bool(ns.get('truncated')),
                # 예산 초과로 일부를 못 봤다는 사실은 반드시 올려보낸다 — 안 보내면
                # UI 가 "TLS 0건"만 보여줘서 "인증서가 없다"로 오해하게 된다
                'budget_exceeded': bool(ns.get('budget_exceeded')),
                'permission': ns.get('permission', 'ok'),
                'duration_s': ns.get('duration_s', 0),
            }
        if explain and str(llm_url or '').strip():
            try:
                result['explanation'] = self._health_scan_explain(summary, llm_url, llm_model)
            except Exception as e:
                result['explain_error'] = f'AI 설명 실패: {getattr(e, "reason", e)}'
        return result

    @staticmethod
    def _health_scan_explain(summary: dict, llm_url: str, llm_model: str) -> str:
        c = summary.get('counts', {})
        lines = []
        for item in (summary.get('immediate') or [])[:20]:
            lines.append(f"- [{item.get('severity')}] {item.get('target')}: "
                         f"{item.get('value')} — {item.get('detail')}")
        body = '\n'.join(lines) or '심각/높음 등급 이슈 없음'
        prompt = (
            f"쿠버네티스 클러스터 헬스 체크 결과입니다. "
            f"심각 {c.get('critical', 0)}건, 높음 {c.get('high', 0)}건, "
            f"중간 {c.get('medium', 0)}건.\n"
            f"우선 조치 대상:\n{body}\n\n"
            f"위 발견사항만 근거로, 운영자가 지금 무엇부터 확인해야 하는지 한국어로 "
            f"3~5줄 요약과 우선순위를 제시하세요. 근거 없는 추측은 하지 말고, "
            f"이슈가 없으면 '✅ 특이사항 없음'만 답하세요."
        )
        return _llm_ask((llm_url or '').strip(),
                        (llm_model or 'local-model').strip() or 'local-model', prompt)

    def get_job_status(self, job_id: str):
        """폴링용 — 현재 job 상태 반환. logs 는 이전 호출 이후 새로 쌓인 만큼만(반환 즉시 비움)."""
        job = _report_jobs.get(job_id)
        if not job:
            return {'status': 'unknown', 'logs': [], 'path': None, 'error': None}
        logs, job['logs'] = job['logs'], []
        return {
            'status': job['status'],
            'logs':   logs,
            'path':   job.get('path'),
            'error':  job.get('error'),
        }

