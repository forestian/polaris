"""APIBase — PolarisAPI 의 공유 상태 + 클러스터/세션/설정/검색/연결.

이 클래스는 모든 mixin 의 MRO 종착점이 됩니다. PolarisAPI 의 __init__,
공유 인스턴스 속성 (self.k8s, self._clusters, ...), 그리고 도메인에 묶이지 않는
범용 메서드 (cluster mgmt, session, settings, connect/disconnect, search) 를 보유.
"""
import os
import json
import socket
import shutil
import threading
import urllib.parse
from datetime import datetime
from pathlib import Path

from src.k8s import K8sManager, HAS_K8S, _diagnose_connect_error
if HAS_K8S:
    from kubernetes import config as k8s_cfg


class APIBase:
    def __init__(self):
        # ── 멀티클러스터 관리 ─────────────────────────────────────────────────
        # { cluster_id: {'mgr': K8sManager, 'display_name': str,
        #                'context': str, 'version': str, 'path': str} }
        self._clusters:   dict[str, dict] = {}
        self._active_id:  str | None      = None
        self._cid_seq:    int             = 0          # cluster_id 채번용
        self._null_mgr:   K8sManager      = K8sManager()  # 미연결 시 폴백

        self._window = None   # pywebview window 레퍼런스 (main()에서 주입)


    @property
    def k8s(self) -> K8sManager:
        """현재 활성 클러스터의 K8sManager. 없으면 미연결 센티넬 반환."""
        if self._active_id and self._active_id in self._clusters:
            return self._clusters[self._active_id]['mgr']
        return self._null_mgr


    def _clean(self, rows: list) -> list:
        """내부 키(_로 시작)를 제거하고 JSON-직렬화 가능한 리스트 반환."""
        return [{k: v for k, v in row.items() if not k.startswith('_')}
                for row in (rows or [])]


    def _make_display_name(self, ctx_name: str) -> str:
        """중복 context 이름에 번호 자동 부여. 예: 'default' → 'default (2)'."""
        base = ctx_name or 'cluster'
        existing = {info['display_name'] for info in self._clusters.values()}
        if base not in existing:
            return base
        i = 2
        while f'{base} ({i})' in existing:
            i += 1
        return f'{base} ({i})'


    def get_clusters(self):
        """전체 클러스터 목록 반환."""
        result = []
        for cid, info in self._clusters.items():
            result.append({
                'id':           cid,
                'display_name': info['display_name'],
                'context':      info['context'],
                'version':      info['version'],
                'path':         info['path'],
                'connected':    info['mgr'].connected,
                'active':       cid == self._active_id,
            })
        return result


    def add_cluster(self, path: str, context: str = None):
        """새 클러스터 kubeconfig 연결 후 탭 추가. {ok, cluster_id, display_name, ...} 반환."""
        mgr = K8sManager()
        ok, msg = mgr.connect(path, context=context or None)
        if not ok:
            return {'ok': False, 'error': msg}

        ctx_name     = mgr.cluster_info.get('context', '') or 'cluster'
        display_name = self._make_display_name(ctx_name)

        self._cid_seq += 1
        cluster_id = f'cid-{self._cid_seq}'

        self._clusters[cluster_id] = {
            'mgr':          mgr,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
            'path':         path,
        }
        self._active_id = cluster_id
        return {
            'ok':           True,
            'cluster_id':   cluster_id,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
        }


    def remove_cluster(self, cluster_id: str):
        """클러스터 탭 제거 및 연결 해제."""
        info = self._clusters.pop(cluster_id, None)
        if not info:
            return {'ok': False, 'error': '클러스터를 찾을 수 없습니다.'}
        self._stop_port_forward_jobs_for_cluster(cluster_id)
        try:
            info['mgr'].disconnect()
        except Exception:
            pass
        # 제거 후 활성 클러스터 재조정 (가장 마지막 탭으로)
        if self._active_id == cluster_id:
            remaining = list(self._clusters.keys())
            self._active_id = remaining[-1] if remaining else None
        return {'ok': True}


    def switch_cluster(self, cluster_id: str):
        """활성 클러스터 전환."""
        if cluster_id not in self._clusters:
            return {'ok': False, 'error': '클러스터를 찾을 수 없습니다.'}
        self._active_id = cluster_id
        return {'ok': True}


    def rename_cluster(self, cluster_id: str, name: str):
        """클러스터 표시 이름 변경."""
        info = self._clusters.get(cluster_id)
        if not info:
            return {'ok': False, 'error': '클러스터를 찾을 수 없습니다.'}
        name = (name or '').strip()
        if not name:
            return {'ok': False, 'error': '이름을 입력하세요.'}
        info['display_name'] = name
        return {'ok': True}


    _SESSION_PATH = Path.home() / '.polaris' / 'session.json'


    def _disable_session_persistence(self):
        self._session_save_blocked = True


    def get_session(self):
        """저장된 세션 상태 반환. 없거나 손상 시 None."""
        try:
            if not self._SESSION_PATH.exists():
                return None
            raw = self._SESSION_PATH.read_text(encoding='utf-8')
            data = json.loads(raw)
            # 최소 스키마 검증
            if not isinstance(data, dict):
                return None
            return data
        except Exception:
            return None


    def save_session(self, state):
        """세션 상태 저장. state는 JSON-직렬화 가능한 dict."""
        try:
            if getattr(self, '_session_save_blocked', False):
                return {'ok': True, 'skipped': True}
            if not isinstance(state, dict):
                return {'ok': False, 'error': 'state must be a dict'}
            self._SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._SESSION_PATH.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def clear_session(self):
        """세션 파일 삭제. 로그아웃·초기화용."""
        try:
            if self._SESSION_PATH.exists():
                self._SESSION_PATH.unlink()
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    _SETTINGS_PATH = Path.home() / '.polaris' / 'settings.json'

    _DEFAULT_SETTINGS = {
        'closeBehavior': 'tray',   # 'tray' | 'exit'
        'autoRestore':   True,      # 다음 실행 시 세션 자동 복원
        'themeId':       'polaris', # UI 배경/텍스트 테마
    }

    _THEME_IDS = {'polaris', 'argus', 'aurora', 'forge', 'vault', 'pharos'}

    @classmethod
    def _normalize_theme_id(cls, value):
        return value if value in cls._THEME_IDS else 'polaris'

    @classmethod
    def _normalize_settings(cls, state):
        state = state if isinstance(state, dict) else {}
        return {
            'closeBehavior': 'exit' if state.get('closeBehavior') == 'exit' else 'tray',
            'autoRestore':   bool(state.get('autoRestore', True)),
            'themeId':       cls._normalize_theme_id(state.get('themeId')),
        }


    def _load_settings_raw(self):
        """파일에서 설정 로드 (기본값 fallback). 내부 헬퍼."""
        try:
            if self._SETTINGS_PATH.exists():
                raw = json.loads(self._SETTINGS_PATH.read_text(encoding='utf-8'))
                if isinstance(raw, dict):
                    merged = dict(self._DEFAULT_SETTINGS)
                    merged.update(raw)
                    return self._normalize_settings(merged)
        except Exception:
            pass
        return dict(self._DEFAULT_SETTINGS)


    def get_settings(self):
        """프론트에 노출되는 설정 조회."""
        return self._load_settings_raw()


    def save_settings(self, state):
        """프론트에서 설정 저장. 화이트리스트 키만 수용."""
        try:
            if not isinstance(state, dict):
                return {'ok': False, 'error': 'state must be a dict'}
            clean = self._normalize_settings(state)
            self._SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._SETTINGS_PATH.write_text(
                json.dumps(clean, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            return {'ok': True, 'settings': clean}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def _notify_visibility(self, state):
        """프론트에 윈도우 가시성 변경 알림. state: 'visible' | 'hidden'."""
        if not self._window:
            return
        try:
            js = ("window.dispatchEvent(new CustomEvent('polaris:visibility',"
                  f" {{detail: {json.dumps(state)}}}))")
            self._window.evaluate_js(js)
        except Exception:
            pass


    def _disconnect_all_clusters(self):
        """앱 종료 시 모든 클러스터 정리."""
        try:
            self._stop_port_forward_jobs_for_cluster('')
            for cid, info in list(self._clusters.items()):
                try:
                    mgr = info.get('mgr')
                    if mgr and hasattr(mgr, 'disconnect'):
                        mgr.disconnect()
                except Exception:
                    pass
            self._clusters.clear()
            self._active_id = None
        except Exception:
            pass


    _SEARCH_KINDS = [
        ('nodes',        'Node'),
        ('namespaces',   'Namespace'),
        ('pods',         'Pod'),
        ('deployments',  'Deployment'),
        ('statefulsets', 'StatefulSet'),
        ('daemonsets',   'DaemonSet'),
        ('services',     'Service'),
        ('ingresses',    'Ingress'),
        ('configmaps',   'ConfigMap'),
        ('secrets',      'Secret'),
        ('pvcs',         'PVC'),
        ('pvs',          'PV'),
        ('jobs',         'Job'),
        ('cronjobs',     'CronJob'),
    ]


    def get_search_index(self, force: bool = False):
        """활성 클러스터의 검색용 경량 리소스 인덱스 반환.
        Returns: [{kind, rtype, name, namespace}]
        """
        import time as _time
        mgr = self.k8s
        if not mgr.connected:
            return []

        if not hasattr(self, '_search_cache'):
            self._search_cache = {}
        cache_key = self._active_id or ''
        now = _time.time()
        cached = self._search_cache.get(cache_key)
        if not force and cached and (now - cached['t'] < 30):
            return cached['data']

        idx = []
        for rtype, kind in self._SEARCH_KINDS:
            try:
                items = mgr.get_resources(rtype, None) or []
            except Exception:
                continue
            for item in items:
                name = item.get('name', '')
                if not name:
                    continue
                idx.append({
                    'kind':      kind,
                    'rtype':     rtype,
                    'name':      name,
                    'namespace': item.get('namespace', ''),
                })

        self._search_cache[cache_key] = {'t': now, 'data': idx}
        return idx


    def get_app_version(self):
        # 지연 import (polaris.py 가 src.api 를 import 하는 순환 회피)
        from polaris import VERSION
        return {'version': VERSION}


    def get_status(self):
        mgr = self.k8s
        return {
            'connected': mgr.connected,
            'version':   mgr.cluster_info.get('version', ''),
            'context':   mgr.cluster_info.get('context', ''),
        }


    def connect(self, path: str):
        """하위 호환 — 내부적으로 add_cluster 호출."""
        result = self.add_cluster(path)
        if result.get('ok'):
            return {'ok': True}
        return result


    def disconnect(self):
        """활성 클러스터 제거."""
        if self._active_id:
            return self.remove_cluster(self._active_id)
        return {'ok': True}


    def browse_kubeconfig(self):
        """파일 탐색기로 kubeconfig 선택."""
        if not self._window:
            return None
        try:
            import webview
            # pywebview 6.x: FileDialog.OPEN / 구버전 폴백
            try:
                dialog_type = webview.FileDialog.OPEN
            except AttributeError:
                dialog_type = webview.OPEN_DIALOG  # < 6.x
            result = self._window.create_file_dialog(
                dialog_type,
                directory=os.path.join(os.path.expanduser('~'), '.kube'),
                allow_multiple=False,
                file_types=('YAML files (*.yaml;*.yml)', 'All files (*.*)'),
            )
            return result[0] if result else None
        except Exception:
            return None


    def list_kubeconfig_contexts(self, path: str):
        """kubeconfig 파일의 모든 컨텍스트 목록과 current-context 반환.
        반환: {ok, contexts: [...], current: str}
        """
        try:
            p = Path(path)
            if not p.is_file():
                return {'ok': False, 'error': f'파일을 찾을 수 없습니다: {path}'}
            if p.stat().st_size > 5 * 1024 * 1024:
                return {'ok': False, 'error': 'kubeconfig 파일이 너무 큽니다 (5 MB 초과).'}
            if not HAS_K8S:
                return {'ok': False, 'error': 'kubernetes 패키지가 없습니다.'}
            contexts, active = k8s_cfg.list_kube_config_contexts(config_file=path)
            ctx_names    = [c['name'] for c in (contexts or [])]
            active_name  = (active or {}).get('name', '')
            if not active_name and ctx_names:
                active_name = ctx_names[0]
            return {'ok': True, 'contexts': ctx_names, 'current': active_name}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

