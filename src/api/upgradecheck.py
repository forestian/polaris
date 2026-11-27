"""K8s 업그레이드 사전 점검 (CHECK 탭, v1.4.1) — 코어 mixin. 판정은 src/upgradecheck.py.

노출 메서드:
  upgrade_check_versions()      → 지금 버전과 고를 수 있는 목표 버전(한 단계 ~ 세 단계 위)
  upgrade_check(target)         → 점검 결과 {ok, verdict, findings, passed, checklist, ...}
  upgrade_check_save(path) · upgrade_check_filename() → 마지막 결과를 DOCX 보고서로 (v1.4.4)

클러스터를 바꾸지 않는다(GET 만). 클러스터 스캔과 같은 연결(활성 클러스터)을 쓴다.
"""
from src import upgradecheck as UC


class UpgradeCheckMixin:
    def upgrade_check_versions(self) -> dict:
        if not getattr(self.k8s, 'kubeconfig', None):
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        try:
            v = UC._get(self.k8s._api_client, '/version').get('gitVersion', '')
        except Exception as e:
            return {'ok': False, 'error': f'버전을 읽지 못했습니다: {UC._short_err(e)}'}
        m = UC.minor_of(v)
        if not m:
            return {'ok': False, 'error': f'버전 형식을 알 수 없습니다: {v}'}
        targets = [{'value': f'{m[0]}.{m[1] + i}', 'label': f'{m[0]}.{m[1] + i}' + (' (다음 단계 · 권장)' if i == 1 else f' ({i}단계 위)')}
                   for i in (1, 2, 3)]
        return {'ok': True, 'version': v, 'minor': f'{m[0]}.{m[1]}', 'rke2': '+rke2' in v, 'targets': targets}

    def upgrade_check(self, target: str = '') -> dict:
        if not getattr(self.k8s, 'kubeconfig', None):
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        if not UC.minor_of(target):
            return {'ok': False, 'error': '목표 버전을 고르세요.'}
        try:
            data = UC.collect(self.k8s, target)
            res = UC.evaluate(data)
        except Exception as e:
            return {'ok': False, 'error': f'점검하지 못했습니다: {UC._short_err(e)}'}
        out = {'ok': True, 'target': target, **res}
        try:
            out['cluster'] = self._cluster_label(fallback='') if hasattr(self, '_cluster_label') else ''
        except Exception:
            out['cluster'] = ''
        self._upgrade_last = out                         # 보고서 저장용 — 화면이 본 그 결과로 만든다
        return out

    def upgrade_check_filename(self) -> str:
        from datetime import datetime
        import re
        last = getattr(self, '_upgrade_last', None) or {}
        # Windows 파일 이름에 못 쓰는 글자는 빼고, 공백은 '-'(보고서 저장과 같은 규칙)
        label = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', str(last.get('cluster') or ''))
        label = re.sub(r'\s+', '-', label).strip('-. ')[:40]
        stamp = datetime.now().strftime('%Y-%m-%d')
        return f'Polaris-upgrade-check-{label}-{stamp}.docx' if label else f'Polaris-upgrade-check-{stamp}.docx'

    def upgrade_check_save(self, path: str) -> dict:
        from src.docxreport import meta_defaults
        last = getattr(self, '_upgrade_last', None)
        if not last:
            return {'ok': False, 'error': '먼저 점검을 실행하세요'}
        if not path:
            return {'ok': False, 'error': '저장할 파일을 고르세요'}
        try:
            out = UC.write_docx(last, meta_defaults(), str(path))
        except ImportError:
            return {'ok': False, 'error': 'DOCX 를 만들 모듈(python-docx)이 이 빌드에 없습니다'}
        except PermissionError:
            return {'ok': False, 'error': '파일을 쓸 수 없습니다 — Word 에서 열려 있으면 닫고 다시 저장하세요'}
        except Exception as e:
            return {'ok': False, 'error': f'저장하지 못했습니다: {type(e).__name__}: {e}'}
        return {'ok': True, 'path': out}
