"""ResourcesMixin — 리소스 브라우저 / 이벤트 / cronjob / delete / 대시보드 / ArgoCD / Helm.
"""
from datetime import datetime, timezone, timedelta

from src.k8s import (
    _is_secret_kind, _argo_primary_source, _argo_sources_from_spec,
    _build_scale_args, _build_rollout_restart_args, _build_rollout_undo_args,
    _normalize_kubectl_kind, _images_from_cr_data, _kubectl_target_error,
)
from src.tools import _run_kubectl


# 이벤트를 모을 때 넘겨 볼 최대 개수 (v1.3.41, 성능 P12) — 아래 _list_events_newest 참고
_EVENT_SCAN_MAX = 3000
_EVENT_PAGE = 500


def _type_selector(type_set):
    """종류가 하나면 서버에서 거른다 — `type=Warning` 만 받으면 오가는 양이 크게 준다."""
    if type_set and len(type_set) == 1:
        (only,) = tuple(type_set)
        if only in ('Normal', 'Warning'):
            return f'type={only}'
    return None


def _list_events_newest(fn, limit, field_selector=None, **kw):
    """이벤트를 **페이지를 넘겨 가며** 모은다.

    (v1.3.41) 예전에는 `limit=500` 으로 한 번만 불렀다. 그런데 쿠버네티스 목록은
    **이름(키) 순서**라 그 500개는 최신 500개가 아니다 — 이벤트가 많은 클러스터에서는
    방금 생긴 경고가 목록에 없었고, 그래서 **알림이 새 경고를 놓칠 수 있었다.**
    이제 _EVENT_SCAN_MAX 까지 이어 받아 호출한 쪽이 시간순으로 정렬해 자른다.
    """
    items, cont = [], None
    while True:
        args = dict(kw, limit=_EVENT_PAGE)
        if field_selector:
            args['field_selector'] = field_selector
        if cont:
            args['_continue'] = cont
        # 모델 변환 없이 읽는다(v1.3.42) — 알림이 15초마다 최대 3000개를 넘겨 본다
        from src.k8s import _list
        r = _list(fn, **args)
        items.extend(r.items or [])
        cont = getattr(getattr(r, 'metadata', None), '_continue', None)
        if not cont or len(items) >= max(limit, _EVENT_SCAN_MAX):
            break
    return items


def _is_forbidden(e) -> bool:
    return getattr(e, 'status', None) == 403 or ' 403' in str(e)[:40] or 'Forbidden' in str(e)[:200]


class ResourcesMixin:
    def get_namespaces_list(self):
        return self.k8s.get_namespaces_list()


    def get_resource(self, rtype: str, ns: str = ''):
        rows = self.k8s.get_resources(rtype, ns or None)
        return self._clean(rows)

    #: 흔한 단수 · 줄임 표기 → 화면 목록 키(GETTERS). 여기 없는 종류는 kubectl 로 본다.
    _KIND_ALIASES = {
        'pod': 'pods', 'po': 'pods', 'deployment': 'deployments', 'deploy': 'deployments',
        'statefulset': 'statefulsets', 'sts': 'statefulsets', 'daemonset': 'daemonsets', 'ds': 'daemonsets',
        'replicaset': 'replicasets', 'rs': 'replicasets', 'job': 'jobs', 'cronjob': 'cronjobs', 'cj': 'cronjobs',
        'service': 'services', 'svc': 'services', 'ingress': 'ingresses', 'ing': 'ingresses',
        'configmap': 'configmaps', 'cm': 'configmaps', 'secret': 'secrets', 'node': 'nodes', 'no': 'nodes',
        'namespace': 'namespaces', 'ns': 'namespaces', 'pvc': 'pvcs', 'persistentvolumeclaim': 'pvcs',
        'persistentvolumeclaims': 'pvcs', 'pv': 'pvs', 'persistentvolume': 'pvs', 'persistentvolumes': 'pvs',
    }
    _LIST_ANY_MAX = 2000

    def list_resources_any(self, kind: str, ns: str = '') -> dict:
        """어떤 종류든 목록 — MCP polaris_list_resources (v1.5.53).

        예전엔 화면 목록용 표(GETTERS 15종)에 없는 종류를 **조용히 0건**으로 돌려줘, CRD(HelmChartConfig · Addon …)
        와 단수 표기(deployment)가 「하나도 없음」 으로 보였다(사용자 신고 — 실제로 있는 HelmChartConfig 를 없다고 판단).
        이제 아는 종류는 그대로, 나머지는 `kubectl get <kind> -o json` 으로 본다(이름으로 하나 볼 때와 같은 길).
        이 길은 **메타데이터만**(이름 · 네임스페이스 · 만든 시각 · apiVersion · kind) 돌려준다 — spec · Secret 값은 싣지 않는다.
        종류를 모르면 0건이 아니라 오류.
        """
        import json as _json
        k = str(kind or '').strip()
        key = self._KIND_ALIASES.get(k.lower(), k.lower())
        if key in self.k8s.GETTERS:
            return {'ok': True, 'kind': key, 'via': 'api', 'items': self.get_resource(key, ns)}
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        bad = _kubectl_target_error(kind=k, ns=ns)
        if bad:
            return {'ok': False, 'error': bad}
        args = ['get', k, '-o', 'json'] + (['-n', ns] if ns else ['-A'])
        out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=60)
        if not out:
            msg = (err or '').strip()
            if "doesn't have a resource type" in msg or 'the server could not find the requested resource' in msg:
                return {'ok': False, 'error': f'이 클러스터에 「{k}」 종류가 없습니다(CRD 가 설치되지 않았거나 이름이 다름) — {msg[:200]}'}
            return {'ok': False, 'error': msg[:400] or '목록을 받지 못했습니다'}
        try:
            data = _json.loads(out)
        except ValueError:
            return {'ok': False, 'error': '목록을 해석하지 못했습니다'}
        rows = []
        for it in data.get('items') or []:
            md = it.get('metadata') or {}
            rows.append({'name': md.get('name', ''), 'namespace': md.get('namespace', ''),
                         'kind': it.get('kind', ''), 'apiVersion': it.get('apiVersion', ''),
                         'created': md.get('creationTimestamp', '')})
        rows.sort(key=lambda r: (r['namespace'], r['name']))
        truncated = len(rows) > self._LIST_ANY_MAX
        return {'ok': True, 'kind': k, 'via': 'kubectl', 'items': rows[:self._LIST_ANY_MAX], 'truncated': truncated,
                'note': '메타데이터만 — 내용은 polaris_get_resource(이름)로 보세요'}


    # ── 리소스 실시간 갱신 (watch API) ───────────────────────────────────────
    # v1: 파드만 지원(k8s_watch._MAPPERS 참고) — 다른 kind 는 기존 수동 새로고침 그대로.
    def _res_watch(self):
        if not hasattr(self, '_polaris_res_watch_mgr'):
            from src.k8s_watch import ResourceWatchManager
            self._polaris_res_watch_mgr = ResourceWatchManager()
        return self._polaris_res_watch_mgr

    def start_resource_watch(self, kind: str, namespace: str = '') -> dict:
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        return self._res_watch().start(self.k8s.kubeconfig, kind, namespace)

    def recv_resource_watch(self, watch_id: str) -> dict:
        return self._res_watch().recv(watch_id)

    def stop_resource_watch(self, watch_id: str) -> dict:
        return self._res_watch().close(watch_id)

    def resource_watch_kinds(self) -> list:
        """프론트가 '실시간' 토글을 보여줄지 판단하는 지원 kind 목록."""
        from src.k8s_watch import ResourceWatchManager
        return ResourceWatchManager.supported_kinds()


    def get_crds(self):
        """클러스터의 CRD 목록 (자동 발견). [{name, group, version, kind, plural, ...}]"""
        if not self.k8s.connected:
            return {'ok': False, 'error': '연결되지 않음', 'items': []}
        try:
            return {'ok': True, 'items': self.k8s.get_crds()}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'items': []}


    def get_crd_objects(self, group: str, version: str, plural: str,
                        namespaced: bool = True, ns: str = '',
                        printer_columns: list = None):
        """특정 CRD 의 커스텀 객체 목록. printer_columns 가 있으면 동적 컬럼 값 포함."""
        if not self.k8s.connected:
            return {'ok': False, 'error': '연결되지 않음', 'items': []}
        try:
            rows = self.k8s.get_crd_objects(group, version, plural,
                                            bool(namespaced), ns or None,
                                            printer_columns or [])
            return {'ok': True, 'items': self._clean(rows)}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'items': []}


    # ── RBAC 분석 ────────────────────────────────────────────────────────────

    def get_rbac(self, include_system: bool = False):
        """RBAC 전체 데이터 (roles / bindings / serviceaccounts) 한 번에 반환.

        + serviceAccount 별 '실제 권한' 역추적:
          SA → 그 SA 를 subject 로 가진 binding → roleRef → role 의 rules
        """
        if not self.k8s.connected:
            return {'ok': False, 'error': '연결되지 않음'}
        try:
            roles    = self.k8s.get_rbac_roles(include_system)
            bindings = self.k8s.get_rbac_bindings(include_system)
            sas      = self.k8s.get_service_accounts()

            # role 빠른 조회용 인덱스: (kind, name, namespace) → role
            role_idx = {}
            for r in roles:
                role_idx[(r['kind'], r['name'], r['namespace'])] = r

            # SA 별 권한 역추적
            sa_perms = {}   # (ns, name) → {'bindings':[...], 'rules':[...]}
            for b in bindings:
                rr = b['role_ref']
                # roleRef 가 가리키는 role 찾기 (ClusterRole 은 namespace='')
                role = (role_idx.get(('ClusterRole', rr['name'], ''))
                        or role_idx.get(('Role', rr['name'], b['namespace'])))
                for s in b['subjects']:
                    if s['kind'] != 'ServiceAccount':
                        continue
                    key = (s['namespace'] or b['namespace'], s['name'])
                    entry = sa_perms.setdefault(key, {'bindings': [], 'rules': []})
                    entry['bindings'].append({
                        'binding':   b['name'],
                        'binding_kind': b['kind'],
                        'role_kind': rr['kind'],
                        'role':      rr['name'],
                    })
                    if role:
                        entry['rules'].extend(role['rules'])

            # SA 목록에 권한 요약 부착
            for sa in sas:
                key = (sa['namespace'], sa['name'])
                p = sa_perms.get(key, {'bindings': [], 'rules': []})
                sa['binding_count'] = len(p['bindings'])
                sa['bindings']      = p['bindings']
                sa['rules']         = p['rules']

            return {
                'ok': True,
                'roles':    roles,
                'bindings': bindings,
                'service_accounts': sas,
                'summary': {
                    'cluster_roles':  sum(1 for r in roles if r['kind'] == 'ClusterRole'),
                    'roles':          sum(1 for r in roles if r['kind'] == 'Role'),
                    'cluster_role_bindings': sum(1 for b in bindings if b['kind'] == 'ClusterRoleBinding'),
                    'role_bindings':  sum(1 for b in bindings if b['kind'] == 'RoleBinding'),
                    'service_accounts': len(sas),
                },
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    @staticmethod
    def _format_events_core(evts, type_set):
        """core/v1 Event 객체 리스트 → dict 리스트."""
        result = []
        for e in evts:
            etype = e.type or ''
            if type_set and etype not in type_set:
                continue
            last  = e.last_timestamp or e.event_time or e.metadata.creation_timestamp
            first = e.first_timestamp or e.metadata.creation_timestamp
            io    = e.involved_object
            result.append({
                'namespace':  e.metadata.namespace or '',
                'type':       etype,
                'reason':     e.reason or '',
                'kind':       (io.kind if io else '') or '',
                'obj_name':   (io.name if io else '') or '',
                'obj':        (f'{io.kind}/{io.name}' if io and io.kind and io.name else ''),
                'message':    (e.message or '')[:300],
                'count':      e.count or 1,
                'first_time': first.isoformat() if first else None,
                'last_time':  last.isoformat()  if last  else None,
                'source':     (e.source.component if e.source and e.source.component else ''),
            })
        return result


    @staticmethod
    def _format_events_v1(items, type_set):
        """events.k8s.io/v1 Event 스키마 → dict 리스트 (필드명 일부 다름)."""
        result = []
        for e in items or []:
            etype = e.get('type', '')
            if type_set and etype not in type_set:
                continue
            meta      = e.get('metadata', {}) or {}
            regarding = e.get('regarding') or e.get('involvedObject') or {}
            series    = e.get('series') or {}
            last  = (series.get('lastObservedTime')
                     or e.get('deprecatedLastTimestamp')
                     or e.get('eventTime')
                     or meta.get('creationTimestamp'))
            first = (e.get('deprecatedFirstTimestamp')
                     or e.get('eventTime')
                     or meta.get('creationTimestamp'))
            kind = regarding.get('kind') or ''
            obj_name = regarding.get('name') or ''
            result.append({
                'namespace':  meta.get('namespace', '') or '',
                'type':       etype,
                'reason':     e.get('reason', '') or '',
                'kind':       kind,
                'obj_name':   obj_name,
                'obj':        (f'{kind}/{obj_name}' if kind and obj_name else ''),
                'message':    (e.get('note') or e.get('message') or '')[:300],
                'count':      (series.get('count')
                               or e.get('deprecatedCount')
                               or 1),
                'first_time': first,
                'last_time':  last,
                'source':     (e.get('reportingController', '')
                               or (e.get('deprecatedSource') or {}).get('component', '')),
            })
        return result


    def get_cluster_events(self, namespace: str = '', limit: int = 500, types=None):
        """
        클러스터 이벤트 목록 — 다중 fallback 전략 (v3.7.9).

        Args:
            namespace: '' 이면 All Namespaces
            limit: 최대 건수 (기본 500)
            types: ['Normal','Warning'] 등 필터. None/[] = 전부

        수집 전략:
          1) namespace 지정 → list_namespaced_event 직접 호출
          2) all-ns 모드:
             a) list_event_for_all_namespaces (빠른 path)
             b) (a) 실패 시 → 네임스페이스 순회 + namespaced 조회
                (RBAC가 cluster-wide list 못 주는 경우 우회)
             c) (b)도 실패 시 → events.k8s.io/v1 cluster custom object 시도
          3) 모두 실패하면 에러 메시지 + 시도한 방법들 반환

        Returns: {
            ok:      bool,
            events:  [{namespace, type, reason, obj, kind, obj_name, message,
                       count, first_time, last_time, source}],
            source:  'namespaced' | 'all-ns' | 'per-ns' | 'events.k8s.io/v1',
            warning: str (optional),    # 일부 NS 권한 부족 등 경고
            error:   str (optional),    # 모두 실패 시
            attempts: [str, ...]        # 시도/실패 내역 (디버그용)
        }
        """
        if not self.k8s.core:
            return {'ok': False, 'error': '연결되지 않음', 'events': [], 'attempts': []}

        type_set = set(types) if types else None
        attempts = []
        fsel = _type_selector(type_set)

        # ── 단일 namespace 모드 ─────────────────────────────────────────────
        if namespace:
            try:
                evts = _list_events_newest(self.k8s.core.list_namespaced_event, limit,
                                           fsel, namespace=namespace)
                formatted = self._format_events_core(evts, type_set)
                formatted.sort(key=lambda r: r.get('last_time') or '', reverse=True)
                formatted = formatted[:limit]
                return {
                    'ok': True, 'events': formatted, 'source': 'namespaced',
                    'attempts': [f'list_namespaced_event({namespace})'],
                }
            except Exception as e:
                return {
                    'ok': False, 'events': [],
                    'error': f'list_namespaced_event({namespace}): {e}',
                    'attempts': [f'list_namespaced_event: {e}'],
                }

        # ── 전체 NS 모드 ─ Path A: list_event_for_all_namespaces ───────────
        # 권한이 없어 거절된 클러스터는 기억해 두고 바로 Path B 로 간다 — 예전엔 폴링
        # (알림 15초 · 이벤트 화면 10초)마다 거절당한 뒤에야 넘어갔다 (v1.3.41)
        forbidden = getattr(self, '_events_all_ns_forbidden', None)
        if forbidden is None:
            forbidden = self._events_all_ns_forbidden = set()
        cid = getattr(self, '_active_id', None)
        if cid in forbidden:
            attempts.append('list_event_for_all_namespaces 건너뜀(이 클러스터는 권한 없음)')
        else:
            try:
                evts = _list_events_newest(self.k8s.core.list_event_for_all_namespaces,
                                           limit, fsel)
                formatted = self._format_events_core(evts, type_set)
                formatted.sort(key=lambda r: r.get('last_time') or '', reverse=True)
                return {
                    'ok': True, 'events': formatted[:limit], 'source': 'all-ns',
                    'attempts': ['list_event_for_all_namespaces'],
                }
            except Exception as e:
                if cid and _is_forbidden(e):
                    forbidden.add(cid)
                attempts.append(f'list_event_for_all_namespaces FAILED: {e}')

        # ── Path B: 네임스페이스 순회 ───────────────────────────────────────
        try:
            ns_items = self.k8s.core.list_namespace().items
            ns_names = [n.metadata.name for n in ns_items]
            attempts.append(f'fallback to per-ns scan ({len(ns_names)} namespaces)')

            # 네임스페이스마다 한 번씩 — **동시에** 묻는다 (v1.3.41). 예전엔 하나씩이라
            # 네임스페이스가 많으면 폴링 한 번이 그 수만큼 왕복을 기다렸다.
            from concurrent.futures import ThreadPoolExecutor
            all_evts  = []
            failed_ns = []
            core = self.k8s.core

            def _one(ns):
                try:
                    return ns, _list_events_newest(core.list_namespaced_event, limit,
                                                   fsel, namespace=ns)
                except Exception:
                    return ns, None

            with ThreadPoolExecutor(max_workers=min(8, max(1, len(ns_names)))) as ex:
                for ns, items in ex.map(_one, ns_names):
                    if items is None:
                        failed_ns.append(ns)
                    else:
                        all_evts.extend(items)

            formatted = self._format_events_core(all_evts, type_set)
            formatted.sort(key=lambda r: r.get('last_time') or '', reverse=True)
            formatted = formatted[:limit]
            result = {
                'ok': True, 'events': formatted, 'source': 'per-ns',
                'attempts': attempts + [f'per-ns scan OK ({len(ns_names) - len(failed_ns)}/{len(ns_names)})'],
            }
            if failed_ns:
                sample = ', '.join(failed_ns[:3])
                more   = f' 외 {len(failed_ns)-3}개' if len(failed_ns) > 3 else ''
                result['warning'] = f'{len(failed_ns)}개 네임스페이스 권한 부족: {sample}{more}'
            return result
        except Exception as e:
            attempts.append(f'per-ns scan FAILED: {e}')

        # ── Path C: events.k8s.io/v1 (신규 API) ─────────────────────────────
        try:
            if self.k8s.custom:
                r = self.k8s.custom.list_cluster_custom_object(
                    group='events.k8s.io', version='v1', plural='events',
                    limit=limit)
                items = r.get('items', [])
                formatted = self._format_events_v1(items, type_set)
                formatted.sort(key=lambda x: x.get('last_time') or '', reverse=True)
                return {
                    'ok': True, 'events': formatted[:limit], 'source': 'events.k8s.io/v1',
                    'attempts': attempts + ['events.k8s.io/v1 OK'],
                }
        except Exception as e:
            attempts.append(f'events.k8s.io/v1 FAILED: {e}')

        # ── 모두 실패 ───────────────────────────────────────────────────────
        return {
            'ok': False, 'events': [],
            'error': '이벤트 조회 실패 (모든 fallback 실패). 자세한 내용은 attempts 참고.',
            'attempts': attempts,
        }


    def trigger_cronjob(self, namespace: str, name: str):
        """
        CronJob 스케줄을 기다리지 않고 즉시 1회 실행.
        내부적으로 `kubectl create job <name>-manual-<ts> --from=cronjob/<name>`.
        """
        import re as _re
        import time as _time
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        ns_clean   = (namespace or '').strip()
        name_clean = (name or '').strip()
        if not ns_clean or not name_clean:
            return {'ok': False, 'error': '네임스페이스와 CronJob 이름이 필요합니다.'}
        # K8s 리소스 이름 검증: 소문자 + 숫자 + 하이픈 + 점 (RFC1123)
        if not _re.match(r'^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$', name_clean):
            return {'ok': False, 'error': '잘못된 CronJob 이름 형식입니다.'}
        if not _re.match(r'^[a-z0-9-]+$', ns_clean):
            return {'ok': False, 'error': '잘못된 네임스페이스 형식입니다.'}

        # Job 이름: <cronjob>-manual-<unix>  (63자 제한 보존)
        suffix = f'-manual-{int(_time.time())}'
        max_prefix = 63 - len(suffix)
        prefix = name_clean[:max_prefix].rstrip('-')
        job_name = f'{prefix}{suffix}'

        try:
            args = ['-n', ns_clean, 'create', 'job', job_name,
                    f'--from=cronjob/{name_clean}']
            out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
            combined = (out or '') + (err or '')
            if 'created' in combined.lower():
                return {'ok': True, 'job_name': job_name}
            return {'ok': False, 'error': (err or out or 'kubectl 응답 없음').strip()}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def delete_resource(self, kind: str, ns: str, name: str):
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        # 「--all」 같은 이름이 오면 그 네임스페이스를 통째로 지운다 — kubectl 에 넘기기 전에 거른다(v1.5.28 검토)
        bad = _kubectl_target_error(kind=kind, ns=ns, name=name)
        if bad:
            return {'ok': False, 'error': bad}
        try:
            # UI 측 short name(pvcs/pvs 등) 을 kubectl 정식 이름으로 정규화
            kind = self._KUBECTL_KIND_MAP.get(kind, kind)
            args = (['-n', ns] if ns else []) + ['delete', kind, name]
            out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
            if err and 'deleted' not in (out + err).lower():
                return {'ok': False, 'error': err.strip()}
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def patch_resource(self, kind: str, ns: str, name: str, patch: str) -> dict:
        """kubectl patch --type=merge — CRD 포함 임의 리소스 부분 수정 (velero Schedule 일시정지 등).

        patch: JSON merge patch 문자열, 예: '{"spec":{"paused":true}}'
        """
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        p = (patch or '').strip()
        if not p:
            return {'ok': False, 'error': '패치 내용이 비어 있습니다.'}
        bad = _kubectl_target_error(kind=kind, ns=ns, name=name)
        if bad:
            return {'ok': False, 'error': bad}
        try:
            k = self._KUBECTL_KIND_MAP.get(kind, kind)
            args = (['-n', ns] if ns else []) + ['patch', k, name, '--type=merge', '-p', p]
            out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
            if err and 'patched' not in (out + err).lower():
                return {'ok': False, 'error': err.strip()}
            return {'ok': True, 'output': (out or err).strip()}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    # ── 리소스 쓰기 (YAML apply / scale / rollout restart) ───────────────────

    def apply_resource_yaml(self, yaml_text: str, kind: str = '') -> dict:
        """편집된 YAML 을 kubectl apply -f - (stdin) 로 적용.

        보안: Secret 은 YAML 조회 시 data/stringData 가 '[REDACTED]' 로 마스킹되므로
        그 YAML 을 그대로 apply 하면 실제 시크릿이 파괴된다. → Secret apply 차단.
        """
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        text = (yaml_text or '').strip()
        if not text:
            return {'ok': False, 'error': '적용할 YAML 이 비어 있습니다.'}

        # Secret 보호 — 마스킹된 YAML 적용 방지
        if _is_secret_kind(kind) or 'kind: Secret' in text:
            if '[REDACTED]' in text:
                return {'ok': False,
                        'error': 'Secret 은 보안상 편집·적용이 차단됩니다. '
                                 '(YAML 조회 시 값이 마스킹되어 그대로 적용하면 데이터가 손상됩니다)'}
            return {'ok': False,
                    'error': 'Secret 리소스는 Polaris 에서 편집·적용을 지원하지 않습니다.'}

        try:
            out, err = _run_kubectl(
                self.k8s.kubeconfig,
                ['apply', '-f', '-'],
                timeout=30,
                stdin_input=text,
            )
            combined = (out + err)
            # kubectl apply 성공 시 stdout 에 'created'/'configured'/'unchanged'
            if any(w in combined.lower() for w in ('created', 'configured', 'unchanged')):
                return {'ok': True, 'output': out.strip() or combined.strip()}
            if err.strip():
                return {'ok': False, 'error': err.strip()}
            return {'ok': True, 'output': out.strip()}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def validate_resource_yaml(self, yaml_text: str) -> dict:
        """편집 중인 YAML 을 실제 적용 없이 **스키마 검증**한다 (kubectl dry-run).

        서버 dry-run(--dry-run=server) 은 API 서버가 CRD·기본값·admission 까지 포함해
        검증하므로 클라이언트 문법 검사보다 훨씬 강력하다. 서버 연결이 안 되면
        클라이언트 dry-run(--dry-run=client, 스키마만)으로 자동 폴백한다.

        반환:
          {ok:True, valid:True,  mode, message}                 — 통과
          {ok:True, valid:False, mode, errors:[...], detail}    — 스키마/admission 위반
          {ok:False, error}                                     — 실행 불가(미연결/kubectl 없음)
        """
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        text = (yaml_text or '').strip()
        if not text:
            return {'ok': False, 'error': '검증할 YAML 이 비어 있습니다.'}

        _CONN_HINTS = ('kubectl을 찾을 수 없', 'unable to connect', 'connection refused',
                       'no route to host', 'did you specify the right host',
                       'couldn\'t get current server api group', 'i/o timeout',
                       'the server could not find the requested resource: openapi')

        def _run(mode):
            out, err = _run_kubectl(
                self.k8s.kubeconfig,
                ['apply', f'--dry-run={mode}', '-f', '-'],
                timeout=30, stdin_input=text)
            return out or '', err or ''

        def _looks_ok(out, err):
            combined = (out + err).lower()
            return any(w in combined for w in
                       ('created', 'configured', 'unchanged', 'dry run', 'dry-run'))

        try:
            out, err = _run('server')
            # 서버 연결/미지원 문제면 클라이언트 dry-run 으로 폴백
            if err and not _looks_ok(out, err) and any(h in err.lower() for h in _CONN_HINTS):
                out2, err2 = _run('client')
                if _looks_ok(out2, err2):
                    return {'ok': True, 'valid': True, 'mode': 'client',
                            'message': out2.strip() or '스키마 검증 통과 (클라이언트 dry-run)'}
                if err2.strip():
                    return {'ok': True, 'valid': False, 'mode': 'client',
                            'errors': self._split_kubectl_errors(err2), 'detail': err2.strip()}
                # 클라이언트도 실행 자체 실패 → 실행 불가로 보고
                return {'ok': False, 'error': (err.strip() or err2.strip())[:600]}

            if _looks_ok(out, err):
                return {'ok': True, 'valid': True, 'mode': 'server',
                        'message': out.strip() or '스키마 검증 통과 (서버 dry-run)'}
            if err.strip():
                return {'ok': True, 'valid': False, 'mode': 'server',
                        'errors': self._split_kubectl_errors(err), 'detail': err.strip()}
            # stderr 없고 성공 토큰도 없음 — 보수적으로 통과 처리
            return {'ok': True, 'valid': True, 'mode': 'server',
                    'message': out.strip() or '스키마 검증 완료'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    @staticmethod
    def _split_kubectl_errors(stderr: str) -> list:
        """kubectl dry-run stderr 를 사람이 읽는 오류 줄 목록으로 분해."""
        lines = []
        for raw in (stderr or '').splitlines():
            s = raw.strip()
            if not s:
                continue
            # 진행 로그/버전 다운로드 잡음 제거
            if s.lower().startswith(('downloading', 'verifying', 'info[')):
                continue
            lines.append(s[:500])
        # 너무 많으면 앞쪽 위주로
        return lines[:40]


    def scale_resource(self, kind: str, ns: str, name: str, replicas) -> dict:
        """kubectl scale — Deployment/StatefulSet/ReplicaSet 의 replicas 변경."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        try:
            args = _build_scale_args(kind, ns, name, replicas)
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        try:
            out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
            if err and 'scaled' not in (out + err).lower():
                return {'ok': False, 'error': err.strip()}
            return {'ok': True, 'output': (out or err).strip()}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def rollout_restart(self, kind: str, ns: str, name: str) -> dict:
        """kubectl rollout restart — Deployment/StatefulSet/DaemonSet 재시작."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        try:
            args = _build_rollout_restart_args(kind, ns, name)
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        try:
            out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
            if err and 'restarted' not in (out + err).lower():
                return {'ok': False, 'error': err.strip()}
            return {'ok': True, 'output': (out or err).strip()}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def get_rollout_revisions(self, kind: str, ns: str, name: str) -> dict:
        """워크로드 리비전 목록 — 사용자가 "언제/무엇으로 되돌릴지" 보고 고르게 한다.

        각 리비전: 번호 · 생성 시각 · 컨테이너 이미지 · replicas · 현재 활성 여부 · change-cause.
          - Deployment           : ReplicaSet 기반 (revision 주석 + spec.template).
          - StatefulSet/DaemonSet : ControllerRevision 기반 (cr.revision + cr.data 템플릿).
            CR 은 파드 수 정보가 없어 replicas/ready = None (UI 에서 해당 칸 생략).
        """
        if not self.k8s.connected or self.k8s.apps is None:
            return {'ok': False, 'error': '연결되지 않음'}
        # _normalize_kubectl_kind 는 복수형을 반환한다('deployment'→'deployments').
        k = _normalize_kubectl_kind(kind)
        try:
            if k == 'deployments':
                return self._revisions_deployment(ns, name)
            if k == 'statefulsets':
                return self._revisions_statefulset(ns, name)
            if k == 'daemonsets':
                return self._revisions_daemonset(ns, name)
            return {'ok': False,
                    'error': '리비전 롤백은 Deployment/StatefulSet/DaemonSet 만 지원합니다.'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def _revisions_deployment(self, ns: str, name: str) -> dict:
        """Deployment 리비전 — 소유 ReplicaSet 들의 revision 주석 + 템플릿."""
        dep = self.k8s.apps.read_namespaced_deployment(name, ns)
        cur_ann = (dep.metadata.annotations or {}).get('deployment.kubernetes.io/revision')
        cur = int(cur_ann) if cur_ann and str(cur_ann).isdigit() else None
        dep_uid = dep.metadata.uid
        revs = []
        for rs in self.k8s.apps.list_namespaced_replica_set(ns).items:
            if not any(o.uid == dep_uid for o in (rs.metadata.owner_references or [])):
                continue
            ann = rs.metadata.annotations or {}
            rev = ann.get('deployment.kubernetes.io/revision')
            if not rev or not str(rev).isdigit():
                continue
            rev = int(rev)
            tmpl = rs.spec.template.spec if (rs.spec and rs.spec.template) else None
            imgs = [c.image for c in (tmpl.containers or [])] if tmpl else []
            ts = rs.metadata.creation_timestamp
            revs.append({
                'revision':     rev,
                'created':      ts.isoformat() if ts else '',
                'images':       imgs,
                'replicas':     rs.spec.replicas or 0,
                'ready':        (rs.status.ready_replicas or 0) if rs.status else 0,
                'change_cause': ann.get('kubernetes.io/change-cause', ''),
                'current':      (rev == cur),
            })
        revs.sort(key=lambda r: r['revision'], reverse=True)
        return {'ok': True, 'current': cur, 'revisions': revs}

    def _revisions_statefulset(self, ns: str, name: str) -> dict:
        """StatefulSet 리비전 — ControllerRevision 기반.
        현재 = status.updateRevision(최신 desired) → 없으면 currentRevision (CR 이름)."""
        sts = self.k8s.apps.read_namespaced_stateful_set(name, ns)
        cur_name = None
        if sts.status:
            cur_name = sts.status.update_revision or sts.status.current_revision
        return self._revisions_from_crs(ns, sts.metadata.uid, current_cr_name=cur_name)

    def _revisions_daemonset(self, ns: str, name: str) -> dict:
        """DaemonSet 리비전 — ControllerRevision 기반.
        DaemonSet status 에는 current/update revision 필드가 없어, 최고 revision 을 현재로 본다."""
        ds = self.k8s.apps.read_namespaced_daemon_set(name, ns)
        return self._revisions_from_crs(ns, ds.metadata.uid, current_is_max=True)

    def _revisions_from_crs(self, ns: str, owner_uid: str,
                            current_cr_name=None, current_is_max=False) -> dict:
        """StatefulSet/DaemonSet 공통 — 소유 ControllerRevision 들을 리비전 목록으로.

        replicas/ready 는 CR 에 없으므로 None(템플릿 스냅샷이라 파드 수 개념 없음).
        현재 리비전은 CR 이름 매칭(sts) 또는 최고 revision(ds) 으로 표시.
        """
        revs, max_rev = [], None
        for cr in self.k8s.apps.list_namespaced_controller_revision(ns).items:
            if not any(o.uid == owner_uid for o in (cr.metadata.owner_references or [])):
                continue
            rev = getattr(cr, 'revision', None)
            try:
                rev = int(rev)
            except (TypeError, ValueError):
                continue
            max_rev = rev if max_rev is None else max(max_rev, rev)
            ts = cr.metadata.creation_timestamp
            revs.append({
                '_cr_name':     cr.metadata.name,
                'revision':     rev,
                'created':      ts.isoformat() if ts else '',
                'images':       _images_from_cr_data(getattr(cr, 'data', None)),
                'replicas':     None,   # ControllerRevision 은 파드 수 정보 없음
                'ready':        None,
                'change_cause': (cr.metadata.annotations or {}).get('kubernetes.io/change-cause', ''),
                'current':      False,
            })
        cur_num = None
        for r in revs:
            if current_is_max:
                r['current'] = (r['revision'] == max_rev)
            elif current_cr_name:
                r['current'] = (r['_cr_name'] == current_cr_name)
            if r['current']:
                cur_num = r['revision']
            del r['_cr_name']
        revs.sort(key=lambda r: r['revision'], reverse=True)
        return {'ok': True, 'current': cur_num, 'revisions': revs}


    def rollout_undo(self, kind: str, ns: str, name: str, revision) -> dict:
        """kubectl rollout undo --to-revision — 지정 리비전으로 롤백."""
        if not self.k8s.kubeconfig:
            return {'ok': False, 'error': '연결되지 않음'}
        try:
            args = _build_rollout_undo_args(kind, ns, name, revision)
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        try:
            out, err = _run_kubectl(self.k8s.kubeconfig, args, timeout=30)
            blob = (out + err).lower()
            if err and 'rolled back' not in blob and 'rolling back' not in blob:
                return {'ok': False, 'error': err.strip()}
            return {'ok': True, 'output': (out or err).strip()}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def get_dashboard(self):
        data = self.k8s.get_dashboard_data()
        data['pods'] = self._clean(data.get('pods', []))
        data['readyz'] = self._dashboard_readyz()
        return data

    def _dashboard_readyz(self) -> dict:
        """컨트롤 플레인 준비 상태 (`/readyz?verbose=true`) — 호출 1회.

        **fail-open 이다.** 클러스터 정책상 `/readyz` 가 403/404 일 수 있는데, 못 읽은
        것을 장애로 표시하면 멀쩡한 클러스터를 문제라고 신고하게 된다. 그 경우
        `available: False` 로 두고 화면은 「확인 불가」로 처리한다.

        readyz 수집 자체는 보고서(_report_fetch_readyz)와 공유한다 — 판정 기준이
        화면과 문서에서 갈리면 안 된다. reports 는 src.k8s 만 의존하므로
        여기서 import 해도 순환이 생기지 않는다.
        """
        if not getattr(self.k8s, 'connected', False):
            return {'available': False, 'reason': '연결되지 않음'}
        try:
            from src.reports import _report_fetch_readyz
            r = _report_fetch_readyz(self.k8s)
        except Exception as e:
            return {'available': False, 'reason': f'{type(e).__name__}: {e}'}

        # status 가 없으면 응답 자체를 못 받은 것 → 확인 불가
        if not r.get('status'):
            return {'available': False,
                    'reason': r.get('error') or '응답 없음'}
        if r.get('status') in (401, 403, 404):
            return {'available': False,
                    'reason': f"HTTP {r['status']} — 이 클러스터는 /readyz 조회가 제한됩니다"}
        return {
            'available': True,
            'ok':        bool(r.get('ok')),
            'status':    r.get('status'),
            'total':     len(r.get('checks') or []) + len(r.get('failed') or []),
            'passed':    len(r.get('checks') or []),
            'failed':    r.get('failed') or [],
        }


    def get_argocd_apps(self):
        raw = self.k8s.get_argocd_apps()
        if raw is None:
            return []
        return [self._transform_argo(item) for item in raw]


    @staticmethod
    def _transform_argo(item: dict) -> dict:
        meta   = item.get('metadata', {})
        spec   = item.get('spec', {})
        status = item.get('status', {})
        sources = _argo_sources_from_spec(spec)
        src    = sources[0] if sources else {}
        dst    = spec.get('destination', {})
        sp     = spec.get('syncPolicy') or {}
        rev    = status.get('sync', {}).get('revision') or ''
        source_count = len(sources)
        source_label = src.get('path') or src.get('chart') or src.get('ref') or ''
        repo = src.get('repoURL', '')
        if source_count > 1:
            repo = f'{repo} (+{source_count - 1})'
        history = [
            {
                'id':          h.get('id'),
                'revision':    (h.get('revision') or '')[:8],
                'deployed_at': str(h.get('deployedAt', ''))[:19],
            }
            for h in (status.get('history') or [])
        ]
        return {
            'name':           meta.get('name', ''),
            'namespace':      meta.get('namespace', 'argocd'),
            'project':        spec.get('project', 'default'),
            'sync':           status.get('sync', {}).get('status', 'Unknown'),
            'health':         status.get('health', {}).get('status', 'Unknown'),
            'repo':           repo,
            'repo_url':       src.get('repoURL', ''),
            'revision':       rev[:8] if rev else '',
            'target_revision': src.get('targetRevision', 'HEAD'),
            'path':           source_label,
            'dest_server':    dst.get('server', ''),
            'dest_namespace': dst.get('namespace', ''),
            'sync_policy':    'automated' if sp.get('automated') else 'none',
            'source_mode':    'multi' if source_count > 1 else 'single',
            'source_count':   source_count,
            'sources':        sources,
            'history':        history,
        }


    def sync_argocd_app(self, ns: str, name: str):
        try:
            self.k8s.sync_argocd_app(ns, name)
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def rollback_argocd_app(self, ns: str, name: str, history_id):
        try:
            self.k8s.rollback_argocd_app(ns, name, int(history_id))
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def create_argocd_app_json(self, data: dict):
        try:
            sp = ({'automated': {'prune': False, 'selfHeal': False}}
                  if data.get('sync_policy') == 'automated' else {})
            self.k8s.create_argocd_app(
                data['namespace'], data['name'], data['project'],
                data['repo_url'], data['path'],
                data.get('target_revision', 'HEAD'),
                data['dest_namespace'], data['dest_server'], sp,
                data.get('sources') if data.get('source_mode') == 'multi' else None,
            )
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def update_argocd_app_json(self, data: dict):
        try:
            sp = ({'automated': {'prune': False, 'selfHeal': False}}
                  if data.get('sync_policy') == 'automated' else {})
            self.k8s.update_argocd_app(
                data['namespace'], data['name'], data['project'],
                data['repo_url'], data['path'],
                data.get('target_revision', 'HEAD'),
                data['dest_namespace'], data['dest_server'], sp,
                data.get('sources') if data.get('source_mode') == 'multi' else None,
            )
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def delete_argocd_app(self, ns: str, name: str):
        try:
            self.k8s.delete_argocd_app(ns, name)
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


    def get_helm_releases(self):
        releases = self.k8s.get_helm_releases()
        # _rev 내부 키 제거
        return [{k: v for k, v in r.items() if not k.startswith('_')}
                for r in releases]

