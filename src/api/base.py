"""APIBase — PolarisAPI 의 공유 상태 + 클러스터/세션/설정/검색/연결.

이 클래스는 모든 mixin 의 MRO 종착점이 됩니다. PolarisAPI 의 __init__,
공유 인스턴스 속성 (self.k8s, self._clusters, ...), 그리고 도메인에 묶이지 않는
범용 메서드 (cluster mgmt, session, settings, connect/disconnect, search) 를 보유.
"""
import ctypes
import os
import re
import json
import socket
import shutil
import threading
import urllib.parse
from datetime import datetime
from pathlib import Path

from src.k8s import K8sManager, HAS_K8S, _diagnose_connect_error
from src.k8s import k8s_cfg            # 처음 쓸 때 불러오는 대리자 (v1.3.73)
from src.paths import polaris_dir


# 창 최소 크기 — create_window 의 min_size 와 같은 값을 유지한다.
# (프론트의 리사이즈 핸들 MIN_W/MIN_H 와도 같아야 한다)
MIN_WINDOW_W = 960
MIN_WINDOW_H = 640

# ── Win32 전용 핸들 ──────────────────────────────────────────────────────────
_USER32 = None


def _user32():
    """argtypes 를 마음대로 지정하기 위한 **우리 전용** user32 핸들.

    ⚠ `ctypes.windll.user32` 를 쓰면 안 된다. 그것은 프로세스 전역 캐시라
    거기에 argtypes 를 지정하면 **같은 프로세스의 다른 사용자 호출까지** 규칙이
    바뀐다. 실제로 pywebview 의 창 이동은 이렇게 부른다:

        windll.user32.SetWindowPos(hwnd, None, x, y, None, None, flags)
                                                    ^^^^  ^^^^  cx, cy 가 None

    우리가 그 자리를 c_int 로 못박아 두면 None 이 들어올 때 ArgumentError 가 나
    **본창·분리 창을 포함한 모든 창 드래그가 프로세스 전체에서 죽는다.**
    v1.2.146~149 에서 실제로 그랬다 — 핀을 한 번 누르면 그때부터 창이 안 움직였다.

    전용 WinDLL 인스턴스는 함수 객체가 별도라 여기서 무엇을 지정하든 남에게
    영향이 없다.
    """
    global _USER32
    if _USER32 is None:
        import ctypes
        _USER32 = ctypes.WinDLL('user32')
    return _USER32


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
        self._maximized = False            # 커스텀 타이틀바 최대화 토글 상태
        self._saved_bounds = None          # 최대화 전 창 위치/크기 (복원용)
        self._on_quit_request = None       # 닫기(exit) 시 종료 콜백 (main()에서 주입)


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

    def _active_cluster_name(self) -> str:
        """현재 활성 클러스터의 **사용자에게 보이는 이름** (보관함에 저장한 그 이름).

        `_clusters`/`_active_id` 가 여기(APIBase) 상태이므로 헬퍼도 여기 둔다 —
        스냅샷·YAML 실험실 등 여러 mixin 이 공유한다.
        """
        info = self._clusters.get(self._active_id or '', {})
        return info.get('display_name', '')

    def _cluster_label(self, fallback: str = 'cluster') -> str:
        """저장물(스냅샷·매니페스트)에 남길 클러스터 표기.

        **display_name 이 우선이다.** kubeconfig 의 context 이름을 앞에 두면 안 된다 —
        RKE2 가 만드는 kubeconfig 는 context 가 죄다 `default` 라, 클러스터가 몇 개든
        전부 'default' 로 저장돼 목록에서 구분이 안 됐다(v1.2.128 에서 수정).
        display_name 은 사용자가 보관함에서 붙인(그리고 바꿀 수 있는) 이름이다.
        """
        try:
            ctx = (self.k8s.cluster_info or {}).get('context', '')
        except Exception:
            ctx = ''
        return self._active_cluster_name() or ctx or fallback


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


    def get_multicluster_summary(self):
        """연결된 모든 클러스터의 핵심 카운트를 병렬 집계 (멀티클러스터 집계 뷰).

        각 클러스터는 독립 K8sManager(별도 ApiClient)이므로 스레드로 병렬 수집한다.
        큰 클러스터에서 파드 전수 조회는 비용이 있으나 사용자 트리거(온디맨드)라 허용.
        반환: {ok, clusters:[{id,display_name,version,active,connected,nodes,pods,error?}], totals}
        """
        import concurrent.futures as _cf

        items = list(self._clusters.items())

        def _one(pair):
            cid, info = pair
            mgr = info.get('mgr')
            row = {
                'id': cid, 'display_name': info.get('display_name'),
                'context': info.get('context', ''), 'version': info.get('version', ''),
                'kc_name': info.get('kc_name'), 'active': cid == self._active_id,
                'connected': bool(getattr(mgr, 'connected', False)),
                'nodes': {}, 'pods': {},
            }
            if mgr is None or not row['connected']:
                row['error'] = '연결 안 됨'
                return row
            try:
                nodes = mgr.get_nodes() or []
                pods = mgr.get_pods() or []
                row['nodes'] = {
                    'total': len(nodes),
                    'ready': sum(1 for n in nodes if n.get('status') == 'Ready'),
                }
                row['pods'] = {
                    'total': len(pods),
                    'notReady': sum(1 for p in pods
                                    if p.get('status') not in ('Running', 'Succeeded')),
                }
            except Exception as e:
                row['error'] = str(e)[:200]
            return row

        rows = []
        if items:
            workers = min(8, len(items))
            with _cf.ThreadPoolExecutor(max_workers=workers) as ex:
                rows = list(ex.map(_one, items))
        # 활성 클러스터 먼저 + 이름 오름차순
        rows.sort(key=lambda r: (not r.get('active'), (r.get('display_name') or '').lower()))

        def _sum(key, sub):
            return sum((r.get(key) or {}).get(sub, 0) for r in rows)

        totals = {
            'clusters':       len(rows),
            'connected':      sum(1 for r in rows if r.get('connected')),
            'nodes':          _sum('nodes', 'total'),
            'nodes_ready':    _sum('nodes', 'ready'),
            'pods':           _sum('pods', 'total'),
            'pods_not_ready': _sum('pods', 'notReady'),
        }
        return {'ok': True, 'clusters': rows, 'totals': totals}


    def _minify_kubeconfig(self, path: str, context: str = None):
        """선택한 context 하나만 남긴 단일-context kubeconfig 문자열을 반환.

        멀티 context 파일이라도 실제로 연(선택한) context 와 그 cluster/user 만 보관하기
        위함. context=None 이면 current-context 기준. 실패 시 None(→ 호출부가 전체 저장).
        """
        # 1) kubectl config view --minify --flatten (가장 견고; cert 까지 임베드)
        try:
            from src.tools import _run_kubectl, _find_kubectl
            if _find_kubectl():
                args = ['config', 'view', '--minify', '--flatten']
                if context:
                    args += ['--context', context]
                out, _err = _run_kubectl(path, args, timeout=15)
                if out and 'apiVersion' in out and 'clusters' in out:
                    return out
        except Exception:
            pass
        # 2) 순수 파이썬 minify (flatten 없음 — 인라인 cert 인 경우 자체 완결)
        try:
            import yaml
            cfg = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
            cur = context or cfg.get('current-context')
            ctx = next((c for c in cfg.get('contexts', []) if c.get('name') == cur), None)
            if not ctx:
                return None
            cl_name = (ctx.get('context') or {}).get('cluster')
            us_name = (ctx.get('context') or {}).get('user')
            cl = next((c for c in cfg.get('clusters', []) if c.get('name') == cl_name), None)
            us = next((u for u in cfg.get('users', []) if u.get('name') == us_name), None)
            mini = {
                'apiVersion': cfg.get('apiVersion', 'v1'), 'kind': 'Config',
                'clusters': [cl] if cl else [], 'users': [us] if us else [],
                'contexts': [ctx], 'current-context': cur, 'preferences': {},
            }
            return yaml.safe_dump(mini, default_flow_style=False, sort_keys=False,
                                  allow_unicode=True)
        except Exception:
            return None

    def _persist_kubeconfig_to_vault(self, kc_name: str, path: str, context: str = None):
        """연결한 kubeconfig 를 vault 에 보관 (파일 의존 제거).

        context 가 주어지면 그 context 하나만 minify 해서 저장(멀티 context 중 실제로
        연 것만). minify 실패 시 전체 파일 저장. vault 가 비활성(평문 빌드)이거나 잠겨
        있으면 조용히 None 반환 → 기존처럼 파일 경로 기반으로만 동작.
        반환: 저장 성공 시 kc_name."""
        try:
            vault_fn = getattr(self, '_vault', None)
            if vault_fn is None:
                return None
            v = vault_fn()
            if v is None or not v.is_unlocked:
                return None
            content = self._minify_kubeconfig(path, context) if path else None
            if not content:
                content = Path(path).read_text(encoding='utf-8')   # 폴백: 전체 저장
            v.store(self._KCFG_PREFIX + kc_name, content)
            return kc_name
        except Exception:
            return None


    def _ensure_kubectl_async(self):
        """kubectl 이 없으면 백그라운드로 1회 자동 설치(다운로드). best-effort · 조용히.

        클러스터 연결 직후 호출 — fresh PC(시스템 kubectl 없음)에서도 곧 파드 YAML 보기·describe·
        kubectl 터미널·파드 셸·Helm 이 동작하도록 ~/.kube/kubectl.exe 를 받아둔다(설치본 번들 X).
        이미 kubectl 이 있거나 이번 세션에 이미 시도했으면 skip. install_kubectl 은 TerminalMixin(코어).
        """
        if getattr(self, '_kubectl_install_tried', False):
            return
        self._kubectl_install_tried = True
        try:
            from src.tools import _find_kubectl
            if _find_kubectl():
                return   # 시스템/기존 kubectl 있음 — 받을 필요 없음
        except Exception:
            return

        def _run():
            try:
                self.install_kubectl()
            except Exception:
                pass

        try:
            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            pass


    def add_cluster(self, path: str, context: str = None, name: str = None):
        """새 클러스터 kubeconfig 연결 후 탭 추가. {ok, cluster_id, display_name, ...} 반환.

        name 이 주어지면 표시 이름·vault 키로 사용 (설치 시 사용자가 지정한 Polaris
        클러스터 이름). 미지정이면 kubeconfig 의 context 이름 — RKE2 는 context 가 항상
        'default' 라 이름이 전부 'default' 로 뭉친다. 설치 경로에서는 반드시 name 을 넘긴다.

        연결 성공 시 kubeconfig 내용을 vault 에 보관 (kc_name) → 다음 실행부터는
        원본 파일 없이도 add_cluster_from_vault 로 복원 가능."""
        mgr = K8sManager()
        ok, msg = mgr.connect(path, context=context or None)
        if not ok:
            return {'ok': False, 'error': msg}

        ctx_name     = mgr.cluster_info.get('context', '') or 'cluster'
        base_name    = (name or '').strip() or ctx_name
        display_name = self._make_display_name(base_name)

        self._cid_seq += 1
        cluster_id = f'cid-{self._cid_seq}'

        # 선택해서 연 context 만 minify 해서 보관 (context 미지정이면 current-context)
        kc_name = self._persist_kubeconfig_to_vault(display_name, path, context)

        self._clusters[cluster_id] = {
            'mgr':          mgr,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
            'path':         path,
            'kc_name':      kc_name,
            'req_context':  context or None,
        }
        self._active_id = cluster_id
        self._ensure_kubectl_async()   # kubectl 없으면 백그라운드 자동 설치 (1회)
        self._prewarm_search_index_async(cluster_id, mgr)   # 팔레트 첫 오픈 지연 제거
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
        # v1.5.23 — 같은 보관본(kc_name) · 같은 context 가 이미 연결돼 있으면 그것을 쓴다.
        # 같은 것을 또 연결하면 「이름 (2)」 로 둘이 생기던 문제(세션 복원과 같은 키).
        for cid, info in self._clusters.items():
            if info.get('kc_name') == kc_name and kc_name and (info.get('req_context') or None) == (context or None) \
                    and getattr(info.get('mgr'), 'connected', False):
                self._active_id = cid
                return {'ok': True, 'cluster_id': cid, 'display_name': info['display_name'], 'context': info.get('context', ''),
                        'version': info.get('version', ''), 'kc_name': kc_name, 'reused': True}
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

        ctx_name = mgr.cluster_info.get('context', '') or (kc_name or 'cluster')
        # ★ 표시 이름 = 보관함에 저장된 이름(kc_name = 사용자가 지정한 이름).
        #   kubeconfig 의 context 이름('default')으로 재유도하면 재연결할 때마다 사용자가
        #   바꾼 이름이 'default (2)' 로 되돌아가고, 그 값이 세션→복원 경로로 vault 이름까지
        #   덮어쓰는 연쇄가 생긴다. 저장된 이름을 그대로 표시 이름으로 쓴다.
        display_name = self._make_display_name(kc_name or ctx_name)

        self._cid_seq += 1
        cluster_id = f'cid-{self._cid_seq}'

        self._clusters[cluster_id] = {
            'mgr':          mgr,
            'display_name': display_name,
            'context':      ctx_name,
            'version':      mgr.cluster_info.get('version', ''),
            'path':         '',           # vault 기반 — 원본 파일 경로 없음
            'kc_name':      kc_name,
            'req_context':  context or None,   # 연결할 때 고른 context — 같은 연결인지 가리는 키(v1.5.23)
        }
        self._active_id = cluster_id
        self._ensure_kubectl_async()   # kubectl 없으면 백그라운드 자동 설치 (1회)
        self._prewarm_search_index_async(cluster_id, mgr)   # 팔레트 첫 오픈 지연 제거
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
        self._stop_kubectl_stream_procs_for_cluster(cluster_id)
        try:
            self._stop_log_streams_for_kubeconfig(getattr(info['mgr'], 'kubeconfig', '') or '')
        except Exception:
            pass
        try:
            info['mgr'].disconnect()
        except Exception:
            pass
        # 알림 감시의 클러스터별 baseline 정리 (재연결 시 다시 기준선부터)
        if hasattr(self, '_polaris_notif_watcher'):
            try: self._polaris_notif_watcher.forget_cluster(cluster_id)
            except Exception: pass
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
        """클러스터 표시 이름 변경 + vault 보관 항목 이름도 함께 이전.

        보관된 kubeconfig 가 있으면 vault 키를 새 이름으로 옮기고(기존 데이터 → 새 이름
        덮어쓰기) 같은 보관본을 참조하는 모든 탭의 kc_name 을 갱신한다. 새 이름이 다른
        보관 항목과 충돌하면 변경을 거부하고 에러를 반환한다(표시 이름도 바꾸지 않음)."""
        info = self._clusters.get(cluster_id)
        if not info:
            return {'ok': False, 'error': '클러스터를 찾을 수 없습니다.'}
        name = (name or '').strip()
        if not name:
            return {'ok': False, 'error': '이름을 입력하세요.'}

        old_kc = info.get('kc_name')
        if old_kc and old_kc != name:
            rename_fn = getattr(self, 'rename_kubeconfig', None)
            vault_fn = getattr(self, '_vault', None)
            v = vault_fn() if vault_fn else None
            if rename_fn is not None and v is not None and v.is_unlocked \
                    and v.has(self._KCFG_PREFIX + old_kc):
                res = rename_fn(old_kc, name)
                if not res.get('ok'):
                    return res   # 충돌/오류 → rename 거부 (표시 이름 유지)
                # 같은 보관본을 가리키는 모든 탭의 kc_name 동기화 (재시작 복원 댕글링 방지)
                for cinfo in self._clusters.values():
                    if cinfo.get('kc_name') == old_kc:
                        cinfo['kc_name'] = name

        info['display_name'] = name
        return {'ok': True, 'kc_name': info.get('kc_name')}


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
        'notifications': {},        # 이벤트→트레이/웹훅 알림 (v1.2.113)
        'security':      {},        # 잠금 관련 (v1.2.167 Windows Hello 요구 여부)
    }

    #: 고를 수 있는 테마 id. **ui/src/themeRegistry.js 의 THEME_IDS 와 같아야 한다** —
    #: 여기 없으면 save_settings 가 조용히 'polaris' 로 되돌린다(v1.3.34 에서 겪음).
    _THEME_IDS = {'polaris', 'argus', 'aurora', 'forge', 'vault', 'pharos',
                  'forestia', 'custom'}

    @classmethod
    def _normalize_theme_id(cls, value):
        return value if value in cls._THEME_IDS else 'polaris'

    @staticmethod
    def _valid_hex_color(c):
        return (isinstance(c, str) and len(c) == 7 and c[0] == '#'
                and all(ch in '0123456789abcdefABCDEF' for ch in c[1:]))

    @classmethod
    def _normalize_notifications(cls, n):
        """알림 설정 검증 — enabled/tray/webhookUrl 만 수용. 잘못된 URL 은 저장하지
        않는다(무음 실패 방지 — 저장은 되는데 안 쓰이는 값이 남는 걸 막음)."""
        n = n if isinstance(n, dict) else {}
        url = str(n.get('webhookUrl', '') or '').strip()
        if url:
            from urllib.parse import urlparse
            p = urlparse(url)
            if p.scheme not in ('http', 'https') or not p.netloc:
                url = ''
        return {
            'enabled':    bool(n.get('enabled', False)),
            'tray':       bool(n.get('tray', True)),
            'webhookUrl': url[:500],
        }

    @classmethod
    def _normalize_settings(cls, state):
        state = state if isinstance(state, dict) else {}
        return {
            'closeBehavior': 'exit' if state.get('closeBehavior') == 'exit' else 'tray',
            'autoRestore':   bool(state.get('autoRestore', True)),
            'themeId':       cls._normalize_theme_id(state.get('themeId')),
            'customTheme':   cls._normalize_custom_theme(state.get('customTheme')),
            'notifications': cls._normalize_notifications(state.get('notifications')),
            'security':      cls._normalize_security(state.get('security')),
        }

    @staticmethod
    def _dropped_settings_keys(state, clean):
        """보낸 설정 중 정규화가 버린 키 경로(두 단계까지). customTheme.overrides 는 토큰 거르기라 뺀다."""
        out = []
        if not isinstance(state, dict):
            return out
        for k, v in state.items():
            if k not in clean:
                out.append(k)
            elif isinstance(v, dict) and isinstance(clean[k], dict):
                # 빈 값은 원래 생략하는 키가 있다
                out += [f'{k}.{s}' for s, x in v.items() if s not in clean[k] and x not in (None, '', [])]
        return sorted(out)

    #: 커스텀 테마에서 직접 덮어쓸 수 있는 토큰 (v1.3.34).
    #: 화이트리스트로 두는 이유는 두 가지다 — 아무 CSS 변수나 심지 않기 위해서,
    #: 그리고 화면이 쓰는 토큰이 늘어날 때 여기도 같이 늘리라고 강제하기 위해서.
    _CUSTOM_TOKENS = (
        '--bg-0', '--bg-1', '--bg-2', '--bg-3', '--bg-4', '--bg-5',
        '--border', '--border-bright',
        '--text', '--text-bright', '--text-mid', '--text-dim',
        '--nimbus', '--nimbus-dark', '--nimbus-dim', '--accent-ink',
        '--green', '--green-bg', '--yellow', '--yellow-bg',
        '--red', '--red-bg', '--blue', '--blue-bg', '--purple',
    )

    @staticmethod
    def _hex_or(value, fallback):
        """'#rgb'·'#rrggbb' 만 통과. 아니면 기본값."""
        s = str(value or '').strip()
        if re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})', s):
            return s.lower()
        return fallback

    @classmethod
    def _normalize_custom_theme(cls, cfg):
        """커스텀 테마 색 (v1.3.34).

        화이트리스트에 넣지 않으면 save_settings 가 이 값을 **조용히 버린다** —
        저장은 성공했다고 나오고 다음 실행에서 색이 사라진다(이 저장소에서 세 번
        겪은 사고다).
        """
        cfg = cfg if isinstance(cfg, dict) else {}
        raw_ov = cfg.get('overrides')
        overrides = {}
        if isinstance(raw_ov, dict):
            for k, v in raw_ov.items():
                if k in cls._CUSTOM_TOKENS:
                    hexv = cls._hex_or(v, None)
                    if hexv:
                        overrides[k] = hexv
        return {
            'bg':     cls._hex_or(cfg.get('bg'), '#f4f1e8'),
            'text':   cls._hex_or(cfg.get('text'), '#201d17'),
            'accent': cls._hex_or(cfg.get('accent'), '#a9741a'),
            'overrides': overrides,
        }

    @classmethod
    def _normalize_security(cls, sec):
        """잠금 관련 설정 (v1.2.167). 지금은 Hello 요구 여부 하나.

        화이트리스트에 넣지 않으면 save_settings 가 이 값을 **조용히 버린다** —
        저장은 성공했다고 나오고 다음 실행에서 설정이 사라진다.
        """
        sec = sec if isinstance(sec, dict) else {}
        return {'require_hello': bool(sec.get('require_hello'))}


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

    # ── 창 컨트롤 (frameless 커스텀 타이틀바) ──────────────────────────────
    def window_minimize(self):
        try:
            if self._window:
                self._window.minimize()
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def enable_taskbar_minimize(self) -> dict:
        """작업표시줄 아이콘을 눌러 **최소화·복원**되게 한다 (v1.3.24, 사용자 신고).

        윈도우는 작업표시줄 버튼으로 창을 내릴 수 있는지를 **`WS_MINIMIZEBOX` 스타일**로
        판단한다. 이 창은 `frameless=True` 라 pywebview 가 그 비트를 켜지 않고, 그래서
        아이콘을 눌러도 앞으로 나오기만 하고 다시 눌러도 안 내려갔다.
        (실행 중인 v1.3.22 창에서 확인: style=0x36010000 → MINIMIZEBOX 꺼짐)

        캡션(`WS_CAPTION`)은 **건드리지 않는다** — 그것을 켜면 제목표시줄이 그려져
        커스텀 타이틀바와 겹친다. MINIMIZEBOX·SYSMENU 는 테두리 없는 창에서 아무것도
        그리지 않는다(적용 전후 창·클라이언트 크기가 그대로인 것을 실측으로 확인).
        """
        win = self._window
        if not win:
            return {'ok': False, 'error': '창이 아직 준비되지 않았습니다.'}
        hwnd = self._win_hwnd_by_title(getattr(win, 'title', '') or '')
        if not hwnd:
            return {'ok': False, 'error': '창을 찾지 못했습니다.'}
        try:
            user32 = _user32()
            GWL_STYLE = -16
            WS_MINIMIZEBOX, WS_SYSMENU = 0x00020000, 0x00080000
            SWP_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020  # NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED
            get_l = getattr(user32, 'GetWindowLongPtrW', user32.GetWindowLongW)
            set_l = getattr(user32, 'SetWindowLongPtrW', user32.SetWindowLongW)
            get_l.restype = ctypes.c_ssize_t
            set_l.restype = ctypes.c_ssize_t
            get_l.argtypes = [ctypes.c_void_p, ctypes.c_int]
            set_l.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
            style = get_l(hwnd, GWL_STYLE)
            want = style | WS_MINIMIZEBOX | WS_SYSMENU
            if style == want:
                return {'ok': True, 'changed': False}
            set_l(hwnd, GWL_STYLE, want)
            # 스타일을 바꾼 뒤에는 프레임을 다시 계산하라고 알려야 반영된다
            user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                            ctypes.c_int, ctypes.c_int,
                                            ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_FLAGS)
            return {'ok': True, 'changed': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def _win_hwnd(self):
        """현재 창의 Win32 HWND (제목으로 조회 — 백엔드 무관하게 안정적)."""
        import ctypes
        try:
            title = getattr(self._window, 'title', None)
            if title:
                h = _user32().FindWindowW(None, title)
                if h:
                    return h
        except Exception:
            pass
        try:
            return _user32().GetForegroundWindow()
        except Exception:
            return 0

    @staticmethod
    def _win_hwnd_by_title(title: str):
        """제목으로 HWND 조회 — 보조 창은 self._window 가 아니라 제목으로만 찾는다.

        restype 을 지정하지 않으면 ctypes 가 반환값을 32비트 int 로 자른다.
        64비트 프로세스에서 핸들이 잘리면 이후 SetWindowPos 등이 조용히 실패한다.
        """
        import ctypes
        try:
            fw = _user32().FindWindowW
            fw.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
            fw.restype = ctypes.c_void_p
            return fw(None, title) or 0
        except Exception:
            return 0

    @staticmethod
    def _win_get_rect_for(hwnd):
        """주어진 창의 화면 좌표/크기 (물리 px). 실패 시 None."""
        import ctypes
        from ctypes import wintypes
        if not hwnd:
            return None
        r = wintypes.RECT()
        gwr = _user32().GetWindowRect
        gwr.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)]
        if gwr(hwnd, ctypes.byref(r)):
            return {'x': r.left, 'y': r.top, 'width': r.right - r.left, 'height': r.bottom - r.top}
        return None

    def _win_get_rect(self):
        """본창의 실제 화면 좌표/크기 (물리 px) — GetWindowRect. 실패 시 None."""
        return self._win_get_rect_for(self._win_hwnd())

    @staticmethod
    def _win_set_pos_for(hwnd, x, y, w, h):
        """주어진 창에 위치/크기 적용 (물리 px)."""
        import ctypes
        if not hwnd:
            return False
        SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
        swp = _user32().SetWindowPos
        swp.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                        ctypes.c_uint]
        swp.restype = ctypes.c_bool
        return bool(swp(hwnd, None, int(x), int(y), int(w), int(h),
                        SWP_NOZORDER | SWP_NOACTIVATE))

    def _win_set_pos(self, x, y, w, h):
        """SetWindowPos 로 본창 위치/크기 적용 (물리 px). pywebview move/resize 의 DPI 단위 모호성 회피."""
        return self._win_set_pos_for(self._win_hwnd(), x, y, w, h)

    def _win_workarea(self):
        """본창이 있는 모니터의 작업영역 — (left, top, width, height). 물리 px."""
        return self._win_workarea_for(self._win_hwnd())

    @staticmethod
    def _win_workarea_for(hwnd):
        """주어진 창이 있는 모니터의 작업영역(작업표시줄 제외).

        hwnd 를 받는 이유 — 보조 창은 다른 모니터에 있을 수 있다. 본창 기준으로
        계산하면 최대화할 때 창이 엉뚱한 모니터로 끌려간다.
        """
        import ctypes
        from ctypes import wintypes
        user32 = _user32()

        class MONITORINFO(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                        ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]

        if hwnd:
            user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            user32.MonitorFromWindow.restype = ctypes.c_void_p
            user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
            mon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if mon and user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                r = mi.rcWork
                return (r.left, r.top, r.right - r.left, r.bottom - r.top)
        # 폴백: 주 모니터 작업영역 (SPI_GETWORKAREA)
        r = wintypes.RECT()
        user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)
        return (r.left, r.top, r.right - r.left, r.bottom - r.top)

    def window_toggle_maximize(self):
        """최대화/복원. 네이티브 maximize(작업표시줄 덮음) 대신 '작업영역'으로 맞춘다.
        모든 좌표를 Win32 물리 px(SetWindowPos/GetWindowRect)로 처리 → DPI 배율 무관 일관."""
        try:
            if not self._window:
                return {'ok': False, 'error': 'no window'}
            if self._maximized:
                b = self._saved_bounds
                if b and self._win_set_pos(b['x'], b['y'], b['w'], b['h']):
                    pass
                else:
                    try: self._window.restore()
                    except Exception: pass
                self._maximized = False
            else:
                rect = self._win_get_rect()
                self._saved_bounds = ({'x': rect['x'], 'y': rect['y'],
                                       'w': rect['width'], 'h': rect['height']} if rect else None)
                left, top, ww, hh = self._win_workarea()
                if not self._win_set_pos(left, top, ww, hh):
                    try: self._window.maximize()
                    except Exception: pass
                self._maximized = True
            return {'ok': True, 'maximized': self._maximized}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def window_drag_begin(self, screen_x, screen_y):
        """제목표시줄 드래그 시작 — 최대화 상태면 복원하고 커서 아래로 창을 맞춘다.

        최대화된 채로 다른 모니터로 옮기면 창은 따라오지만 '최대화' 상태와 복원
        기준이 원래 모니터에 남아, 최소화했다가 되돌리면 처음 모니터로 튀어간다.
        브라우저·탐색기가 하는 것처럼 **드래그를 시작하는 순간 복원**해 평범한
        창으로 옮기고, 새 모니터에서 최대화를 다시 누르면 그 모니터를 채우게 한다.

        반환의 grab_x/grab_y 는 '창 좌상단에서 커서까지의 거리'(물리 px)다.
        프론트는 이후 이동 중 창 위치를 (커서 - grab) 으로만 계산하면 된다.
        """
        rect = self._win_get_rect()
        if not rect:
            return {'ok': False, 'error': 'no hwnd'}
        sx, sy = int(screen_x), int(screen_y)

        if not self._maximized:
            return {'ok': True, 'restored': False,
                    'x': rect['x'], 'y': rect['y'],
                    'width': rect['width'], 'height': rect['height'],
                    'grab_x': sx - rect['x'], 'grab_y': sy - rect['y']}

        b = self._saved_bounds or {}
        rw = int(b.get('w') or max(MIN_WINDOW_W, rect['width'] // 2))
        rh = int(b.get('h') or max(MIN_WINDOW_H, rect['height'] // 2))
        ox, oy = sx - rect['x'], sy - rect['y']
        # 가로는 비율로 옮긴다 — 오른쪽 끝을 잡고 드래그했으면 복원 뒤에도
        # 오른쪽 끝을 잡고 있어야 창이 커서 왼쪽으로 튀지 않는다.
        gx = int(ox * rw / max(1, rect['width']))
        gy = min(oy, max(0, rh - 1))       # 세로는 그대로(제목표시줄은 맨 위)
        nx, ny = sx - gx, sy - gy
        self._win_set_pos(nx, ny, rw, rh)
        self._maximized = False
        return {'ok': True, 'restored': True,
                'x': nx, 'y': ny, 'width': rw, 'height': rh,
                'grab_x': gx, 'grab_y': gy}

    def window_get_bounds(self):
        """현재 창 위치/크기 (리사이즈 시작 기준값). Win32 물리 px."""
        try:
            r = self._win_get_rect()
            if not r:
                return {'ok': False, 'error': 'no hwnd'}
            return {'ok': True, **r, 'maximized': bool(self._maximized)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def window_set_bounds(self, x, y, width, height):
        """가장자리/모서리 드래그 리사이즈 — 목표 절대 bounds 적용 (frameless 창 OS 리사이즈 대체).
        JS 가 screenX×devicePixelRatio 로 물리 px 를 보내고, 여기서 SetWindowPos 로 적용."""
        try:
            if not self._window or self._maximized:
                return {'ok': False, 'error': 'unavailable'}
            MINW, MINH = 760, 520   # 안전 하한 (실사용 클램프는 프론트 960×640)
            if not self._win_set_pos(int(x), int(y), max(MINW, int(width)), max(MINH, int(height))):
                return {'ok': False, 'error': 'set_pos failed'}
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def window_close(self):
        """커스텀 닫기 버튼 → 네이티브 X 와 동일하게 closeBehavior(tray/exit) 적용."""
        try:
            behavior = self._load_settings_raw().get('closeBehavior', 'tray')
        except Exception:
            behavior = 'tray'
        try:
            if behavior == 'exit':
                if callable(self._on_quit_request):
                    self._on_quit_request()
                elif self._window:
                    self._window.destroy()
            else:
                if self._window:
                    self._window.hide()
            return {'ok': True, 'behavior': behavior}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def save_settings(self, state):
        """프론트에서 설정 저장. 화이트리스트 키만 수용.

        `security.require_hello` 는 **여기서 바꾸지 않는다** (v1.3.39) — 지금 값을
        그대로 둔다. 그 값은 `vault_set_require_hello` 만 바꾼다. 여기로 끌 수 있으면
        그 함수에 세운 확인(Hello 또는 열린 보관함)을 일반 설정 저장으로 돌아갈 수 있다.
        """
        try:
            if not isinstance(state, dict):
                return {'ok': False, 'error': 'state must be a dict'}
            clean = self._normalize_settings(state)
            try:
                # _load_settings_raw 는 못 읽으면 기본값을 돌려준다 — 여기선 그러면 안 되므로 직접 읽는다
                if self._SETTINGS_PATH.exists():
                    _raw = json.loads(self._SETTINGS_PATH.read_text(encoding='utf-8'))
                    if not isinstance(_raw, dict):
                        raise ValueError('settings.json 형식 오류')
                cur = self._load_settings_raw() or {}
            except Exception:
                if self._SETTINGS_PATH.exists():
                    # 지금 설정을 못 읽으면 저장하지 않는다(v1.5.28 검토) — 빈 값으로 덮으면 「Windows Hello 필수」 가
                    # 조용히 꺼졌다
                    return {'ok': False, 'error': '지금 설정 파일을 읽지 못해 저장하지 않았습니다 — 잠시 뒤 다시 시도하세요.'}
                cur = {}
            cur_sec = cur.get('security') or {}
            clean['security'] = {**(clean.get('security') or {}),
                                 'require_hello': bool(cur_sec.get('require_hello'))}
            # 시작 화면은 보낸 쪽이 그 키를 담았을 때만 바꾼다 — 다른 화면이 설정을 저장하면서
            res = self._write_settings(clean)
            # 화이트리스트에 없어 버린 키를 알린다(v1.5.60) — 예전엔 조용히 버려서 세 번 사고가 났다
            dropped = self._dropped_settings_keys(state, clean)
            if dropped and isinstance(res, dict):
                res['dropped'] = dropped
                print(f'[settings] 저장하지 않은 키(화이트리스트 밖): {", ".join(dropped)}', flush=True)
            return res
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def _write_settings(self, clean: dict) -> dict:
        """정규화가 끝난 설정을 디스크에 쓴다 (내부용)."""
        try:
            from src.paths import atomic_write_text
            self._SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            # 임시 파일에 쓰고 바꿔 끼운다 — 쓰는 도중 꺼지면 반쯤 쓴 설정이 남아 다음 실행이 기본값으로 돌았다
            atomic_write_text(self._SETTINGS_PATH, json.dumps(clean, ensure_ascii=False, indent=2))
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
            self._stop_kubectl_stream_procs_for_cluster('')
            # 내장 파드 exec 세션 정리 (매니저가 생성된 경우에만)
            if hasattr(self, '_polaris_pod_exec_mgr'):
                try: self._polaris_pod_exec_mgr.close_all()
                except Exception: pass
            # 리소스 watch 세션 정리
            if hasattr(self, '_polaris_res_watch_mgr'):
                try: self._polaris_res_watch_mgr.close_all()
                except Exception: pass
            # 알림 감시 스레드 정리
            if hasattr(self, '_polaris_notif_watcher'):
                try: self._polaris_notif_watcher.stop()
                except Exception: pass
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


    # 검색 인덱스용 목록 경로 — metadata 만 받는다 (v1.3.42)
    _SEARCH_PATHS = {
        'nodes':        '/api/v1/nodes',
        'namespaces':   '/api/v1/namespaces',
        'pods':         '/api/v1/pods',
        'deployments':  '/apis/apps/v1/deployments',
        'statefulsets': '/apis/apps/v1/statefulsets',
        'daemonsets':   '/apis/apps/v1/daemonsets',
        'services':     '/api/v1/services',
        'ingresses':    '/apis/networking.k8s.io/v1/ingresses',
        'configmaps':   '/api/v1/configmaps',
        'secrets':      '/api/v1/secrets',
        'pvcs':         '/api/v1/persistentvolumeclaims',
        'pvs':          '/api/v1/persistentvolumes',
        'jobs':         '/apis/batch/v1/jobs',
        'cronjobs':     '/apis/batch/v1/cronjobs',
    }

    def get_search_index(self, force: bool = False, _cluster_id=None, _mgr=None):
        """활성(또는 지정된) 클러스터의 검색용 경량 리소스 인덱스 반환.
        Returns: [{kind, rtype, name, namespace}]

        _cluster_id/_mgr 는 백그라운드 프리웜(_prewarm_search_index_async) 전용 — 호출 시점에
        캐시 키/대상 클러스터를 고정해, 프리웜 도중 사용자가 다른 클러스터로 전환해도 엉뚱한
        슬롯을 채우지 않는다. 일반 호출(팔레트 오픈)은 항상 인자 없이 호출해 '현재 활성' 기준으로 동작.
        """
        import time as _time
        from concurrent.futures import ThreadPoolExecutor

        mgr = _mgr if _mgr is not None else self.k8s
        cache_key = _cluster_id if _cluster_id is not None else (self._active_id or '')
        if not mgr.connected:
            return []

        if not hasattr(self, '_search_cache'):
            self._search_cache = {}
        now = _time.time()
        cached = self._search_cache.get(cache_key)
        if not force and cached and (now - cached['t'] < 30):
            return cached['data']

        # 14종 리소스를 순차 조회하면 대형 클러스터에서 지연이 누적된다(각 호출이 독립적인
        # I/O 라 병렬화 시 총 소요가 '합'이 아니라 '최댓값'으로 줄어든다).
        #
        # (v1.3.42, 성능 P3) 인덱스에는 **이름·네임스페이스만** 들어간다. 예전에는 14종을
        # 본문째 받았다 — 모든 Secret·ConfigMap 내용까지. 이제 metadata 만 받고, 그게
        # 안 되는 서버에서만 예전 경로로 돌아간다.
        from src.k8s_fast import list_metadata

        def _fetch(rtype):
            path = self._SEARCH_PATHS.get(rtype)
            client = getattr(mgr, '_api_client', None)
            if path and client is not None:
                try:
                    return [{'name': o.metadata.name or '',
                             'namespace': o.metadata.namespace or ''}
                            for o in list_metadata(client, path).items]
                except Exception:
                    pass
            try:
                return mgr.get_resources(rtype, None) or []
            except Exception:
                return []

        idx = []
        with ThreadPoolExecutor(max_workers=min(8, len(self._SEARCH_KINDS))) as ex:
            results = ex.map(_fetch, [rtype for rtype, _kind in self._SEARCH_KINDS])
            for (rtype, kind), items in zip(self._SEARCH_KINDS, results):
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


    def _prewarm_search_index_async(self, cluster_id, mgr):
        """클러스터 연결 직후 검색 인덱스를 백그라운드로 미리 채운다 — 30초 캐시이므로 그 안에
        사용자가 명령 팔레트(Ctrl+K)를 열면 즉시 응답. best-effort, 실패해도 조용히 무시
        (팔레트를 열 때 다시 시도되는 일반 경로로 자연 복구)."""
        def _run():
            try:
                self.get_search_index(force=True, _cluster_id=cluster_id, _mgr=mgr)
            except Exception:
                pass
        try:
            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            pass


    def get_app_version(self):
        # 지연 import (polaris.py 가 src.api 를 import 하는 순환 회피)
        from polaris import VERSION
        return {'version': VERSION}

    def open_third_party_notices(self):
        """오픈소스 고지(THIRD_PARTY_NOTICES.txt) 열기 (v1.4.19) — 빌드가 polaris.exe 옆에 만든다."""
        import os
        import sys
        if getattr(sys, 'frozen', False):
            path = Path(sys.executable).resolve().parent / 'THIRD_PARTY_NOTICES.txt'
        else:
            path = Path(__file__).resolve().parents[2] / 'dist' / 'polaris' / 'THIRD_PARTY_NOTICES.txt'
        if not path.is_file():
            return {'ok': False, 'error': f'고지 파일이 없습니다({path}) — 설치본에 함께 들어 있습니다.'}
        try:
            os.startfile(str(path))       # noqa: S606 (Windows 전용 — 기본 텍스트 편집기로 연다)
            return {'ok': True, 'path': str(path)}
        except OSError as e:
            return {'ok': False, 'error': f'고지 파일을 열지 못했습니다: {e}'}


    def get_enabled_features(self):
        """이 빌드에 들어 있는 옵셔널 플러그인 ID 목록."""
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
            # 옮긴 폴더를 못 찾아 기본 폴더로 열었다(v1.4.24) — 화면 위에 알린다
            'fallback_from': paths.fallback_from(),
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
            if str(new_path).strip().replace('/', '\\').startswith('\\\\'):
                # 네트워크 공유(\\서버\공유) 는 받지 않는다(v1.5.28 검토) — 보안 보관함 · 세션이 네트워크로 오가고,
                # 공유가 끊기면 시작조차 못 한다
                return {'ok': False, 'error': '네트워크 공유(\\\\서버\\공유) 경로는 데이터 폴더로 쓸 수 없습니다 — 이 PC 의 폴더를 고르세요.'}
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
            # 새 위치의 ACL 을 현재 사용자 전용으로 조임 (best-effort, v1.2.3) —
            # 느슨한 위치로 옮겨도 민감 파일이 노출되지 않도록. 재시작 전에도 적용.
            try:
                from src import winsec
                winsec.harden_dir(new_dir)
            except Exception:
                pass
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

