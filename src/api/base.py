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
from src.paths import polaris_dir
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


    # kubeconfig vault 키 접두사 (VaultMixin._KCFG_PREFIX 와 동일하게 유지)
    _KCFG_PREFIX = 'kubeconfig.'

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
                'kc_name':      info.get('kc_name'),   # vault 보관 키 (v1.2.1)
                'connected':    info['mgr'].connected,
                'active':       cid == self._active_id,
            })
        return result


    def _persist_kubeconfig_to_vault(self, kc_name: str, path: str):
        """kubeconfig 파일 내용을 vault 에 보관 (파일 의존 제거).

        vault 가 비활성(평문 빌드)이거나 잠겨 있으면 조용히 None 반환 →
        기존처럼 파일 경로 기반으로만 동작. 반환: 저장 성공 시 kc_name."""
        try:
            vault_fn = getattr(self, '_vault', None)
            if vault_fn is None:
                return None
            v = vault_fn()
            if v is None or not v.is_unlocked:
                return None
            content = Path(path).read_text(encoding='utf-8')
            v.store(self._KCFG_PREFIX + kc_name, content)
            return kc_name
        except Exception:
            return None


    def add_cluster(self, path: str, context: str = None):
        """새 클러스터 kubeconfig 연결 후 탭 추가. {ok, cluster_id, display_name, ...} 반환.

        연결 성공 시 kubeconfig 내용을 vault 에 보관 (kc_name) → 다음 실행부터는
        원본 파일 없이도 add_cluster_from_vault 로 복원 가능."""
        mgr = K8sManager()
        ok, msg = mgr.connect(path, context=context or None)
        if not ok:
            return {'ok': False, 'error': msg}

        ctx_name     = mgr.cluster_info.get('context', '') or 'cluster'
        display_name = self._make_display_name(ctx_name)

        self._cid_seq += 1
        cluster_id = f'cid-{self._cid_seq}'

        kc_name = self._persist_kubeconfig_to_vault(display_name, path)

        self._clusters[cluster_id] = {
            'mgr':          mgr,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
            'path':         path,
            'kc_name':      kc_name,
        }
        self._active_id = cluster_id
        return {
            'ok':           True,
            'cluster_id':   cluster_id,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
            'kc_name':      kc_name,
        }


    def add_cluster_from_vault(self, kc_name: str, context: str = None):
        """vault 에 보관된 kubeconfig 내용으로 클러스터 연결 (원본 파일 불필요).

        세션 복원 시 사용. vault 잠김/내용 없음/연결 실패는 명시적 에러 반환."""
        vault_fn = getattr(self, '_vault', None)
        if vault_fn is None:
            return {'ok': False, 'error': 'vault 를 사용할 수 없습니다.'}
        try:
            v = vault_fn()
            if v is None or not v.is_unlocked:
                return {'ok': False, 'error': 'vault 가 잠겨 있습니다.', 'need_unlock': True}
            key = self._KCFG_PREFIX + (kc_name or '')
            if not v.has(key):
                return {'ok': False, 'error': '보관된 kubeconfig 가 없습니다.', 'missing': True}
            content = v.retrieve(key)
        except Exception as e:
            return {'ok': False, 'error': str(e)}

        mgr = K8sManager()
        ok, msg = mgr.connect(context=context or None, content=content)
        if not ok:
            return {'ok': False, 'error': msg}

        ctx_name     = mgr.cluster_info.get('context', '') or (kc_name or 'cluster')
        display_name = self._make_display_name(ctx_name)

        self._cid_seq += 1
        cluster_id = f'cid-{self._cid_seq}'

        self._clusters[cluster_id] = {
            'mgr':          mgr,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
            'path':         '',           # vault 기반 — 원본 파일 경로 없음
            'kc_name':      kc_name,
        }
        self._active_id = cluster_id
        return {
            'ok':           True,
            'cluster_id':   cluster_id,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
            'kc_name':      kc_name,
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


    _SESSION_PATH = polaris_dir() / 'session.json'


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


    _SETTINGS_PATH = polaris_dir() / 'settings.json'

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


    def get_enabled_features(self):
        """프론트가 어떤 옵셔널 플러그인이 활성인지 알아야 ModeSwitcher 등을
        조건부 표시할 수 있다. ENABLED_FEATURES 는 src.api 모듈 로드 시 자동
        발견된 옵셔널 mixin 의 ID 튜플."""
        from src.api import ENABLED_FEATURES
        return {'features': list(ENABLED_FEATURES)}


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


    # ── 데이터 디렉터리 위치 (v1.2.2) ───────────────────────────────────────
    def browse_folder(self, start: str = None):
        """폴더 선택 다이얼로그. 선택 경로 문자열 또는 None."""
        if not self._window:
            return None
        try:
            import webview
            try:
                dialog_type = webview.FileDialog.FOLDER
            except AttributeError:
                dialog_type = webview.FOLDER_DIALOG  # < 6.x
            result = self._window.create_file_dialog(
                dialog_type,
                directory=start or os.path.expanduser('~'),
                allow_multiple=False,
            )
            if not result:
                return None
            return result[0] if isinstance(result, (list, tuple)) else result
        except Exception:
            return None


    def get_data_dir(self):
        """현재 데이터 디렉터리 위치 반환."""
        from src import paths
        cur = paths.polaris_dir()
        return {
            'ok': True,
            'path': str(cur),
            'default': str(paths.DEFAULT_DIR),
            'is_default': cur.resolve() == paths.DEFAULT_DIR.resolve(),
        }


    def change_data_dir(self, new_path: str):
        """데이터 디렉터리 위치 변경.

        현재 위치의 파일을 새 위치로 **복사**하고 포인터(location.json)를 갱신한다.
        기존 폴더는 삭제하지 않으며(권한 이슈 회피), 변경은 재시작 후 반영된다.
        반환: {ok, old_dir, new_dir, copied, needs_restart} 또는 {ok: False, error}
        """
        import shutil
        from src import paths
        try:
            if not new_path or not str(new_path).strip():
                return {'ok': False, 'error': '경로를 입력하세요.'}
            cur = paths.polaris_dir().resolve()
            new_dir = Path(str(new_path)).expanduser()
            try:
                new_res = new_dir.resolve()
            except Exception:
                new_res = new_dir
            if new_res == cur:
                return {'ok': False, 'error': '현재 위치와 동일합니다.'}
            # 상호 포함 관계 금지 (copytree 무한 재귀 방지)
            cs, ns = str(cur), str(new_res)
            if ns.startswith(cs + os.sep) or cs.startswith(ns + os.sep):
                return {'ok': False, 'error': '현재 폴더의 상위/하위 경로는 선택할 수 없습니다.'}
            # 새 위치에 이미 polaris 데이터가 있으면 덮어쓰기 방지
            for marker in ('vault.json', 'session.json', 'settings.json'):
                if (new_dir / marker).exists():
                    return {'ok': False,
                            'error': f'대상 폴더에 이미 Polaris 데이터({marker})가 있습니다. 빈 폴더를 선택하세요.'}
            new_dir.mkdir(parents=True, exist_ok=True)
            # 복사 (location.json 포인터는 제외 — 기본 폴더에만 존재)
            copied = []
            if cur.exists():
                for item in Path(cur).iterdir():
                    if item.name == 'location.json':
                        continue
                    dest = new_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
                    copied.append(item.name)
            # 포인터 갱신 (재시작 시 새 위치 사용)
            paths.write_pointer(new_dir)
            return {
                'ok': True,
                'old_dir': str(cur),
                'new_dir': str(new_dir),
                'copied': copied,
                'needs_restart': True,
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}


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

