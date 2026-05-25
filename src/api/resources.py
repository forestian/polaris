"""ResourcesMixin — 리소스 브라우저 / 이벤트 / cronjob / delete / 대시보드 / ArgoCD / Helm.
"""
from datetime import datetime, timezone, timedelta

from src.k8s import _is_secret_kind, _argo_primary_source, _argo_sources_from_spec
from src.tools import _run_kubectl


class ResourcesMixin:
    def get_namespaces_list(self):
        return self.k8s.get_namespaces_list()


    def get_resource(self, rtype: str, ns: str = ''):
        rows = self.k8s.get_resources(rtype, ns or None)
        return self._clean(rows)


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

        # ── 단일 namespace 모드 ─────────────────────────────────────────────
        if namespace:
            try:
                evts = self.k8s.core.list_namespaced_event(
                    namespace=namespace, limit=limit).items
                formatted = self._format_events_core(evts, type_set)
                formatted.sort(key=lambda r: r.get('last_time') or '', reverse=True)
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
        try:
            evts = self.k8s.core.list_event_for_all_namespaces(limit=limit).items
            formatted = self._format_events_core(evts, type_set)
            formatted.sort(key=lambda r: r.get('last_time') or '', reverse=True)
            return {
                'ok': True, 'events': formatted, 'source': 'all-ns',
                'attempts': ['list_event_for_all_namespaces'],
            }
        except Exception as e:
            attempts.append(f'list_event_for_all_namespaces FAILED: {e}')

        # ── Path B: 네임스페이스 순회 ───────────────────────────────────────
        try:
            ns_items = self.k8s.core.list_namespace().items
            ns_names = [n.metadata.name for n in ns_items]
            attempts.append(f'fallback to per-ns scan ({len(ns_names)} namespaces)')

            # NS당 가져올 양 (전체 한도를 NS 수로 나누되 최소 50, 최대 limit)
            per_ns_limit = max(50, min(limit, limit // max(len(ns_names), 1) + 50))
            all_evts  = []
            failed_ns = []
            for ns in ns_names:
                try:
                    items = self.k8s.core.list_namespaced_event(
                        namespace=ns, limit=per_ns_limit).items
                    all_evts.extend(items)
                except Exception:
                    failed_ns.append(ns)

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


    def get_dashboard(self):
        data = self.k8s.get_dashboard_data()
        data['pods'] = self._clean(data.get('pods', []))
        return data


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

