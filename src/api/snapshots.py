"""SnapshotsMixin — 클러스터 스냅샷 저장 / 목록 / Diff (운영 점검 코어 기능).

_report_collect() 로 클러스터 전체 상태를 수집해 시점별 JSON 으로 저장하고,
두 시점을 비교(diff)해 변화 + 이슈 추이를 보여준다.

주의: 이 파일은 src/api/ 의 코어 모듈 목록(_CORE_MODULE_NAMES)에 등록되어야
plugin 자동 발견에서 옵셔널로 잡히지 않는다. (운영 점검은 Polaris 정체성 = 코어)
"""
from src.reports import _report_collect, _report_evaluate
from src.snapshot import (
    save_snapshot, list_snapshots, load_snapshot, delete_snapshot,
    diff_snapshots, diff_findings,
)


class SnapshotsMixin:
    def _snapshot_vault(self):
        """스냅샷 암복호화용 vault 인스턴스 (crypto 미사용 빌드면 None)."""
        try:
            return self._vault()   # VaultMixin 제공 (코어)
        except Exception:
            return None

    def take_snapshot(self, label: str = '') -> dict:
        """현재 활성 클러스터 상태를 수집해 (암호화) 스냅샷으로 저장."""
        if not self.k8s.connected:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        try:
            data = _report_collect(self.k8s, lambda _msg: None)
            # 진단 finding 도 함께 저장 (나중에 이슈 추이 비교용)
            try:
                data['_findings'] = _report_evaluate(data)
            except Exception:
                data['_findings'] = []
            cluster = (self.k8s.cluster_info.get('context')
                       or self._active_cluster_name() or 'cluster')
            return save_snapshot(data, cluster, label, vault=self._snapshot_vault())
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def _active_cluster_name(self) -> str:
        info = self._clusters.get(self._active_id or '', {})
        return info.get('display_name', '')

    def list_snapshots(self) -> dict:
        """저장된 스냅샷 목록."""
        try:
            return {'ok': True, 'items': list_snapshots()}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'items': []}

    def delete_snapshot(self, sid: str) -> dict:
        return {'ok': delete_snapshot(sid)}

    def diff_snapshots(self, id_a: str, id_b: str) -> dict:
        """두 스냅샷 비교. a=이전(기준), b=이후."""
        v = self._snapshot_vault()
        pa = load_snapshot(id_a, vault=v)
        pb = load_snapshot(id_b, vault=v)
        if pa is None or pb is None:
            return {'ok': False, 'error': '스냅샷을 찾을 수 없습니다 (또는 vault 잠김).'}
        try:
            result = diff_snapshots(pa, pb)
            # 이슈 추이 (저장된 _findings 사용; 없으면 즉석 평가)
            fa = pa.get('data', {}).get('_findings') or []
            fb = pb.get('data', {}).get('_findings') or []
            result['finding_delta'] = diff_findings(fa, fb)
            result['ok'] = True
            return result
        except Exception as e:
            return {'ok': False, 'error': str(e)}
