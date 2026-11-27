# -*- coding: utf-8 -*-
"""yamllab 플러그인 — YAML 실험실 (매니페스트 저장 · 적용 · 파급 관찰 · 반출).

PolarisAPI 의 옵셔널 mixin(src/api/ 자동 발견). 판정·저장 로직은 `src/yamllab.py`
(코어, 순수 함수 위주)에 있고 여기는 I/O 와 job 오케스트레이션만 한다.

노출 메서드 (window.pywebview.api.xxx()):
  lab_list(query)                       → 목록 (이름·태그·본문 FTS 검색)
  lab_get(mid)                          → 본문 + 버전/적용 이력
  lab_save(mid, name, content, tags, notes)  → 신규/새 버전 (+ 비밀 경고)
  lab_delete(mid)                       → 삭제
  lab_version_diff(va, vb)              → 내 버전끼리 unified diff
  lab_preview(content)                  → 적용 **전**: 스키마 검증 + kubectl diff
  lab_apply(mid, content, watch_s)      → 적용 + 파급 관찰 job 시작
  lab_apply_status(job_id)              → 폴링 (로그는 drain-on-read)
  lab_apply_cancel(job_id)              → 관찰 중단 (적용 자체는 되돌리지 않음)
  lab_teardown(mid)                     → kubectl delete -f - (테스트 정리)
  lab_export_text(ids)                  → 선택분 이어붙인 문자열 (프론트가 클립보드로)
  lab_export_folder(ids, by_cluster)    → 폴더 선택 → 파일 트리 생성

GitLab 자동 승격은 **의도적으로 없다** — 클러스터마다 GitLab 서버·프로젝트가 달라
승격 대상이 하나로 정해지지 않는다. 반출까지만 하고 형상관리 반영은 사용자가 한다.
"""
import json
import threading
import time
import uuid
from pathlib import Path

from src.tools import _run_kubectl, _run_kubectl_rc
from src.yamllab import (
    open_db, list_manifests, get_manifest, get_version_content,
    save_manifest, delete_manifest, record_apply, export_items,
    parse_targets, target_namespaces, scan_secrets,
    version_diff, scope_diff, plan_export, join_documents,
)

# 적용/관찰 job. 플러그인 자체 상태.
_lab_jobs = {}

_WATCH_POLL_S = 4.0
_WATCH_MAX_S = 180.0     # 관찰 창 상한 — 무한정 붙잡지 않는다


class YamlLabMixin:
    # ── 저장소 ────────────────────────────────────────────────────────────────
    def _lab_db(self):
        """요청마다 새 연결. sqlite3 연결은 스레드 간 공유가 안 되고, 관찰 job 이
        별도 스레드에서 돌기 때문에 커넥션을 캐시하면 터진다."""
        return open_db()

    def _lab_cluster(self) -> str:
        """어느 클러스터에서 테스트했는지. 보관함 이름 우선(APIBase._cluster_label)."""
        try:
            return self._cluster_label(fallback='')
        except Exception:
            return ''

    def lab_list(self, query: str = '') -> dict:
        try:
            conn = self._lab_db()
            try:
                return {'ok': True, 'items': list_manifests(conn, query)}
            finally:
                conn.close()
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}', 'items': []}

    def lab_get(self, mid) -> dict:
        try:
            conn = self._lab_db()
            try:
                item = get_manifest(conn, mid)
                if not item:
                    return {'ok': False, 'error': '항목을 찾을 수 없습니다.'}
                item['warnings'] = scan_secrets(item.get('content', ''))
                item['targets'] = parse_targets(item.get('content', ''))
                return {'ok': True, 'item': item}
            finally:
                conn.close()
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    def lab_save(self, mid=None, name: str = '', content: str = '',
                 tags: str = '', notes: str = '') -> dict:
        if not (content or '').strip():
            return {'ok': False, 'error': '저장할 YAML 이 비어 있습니다.'}
        try:
            conn = self._lab_db()
            try:
                return save_manifest(conn, mid, name, content,
                                     cluster=self._lab_cluster(), tags=tags, notes=notes)
            finally:
                conn.close()
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    def lab_delete(self, mid) -> dict:
        try:
            conn = self._lab_db()
            try:
                return {'ok': delete_manifest(conn, mid)}
            finally:
                conn.close()
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    def lab_version_diff(self, version_a, version_b) -> dict:
        try:
            conn = self._lab_db()
            try:
                a = get_version_content(conn, version_a)
                b = get_version_content(conn, version_b)
                if not a and not b:
                    return {'ok': False, 'error': '버전을 찾을 수 없습니다.'}
                return {'ok': True, 'diff': version_diff(a, b,
                                                         f'v{version_a}', f'v{version_b}')}
            finally:
                conn.close()
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    # ── 1층: 적용 전 미리보기 ─────────────────────────────────────────────────
    def lab_preview(self, content: str) -> dict:
        """스키마 검증(dry-run) + 라이브 대비 diff. **클러스터를 변경하지 않는다.**

        kubectl diff 는 종료코드로 결과를 알린다(0=차이없음 / 1=차이있음 / ≥2=실패).
        그래서 `_run_kubectl_rc` 를 쓴다 — 종료코드가 없으면 정상 diff 를 오류로 신고한다.
        """
        text = (content or '').strip()
        if not text:
            return {'ok': False, 'error': '검증할 YAML 이 비어 있습니다.'}
        if not getattr(self.k8s, 'kubeconfig', ''):
            return {'ok': False, 'error': '연결되지 않음'}

        valid = self.validate_resource_yaml(text)
        out = {
            'ok': True,
            'targets': parse_targets(text),
            'warnings': scan_secrets(text),
            'valid': valid.get('valid'),
            'validate_mode': valid.get('mode'),
            'validate_errors': valid.get('errors') or [],
            'validate_message': valid.get('message') or valid.get('error') or '',
        }
        # 스키마부터 틀렸으면 diff 는 의미 없다 — 시간만 쓴다.
        if valid.get('ok') and valid.get('valid') is False:
            out['diff_text'] = ''
            out['has_diff'] = None
            return out

        rc, so, se = _run_kubectl_rc(self.k8s.kubeconfig, ['diff', '-f', '-'],
                                     timeout=40, stdin_input=text)
        if rc == 0:
            out.update({'diff_text': '', 'has_diff': False,
                        'diff_note': '라이브 상태와 동일합니다 — 적용해도 바뀌는 것이 없습니다.'})
        elif rc == 1:
            out.update({'diff_text': so, 'has_diff': True})
        else:
            # diff 실패는 치명적이지 않다 — 검증 결과는 이미 위에서 나왔다.
            out.update({'diff_text': '', 'has_diff': None,
                        'diff_error': (se or so or '알 수 없는 오류').strip()[:600]})
        return out

    # ── 2층: 적용 + 파급 관찰 ─────────────────────────────────────────────────
    def _lab_collect(self, namespaces: list) -> dict:
        """범위 한정 수집. take_snapshot(_report_collect, 전역 29단계) 을 쓰지 않는 이유는
        apply 마다 2번 돌리면 반복 테스트가 1분 단위가 되기 때문이다.

        반환 모양은 src/snapshot.py 의 비교 헬퍼가 먹을 수 있도록 평평한 dict 리스트.
        """
        k = self.k8s
        out = {key: [] for _, key, _ in __import__('src.yamllab', fromlist=['LAB_KINDS']).LAB_KINDS}

        def _pod_row(p):
            st = p.status
            ready = sum(1 for c in (st.container_statuses or []) if c.ready)
            total = len(st.container_statuses or [])
            restarts = sum((c.restart_count or 0) for c in (st.container_statuses or []))
            return {'namespace': p.metadata.namespace, 'name': p.metadata.name,
                    'phase': st.phase or '', 'ready': f'{ready}/{total}',
                    'restarts': restarts, 'node': p.spec.node_name or ''}

        def _wl_row(w):
            s = w.status
            return {'namespace': w.metadata.namespace, 'name': w.metadata.name,
                    'ready': getattr(s, 'ready_replicas', None) or 0,
                    'desired': getattr(w.spec, 'replicas', None)
                               if hasattr(w.spec, 'replicas') else
                               getattr(s, 'desired_number_scheduled', 0),
                    'images': ','.join(sorted(
                        c.image for c in (w.spec.template.spec.containers or [])))}

        for ns in (namespaces or []):
            try:
                out['pods'] += [_pod_row(p) for p in
                                k.core.list_namespaced_pod(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['deployments'] += [_wl_row(d) for d in
                                       k.apps.list_namespaced_deployment(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['statefulsets'] += [_wl_row(d) for d in
                                        k.apps.list_namespaced_stateful_set(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['daemonsets'] += [_wl_row(d) for d in
                                      k.apps.list_namespaced_daemon_set(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['replicasets'] += [
                    {'namespace': r.metadata.namespace, 'name': r.metadata.name,
                     'desired': r.spec.replicas or 0,
                     'ready': getattr(r.status, 'ready_replicas', None) or 0}
                    for r in k.apps.list_namespaced_replica_set(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['services'] += [
                    {'namespace': s.metadata.namespace, 'name': s.metadata.name,
                     'type': s.spec.type or '', 'cluster_ip': s.spec.cluster_ip or '',
                     'ports': ','.join(str(p.port) for p in (s.spec.ports or []))}
                    for s in k.core.list_namespaced_service(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['ingresses'] += [
                    {'namespace': i.metadata.namespace, 'name': i.metadata.name,
                     'hosts': ','.join(sorted(r.host or '' for r in (i.spec.rules or [])))}
                    for i in k.net.list_namespaced_ingress(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['configmaps'] += [
                    {'namespace': c.metadata.namespace, 'name': c.metadata.name,
                     'keys': ','.join(sorted((c.data or {}).keys()))}
                    for c in k.core.list_namespaced_config_map(ns, _request_timeout=10).items]
            except Exception:
                pass
            try:
                out['jobs'] += [
                    {'namespace': j.metadata.namespace, 'name': j.metadata.name,
                     'succeeded': j.status.succeeded or 0, 'failed': j.status.failed or 0}
                    for j in k.batch.list_namespaced_job(ns, _request_timeout=10).items]
            except Exception:
                pass
        return out

    def _lab_warnings(self, namespaces: list, since_ts) -> list:
        """적용 이후 발생한 Warning 이벤트만."""
        rows = []
        for ns in (namespaces or []):
            try:
                for e in self.k8s.core.list_namespaced_event(ns, _request_timeout=10).items:
                    if (e.type or '') != 'Warning':
                        continue
                    ts = e.last_timestamp or e.event_time or e.first_timestamp
                    if ts is not None and ts.timestamp() < since_ts:
                        continue
                    obj = e.involved_object
                    rows.append({
                        'namespace': ns,
                        'object': f'{(obj.kind or "")}/{(obj.name or "")}',
                        'reason': e.reason or '',
                        'message': (e.message or '')[:300],
                    })
            except Exception:
                pass
        return rows[:50]

    def lab_apply(self, mid=None, content: str = '', watch_s: int = 40) -> dict:
        """적용 + 파급 관찰 job 시작. job_id 반환 → lab_apply_status 로 폴링."""
        text = (content or '').strip()
        if not text:
            return {'ok': False, 'error': '적용할 YAML 이 비어 있습니다.'}
        if not getattr(self.k8s, 'connected', False):
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}

        try:
            watch_s = max(0, min(float(watch_s or 0), _WATCH_MAX_S))
        except Exception:
            watch_s = 40.0

        targets = parse_targets(text)
        namespaces = target_namespaces(targets)
        job_id = uuid.uuid4().hex[:12]
        _lab_jobs[job_id] = {
            'status': 'running', 'logs': [], 'cancel': False,
            'targets': targets, 'namespaces': namespaces,
            'apply_ok': None, 'apply_output': '', 'diff': None, 'warnings': [],
            'error': None, 'elapsed': 0.0,
        }
        job = _lab_jobs[job_id]

        def log(msg):
            job['logs'].append(msg)

        def run():
            t0 = time.time()
            try:
                log(f'[1/4] 적용 전 상태 수집 — 네임스페이스 {", ".join(namespaces) or "(없음)"}')
                before = self._lab_collect(namespaces)

                log('[2/4] kubectl apply 실행')
                res = self.apply_resource_yaml(text)
                job['apply_ok'] = bool(res.get('ok'))
                job['apply_output'] = res.get('output') or res.get('error') or ''
                log(('  적용 성공: ' if res.get('ok') else '  적용 실패: ')
                    + (job['apply_output'] or '').strip()[:300])
                if not res.get('ok'):
                    job['status'] = 'error'
                    job['error'] = job['apply_output']
                    return

                applied_ts = time.time()
                log(f'[3/4] 파급 관찰 ({int(watch_s)}초) — 새 ReplicaSet·Pod 등')
                deadline = applied_ts + watch_s
                after = self._lab_collect(namespaces)
                while time.time() < deadline and not job['cancel']:
                    time.sleep(min(_WATCH_POLL_S, max(0.1, deadline - time.time())))
                    if job['cancel']:
                        break
                    after = self._lab_collect(namespaces)
                    job['diff'] = scope_diff(before, after)
                    t = job['diff']['totals']
                    job['elapsed'] = round(time.time() - t0, 1)
                    log(f'  변화: 추가 {t["added"]} · 삭제 {t["removed"]} · 변경 {t["changed"]}')

                job['diff'] = scope_diff(before, after)
                job['warnings'] = self._lab_warnings(namespaces, applied_ts - 5)
                if job['cancel']:
                    log('  관찰 중단됨 (적용 자체는 되돌리지 않았습니다)')

                log('[4/4] 완료')
                job['status'] = 'done'
            except Exception as e:
                job['status'] = 'error'
                job['error'] = f'{type(e).__name__}: {e}'
                log(f'[오류] {job["error"]}')
            finally:
                job['elapsed'] = round(time.time() - t0, 1)
                # 적용 이력 기록 — 실패해도 job 결과에는 영향 없음
                try:
                    if mid:
                        conn = self._lab_db()
                        try:
                            item = get_manifest(conn, mid)
                            vid = item.get('current_version_id')
                            if vid:
                                record_apply(conn, vid, self._lab_cluster(),
                                             bool(job.get('apply_ok')),
                                             job.get('apply_output', ''), job.get('diff'))
                        finally:
                            conn.close()
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'job_id': job_id, 'namespaces': namespaces}

    def lab_apply_status(self, job_id: str) -> dict:
        """폴링. logs 는 이전 호출 이후 새로 쌓인 만큼만(반환 즉시 비움) — 보고서와 동일 방식."""
        job = _lab_jobs.get(job_id)
        if not job:
            return {'status': 'unknown', 'logs': []}
        logs, job['logs'] = job['logs'], []
        return {
            'status': job['status'], 'logs': logs,
            'apply_ok': job['apply_ok'], 'apply_output': job['apply_output'],
            'diff': job['diff'], 'warnings': job['warnings'],
            'error': job['error'], 'elapsed': job['elapsed'],
            'namespaces': job['namespaces'], 'targets': job['targets'],
        }

    def lab_apply_cancel(self, job_id: str) -> dict:
        job = _lab_jobs.get(job_id)
        if not job:
            return {'ok': False, 'error': '작업을 찾을 수 없습니다.'}
        job['cancel'] = True
        return {'ok': True}

    def lab_teardown(self, mid=None, content: str = '') -> dict:
        """테스트 정리 — `kubectl delete -f -`. 실험실에서 올린 걸 되돌릴 때."""
        text = (content or '').strip()
        if not text and mid:
            conn = self._lab_db()
            try:
                text = (get_manifest(conn, mid) or {}).get('content', '')
            finally:
                conn.close()
        if not text:
            return {'ok': False, 'error': '삭제할 YAML 이 없습니다.'}
        if not getattr(self.k8s, 'kubeconfig', ''):
            return {'ok': False, 'error': '연결되지 않음'}
        out, err = _run_kubectl(self.k8s.kubeconfig,
                                ['delete', '-f', '-', '--ignore-not-found'],
                                timeout=60, stdin_input=text)
        if err.strip() and 'deleted' not in (out + err).lower():
            return {'ok': False, 'error': err.strip()[:600]}
        return {'ok': True, 'output': (out or err).strip()}

    # ── 반출 ─────────────────────────────────────────────────────────────────
    def lab_export_text(self, ids: list) -> dict:
        """선택분을 멀티 문서 YAML 로 이어붙여 반환. 프론트가 클립보드에 넣는다."""
        try:
            conn = self._lab_db()
            try:
                items = export_items(conn, list(ids or []))
            finally:
                conn.close()
            if not items:
                return {'ok': False, 'error': '선택된 항목이 없습니다.'}
            return {'ok': True, 'text': join_documents(items), 'count': len(items)}
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    def lab_export_folder(self, ids: list, by_cluster: bool = True) -> dict:
        """폴더를 고르게 하고 파일 트리로 내보낸다.

        경로 계산은 순수 함수 plan_export 가 하고 여기서는 쓰기만 한다. 계산 결과가
        선택 폴더를 벗어나면 **쓰지 않고 실패**시킨다 — 이름에 `..` 나 구분자가 섞여도
        남의 파일을 건드리지 않게 하는 최종 방어선.
        """
        try:
            conn = self._lab_db()
            try:
                items = export_items(conn, list(ids or []))
            finally:
                conn.close()
            if not items:
                return {'ok': False, 'error': '선택된 항목이 없습니다.'}

            dest = self.browse_folder()
            if not dest:
                return {'ok': False, 'cancelled': True}
            root = Path(dest).resolve()

            written = []
            for entry in plan_export(items, by_cluster=bool(by_cluster)):
                target = (root / entry['rel_path']).resolve()
                if root not in target.parents:
                    return {'ok': False,
                            'error': f'경로가 선택 폴더를 벗어납니다: {entry["rel_path"]}'}
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(entry['content'], encoding='utf-8')
                written.append(entry['rel_path'])

            return {'ok': True, 'path': str(root), 'count': len(written), 'files': written}
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
