# -*- coding: utf-8 -*-
"""ResourceWatchManager — kubernetes watch API 기반 실시간 리소스 갱신.

파드 exec(pod_exec.py
PodExecManager)과 동일한 인터페이스 형태(start/recv/close/list, 백그라운드 reader
스레드 + non-blocking buffer + 프론트 폴링)를 리소스 watch 스트림에 적용한다.

범위(v1): 가장 변화가 잦고 가치가 큰 **파드**만 지원. 다른 kind 는 `_MAPPERS` 에
매퍼 함수를 추가하면 확장 가능하지만, k8s.py 의 15개 GETTERS 를 한 번에 모두
증분(watch) 매핑으로 리팩터링하는 위험을 피하기 위해 이번 버전은 파드로 한정한다.
(다른 kind 는 기존 수동 새로고침 그대로 — 회귀 위험 없음.)

설계:
  - 세션 = 전용 ApiClient(격리 로드, 멀티클러스터 안전) + kubernetes.watch.Watch().
  - watch 스트림은 유한 시간 후 서버가 끊거나 네트워크 오류로 종료될 수 있어,
    reader 루프가 예외를 잡고 짧은 backoff 후 자동 재연결한다(사용자가 계속
    켜두면 최대한 끊기지 않게).
  - 이벤트는 {type: ADDED|MODIFIED|DELETED, row: {...}} 형태로 buffer 에 쌓이고,
    recv() 가 이를 비워 반환 — 파드 exec 와 같은 폴링 계약.
"""
import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Optional

from src.k8s import _age


def _map_pod(p):
    """kubernetes V1Pod 객체 하나 → get_pods() 와 동일한 row shape.

    k8s.py K8sManager.get_pods() 의 매핑 로직과 의도적으로 동일하게 유지한다
    (list 결과와 watch 증분 결과의 필드가 어긋나지 않도록). get_pods() 자체는
    건드리지 않아 기존 전체 목록 조회 경로에는 회귀 위험이 없다.
    """
    spec = getattr(p, 'spec', None)
    status = getattr(p, 'status', None)
    total = len(spec.containers) if spec and spec.containers else 0
    ready = restarts = 0
    if status and status.container_statuses:
        for cs in status.container_statuses:
            if cs.ready:
                ready += 1
            restarts += cs.restart_count or 0
    return {
        'name':      p.metadata.name,
        'namespace': p.metadata.namespace,
        'ready':     f'{ready}/{total}',
        'status':    (status.phase if status else None) or 'Unknown',
        'restarts':  str(restarts),
        'node':      (spec.node_name if spec else None) or 'N/A',
        'age':       _age(p.metadata.creation_timestamp),
        '_ns': p.metadata.namespace, '_kind': 'pod',
    }


# kind(짧은 이름) → 단일 객체 매퍼. 여기 추가하면 해당 kind 도 watch 지원.
_MAPPERS = {
    'pods': _map_pod,
}

_RECONNECT_BACKOFF = 1.5   # 스트림 오류/종료 후 재연결 대기(초)


# 읽기 타임아웃(v1.5.28 검토) — 예전엔 없어서 VPN 이 조용히 끊기면 watch 가 영영 멈춰 「실시간」 목록이 굳었다.
# 서버 쪽 timeout_seconds 보다 조금 길게 — 정상이면 서버가 먼저 끊고, 네트워크가 죽었으면 이 값에서 끊겨 다시 연결한다
_WATCH_SERVER_TIMEOUT_S = 300
_WATCH_REQUEST_TIMEOUT = (10, 330)

@dataclass
class _WatchSession:
    id:        str
    kind:      str
    namespace: str
    watch:     object                                  # kubernetes.watch.Watch
    buffer:    list = field(default_factory=list)       # list[{'type','row'}]
    lock:      threading.Lock = field(default_factory=threading.Lock)
    closed:    bool = False
    error:     str = ''
    reader:    Optional[threading.Thread] = None
    started_at: float = field(default_factory=time.time)
    last_recv:  float = field(default_factory=time.time)


class ResourceWatchManager:
    """모든 활성 리소스 watch 세션 관리."""

    BUFFER_LIMIT = 5000   # 세션당 최대 누적 이벤트(과도한 이벤트 폭주 시 앞부분 drop)

    def __init__(self):
        self._sessions: dict[str, _WatchSession] = {}
        self._lock = threading.Lock()

    @staticmethod
    def supported_kinds():
        return sorted(_MAPPERS.keys())

    def start(self, kubeconfig: str, kind: str, namespace: str = '') -> dict:
        kind = (kind or '').strip().lower()
        mapper = _MAPPERS.get(kind)
        if mapper is None:
            return {'ok': False, 'error': f"watch 미지원 kind: {kind!r} "
                    f"(지원: {', '.join(self.supported_kinds())})"}
        if not kubeconfig:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        try:
            from kubernetes import client, config, watch
        except Exception as e:
            return {'ok': False, 'error': f'kubernetes 클라이언트 로드 실패: {e}'}
        try:
            cfg = client.Configuration()
            config.load_kube_config(config_file=kubeconfig, client_configuration=cfg)
            core = client.CoreV1Api(client.ApiClient(configuration=cfg))
        except Exception as e:
            return {'ok': False, 'error': f'kubeconfig 로드 실패: {e}'}

        w = watch.Watch()
        sid = f'watch-{uuid.uuid4().hex[:8]}'
        sess = _WatchSession(id=sid, kind=kind, namespace=namespace or '', watch=w)
        sess.reader = threading.Thread(
            target=self._reader_loop, args=(sess, core, mapper),
            daemon=True, name=f'res-watch-{sid}')
        with self._lock:
            self._sessions[sid] = sess
        sess.reader.start()
        return {'ok': True, 'watch_id': sid, 'kind': kind, 'namespace': namespace or ''}

    def _reader_loop(self, sess: _WatchSession, core, mapper):
        while not sess.closed:
            sess.error = ''   # 재연결 시도 시작 — 이전 오류 상태 정리
            try:
                if sess.namespace:
                    stream = sess.watch.stream(core.list_namespaced_pod, sess.namespace,
                                               timeout_seconds=_WATCH_SERVER_TIMEOUT_S,
                                               _request_timeout=_WATCH_REQUEST_TIMEOUT)
                else:
                    stream = sess.watch.stream(core.list_pod_for_all_namespaces,
                                               timeout_seconds=_WATCH_SERVER_TIMEOUT_S,
                                               _request_timeout=_WATCH_REQUEST_TIMEOUT)
                for ev in stream:
                    if sess.closed:
                        break
                    etype = ev.get('type', 'MODIFIED')
                    obj = ev.get('object')
                    if obj is None:
                        continue
                    try:
                        row = mapper(obj)
                    except Exception:
                        continue
                    self._append(sess, {'type': etype, 'row': row})
                # 스트림이 정상 종료(timeout_seconds 도달 등) — closed 아니면 재연결
            except Exception as e:
                sess.error = str(e)[:300]
                if not sess.closed:
                    time.sleep(_RECONNECT_BACKOFF)

    def _append(self, sess: _WatchSession, item: dict) -> None:
        with sess.lock:
            sess.buffer.append(item)
            if len(sess.buffer) > self.BUFFER_LIMIT:
                del sess.buffer[:len(sess.buffer) - self.BUFFER_LIMIT]

    def recv(self, watch_id: str) -> dict:
        sess = self._get(watch_id)
        if sess is None:
            return {'ok': False, 'error': 'watch session 없음'}
        with sess.lock:
            events = sess.buffer
            sess.buffer = []
        sess.last_recv = time.time()
        return {'ok': True, 'events': events, 'closed': sess.closed,
                'error': sess.error if sess.closed else ''}

    def close(self, watch_id: str) -> dict:
        with self._lock:
            sess = self._sessions.pop(watch_id, None)
        if sess is None:
            return {'ok': False, 'error': 'watch session 없음'}
        sess.closed = True
        try:
            sess.watch.stop()
        except Exception:
            pass
        return {'ok': True}

    def close_all(self) -> None:
        with self._lock:
            ids = list(self._sessions.keys())
        for wid in ids:
            self.close(wid)

    def list(self) -> list:
        with self._lock:
            sessions = list(self._sessions.values())
        return [{'id': s.id, 'kind': s.kind, 'namespace': s.namespace,
                 'closed': s.closed, 'started_at': s.started_at,
                 'last_recv': s.last_recv} for s in sessions]

    def _get(self, watch_id: str) -> Optional[_WatchSession]:
        with self._lock:
            return self._sessions.get(watch_id)
