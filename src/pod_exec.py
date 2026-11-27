"""파드 exec 세션 매니저 — xterm.js 와 1:1 연결되는 클러스터 내장 셸.

인터페이스(start/recv/send/resize/close/snapshot/list)를 제공하고,
백엔드는 쿠버네티스 exec 스트림(WebSocket)을 사용한다. 외부 터미널을 띄우지 않고 Polaris 안에서 파드 셸을 쓴다.

설계:
  - 각 세션 = 한 kubernetes WSClient (connect_get_namespaced_pod_exec, tty=True)
  - kubeconfig 는 활성 클러스터 파일 경로를 받아 전용 ApiClient 로 격리 로드
    (load_kube_config 전역 상태 오염 방지 → 멀티클러스터 안전).
  - 출력은 non-blocking buffer 패턴: 백그라운드 reader 스레드가 ws.update() 로
    프레임을 받아 buffer 에 누적, frontend 가 recv() 로 가져감.
  - resize 는 exec RESIZE 채널(4)에 {"Width","Height"} JSON 전송.
  - WSClient 는 스레드-세이프 보장이 없어 update/write/close 를 io_lock 으로 직렬화.

주의: WSClient.read_stdout() 는 프레임 단위로 utf-8 디코딩된 str 을 준다. 멀티바이트
문자가 프레임 경계에 걸리면 드물게 깨질 수 있으나 대화형 셸에선 실질 영향 미미.
"""
import time
import json
import uuid
import threading
from dataclasses import dataclass, field
from typing import Optional


# 기본 셸 — bash 가 있으면 bash, 없으면 sh. tty 로 exec 하여 프롬프트/색상 유지.
_DEFAULT_SHELL_CMD = ['/bin/sh', '-c',
                      'if command -v bash >/dev/null 2>&1; then exec bash; else exec sh; fi']


@dataclass
class _PodSession:
    id:          str
    namespace:   str
    pod:         str
    container:   str
    ws:          object                              # kubernetes WSClient
    buffer:      list = field(default_factory=list)  # list[str]
    history:     list = field(default_factory=list)  # list[str]
    lock:        threading.Lock = field(default_factory=threading.Lock)   # buffer 보호
    io_lock:     threading.Lock = field(default_factory=threading.Lock)   # ws 소켓 op 직렬화
    closed:      bool = False
    exit_msg:    str = ''
    reader:      Optional[threading.Thread] = None
    started_at:  float = field(default_factory=time.time)
    last_recv:   float = field(default_factory=time.time)


class PodExecManager:
    """모든 활성 파드 exec 세션 관리."""

    DEFAULT_COLS = 80
    DEFAULT_ROWS = 24
    HISTORY_LIMIT = 1024 * 1024
    BUFFER_LIMIT = 1024 * 1024

    def __init__(self):
        self._sessions: dict[str, _PodSession] = {}
        self._lock = threading.Lock()

    # ── 세션 생성 ──────────────────────────────────────────────────────────
    def start(self, kubeconfig: str, namespace: str, pod: str,
              container: str = '', shell: str = '',
              cols: int = DEFAULT_COLS, rows: int = DEFAULT_ROWS) -> dict:
        if not kubeconfig:
            return {'ok': False, 'error': '클러스터에 연결되지 않았습니다.'}
        if not namespace or not pod:
            return {'ok': False, 'error': 'namespace/pod 가 필요합니다.'}
        try:
            from kubernetes import client, config
            from kubernetes.stream import stream
        except Exception as e:
            return {'ok': False, 'error': f'kubernetes 클라이언트 로드 실패: {e}'}

        try:
            cfg = client.Configuration()
            config.load_kube_config(config_file=kubeconfig, client_configuration=cfg)
            api_client = client.ApiClient(configuration=cfg)
            core = client.CoreV1Api(api_client)
        except Exception as e:
            return {'ok': False, 'error': f'kubeconfig 로드 실패: {e}'}

        command = [shell] if shell else list(_DEFAULT_SHELL_CMD)
        kwargs = dict(command=command, stderr=True, stdin=True, stdout=True,
                      tty=True, _preload_content=False)
        if container:
            kwargs['container'] = container
        try:
            ws = stream(core.connect_get_namespaced_pod_exec, pod, namespace, **kwargs)
        except Exception as e:
            return {'ok': False, 'error': f'exec 스트림 오픈 실패: {e}'}

        sid = f'pod-{uuid.uuid4().hex[:8]}'
        sess = _PodSession(id=sid, namespace=namespace, pod=pod, container=container, ws=ws)
        # 초기 창 크기 반영
        try:
            self._resize_ws(sess, cols, rows)
        except Exception:
            pass
        sess.reader = threading.Thread(target=self._reader_loop, args=(sess,),
                                       daemon=True, name=f'pod-exec-{sid}')
        with self._lock:
            self._sessions[sid] = sess
        sess.reader.start()
        return {'ok': True, 'session_id': sid, 'namespace': namespace,
                'pod': pod, 'container': container}

    # ── 백그라운드 reader ──────────────────────────────────────────────────
    def _reader_loop(self, sess: _PodSession) -> None:
        ws = sess.ws
        while not sess.closed:
            try:
                with sess.io_lock:
                    if not ws.is_open():
                        self._capture_exit(sess)
                        sess.closed = True
                        break
                    ws.update(timeout=0.05)
                    chunk = ''
                    if ws.peek_stdout():
                        chunk += ws.read_stdout()
                    if ws.peek_stderr():
                        chunk += ws.read_stderr()
                if chunk:
                    self._append(sess, chunk)
                else:
                    time.sleep(0.01)
            except Exception:
                sess.closed = True
                break

    def _capture_exit(self, sess: _PodSession) -> None:
        """종료 시 exec ERROR 채널에서 상태 메시지 추출(성공/실패 사유)."""
        try:
            from kubernetes.stream.ws_client import ERROR_CHANNEL
            raw = sess.ws.read_channel(ERROR_CHANNEL, timeout=0)
            if raw:
                try:
                    obj = json.loads(raw)
                    status = obj.get('status')
                    if status and status != 'Success':
                        # NonZeroExitCode 등 사유 요약
                        msg = obj.get('message') or ''
                        sess.exit_msg = (msg or status)[:300]
                except Exception:
                    sess.exit_msg = str(raw)[:300]
        except Exception:
            pass

    def _append(self, sess: _PodSession, data: str) -> None:
        with sess.lock:
            sess.buffer.append(data)
            sess.history.append(data)
            self._cap(sess.buffer, self.BUFFER_LIMIT)
            self._cap(sess.history, self.HISTORY_LIMIT)

    @staticmethod
    def _cap(chunks: list, limit: int) -> None:
        total = sum(len(c) for c in chunks)
        while total > limit and len(chunks) > 1:
            total -= len(chunks.pop(0))

    # ── read / write ─────────────────────────────────────────────────────
    def recv(self, session_id: str) -> dict:
        sess = self._get(session_id)
        if sess is None:
            return {'ok': False, 'error': 'session 없음'}
        with sess.lock:
            data = ''.join(sess.buffer)
            sess.buffer.clear()
        sess.last_recv = time.time()
        return {'ok': True, 'data': data, 'closed': sess.closed,
                'exit_msg': sess.exit_msg if sess.closed else ''}

    def snapshot(self, session_id: str) -> dict:
        sess = self._get(session_id)
        if sess is None:
            return {'ok': False, 'error': 'session 없음'}
        with sess.lock:
            data = ''.join(sess.history)
            sess.buffer.clear()
        sess.last_recv = time.time()
        return {'ok': True, 'history': data, 'history_bytes': len(data),
                'closed': sess.closed}

    def send(self, session_id: str, data: str) -> dict:
        sess = self._get(session_id)
        if sess is None:
            return {'ok': False, 'error': 'session 없음'}
        if sess.closed:
            return {'ok': False, 'error': 'session 종료됨'}
        try:
            with sess.io_lock:
                sess.ws.write_stdin(data)
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def resize(self, session_id: str, cols: int, rows: int) -> dict:
        sess = self._get(session_id)
        if sess is None:
            return {'ok': False, 'error': 'session 없음'}
        try:
            with sess.io_lock:
                self._resize_ws(sess, cols, rows)
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    @staticmethod
    def _resize_ws(sess: _PodSession, cols: int, rows: int) -> None:
        from kubernetes.stream.ws_client import RESIZE_CHANNEL
        c = max(1, min(int(cols or 80), 1000))
        r = max(1, min(int(rows or 24), 1000))
        sess.ws.write_channel(RESIZE_CHANNEL, json.dumps({'Width': c, 'Height': r}))

    # ── 종료 ──────────────────────────────────────────────────────────────
    def close(self, session_id: str) -> dict:
        with self._lock:
            sess = self._sessions.pop(session_id, None)
        if sess is None:
            return {'ok': False, 'error': 'session 없음'}
        sess.closed = True
        try:
            with sess.io_lock:
                sess.ws.close()
        except Exception:
            pass
        return {'ok': True}

    def close_all(self) -> None:
        with self._lock:
            ids = list(self._sessions.keys())
        for sid in ids:
            self.close(sid)

    def list(self) -> list:
        with self._lock:
            sessions = list(self._sessions.values())
        return [{'id': s.id, 'namespace': s.namespace, 'pod': s.pod,
                 'container': s.container, 'closed': s.closed,
                 'started_at': s.started_at, 'last_recv': s.last_recv}
                for s in sessions]

    def _get(self, session_id: str) -> Optional[_PodSession]:
        with self._lock:
            return self._sessions.get(session_id)
