"""ReportsMixin — 파일 다이얼로그 + 보고서 생성 (DOCX/TXT).
"""
import os
import threading
import uuid
from pathlib import Path

from src.k8s import HAS_K8S
from src.reports import (
    _report_collect, _report_evaluate,
    _llm_ask, _report_write_docx, _report_write_txt,
)
from src._state import _report_jobs


class ReportsMixin:
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
                log_fn('[1/5] 클러스터 데이터 수집 중...')
                data = _report_collect(k8s_ref, log_fn)

                log_fn('[2/5] 발견 사항 평가 중...')
                findings = _report_evaluate(data)
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
                actual_path = _report_write_docx(data, findings, llm_fn, save_path, log_fn)

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


    def get_job_status(self, job_id: str):
        """폴링용 — 현재 job 상태 반환."""
        job = _report_jobs.get(job_id)
        if not job:
            return {'status': 'unknown', 'logs': [], 'path': None, 'error': None}
        return {
            'status': job['status'],
            'logs':   list(job['logs']),
            'path':   job.get('path'),
            'error':  job.get('error'),
        }

