"""K8sManager 클래스 + Kubernetes 도메인 헬퍼.

이 모듈은 kubernetes Python 라이브러리에 의존합니다. PolarisAPI 의 모든 K8s
호출은 이 모듈을 통해 이루어집니다.

구성:
  - 파싱 헬퍼: _age, _parse_cpu, _parse_mem, _pct, _build_node_metrics, ...
  - 보안: _redact_secret_yaml, _redact_secret_describe (시크릿 마스킹)
  - 검증: RFC1123 정규식 + _build_pod_exec_args / _build_port_forward_spec
  - ArgoCD spec 빌더
  - K8sManager 클래스: kubernetes 클라이언트 래퍼 (각 리소스 getter)
"""
import re
import os
import json
import atexit
import tempfile
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.tools import _NO_WINDOW, _find_helm


# ── 평문 임시 kubeconfig 크래시-세이프 정리 (v1.2.3) ───────────────────────────
# vault content 로 연결하면 kubectl 이 파일 경로를 필요로 해 %TEMP% 에 평문
# kubeconfig(polaris-kc-*.yaml)를 잠깐 만든다. 정상 흐름은 disconnect 시 삭제하지만,
# 명시적 disconnect 없이 창만 닫혀 프로세스가 끝나면 평문 파일이 남을 수 있다.
# 이 프로세스가 만든 임시 파일을 추적해 인터프리터 종료 시(atexit) 일괄 삭제한다.
# (우리가 만든 파일만 지우므로 다중 인스턴스에도 안전.)
_TEMP_KUBECONFIGS: set = set()


@atexit.register
def _purge_temp_kubeconfigs() -> None:
    for _p in list(_TEMP_KUBECONFIGS):
        try:
            os.remove(_p)
        except Exception:
            pass
    _TEMP_KUBECONFIGS.clear()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == 'nt':
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            try:
                code = ctypes.c_ulong()
                return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
            finally:
                k32.CloseHandle(h)
        except Exception:
            return True                                     # 모르면 지우지 않는다
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return True


def sweep_stale_temp_kubeconfigs(tmpdir: str = None, now: float = None) -> int:
    """강제 종료 · 정전으로 atexit 가 못 돈 뒤 %TEMP% 에 남은 평문 kubeconfig 를 지운다(v1.5.28 검토).

    polaris-kc-<pid>-*.yaml — 그 프로세스가 이미 없으면 지운다(다른 Polaris 가 쓰는 중인 것은 둔다).
    예전 이름(polaris-kc-<무작위>.yaml)은 12시간 넘은 것만. 지운 개수."""
    import glob
    import time as _t
    tmpdir = tmpdir or tempfile.gettempdir()
    now = _t.time() if now is None else now
    n = 0
    for p in glob.glob(os.path.join(tmpdir, 'polaris-kc-*.yaml')):
        if p in _TEMP_KUBECONFIGS:
            continue
        stem = os.path.basename(p)[len('polaris-kc-'):]
        head = stem.split('-', 1)[0]
        try:
            if head.isdigit() and '-' in stem:
                if _pid_alive(int(head)):
                    continue
            elif now - os.path.getmtime(p) < 12 * 3600:
                continue
            os.remove(p)
            n += 1
        except Exception:
            pass
    return n

# ── kubernetes 라이브러리 ─────────────────────────────────────────────────────
# (v1.3.73, 성능 점검 P1) 앱 시작 2.1초 중 1.55초가 이 라이브러리를 불러오는 데 들었다
# (`kubernetes.client` 가 모든 API 모델을 한꺼번에 읽는다). 창이 뜨는 것과는 무관하므로
# **처음 쓸 때** 불러온다 — `k8s.X` · `k8s_cfg.X` 로 쓰는 코드는 그대로다. 있는지 여부는
# 불러오지 않고 find_spec 으로만 본다. 시작 몇 초 뒤 백그라운드로 미리 불러 둔다(runtime).
import importlib
import importlib.util
import threading as _threading

HAS_K8S = importlib.util.find_spec('kubernetes') is not None
_K8S_LOAD_LOCK = _threading.Lock()
_K8S_READY = False


def _after_k8s_import():
    """라이브러리를 처음 불러온 직후 한 번 — API 호출 타임아웃·재시도 기본값(v1.3.41)."""
    global _K8S_READY
    with _K8S_LOAD_LOCK:
        if _K8S_READY:
            return
        from src import k8s_http as _k8s_http
        _k8s_http.install()
        _K8S_READY = True


class _LazyModule:
    """첫 속성 접근 때 import 하는 모듈 대리자."""

    def __init__(self, name):
        object.__setattr__(self, '_lazy_name', name)
        object.__setattr__(self, '_lazy_mod', None)

    def _lazy_load(self):
        mod = object.__getattribute__(self, '_lazy_mod')
        if mod is None:
            mod = importlib.import_module(object.__getattribute__(self, '_lazy_name'))
            _after_k8s_import()          # 클라이언트를 만들기 **전에** 기본값을 입힌다
            object.__setattr__(self, '_lazy_mod', mod)
        return mod

    def __getattr__(self, attr):
        return getattr(self._lazy_load(), attr)

    def __setattr__(self, attr, value):          # 테스트가 속성을 갈아 끼울 때
        setattr(self._lazy_load(), attr, value)


k8s = _LazyModule('kubernetes.client')
k8s_cfg = _LazyModule('kubernetes.config')


def _pyinstaller_hint():   # 부르지 않는다 — 이름으로 부르는 import 를 PyInstaller 가 못 따라가므로 정적 표시
    import kubernetes.client  # noqa: F401
    import kubernetes.config  # noqa: F401


def preload_k8s() -> bool:
    """백그라운드에서 미리 불러 둔다 — 첫 클러스터 연결이 1.5초 느려지지 않게."""
    if not HAS_K8S:
        return False
    try:
        k8s._lazy_load()
        k8s_cfg._lazy_load()
        return True
    except Exception:
        return False

# 큰 목록은 모델 변환 없이 읽는다 (v1.3.42 — 파드 2000개 2.3초 → 수십 ms, src/k8s_fast.py).
# 테스트가 모델 경로와 결과를 나란히 비교할 때만 끈다.
_FAST_LISTS = True


def _list(fn, *args, **kw):
    """kubernetes list_* 호출 — 기본은 빠른 길(KList), _FAST_LISTS 가 꺼지면 모델."""
    if _FAST_LISTS:
        from src.k8s_fast import fast_list
        return fast_list(fn, *args, **kw)
    return fn(*args, **kw)


# ─────────────────────────────────────────────────────────────────────────────
# 파싱 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _age(ts):
    """kubernetes 객체의 creation_timestamp → 경과 시간 문자열."""
    if not ts:
        return 'N/A'
    s = int((datetime.now(timezone.utc) - ts).total_seconds())
    if s < 60:    return f'{s}s'
    if s < 3600:  return f'{s // 60}m'
    if s < 86400: return f'{s // 3600}h'
    return f'{s // 86400}d'


# ── 파드 이상 판정 (대시보드 「주의가 필요한 파드」) ──────────────────────────
#
# 왜 phase 만으로 안 되는가 — **CrashLoopBackOff 파드의 phase 는 `Running` 이다.**
# 파드는 떠 있고 컨테이너만 재시작을 반복하는 상태라서 그렇다. 그래서 phase 로만
# 걸러내면 가장 대표적인 장애 파드가 '정상'으로 분류된다. kubectl 의 STATUS 열도
# phase 가 아니라 컨테이너 상태에서 계산한 값이다.
#
# 컨테이너가 뜨는 중인 정상 과정. 이 사유는 문제로 보지 않는다.
_BENIGN_WAITING = frozenset({'ContainerCreating', 'PodInitializing'})
# 정상 종료. Job/CronJob 파드가 여기 걸린다.
_BENIGN_TERMINATED = frozenset({'Completed'})


def _pod_problem_reason(pod) -> str:
    """파드가 문제인 사유 한 개 (없으면 빈 문자열).

    허용목록(CrashLoopBackOff, ImagePullBackOff, …)을 쓰지 않는다 — 새 사유가
    생기면 조용히 놓친다. **정상인 사유만 제외**하고 나머지는 전부 문제로 본다.
    init 컨테이너를 먼저 본다 (init 이 막히면 앱 컨테이너는 아직 상태가 없다).
    """
    st = getattr(pod, 'status', None)
    if st is None:
        return ''
    # pod 레벨 사유 (Evicted 등) 가 가장 구체적
    if (st.reason or '') and st.reason != 'Completed':
        return st.reason
    for group in (st.init_container_statuses, st.container_statuses):
        for cs in (group or []):
            state = getattr(cs, 'state', None)
            if state is None:
                continue
            w = getattr(state, 'waiting', None)
            if w is not None and (w.reason or '') not in _BENIGN_WAITING:
                return w.reason or 'Waiting'
            t = getattr(state, 'terminated', None)
            if t is not None and (t.reason or '') not in _BENIGN_TERMINATED:
                return t.reason or 'Terminated'
    return ''


def _pod_last_restart_at(pod) -> str:
    """마지막 재시작 시각 (ISO8601, 없으면 빈 문자열).

    누적 횟수(restartCount)는 리셋되지 않아 '언제' 재시작했는지 알 수 없다.
    lastState.terminated.finishedAt = 직전 인스턴스가 죽은 시각 = 재시작 순간.
    그게 없으면(첫 기동 후 재시작만 있고 종료 기록이 유실된 경우) 현재 인스턴스의
    startedAt 으로 대체한다.
    """
    best = None
    st = getattr(pod, 'status', None)
    if st is None:
        return ''
    for group in (st.init_container_statuses, st.container_statuses):
        for cs in (group or []):
            if not (cs.restart_count or 0):
                continue
            cand = None
            last = getattr(cs, 'last_state', None)
            term = getattr(last, 'terminated', None) if last is not None else None
            if term is not None and term.finished_at:
                cand = term.finished_at
            else:
                running = getattr(getattr(cs, 'state', None), 'running', None)
                if running is not None and running.started_at:
                    cand = running.started_at
            if cand is not None and (best is None or cand > best):
                best = cand
    return best.isoformat() if best is not None else ''


def _pod_is_abnormal(pod, ready: int, total: int) -> bool:
    """지금 주의가 필요한 파드인가.

    Succeeded(정상 완료)는 제외. 그 외에는 문제 사유가 있거나, Running 인데
    컨테이너가 다 Ready 가 아니면 비정상으로 본다.
    """
    phase = (getattr(getattr(pod, 'status', None), 'phase', '') or '')
    if phase == 'Succeeded':
        return False
    if _pod_problem_reason(pod):
        return True
    if phase != 'Running':
        return True
    return total > 0 and ready < total


def _collect_fail(errors, what, e=None):
    """수집 실패를 호출한 쪽이 넘긴 목록에 적는다 (v1.4.13, 보고서 수집 전용).

    getter 들은 예외를 삼키고 [] / {} 를 돌려준다 — 화면에는 그게 맞지만 보고서는
    「0건」 과 「수집하지 못함」 을 구분해야 한다(못 본 것을 「정상」 으로 적으면 안 된다).
    errors 를 넘기지 않는 기존 호출은 아무것도 달라지지 않는다.
    """
    if errors is None:
        return
    errors.append(f'{what}: {type(e).__name__}: {str(e)[:160]}' if e is not None else what)


def _controller_owner(meta):
    """ownerReferences 중 컨트롤러 하나 → (kind, name). 없으면 ('', '')."""
    refs = getattr(meta, 'owner_references', None) or []
    for r in refs:
        if getattr(r, 'controller', False):
            return (getattr(r, 'kind', '') or '', getattr(r, 'name', '') or '')
    if refs:
        return (getattr(refs[0], 'kind', '') or '', getattr(refs[0], 'name', '') or '')
    return ('', '')


def _parse_iso(s):
    """ISO8601 → tz-aware datetime. 실패 시 None. 'Z' 접미도 허용."""
    if not s:
        return None
    try:
        txt = str(s).strip()
        if txt.endswith('Z'):
            txt = txt[:-1] + '+00:00'
        dt = datetime.fromisoformat(txt)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def select_attention_pods(pods: list, now=None, days: int = 3, limit: int = 10) -> dict:
    """대시보드에 띄울 「주의가 필요한 파드」 선별. **순수 함수** (클러스터 불필요).

    포함 규칙이 **두 개**다:
      ① 지금 비정상  → 재시작 이력과 무관하게 **항상** 포함
      ② 정상인데 최근 `days` 일 내 재시작 → 포함 (재발 조짐)

    ①이 필요한 이유: ImagePullBackOff·Pending·CreateContainerConfigError 파드는
    한 번도 못 떴으므로 restartCount 가 0 이고 재시작 시각도 없다. '기간 내 재시작'
    으로만 거르면 **지금 가장 급한 파드가 목록에서 사라진다.**

    반환: {items, total, truncated, abnormal_count, restart_count}
      total 을 함께 주는 이유 — limit 으로 조용히 자르면 "10개뿐"으로 오독된다.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max(0, days))

    picked = []
    abnormal_n = restart_n = 0
    for p in (pods or []):
        is_abn = bool(p.get('abnormal'))
        at = _parse_iso(p.get('restarted_at'))
        recent = at is not None and at >= cutoff
        if not (is_abn or recent):
            continue
        if is_abn:
            abnormal_n += 1
        if recent:
            restart_n += 1
        picked.append({**p, 'recent_restart': recent, '_restart_dt': at})

    def _key(p):
        # 비정상 먼저 → 최근 재시작 순 → 누적 재시작 많은 순
        ts = p['_restart_dt'].timestamp() if p['_restart_dt'] else 0
        try:
            restarts = int(p.get('restarts') or 0)
        except Exception:
            restarts = 0
        return (0 if p.get('abnormal') else 1, -ts, -restarts)

    picked.sort(key=_key)
    items = [{k: v for k, v in p.items() if k != '_restart_dt'} for p in picked[:limit]]
    return {
        'items':          items,
        'total':          len(picked),
        'truncated':      len(picked) > len(items),
        'abnormal_count': abnormal_n,
        'restart_count':  restart_n,
        'window_days':    days,
    }


def _jsonpath_get(obj, path):
    """CRD additionalPrinterColumns 의 단순 JSONPath(.a.b.c) 값 추출.

    printer column 의 jsonPath 는 대부분 `.status.phase`, `.spec.replicas`,
    `.metadata.creationTimestamp` 같은 단순 dot 경로. 배열 인덱스나 필터는
    드물어 미지원(빈 문자열 반환). 값이 dict/list 면 빈 문자열.
    """
    if not path:
        return ''
    p = str(path).lstrip('.')
    cur = obj
    for part in p.split('.'):
        if not part:
            continue
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return ''
    if cur is None:
        return ''
    if isinstance(cur, bool):
        return 'true' if cur else 'false'
    if isinstance(cur, (str, int, float)):
        return str(cur)
    return ''   # dict/list 등 복합 타입은 표시 생략


def _parse_ts(value):
    """ISO8601 타임스탬프 문자열(또는 datetime) → tz-aware datetime. 실패 시 None.

    custom object(dict) 의 metadata.creationTimestamp 는 '2024-01-01T00:00:00Z'
    같은 문자열이므로 _age() 에 넘기기 전에 변환한다.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        s = str(value).replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _parse_cpu(s):
    """metrics.k8s.io CPU 값 ('123n', '45m', '0.1') → millicore (int)."""
    if not s:
        return 0
    try:
        if s.endswith('n'):   return int(s[:-1]) // 1_000_000
        if s.endswith('u'):   return int(s[:-1]) // 1_000
        if s.endswith('m'):   return int(s[:-1])
        return int(float(s) * 1000)
    except Exception:
        return 0


def _parse_mem(s):
    """memory 값 ('123Ki', '456Mi', '789') → bytes (int)."""
    if not s:
        return 0
    try:
        units = {
            'Ki': 1024, 'Mi': 1024 ** 2, 'Gi': 1024 ** 3, 'Ti': 1024 ** 4,
            'K':  1000, 'M':  1000 ** 2, 'G':  1000 ** 3, 'T':  1000 ** 4,
        }
        for u, mul in units.items():
            if s.endswith(u):
                return int(s[: -len(u)]) * mul
        return int(s)
    except Exception:
        return 0


def _pct(used, total):
    if not total:
        return None
    return min(round((used or 0) / total * 100), 100)


def _build_node_metrics(items):
    out = []
    for item in items or []:
        usage = item.get('usage', {})
        name = item.get('metadata', {}).get('name', '')
        if not name:
            continue
        out.append({
            'name': name,
            'cpu_m': _parse_cpu(usage.get('cpu', '0')),
            'mem_mi': _parse_mem(usage.get('memory', '0')) // (1024 * 1024),
        })
    return out


def _apply_node_metric(node, metric):
    enriched = dict(node)
    if not metric:
        enriched.update({
            'metrics_available': False,
            'cpu_used_m': 0,
            'mem_used_mi': 0,
            'cpu_pct': None,
            'mem_pct': None,
        })
        return enriched

    cpu_used = int(metric.get('cpu_m') or 0)
    mem_used = int(metric.get('mem_mi') or 0)
    enriched.update({
        'metrics_available': True,
        'cpu_used_m': cpu_used,
        'mem_used_mi': mem_used,
        'cpu_pct': _pct(cpu_used, enriched.get('cpu_alloc_m') or 0),
        'mem_pct': _pct(mem_used, enriched.get('mem_alloc_mi') or 0),
    })
    return enriched


# ─────────────────────────────────────────────────────────────────────────────
# 연결 에러 진단 (사용자 친화적 메시지로 변환)
# ─────────────────────────────────────────────────────────────────────────────

def _diagnose_connect_error(e: Exception, path: str) -> str:
    """연결 실패 원인을 사용자 친화적 메시지로 변환."""
    import ssl
    msg     = str(e)
    msg_low = msg.lower()

    # ── kubeconfig 파일 문제 ──────────────────────────────────────────────────
    if isinstance(e, FileNotFoundError):
        return f'kubeconfig 파일을 찾을 수 없습니다: {path}'

    try:
        import yaml
        if isinstance(e, yaml.YAMLError):
            return 'kubeconfig 파일 형식이 올바르지 않습니다 (YAML 파싱 오류).'
    except ImportError:
        pass

    if HAS_K8S:
        try:
            from kubernetes.config.config_exception import ConfigException
            if isinstance(e, ConfigException):
                if 'no configuration' in msg_low or 'invalid' in msg_low or 'context' in msg_low:
                    return ('kubeconfig 구성 오류입니다.\n'
                            '• 파일에 유효한 컨텍스트가 있는지 확인하세요.\n'
                            f'• 상세: {msg}')
                return f'kubeconfig 구성 오류: {msg}'
        except ImportError:
            pass

    # ── SSL / TLS 인증서 문제 ─────────────────────────────────────────────────
    if isinstance(e, (ssl.SSLError, ssl.SSLCertVerificationError)) or \
            'ssl' in msg_low or 'certificate verify failed' in msg_low:
        return ('TLS/SSL 인증서 오류입니다.\n'
                '• 클러스터 CA 인증서가 kubeconfig에 올바르게 포함되어 있는지 확인하세요.\n'
                '• 자체 서명 인증서라면 insecure-skip-tls-verify 옵션을 확인하세요.')

    # ── 인증 / 권한 문제 ──────────────────────────────────────────────────────
    if HAS_K8S:
        try:
            from kubernetes.client.exceptions import ApiException
            if isinstance(e, ApiException):
                if e.status == 401:
                    return ('인증 실패 (401 Unauthorized).\n'
                            '• 클러스터 자격증명(토큰/인증서)이 만료됐거나 올바르지 않습니다.\n'
                            '• kubeconfig를 다시 발급받으세요.')
                if e.status == 403:
                    return ('권한 없음 (403 Forbidden).\n'
                            '• 현재 사용자에게 클러스터 접근 권한이 없습니다.\n'
                            '• 클러스터 관리자에게 RBAC 권한을 요청하세요.')
                return f'API 오류 ({e.status}): {e.reason}'
        except ImportError:
            pass

    # 지연 import (circular import 방지)
    from src.tools import _extract_host_port

    # ── 연결 타임아웃 ─────────────────────────────────────────────────────────
    if isinstance(e, TimeoutError) or 'timed out' in msg_low or 'timeout' in msg_low:
        hp = _extract_host_port(msg)
        return (f'연결 시간 초과 ({hp}).\n'
                '• 서버가 응답하지 않습니다. 네트워크/VPN 연결 상태를 확인하세요.\n'
                '• 방화벽이 해당 포트(일반적으로 6443)를 차단하고 있을 수 있습니다.')

    # ── 포트 접근 불가 / 연결 거부 ───────────────────────────────────────────
    if ('connection refused' in msg_low or 'newconnectionerror' in msg_low
            or 'max retries exceeded' in msg_low or 'failed to establish' in msg_low
            or 'nodename nor servname' in msg_low or 'name or service not known' in msg_low):
        hp = _extract_host_port(msg)
        return (f'서버({hp})에 접근할 수 없습니다.\n'
                '• 네트워크/VPN 연결 상태를 확인하세요.\n'
                f'• 방화벽이 {hp} 포트를 허용하는지 확인하세요.\n'
                '• kubeconfig의 server 주소가 올바른지 확인하세요.\n'
                '• kubectl cluster-info 로 클러스터 상태를 직접 확인해보세요.')

    # ── DNS 해석 실패 ─────────────────────────────────────────────────────────
    if 'getaddrinfo' in msg_low or 'dns' in msg_low or 'name resolution' in msg_low:
        hp = _extract_host_port(msg)
        return (f'DNS 해석 실패 ({hp}).\n'
                '• 호스트명을 IP로 해석할 수 없습니다.\n'
                '• VPN 연결 여부 및 DNS 설정을 확인하세요.')

    # ── 기타 ─────────────────────────────────────────────────────────────────
    return f'연결 실패: {msg}'


# ─────────────────────────────────────────────────────────────────────────────
# RFC1123 검증 + Secret 마스킹
# ─────────────────────────────────────────────────────────────────────────────

# RFC1123 DNS label (네임스페이스 / 컨테이너) : 1~63자, 영소문자·숫자·하이픈
# RFC1123 DNS subdomain (파드 이름) : 최대 253자, 점(.) 포함 가능
_RFC1123_DNS_LABEL     = re.compile(r'^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$')
_RFC1123_DNS_SUBDOMAIN = re.compile(
    r'^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?(\.[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?)*$'
)


# ── kubectl 인자 검사 (v1.5.28 검토) ─────────────────────────────────────────
# kind · 이름 · 네임스페이스 · 컨테이너는 kubectl argv 에 그대로 들어간다. 「--all」 · 「--kubeconfig=\\host\x」 ·
# 「--server=…」 · 「secret,configmap」 같은 값이 오면 다른 뜻이 된다(전부 지우기 · 다른 kubeconfig 의 exec 실행 ·
# 토큰을 다른 서버로 · Secret 가리기 우회). 화면 · MCP 에서 오는 값을 kubectl 에 넘기기 전에 여기서 거른다.
# 이름은 RFC1123 보다 넓다 — ClusterRole 「system:aggregate-to-admin」 처럼 ':' 가 들어간 이름이 실제로 있다.
_KIND_RE = re.compile(r'^[A-Za-z][A-Za-z0-9.\-]{0,252}$')
_OBJ_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:@\-]{0,252}$')


def _kubectl_target_error(kind: str = None, ns: str = None, name: str = None, container: str = None) -> str:
    """빈 문자열 = 통과. None 인 인자는 검사하지 않는다(빈 문자열 ns 는 「네임스페이스 없음」 으로 허용)."""
    if kind is not None and not _KIND_RE.match(str(kind)):
        return f'리소스 종류가 올바르지 않습니다: {str(kind)[:60]!r}'
    if ns not in (None, '') and not _RFC1123_DNS_LABEL.match(str(ns)):
        return f'네임스페이스 이름이 올바르지 않습니다: {str(ns)[:60]!r}'
    if name is not None and not _OBJ_NAME_RE.match(str(name)):
        return f'리소스 이름이 올바르지 않습니다: {str(name)[:60]!r}'
    if container not in (None, '') and not _RFC1123_DNS_LABEL.match(str(container)):
        return f'컨테이너 이름이 올바르지 않습니다: {str(container)[:60]!r}'
    return ''


_KC_PATH_FIELDS = {'clusters': ('cluster', ('certificate-authority',)),
                   'users': ('user', ('client-certificate', 'client-key', 'tokenFile'))}


def _kubeconfig_with_context(text, context: str, base_dir: str = ''):
    """current-context 를 context 로 바꾼 kubeconfig 글. 이미 그렇거나 그런 context 가 없거나 못 읽으면 None.

    base_dir — 원래 파일이 있던 폴더. 사본은 임시 폴더에 놓이므로 상대 경로(인증서 · 키 파일)를 절대 경로로 바꾼다.
    """
    if not text or not context:
        return None
    import yaml
    try:
        kc = yaml.safe_load(text)
    except Exception:
        return None
    if not isinstance(kc, dict) or kc.get('current-context') == context:
        return None
    if not any(isinstance(c, dict) and c.get('name') == context for c in kc.get('contexts') or []):
        return None
    kc['current-context'] = context
    if base_dir:
        for section, (inner, fields) in _KC_PATH_FIELDS.items():
            for item in kc.get(section) or []:
                body = item.get(inner) if isinstance(item, dict) else None
                if not isinstance(body, dict):
                    continue
                for fld in fields:
                    v = body.get(fld)
                    if isinstance(v, str) and v and not os.path.isabs(os.path.expanduser(v)):
                        body[fld] = os.path.normpath(os.path.join(base_dir, v))
    return yaml.safe_dump(kc, sort_keys=False, allow_unicode=True)


def _is_secret_kind(kind: str) -> bool:
    """Kubernetes Secret 리소스 여부 (UI alias 도 포함)."""
    return (kind or '').lower().rstrip('s') == 'secret'


# kubectl apply 로 만든 리소스는 metadata.annotations 에 원본 오브젝트 전체(JSON, Secret data
# 포함)를 이 키로 그대로 보관한다 — data:/stringData: 블록 밖이라 아래 스캐너가 원래 못 잡았다
# (Secret 마스킹 우회 경로). 값은 한 줄/블록 스칼라(|)/줄바꿈 래핑 어느 형태든 key 보다 더 들여쓰인
# continuation 줄로 이어지므로, 아래에서 data:/stringData: 와 동일한 들여쓰기 추적으로 함께 마스킹.
_LAST_APPLIED_ANNOTATION_RE = re.compile(
    r'^(\s*)"?kubectl\.kubernetes\.io/last-applied-configuration"?\s*:'
)


def _redact_secret_yaml(yaml_text: str) -> str:
    """Secret YAML 의 data: / stringData: 블록 값 + last-applied-configuration 주석(원본 통째
    보관 — 우회 경로)을 '[REDACTED]' 로 치환.

    base64 인코딩된 token / TLS key / 패스워드가 UI 에 평문 노출되지 않게 한다.
    파싱 실패 시 입력 그대로 반환 (안전한 폴백).
    """
    if not yaml_text or 'kind: Secret' not in yaml_text:
        return yaml_text
    try:
        lines = yaml_text.split('\n')
        out = []
        in_block = False
        block_indent = -1
        in_annotation = False
        annotation_indent = -1
        for line in lines:
            stripped_r = line.rstrip()
            leading = len(stripped_r) - len(stripped_r.lstrip(' '))
            bare = stripped_r.strip()

            # last-applied-configuration 값 continuation(블록 스칼라/줄바꿈) 스킵 중.
            # 빈 줄은 블록 내부일 수 있어 그냥 버림(원본 보존 불필요), 더 들여쓰였으면 계속 값 내부.
            if in_annotation:
                if not bare or leading > annotation_indent:
                    continue
                in_annotation = False   # 값 종료 — 이 줄부터 정상 처리로 재진입

            m = _LAST_APPLIED_ANNOTATION_RE.match(stripped_r)
            if m and not in_block:
                out.append(f'{m.group(1)}kubectl.kubernetes.io/last-applied-configuration: "[REDACTED]"')
                in_annotation = True
                annotation_indent = len(m.group(1))
                continue

            # 'data:' / 'stringData:' 블록 시작 (key 만 있고 값 비어있는 형태)
            if (bare == 'data:' or bare == 'stringData:' or
                bare == 'data: {}' or bare == 'stringData: {}'):
                in_block = bare in ('data:', 'stringData:')
                block_indent = leading
                out.append(line)
                continue
            if in_block:
                if not bare:
                    out.append(line)
                    continue
                # 블록 외부로 나옴 (같은/짧은 들여쓰기)
                if leading <= block_indent:
                    in_block = False
                    out.append(line)
                    continue
                # 블록 내부 'key: value' → 값 마스킹
                if ':' in bare:
                    key = bare.split(':', 1)[0].rstrip()
                    out.append(' ' * leading + f'{key}: "[REDACTED]"')
                    continue
            out.append(line)
        return '\n'.join(out)
    except Exception:
        return yaml_text


# describe 출력에서 token / cert / key 가 value 형태로 노출되는 라인 패턴.
_DESCRIBE_SENSITIVE = re.compile(
    r'(?im)^(\s*(?:[\w\-./]*?(?:token|password|secret|cert|key|credential)[\w\-./]*?)\s*:)\s*[^\s].*$'
)


# CRD 커스텀 객체(plural.group 형식 kind)는 _is_secret_kind 가 절대 True 가 안 돼 위 두 함수의
# 대상이 아니었다 — DB 오퍼레이터 등 일부 CRD 는 자격증명을 spec 에 인라인으로 담는다(예:
# password/apiKey 필드). suffix 매칭이라 'secretName'/'secretRef'/'tokenLifetime' 처럼 값 자체는
# 민감하지 않은 참조·메타 필드(흔히 built-in 리소스 describe 에도 나옴)는 피하고, 'password'/
# 'dbPassword'/'apiKey'/'rootToken' 처럼 값 자체가 자격증명인 필드만 잡는다. 'cert'는 의도적으로
# 제외 — 서버 인증서(공개)는 그 자체가 비밀이 아니라 개인키(privatekey)만 문제.
_SENSITIVE_KEY_SUFFIXES = (
    'password', 'passwd', 'pwd', 'passphrase',
    'apikey', 'accesskey', 'secretkey', 'privatekey',
    'token', 'credential', 'credentials', 'secret',
)


def _looks_sensitive_key(key: str) -> bool:
    norm = re.sub(r'[_\-\s]', '', key).lower()
    return any(norm.endswith(suf) for suf in _SENSITIVE_KEY_SUFFIXES)


def _redact_sensitive_yaml_fields(yaml_text: str) -> str:
    """YAML 의 'key: value' 스칼라 라인 중 key 이름이 민감해 보이면 값을 마스킹.

    kind 와 무관하게(주로 CRD 커스텀 객체) baseline 으로 적용. data:/stringData: 같은 중첩
    블록은 대상 아님(Secret 전용 _redact_secret_yaml 이 이미 처리) — 여기는 flat scalar 라인만
    다뤄 'secretName: foo' 같은 참조 필드는 안전하게 통과시킨다. 파싱 실패 시 원본 반환.
    """
    if not yaml_text:
        return yaml_text
    try:
        out = []
        for line in yaml_text.split('\n'):
            m = re.match(r'^([\w.\-]+):\s*(.+)$', line.strip())
            if m and _looks_sensitive_key(m.group(1)):
                val = m.group(2).strip()
                if val and val[0] not in '|>{[' and val not in ('null', '~'):
                    leading = len(line) - len(line.lstrip(' '))
                    out.append(' ' * leading + f'{m.group(1)}: "[REDACTED]"')
                    continue
            out.append(line)
        return '\n'.join(out)
    except Exception:
        return yaml_text


def _redact_sensitive_describe_fields(text: str) -> str:
    """kubectl describe 출력의 'Key:   value' 라인(tabwriter 정렬) 중 key 이름이 민감해 보이면
    값을 마스킹. _redact_sensitive_yaml_fields 와 동일 suffix 휴리스틱."""
    if not text:
        return text
    try:
        out = []
        for line in text.split('\n'):
            m = re.match(r'^(\s*)([\w][\w \-./]*?):(\s+)(\S.*)$', line)
            if m and _looks_sensitive_key(m.group(2)):
                out.append(f'{m.group(1)}{m.group(2)}:{m.group(3)}[REDACTED]')
                continue
            out.append(line)
        return '\n'.join(out)
    except Exception:
        return text


def _redact_secret_describe(text: str) -> str:
    """kubectl describe secret 출력에서 token/password/cert/key 가 들어간 라인의
    값을 마스킹. describe 의 'Data' 섹션은 길이만 노출하지만,
    Annotations/Events 등에 평문이 새는 케이스 보강.

    last-applied-configuration 주석은 키 자체에 token/password 등 키워드가 없어 위 정규식이
    못 잡는다 — describe 가 원본 Secret data 를 통째로(여러 줄에 걸쳐) 출력할 수 있어 별도 처리."""
    if not text:
        return text
    try:
        text = _DESCRIBE_SENSITIVE.sub(r'\1 [REDACTED]', text)
        lines = text.split('\n')
        out = []
        skipping = False
        skip_indent = -1
        needle = 'kubectl.kubernetes.io/last-applied-configuration'
        for line in lines:
            stripped_r = line.rstrip()
            leading = len(stripped_r) - len(stripped_r.lstrip(' '))
            bare = stripped_r.strip()
            if skipping:
                if not bare or leading > skip_indent:
                    continue
                skipping = False
            idx = line.find(needle)
            if idx >= 0:
                out.append(f'{line[:idx]}{needle}: [REDACTED]')
                skipping = True
                skip_indent = idx
                continue
            out.append(line)
        return '\n'.join(out)
    except Exception:
        return text


# ─────────────────────────────────────────────────────────────────────────────
# 파드 exec / 로그 args 빌더
# ─────────────────────────────────────────────────────────────────────────────

def _build_pod_exec_args(ns: str, name: str, container: str = '') -> list[str]:
    ns = str(ns or '').strip()
    name = str(name or '').strip()
    container = str(container or '').strip()
    if not ns or not name:
        raise ValueError('namespace and pod name are required')
    # 보안 — terminal/cmd start title 등에 사용자 제어 문자열이 그대로 들어가지 않도록
    # K8s RFC1123 명명 규칙으로 화이트리스트 검증.
    if len(ns) > 63 or not _RFC1123_DNS_LABEL.match(ns):
        raise ValueError(f'invalid namespace name: {ns!r}')
    if len(name) > 253 or not _RFC1123_DNS_SUBDOMAIN.match(name):
        raise ValueError(f'invalid pod name: {name!r}')
    if container and (len(container) > 63 or not _RFC1123_DNS_LABEL.match(container)):
        raise ValueError(f'invalid container name: {container!r}')
    args = ['exec', '-it', '-n', ns, name]
    if container:
        args.extend(['-c', container])
    args.extend(['--', 'sh'])
    return args


_LOG_SOURCE_ALIASES = {
    'pod': 'pod',
    'pods': 'pod',
    'deployment': 'deployment',
    'deployments': 'deployment',
    'deploy': 'deployment',
    'deploys': 'deployment',
    'statefulset': 'statefulset',
    'statefulsets': 'statefulset',
    'sts': 'statefulset',
    'replicaset': 'replicaset',
    'replicasets': 'replicaset',
    'rs': 'replicaset',
    'daemonset': 'daemonset',
    'daemonsets': 'daemonset',
    'ds': 'daemonset',
    'job': 'job',
    'jobs': 'job',
    'ingress': 'ingress',
    'ingresses': 'ingress',
}

_WORKLOAD_LOG_TYPES = {'deployment', 'statefulset', 'replicaset', 'daemonset', 'job'}


def _normalize_log_source_type(source_type: str) -> str:
    key = str(source_type or 'pod').strip().lower()
    return _LOG_SOURCE_ALIASES.get(key, key)


def _build_pod_log_args(ns: str, name: str, container: str = '',
                        tail: int = 200, follow: bool = False,
                        all_containers: bool = False) -> list[str]:
    name = str(name or '').strip()
    if not name:
        raise ValueError('pod name is required')
    try:
        tail = max(1, int(tail))
    except Exception:
        tail = 200
    args = ['logs', name, f'--tail={tail}']
    if ns:
        args.extend(['-n', str(ns).strip()])
    if all_containers:
        args.append('--all-containers=true')
    elif container:
        args.extend(['-c', str(container).strip()])
    if follow:
        args.append('--follow')
    return args


def _is_ingress_controller_pod(name: str, labels: dict | None = None) -> bool:
    text = str(name or '').lower()
    label_text = ' '.join(f'{k}={v}' for k, v in (labels or {}).items()).lower()
    haystack = f'{text} {label_text}'
    keywords = ('ingress', 'traefik', 'contour', 'istio-ingressgateway')
    return any(kw in haystack for kw in keywords)


# ─────────────────────────────────────────────────────────────────────────────
# port-forward spec 빌더
# ─────────────────────────────────────────────────────────────────────────────

_PORT_FORWARD_KIND_ALIASES = {
    'pod': 'pod',
    'pods': 'pod',
    'service': 'service',
    'services': 'service',
    'svc': 'service',
    'svcs': 'service',
}


def _normalize_port_forward_kind(kind: str) -> str:
    key = str(kind or 'service').strip().lower()
    normalized = _PORT_FORWARD_KIND_ALIASES.get(key)
    if not normalized:
        raise ValueError('kind must be service or pod')
    return normalized


def _coerce_port(value, label: str) -> int:
    try:
        port = int(str(value).strip())
    except Exception as exc:
        raise ValueError(f'{label} port must be a number') from exc
    if port < 1 or port > 65535:
        raise ValueError(f'{label} port must be between 1 and 65535')
    return port


def _build_port_forward_spec(kind: str, namespace: str, name: str,
                             local_port, remote_port) -> dict:
    normalized = _normalize_port_forward_kind(kind)
    namespace = str(namespace or '').strip()
    name = str(name or '').strip()
    if not namespace:
        raise ValueError('namespace is required')
    if not name:
        raise ValueError('target name is required')

    remote = _coerce_port(remote_port, 'remote')
    local_blank = local_port is None or str(local_port).strip() == ''
    local = remote if local_blank else _coerce_port(local_port, 'local')
    prefix = 'svc' if normalized == 'service' else 'pod'
    resource = f'{prefix}/{name}'
    return {
        'kind': normalized,
        'namespace': namespace,
        'name': name,
        'resource': resource,
        'local_port': local,
        'remote_port': remote,
        'args': ['-n', namespace, 'port-forward', resource, f'{local}:{remote}'],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ArgoCD spec 빌더
# ─────────────────────────────────────────────────────────────────────────────

def _clean_argo_sources(sources) -> list[dict]:
    cleaned = []
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        item = {}
        for key in (
            'repoURL', 'path', 'chart', 'targetRevision', 'helm', 'kustomize',
            'directory', 'plugin', 'ref',
        ):
            if key in src and src[key] not in (None, ''):
                item[key] = src[key]
        if item.get('repoURL'):
            cleaned.append(item)
    return cleaned


def _argo_sources_from_spec(spec: dict) -> list[dict]:
    if isinstance(spec.get('sources'), list) and spec.get('sources'):
        return _clean_argo_sources(spec.get('sources'))
    source = spec.get('source')
    return _clean_argo_sources([source]) if isinstance(source, dict) else []


def _argo_primary_source(spec: dict) -> dict:
    sources = _argo_sources_from_spec(spec)
    return sources[0] if sources else {}


def _build_argocd_spec(project: str, repo_url: str, path: str, revision: str,
                       dest_ns: str, dest_server: str, sync_policy=None,
                       sources=None) -> dict:
    spec = {
        'project': project or 'default',
        'destination': {'server': dest_server, 'namespace': dest_ns},
        'syncPolicy': sync_policy or {},
    }
    clean_sources = _clean_argo_sources(sources)
    if clean_sources:
        spec['sources'] = clean_sources
    else:
        source = {
            'repoURL': repo_url,
            'targetRevision': revision or 'HEAD',
        }
        if path:
            source['path'] = path
        spec['source'] = source
    return spec


def _build_argocd_sync_operation(is_multi_source: bool = False) -> dict:
    sync = {'prune': False}
    if not is_multi_source:
        sync['revision'] = 'HEAD'
    return {
        'operation': {
            'sync': sync,
            'initiatedBy': {'username': 'polaris'},
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 리소스 이벤트 field selector
# ─────────────────────────────────────────────────────────────────────────────

_RESOURCE_EVENT_KIND_MAP = {
    'pods': 'Pod',
    'pod': 'Pod',
    'deployments': 'Deployment',
    'deployment': 'Deployment',
    'statefulsets': 'StatefulSet',
    'statefulset': 'StatefulSet',
    'daemonsets': 'DaemonSet',
    'daemonset': 'DaemonSet',
    'replicasets': 'ReplicaSet',
    'replicaset': 'ReplicaSet',
    'jobs': 'Job',
    'job': 'Job',
    'cronjobs': 'CronJob',
    'cronjob': 'CronJob',
    'services': 'Service',
    'service': 'Service',
    'ingresses': 'Ingress',
    'ingress': 'Ingress',
    'configmaps': 'ConfigMap',
    'configmap': 'ConfigMap',
    'secrets': 'Secret',
    'secret': 'Secret',
    'pvcs': 'PersistentVolumeClaim',
    'persistentvolumeclaims': 'PersistentVolumeClaim',
}


def _resource_event_field_selector(kind: str, name: str) -> str:
    name = str(name or '').strip()
    mapped = _RESOURCE_EVENT_KIND_MAP.get(str(kind or '').strip().lower())
    if mapped:
        return f'involvedObject.kind={mapped},involvedObject.name={name}'
    return f'involvedObject.name={name}'


# ─────────────────────────────────────────────────────────────────────────────
# 리소스 쓰기 (scale / rollout restart) args 빌더 — 순수 함수, 단위 테스트 대상
# ─────────────────────────────────────────────────────────────────────────────

# UI 내부 리소스 키 → kubectl 정식 리소스 타입
_KUBECTL_KIND_ALIASES = {
    'pods': 'pods', 'pod': 'pods',
    'deployments': 'deployments', 'deployment': 'deployments', 'deploy': 'deployments',
    'statefulsets': 'statefulsets', 'statefulset': 'statefulsets', 'sts': 'statefulsets',
    'daemonsets': 'daemonsets', 'daemonset': 'daemonsets', 'ds': 'daemonsets',
    'replicasets': 'replicasets', 'replicaset': 'replicasets', 'rs': 'replicasets',
    'services': 'services', 'service': 'services', 'svc': 'services',
    'ingresses': 'ingresses', 'ingress': 'ingresses',
    'configmaps': 'configmaps', 'configmap': 'configmaps', 'cm': 'configmaps',
    'secrets': 'secrets', 'secret': 'secrets',
    'jobs': 'jobs', 'job': 'jobs',
    'cronjobs': 'cronjobs', 'cronjob': 'cronjobs', 'cj': 'cronjobs',
    'pvcs': 'persistentvolumeclaims', 'pvc': 'persistentvolumeclaims',
    'pvs': 'persistentvolumes', 'pv': 'persistentvolumes',
    'namespaces': 'namespaces', 'namespace': 'namespaces', 'ns': 'namespaces',
    'nodes': 'nodes', 'node': 'nodes',
}

# scale 가능한 리소스 (replicas 필드를 가진 워크로드)
_SCALABLE_KINDS = {'deployments', 'statefulsets', 'replicasets'}

# rollout restart 가능한 리소스
_RESTARTABLE_KINDS = {'deployments', 'statefulsets', 'daemonsets'}


def _normalize_kubectl_kind(kind: str) -> str:
    """UI 키 → kubectl 정식 리소스 타입. 매핑 없으면 입력값 그대로 (소문자)."""
    key = str(kind or '').strip().lower()
    return _KUBECTL_KIND_ALIASES.get(key, key)


def _build_scale_args(kind: str, ns: str, name: str, replicas) -> list[str]:
    """kubectl scale args 빌더. 검증 실패 시 ValueError."""
    k = _normalize_kubectl_kind(kind)
    if k not in _SCALABLE_KINDS:
        raise ValueError(f'scale 불가 리소스: {kind} (지원: deployment/statefulset/replicaset)')
    name = str(name or '').strip()
    if not name:
        raise ValueError('리소스 이름이 필요합니다.')
    if len(name) > 253 or not _RFC1123_DNS_SUBDOMAIN.match(name):
        raise ValueError(f'잘못된 리소스 이름: {name!r}')
    try:
        r = int(replicas)
    except Exception as exc:
        raise ValueError('replicas 는 정수여야 합니다.') from exc
    if r < 0 or r > 1000:
        raise ValueError('replicas 는 0~1000 범위여야 합니다.')
    ns = str(ns or '').strip()
    if ns and (len(ns) > 63 or not _RFC1123_DNS_LABEL.match(ns)):
        raise ValueError(f'잘못된 네임스페이스: {ns!r}')
    return (['-n', ns] if ns else []) + ['scale', k, name, f'--replicas={r}']


def _build_rollout_restart_args(kind: str, ns: str, name: str) -> list[str]:
    """kubectl rollout restart args 빌더. 검증 실패 시 ValueError."""
    k = _normalize_kubectl_kind(kind)
    if k not in _RESTARTABLE_KINDS:
        raise ValueError(f'restart 불가 리소스: {kind} (지원: deployment/statefulset/daemonset)')
    name = str(name or '').strip()
    if not name:
        raise ValueError('리소스 이름이 필요합니다.')
    if len(name) > 253 or not _RFC1123_DNS_SUBDOMAIN.match(name):
        raise ValueError(f'잘못된 리소스 이름: {name!r}')
    ns = str(ns or '').strip()
    if ns and (len(ns) > 63 or not _RFC1123_DNS_LABEL.match(ns)):
        raise ValueError(f'잘못된 네임스페이스: {ns!r}')
    # kubectl rollout restart deployments/<name> 형태
    return (['-n', ns] if ns else []) + ['rollout', 'restart', f'{k}/{name}']


def _build_rollout_undo_args(kind: str, ns: str, name: str, revision) -> list[str]:
    """kubectl rollout undo --to-revision args 빌더. 검증 실패 시 ValueError.

    지정 리비전으로 롤백한다. (지원: deployment/statefulset/daemonset)"""
    k = _normalize_kubectl_kind(kind)
    if k not in _RESTARTABLE_KINDS:
        raise ValueError(f'rollback 불가 리소스: {kind} (지원: deployment/statefulset/daemonset)')
    name = str(name or '').strip()
    if not name:
        raise ValueError('리소스 이름이 필요합니다.')
    if len(name) > 253 or not _RFC1123_DNS_SUBDOMAIN.match(name):
        raise ValueError(f'잘못된 리소스 이름: {name!r}')
    try:
        rev = int(revision)
    except Exception as exc:
        raise ValueError('revision 은 정수여야 합니다.') from exc
    if rev <= 0:
        raise ValueError('revision 은 1 이상이어야 합니다.')
    ns = str(ns or '').strip()
    if ns and (len(ns) > 63 or not _RFC1123_DNS_LABEL.match(ns)):
        raise ValueError(f'잘못된 네임스페이스: {ns!r}')
    return (['-n', ns] if ns else []) + ['rollout', 'undo', f'{k}/{name}', f'--to-revision={rev}']


def _images_from_cr_data(data) -> list[str]:
    """ControllerRevision.data(직렬화된 템플릿 패치)에서 컨테이너 이미지 목록 추출.

    StatefulSet/DaemonSet 의 리비전은 ControllerRevision 에 보관되며, 그 시점 템플릿이
    data.spec.template.spec.containers 경로에 들어 있다 (Deployment 의 ReplicaSet
    spec.template 에 대응). dict / JSON 문자열 / bytes 를 모두 수용하고, 구조가
    예상과 다르거나 파싱에 실패하면 빈 리스트를 반환한다(나머지 리비전 정보는 유지).
    """
    import json as _json
    try:
        if data is None:
            return []
        if isinstance(data, (bytes, bytearray)):
            data = data.decode('utf-8', 'replace')
        if isinstance(data, str):
            data = _json.loads(data)
        if not isinstance(data, dict):
            return []
        spec = (((data.get('spec') or {}).get('template') or {}).get('spec') or {})
        return [c['image'] for c in (spec.get('containers') or [])
                if isinstance(c, dict) and c.get('image')]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# K8sManager — kubernetes Python 클라이언트 래퍼
# ─────────────────────────────────────────────────────────────────────────────

class K8sManager:
    def __init__(self):
        self.kubeconfig    = None
        self.connected     = False
        self.cluster_info  = {}
        self._api_client   = None   # 인스턴스 전용 ApiClient (전역 config 분리)
        self._temp_kubeconfig = None  # vault content 로 연결 시 세션 임시 파일
        self.core = self.apps = self.batch = self.net = None
        self.custom = self.autoscaling = self.storage = self.rbac = self.policy = None

    # ── 임시 kubeconfig (vault content 복원용) ─────────────────────────────────
    # kubectl 기반 기능(logs/port-forward/terminal 등)이 self.kubeconfig 파일
    # 경로를 필요로 하므로, vault 에 보관된 내용으로 연결할 때는 세션 동안 유지되는
    # 임시 파일을 만들고 disconnect 시 삭제한다.
    def _write_temp_kubeconfig(self, content: str) -> str:
        self._cleanup_temp_kubeconfig()
        fd, tmp = tempfile.mkstemp(suffix='.yaml', prefix=f'polaris-kc-{os.getpid()}-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(tmp, 0o600)   # 소유자만 읽기 (best-effort; Windows 는 %TEMP% 가 사용자 전용)
        except Exception:
            pass
        self._temp_kubeconfig = tmp
        _TEMP_KUBECONFIGS.add(tmp)   # atexit 크래시-세이프 정리 대상 등록 (v1.2.3)
        return tmp

    def _cleanup_temp_kubeconfig(self):
        tmp = getattr(self, '_temp_kubeconfig', None)
        if tmp:
            try:
                os.remove(tmp)
            except Exception:
                pass
            _TEMP_KUBECONFIGS.discard(tmp)
            self._temp_kubeconfig = None

    # ── 연결 ─────────────────────────────────────────────────────────────────

    def connect(self, path: str = None, context: str = None, content: str = None):
        if not HAS_K8S:
            return False, 'pip install kubernetes 후 재시작하세요.'

        # ── 고른 context 를 kubectl · helm · exec 에도 (v1.5.28 검토) ───────────
        # 파이썬 클라이언트만 context 를 받고, kubectl · helm · 파드 셸 · 로그 · 포트포워딩은 `--kubeconfig 파일` 만 받아
        # 그 파일의 current-context 로 갔다 — prod 를 골라 놓고 삭제 · 적용 · helm 업그레이드가 dev 에 들어갈 수 있었다.
        # 고른 context 가 current-context 와 다르면 그것을 current-context 로 둔 사본으로 연결한다.
        if context:
            try:
                src_text = content if content is not None else (
                    Path(path).read_text(encoding='utf-8') if path and Path(path).is_file()
                    and Path(path).stat().st_size <= 5 * 1024 * 1024 else None)
                fixed = _kubeconfig_with_context(src_text, context, str(Path(path).parent) if path and content is None else '')
                if fixed is not None:
                    content = fixed
            except Exception:
                pass                      # 못 읽으면 아래 기존 경로가 알맞은 오류를 낸다

        # ── content 기반 연결 (vault 복원) — 세션 임시 파일 생성 ────────────────
        used_temp = False
        if content is not None:
            try:
                path = self._write_temp_kubeconfig(content)
                used_temp = True
            except Exception as e:
                return False, f'kubeconfig 임시 파일 생성 실패: {e}'

        # ── 사전 검증 ──────────────────────────────────────────────────────────
        p = Path(path) if path else None
        if not p or not p.is_file():
            if used_temp:
                self._cleanup_temp_kubeconfig()
            return False, f'kubeconfig 파일을 찾을 수 없습니다: {path}'
        if p.stat().st_size > 5 * 1024 * 1024:  # 5 MB 초과는 kubeconfig 아님
            if used_temp:
                self._cleanup_temp_kubeconfig()
            return False, 'kubeconfig 파일이 너무 큽니다 (5 MB 초과).'

        try:
            # ── 인스턴스 전용 Configuration 생성 (전역 덮어쓰기 방지) ───────────
            cfg = k8s.Configuration()
            k8s_cfg.load_kube_config(
                config_file=path,
                context=context or None,
                client_configuration=cfg,
            )
            api_client       = k8s.ApiClient(configuration=cfg)
            self._api_client = api_client

            self.core        = k8s.CoreV1Api(api_client=api_client)
            self.apps        = k8s.AppsV1Api(api_client=api_client)
            self.batch       = k8s.BatchV1Api(api_client=api_client)
            self.net         = k8s.NetworkingV1Api(api_client=api_client)
            self.custom      = k8s.CustomObjectsApi(api_client=api_client)
            self.autoscaling = k8s.AutoscalingV1Api(api_client=api_client)
            self.storage     = k8s.StorageV1Api(api_client=api_client)
            self.rbac        = k8s.RbacAuthorizationV1Api(api_client=api_client)
            self.policy      = k8s.PolicyV1Api(api_client=api_client)
            # 연결 확인은 짧게 — 여기서 기다리는 동안 세션 복원이 통째로 멈춘다
            ver = k8s.VersionApi(api_client=api_client).get_code(_request_timeout=(5, 20))
            # 컨텍스트 이름 결정: 지정된 context 우선, 없으면 current-context
            if context:
                ctx_name = context
            else:
                try:
                    _, active_ctx = k8s_cfg.list_kube_config_contexts(config_file=path)
                    ctx_name = (active_ctx.get('context', {}).get('cluster', '')
                                or active_ctx.get('name', ''))
                except Exception:
                    ctx_name = ''
            self.kubeconfig   = path
            self.connected    = True
            self.cluster_info = {'version': ver.git_version, 'context': ctx_name}
            try:   # kubectl 을 이 클러스터 판에 가장 가까운 것으로 고르게(v1.5.74)
                from src.tools import note_server_version
                note_server_version(path, ver.git_version)
            except Exception:
                pass
            return True, f'연결 성공 — {ver.git_version}'
        except Exception as e:
            self.connected = False
            if used_temp:
                self._cleanup_temp_kubeconfig()
            return False, _diagnose_connect_error(e, path)

    def disconnect(self):
        self.connected = False
        self.kubeconfig = None
        self.cluster_info = {}
        self._cleanup_temp_kubeconfig()
        # ApiClient 연결 풀 해제
        try:
            if self._api_client:
                self._api_client.rest_client.pool_manager.clear()
        except Exception:
            pass
        self._api_client = None
        self.core = self.apps = self.batch = self.net = None
        self.custom = self.autoscaling = self.storage = self.rbac = self.policy = None

    # ── 내부 유틸 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _an(ns) -> bool:
        """All-Namespaces 여부 확인."""
        return not ns or str(ns).lower() in ('all namespaces', 'all', '')

    # ── 네임스페이스 ──────────────────────────────────────────────────────────

    def get_namespaces_list(self) -> list:
        try:
            return [n.metadata.name for n in self.core.list_namespace().items]
        except Exception:
            return []

    def get_namespaces(self, _=None) -> list:
        try:
            return [{'name': n.metadata.name,
                     'status': n.status.phase or 'Active',
                     'age': _age(n.metadata.creation_timestamp),
                     '_ns': None, '_kind': 'namespace'}
                    for n in self.core.list_namespace().items]
        except Exception:
            return []

    # ── 노드 ──────────────────────────────────────────────────────────────────

    def get_nodes(self, _=None) -> list:
        rows = []
        try:
            for n in self.core.list_node().items:
                labels = n.metadata.labels or {}
                roles = [lbl.split('/')[-1] for lbl in labels
                         if 'node-role.kubernetes.io/' in lbl] or ['<none>']
                status = 'Unknown'
                for cond in (n.status.conditions or []):
                    if cond.type == 'Ready':
                        status = 'Ready' if cond.status == 'True' else 'NotReady'
                ni = n.status.node_info
                rows.append({
                    'name':    n.metadata.name,
                    'status':  status,
                    'roles':   ','.join(roles),
                    'version': ni.kubelet_version if ni else 'N/A',
                    'os':      ni.os_image if ni else 'N/A',
                    'age':     _age(n.metadata.creation_timestamp),
                    '_ns': None, '_kind': 'node',
                })
        except Exception:
            pass
        return rows

    # ── 파드 ──────────────────────────────────────────────────────────────────

    def get_pods(self, ns=None, detail=False, *, owner=False, errors=None) -> list:
        """파드 목록.

        detail=True 면 `reason`(비정상 사유) · `restarted_at`(마지막 재시작 시각) ·
        `abnormal` 을 추가한다. **기본값은 False 로 기존 반환 형태를 그대로 유지** —
        이 함수는 리소스 브라우저·스냅샷·보고서 등 8곳이 공유하므로 필드를 무조건
        늘리면 엉뚱한 화면에 열이 새어나온다. 대시보드만 detail 을 켠다.

        owner=True 면 `owner_kind` · `owner_name`(컨트롤러 ownerReference)을 더한다 —
        보고서가 「이미 성공한 Job 의 실패한 이전 시도」 를 가려내는 데 쓴다(v1.4.13).
        errors 에 목록을 넘기면 조회 실패를 거기에 적는다(반환값은 그대로 []).
        """
        try:
            items = (_list(self.core.list_namespaced_pod, ns).items
                     if not self._an(ns)
                     else _list(self.core.list_pod_for_all_namespaces).items)
        except Exception as e:
            _collect_fail(errors, 'pods', e)
            return []
        rows = []
        for p in items:
            total = len(p.spec.containers or [])
            ready = restarts = 0
            if p.status.container_statuses:
                for cs in p.status.container_statuses:
                    if cs.ready:
                        ready += 1
                    restarts += cs.restart_count or 0
            row = {
                'name':      p.metadata.name,
                'namespace': p.metadata.namespace,
                'ready':     f'{ready}/{total}',
                'status':    p.status.phase or 'Unknown',
                'restarts':  str(restarts),
                'node':      p.spec.node_name or 'N/A',
                'age':       _age(p.metadata.creation_timestamp),
                '_ns': p.metadata.namespace, '_kind': 'pod',
            }
            if detail:
                row['reason'] = _pod_problem_reason(p)
                row['restarted_at'] = _pod_last_restart_at(p)
                row['abnormal'] = _pod_is_abnormal(p, ready, total)
            if owner:
                row['owner_kind'], row['owner_name'] = _controller_owner(p.metadata)
            rows.append(row)
        return rows

    # ── 디플로이먼트 ──────────────────────────────────────────────────────────

    def get_deployments(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_deployment(ns).items
                     if not self._an(ns)
                     else self.apps.list_deployment_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':       d.metadata.name,
            'namespace':  d.metadata.namespace,
            'ready':      f'{d.status.ready_replicas or 0}/{d.spec.replicas or 0}',
            'up-to-date': str(d.status.updated_replicas or 0),
            'available':  str(d.status.available_replicas or 0),
            'age':        _age(d.metadata.creation_timestamp),
            '_ns': d.metadata.namespace, '_kind': 'deployment',
        } for d in items]

    # ── 스테이트풀셋 ──────────────────────────────────────────────────────────

    def get_statefulsets(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_stateful_set(ns).items
                     if not self._an(ns)
                     else self.apps.list_stateful_set_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      s.metadata.name,
            'namespace': s.metadata.namespace,
            'ready':     f'{s.status.ready_replicas or 0}/{s.spec.replicas or 0}',
            'age':       _age(s.metadata.creation_timestamp),
            '_ns': s.metadata.namespace, '_kind': 'statefulset',
        } for s in items]

    # ── 데몬셋 ───────────────────────────────────────────────────────────────

    def get_daemonsets(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_daemon_set(ns).items
                     if not self._an(ns)
                     else self.apps.list_daemon_set_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      d.metadata.name,
            'namespace': d.metadata.namespace,
            'desired':   str(d.status.desired_number_scheduled or 0),
            'ready':     str(d.status.number_ready or 0),
            'age':       _age(d.metadata.creation_timestamp),
            '_ns': d.metadata.namespace, '_kind': 'daemonset',
        } for d in items]

    # ── 레플리카셋 ────────────────────────────────────────────────────────────

    def get_replicasets(self, ns=None) -> list:
        try:
            items = (self.apps.list_namespaced_replica_set(ns).items
                     if not self._an(ns)
                     else self.apps.list_replica_set_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      r.metadata.name,
            'namespace': r.metadata.namespace,
            'desired':   str(r.spec.replicas or 0),
            'ready':     str(r.status.ready_replicas or 0),
            'age':       _age(r.metadata.creation_timestamp),
            '_ns': r.metadata.namespace, '_kind': 'replicaset',
        } for r in items]

    # ── 잡 ───────────────────────────────────────────────────────────────────

    def get_jobs(self, ns=None, *, errors=None) -> list:
        try:
            items = (self.batch.list_namespaced_job(ns).items
                     if not self._an(ns)
                     else self.batch.list_job_for_all_namespaces().items)
        except Exception as e:
            _collect_fail(errors, 'jobs', e)
            return []
        rows = []
        for j in items:
            conditions = j.status.conditions or []
            cond_types = {c.type for c in conditions if c.status == 'True'}
            if 'Complete' in cond_types:
                status = 'Complete'
            elif 'Failed' in cond_types:
                status = 'Failed'
            elif j.status.active:
                status = 'Running'
            else:
                status = 'Pending'
            rows.append({
                'name':        j.metadata.name,
                'namespace':   j.metadata.namespace,
                'completions': f'{j.status.succeeded or 0}/{j.spec.completions or 1}',
                'status':      status,
                'age':         _age(j.metadata.creation_timestamp),
                '_ns': j.metadata.namespace, '_kind': 'job',
            })
        return rows

    # ── 크론잡 ───────────────────────────────────────────────────────────────

    def get_cronjobs(self, ns=None) -> list:
        try:
            items = (self.batch.list_namespaced_cron_job(ns).items
                     if not self._an(ns)
                     else self.batch.list_cron_job_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':          c.metadata.name,
            'namespace':     c.metadata.namespace,
            'schedule':      c.spec.schedule,
            'suspend':       str(c.spec.suspend or False),
            'last-schedule': (_age(c.status.last_schedule_time)
                              if c.status.last_schedule_time else 'Never'),
            'age':           _age(c.metadata.creation_timestamp),
            '_ns': c.metadata.namespace, '_kind': 'cronjob',
        } for c in items]

    # ── 서비스 ───────────────────────────────────────────────────────────────

    def get_services(self, ns=None, *, errors=None) -> list:
        try:
            items = (self.core.list_namespaced_service(ns).items
                     if not self._an(ns)
                     else self.core.list_service_for_all_namespaces().items)
        except Exception as e:
            _collect_fail(errors, 'services', e)
            return []
        rows = []
        for s in items:
            ext = []
            if s.status.load_balancer and s.status.load_balancer.ingress:
                ext = [i.ip or i.hostname or ''
                       for i in s.status.load_balancer.ingress]
            ports = [f'{p.port}{":" + str(p.node_port) if p.node_port else ""}/{p.protocol}'
                     for p in (s.spec.ports or [])]
            rows.append({
                'name':        s.metadata.name,
                'namespace':   s.metadata.namespace,
                'type':        s.spec.type,
                'cluster-ip':  s.spec.cluster_ip or 'None',
                'external-ip': ','.join(ext) if ext else '<none>',
                'ports':       ','.join(ports),
                'age':         _age(s.metadata.creation_timestamp),
                '_ns': s.metadata.namespace, '_kind': 'service',
            })
        return rows

    # ── 인그레스 ─────────────────────────────────────────────────────────────

    def get_ingresses(self, ns=None, *, tls=False, errors=None) -> list:
        """Ingress 목록. tls=True 면 `tls`(spec.tls 항목별 Secret 이름 · 없으면 호스트) 목록을
        더한다 — 빈 목록이면 TLS 설정이 없다는 뜻이다(v1.4.13, 보고서 전용).
        기본값은 기존 반환 형태 그대로 — 스냅샷 diff 대상이라 필드를 늘리면 첫 비교에서
        모든 Ingress 가 「변경」 으로 나온다."""
        try:
            items = (self.net.list_namespaced_ingress(ns).items
                     if not self._an(ns)
                     else self.net.list_ingress_for_all_namespaces().items)
        except Exception as e:
            _collect_fail(errors, 'ingresses', e)
            return []
        rows = []
        for i in items:
            hosts = [r.host for r in (i.spec.rules or []) if r.host]
            addrs = [x.ip or x.hostname or ''
                     for x in ((i.status.load_balancer.ingress or [])
                                if i.status.load_balancer else [])]
            rows.append({
                'name':      i.metadata.name,
                'namespace': i.metadata.namespace,
                'class':     i.spec.ingress_class_name or '<none>',
                'hosts':     ','.join(hosts) or '*',
                'address':   ','.join(addrs),
                'age':       _age(i.metadata.creation_timestamp),
                '_ns': i.metadata.namespace, '_kind': 'ingress',
            })
            if tls:
                rows[-1]['tls'] = [
                    (getattr(t, 'secret_name', None)
                     or ','.join(getattr(t, 'hosts', None) or []) or '(기본 인증서)')
                    for t in (getattr(i.spec, 'tls', None) or [])]
        return rows

    # ── 컨피그맵 ─────────────────────────────────────────────────────────────

    def get_configmaps(self, ns=None) -> list:
        try:
            items = (self.core.list_namespaced_config_map(ns).items
                     if not self._an(ns)
                     else self.core.list_config_map_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      c.metadata.name,
            'namespace': c.metadata.namespace,
            'data':      str(len(c.data) if c.data else 0),
            'age':       _age(c.metadata.creation_timestamp),
            '_ns': c.metadata.namespace, '_kind': 'configmap',
        } for c in items]

    # ── 시크릿 ───────────────────────────────────────────────────────────────

    def get_secrets(self, ns=None) -> list:
        try:
            items = (self.core.list_namespaced_secret(ns).items
                     if not self._an(ns)
                     else self.core.list_secret_for_all_namespaces().items)
        except Exception:
            return []
        return [{
            'name':      s.metadata.name,
            'namespace': s.metadata.namespace,
            'type':      s.type,
            'data':      str(len(s.data) if s.data else 0),
            'age':       _age(s.metadata.creation_timestamp),
            '_ns': s.metadata.namespace, '_kind': 'secret',
        } for s in items]

    # ── PVC ──────────────────────────────────────────────────────────────────

    def get_pvcs(self, ns=None, *, errors=None) -> list:
        try:
            items = (self.core.list_namespaced_persistent_volume_claim(ns).items
                     if not self._an(ns)
                     else self.core.list_persistent_volume_claim_for_all_namespaces().items)
        except Exception as e:
            _collect_fail(errors, 'pvcs', e)
            return []
        return [{
            'name':         p.metadata.name,
            'namespace':    p.metadata.namespace,
            'status':       p.status.phase or 'Unknown',
            'volume':       p.spec.volume_name or '',
            'capacity':     (p.status.capacity or {}).get('storage', 'N/A'),
            'access-modes': ','.join(p.spec.access_modes or []),
            'age':          _age(p.metadata.creation_timestamp),
            '_ns': p.metadata.namespace, '_kind': 'persistentvolumeclaim',
        } for p in items]

    # ── PV ───────────────────────────────────────────────────────────────────

    def get_pvs(self, _=None) -> list:
        rows = []
        try:
            for p in self.core.list_persistent_volume().items:
                ref = p.spec.claim_ref
                rows.append({
                    'name':           p.metadata.name,
                    'capacity':       (p.spec.capacity or {}).get('storage', 'N/A'),
                    'access-modes':   ','.join(p.spec.access_modes or []),
                    'reclaim-policy': p.spec.persistent_volume_reclaim_policy or 'N/A',
                    'status':         p.status.phase or 'Unknown',
                    'claim':          f'{ref.namespace}/{ref.name}' if ref else '',
                    'age':            _age(p.metadata.creation_timestamp),
                    '_ns': None, '_kind': 'persistentvolume',
                })
        except Exception:
            pass
        return rows

    # ── 리소스 라우터 ─────────────────────────────────────────────────────────

    GETTERS = {
        'nodes':        get_nodes,
        'namespaces':   get_namespaces,
        'pods':         get_pods,
        'deployments':  get_deployments,
        'statefulsets': get_statefulsets,
        'daemonsets':   get_daemonsets,
        'replicasets':  get_replicasets,
        'jobs':         get_jobs,
        'cronjobs':     get_cronjobs,
        'services':     get_services,
        'ingresses':    get_ingresses,
        'configmaps':   get_configmaps,
        'secrets':      get_secrets,
        'pvcs':         get_pvcs,
        'pvs':          get_pvs,
    }

    def get_resources(self, rtype: str, ns=None) -> list:
        fn = self.GETTERS.get(rtype)
        return fn(self, ns) if fn else []

    def get_workload_pods(self, ns: str, wl_type: str, wl_name: str):
        wl_type = _normalize_log_source_type(wl_type)
        wl_name = str(wl_name or '').strip()
        if wl_type not in _WORKLOAD_LOG_TYPES:
            return [], f'지원하지 않는 워크로드 타입: {wl_type}'
        if not ns or not wl_name:
            return [], 'namespace와 워크로드 이름이 필요합니다.'

        try:
            if wl_type == 'deployment':
                wl = self.apps.read_namespaced_deployment(wl_name, ns)
            elif wl_type == 'statefulset':
                wl = self.apps.read_namespaced_stateful_set(wl_name, ns)
            elif wl_type == 'daemonset':
                wl = self.apps.read_namespaced_daemon_set(wl_name, ns)
            elif wl_type == 'replicaset':
                wl = self.apps.read_namespaced_replica_set(wl_name, ns)
            else:
                wl = self.batch.read_namespaced_job(wl_name, ns)
        except Exception as e:
            return [], f'워크로드 조회 실패: {e}'

        wl_uid = getattr(wl.metadata, 'uid', None)
        sel_labels = (wl.spec.selector.match_labels or {}) if wl.spec and wl.spec.selector else {}
        desired = getattr(wl.spec, 'replicas', None)
        ready = (getattr(wl.status, 'ready_replicas', None) or
                 getattr(wl.status, 'number_ready', None) or
                 getattr(wl.status, 'succeeded', None) or 0)

        if wl_type == 'deployment' and sel_labels:
            try:
                label_sel = ','.join(f'{k}={v}' for k, v in sel_labels.items())
                rss = self.apps.list_namespaced_replica_set(ns, label_selector=label_sel).items
                owned_rs_uids = {
                    rs.metadata.uid for rs in rss
                    if any(o.uid == wl_uid for o in (rs.metadata.owner_references or []))
                }
                if owned_rs_uids:
                    pods = self.core.list_namespaced_pod(ns).items
                    names = [p.metadata.name for p in pods
                             if any(o.uid in owned_rs_uids
                                    for o in (p.metadata.owner_references or []))]
                    if names:
                        return sorted(names), None
            except Exception:
                pass

        try:
            pods = self.core.list_namespaced_pod(ns).items
            owned = [p.metadata.name for p in pods
                     if any(o.uid == wl_uid for o in (p.metadata.owner_references or []))]
            if owned:
                return sorted(owned), None
        except Exception:
            pass

        if sel_labels:
            try:
                label_sel = ','.join(f'{k}={v}' for k, v in sel_labels.items())
                pods = self.core.list_namespaced_pod(ns, label_selector=label_sel).items
                names = [p.metadata.name for p in pods]
                if names:
                    return sorted(names), None
            except Exception as e:
                return [], f'파드 조회 실패: {e}'

        if desired == 0:
            return [], f'{wl_type}의 desired replicas가 0입니다.'
        return [], f'{wl_type}/{wl_name}에 연결된 활성 파드가 없습니다. ready={ready}'

    def get_ingress_log_pods(self):
        candidates = ['kube-system', 'ingress-nginx', 'nginx-ingress', 'traefik', 'istio-system']
        found: list[tuple[str, str]] = []
        seen = set()

        def add_matches(items):
            for pod in items or []:
                ns = pod.metadata.namespace
                name = pod.metadata.name
                key = (ns, name)
                if key in seen:
                    continue
                if _is_ingress_controller_pod(name, pod.metadata.labels or {}):
                    seen.add(key)
                    found.append(key)

        for ns in candidates:
            try:
                add_matches(self.core.list_namespaced_pod(ns).items)
            except Exception:
                pass
        if found:
            return found, None

        try:
            add_matches(self.core.list_pod_for_all_namespaces().items)
        except Exception as e:
            return [], f'Ingress controller 파드 조회 실패: {e}'

        if found:
            return found, None
        return [], 'ingress / traefik / contour / istio-ingressgateway 키워드로 controller 파드를 찾지 못했습니다.'

    # ── 대시보드 ─────────────────────────────────────────────────────────────

    def get_node_metrics(self):
        if not self.custom:
            return []
        try:
            r = self.custom.list_cluster_custom_object(
                group='metrics.k8s.io', version='v1beta1', plural='nodes')
            return _build_node_metrics(r.get('items', []))
        except Exception:
            return []

    def get_dashboard_data(self) -> dict:
        result = {
            'pods': [], 'nodes': [], 'node_metrics': [],
            'total_restarts': 0, 'namespace_count': 0,
            'attention': {'items': [], 'total': 0, 'truncated': False,
                          'abnormal_count': 0, 'restart_count': 0, 'window_days': 3},
        }
        if not self.core:
            return result
        try:
            # detail=True — 사유/재시작 시각이 필요하다. 추가 API 호출은 없다(같은 응답에서 추출).
            pods = self.get_pods(None, detail=True)
            result['pods'] = pods
            result['total_restarts'] = sum(int(p.get('restarts', 0)) for p in pods)
            result['attention'] = select_attention_pods(pods)

            node_pod_cnt = {}
            for p in pods:
                nd = p.get('node', '')
                node_pod_cnt[nd] = node_pod_cnt.get(nd, 0) + 1

            for n in _list(self.core.list_node).items:
                labels = n.metadata.labels or {}
                roles = [lbl.split('/')[-1] for lbl in labels
                         if 'node-role.kubernetes.io/' in lbl] or ['<none>']
                status = 'Ready'
                for cond in (n.status.conditions or []):
                    if cond.type == 'Ready':
                        status = 'Ready' if cond.status == 'True' else 'NotReady'
                alloc = n.status.allocatable or {}
                result['nodes'].append(_apply_node_metric({
                    'name':         n.metadata.name,
                    'status':       status,
                    'role':         ','.join(roles),
                    'cpu_alloc_m':  _parse_cpu(alloc.get('cpu', '0')),
                    'mem_alloc_mi': _parse_mem(alloc.get('memory', '0')) // (1024 * 1024),
                    'max_pods':     int(alloc.get('pods', '110')),
                    'pod_count':    node_pod_cnt.get(n.metadata.name, 0),
                }, None))

            result['node_metrics'] = self.get_node_metrics()
            metrics = {m['name']: m for m in result['node_metrics']}
            result['nodes'] = [
                _apply_node_metric(n, metrics.get(n['name']))
                for n in result['nodes']
            ]
            result['namespace_count'] = len(_list(self.core.list_namespace).items)
        except Exception:
            pass
        return result

    # ── CRD (CustomResourceDefinition) 자동 발견 ─────────────────────────────

    def get_crds(self):
        """클러스터의 모든 CRD 메타 목록.

        반환: [{name, group, version(스토리지 버전), kind, plural, scoped, ...}]
        custom API 로 apiextensions.k8s.io/v1/customresourcedefinitions 조회.
        """
        if not self.custom:
            return []
        try:
            result = self.custom.list_cluster_custom_object(
                group='apiextensions.k8s.io', version='v1',
                plural='customresourcedefinitions',
            )
        except Exception:
            return []
        out = []
        for item in result.get('items', []):
            spec = item.get('spec', {})
            md   = item.get('metadata', {})
            names = spec.get('names', {})
            versions = spec.get('versions', []) or []
            # 스토리지/served 버전 선택 (storage=true 우선, 없으면 첫 served)
            storage_v = next((v.get('name') for v in versions if v.get('storage')), '')
            served    = [v.get('name') for v in versions if v.get('served')]
            ver = storage_v or (served[0] if served else (versions[0].get('name') if versions else ''))
            group = spec.get('group', '')
            # 선택된 버전의 additionalPrinterColumns 추출 (없으면 [])
            ver_obj = next((v for v in versions if v.get('name') == ver), {})
            printer_cols = [
                {'name': c.get('name', ''), 'jsonPath': c.get('jsonPath', '')}
                for c in (ver_obj.get('additionalPrinterColumns', []) or [])
                if c.get('name') and c.get('jsonPath')
                and c.get('name', '').lower() != 'age'   # Age 는 우리가 따로 표시
            ]
            out.append({
                'name':    md.get('name', ''),
                'group':   group,
                'version': ver,
                'kind':    names.get('kind', ''),
                'plural':  names.get('plural', ''),
                'short':   ','.join(names.get('shortNames', []) or []),
                'scope':   spec.get('scope', 'Namespaced'),
                'namespaced': spec.get('scope', 'Namespaced') == 'Namespaced',
                'versions': served,
                'printer_columns': printer_cols[:5],   # 너무 많으면 5개로 제한
                'age':     _age(_parse_ts(md.get('creationTimestamp'))),
            })
        out.sort(key=lambda x: (x['group'], x['kind']))
        return out

    def get_crd_objects(self, group: str, version: str, plural: str,
                        namespaced: bool, ns: str = None,
                        printer_columns: list = None):
        """특정 CRD 의 커스텀 객체 목록 (generic 테이블용).

        printer_columns: [{'name', 'jsonPath'}] — CRD 가 정의한 추가 컬럼.
        각 객체에서 jsonPath 값을 추출해 'col_<name>' 키로 담는다.

        반환: [{name, namespace, age, col_<...>, _ns, _kind}]
        """
        if not self.custom:
            return []
        try:
            if namespaced and ns and not self._an(ns):
                result = self.custom.list_namespaced_custom_object(
                    group=group, version=version, namespace=ns, plural=plural)
            else:
                result = self.custom.list_cluster_custom_object(
                    group=group, version=version, plural=plural)
        except Exception:
            return []
        cols = printer_columns or []
        rows = []
        for item in result.get('items', []):
            md = item.get('metadata', {})
            row = {
                'name':      md.get('name', ''),
                'namespace': md.get('namespace', '') or '',
                'age':       _age(_parse_ts(md.get('creationTimestamp'))),
                '_ns':       md.get('namespace'),
                '_kind':     f'{plural}.{group}',
            }
            for c in cols:
                row[f'col_{c["name"]}'] = _jsonpath_get(item, c.get('jsonPath', ''))
            rows.append(row)
        return rows


    # ── ArgoCD ───────────────────────────────────────────────────────────────

    def get_argocd_apps(self):
        """ArgoCD Application CRD 목록. CRD 없으면 None."""
        if not self.custom:
            return None
        try:
            result = self.custom.list_cluster_custom_object(
                group='argoproj.io', version='v1alpha1', plural='applications')
            return result.get('items', [])
        except Exception:
            return None

    def create_argocd_app(self, ns, name, project, repo_url, path,
                           revision, dest_ns, dest_server, sync_policy=None,
                           sources=None):
        body = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'Application',
            'metadata': {'name': name, 'namespace': ns},
            'spec': _build_argocd_spec(
                project, repo_url, path, revision,
                dest_ns, dest_server, sync_policy, sources,
            ),
        }
        self.custom.create_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', body=body)

    def update_argocd_app(self, ns, name, project, repo_url, path,
                           revision, dest_ns, dest_server, sync_policy=None,
                           sources=None):
        patch = {
            'spec': _build_argocd_spec(
                project, repo_url, path, revision,
                dest_ns, dest_server, sync_policy, sources,
            ),
        }
        self.custom.patch_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name, body=patch)

    def delete_argocd_app(self, ns, name):
        self.custom.delete_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name)

    def sync_argocd_app(self, ns, name):
        is_multi_source = False
        try:
            app = self.custom.get_namespaced_custom_object(
                group='argoproj.io', version='v1alpha1',
                namespace=ns, plural='applications', name=name)
            is_multi_source = len(_argo_sources_from_spec(app.get('spec', {}))) > 1
        except Exception:
            is_multi_source = False
        patch = _build_argocd_sync_operation(is_multi_source=is_multi_source)
        self.custom.patch_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name, body=patch)

    def rollback_argocd_app(self, ns, name, history_id):
        patch = {
            'operation': {
                'rollback': {'id': int(history_id), 'prune': False},
                'initiatedBy': {'username': 'polaris'},
            }
        }
        self.custom.patch_namespaced_custom_object(
            group='argoproj.io', version='v1alpha1',
            namespace=ns, plural='applications', name=name, body=patch)

    # ── Helm ─────────────────────────────────────────────────────────────────

    def get_helm_releases(self, *, errors=None) -> list:
        """Helm 릴리스 목록 — helm CLI 우선, K8s Secret 폴백.

        errors 는 폴백(Secret 조회)까지 실패했을 때만 적는다 — helm CLI 가 없어도
        Secret 으로 읽혔으면 수집된 것이다."""
        helm = _find_helm()
        if helm and self.kubeconfig:
            try:
                cmd = [helm, 'list', '--all-namespaces', '-o', 'json',
                       '--kubeconfig', self.kubeconfig]
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=30, creationflags=_NO_WINDOW)
                if r.returncode == 0:
                    data = json.loads(r.stdout or '[]')
                    return [{
                        'name':        d.get('name', '-'),
                        'namespace':   d.get('namespace', '-'),
                        'chart':       d.get('chart', '-'),
                        'app_version': d.get('app_version', '-'),
                        'status':      d.get('status', '-'),
                        'revision':    str(d.get('revision', '-')),
                        'updated':     (d.get('updated', '')[:19]
                                        if d.get('updated') else '-'),
                    } for d in data]
            except Exception:
                pass
        return self._helm_releases_from_secrets(errors=errors)

    def _helm_releases_from_secrets(self, *, errors=None) -> list:
        """K8s Secret (type=helm.sh/release.v1) 에서 릴리즈 메타 추출.

        label_selector/field_selector 로 서버측 선필터 — helm 릴리스가 아닌 나머지 Secret
        (TLS·토큰·레지스트리 등, 대개 훨씬 많고 helm 릴리스는 차트 전체를 gzip+base64 로 품어
        개당 최대 1MB 급)을 전송받지 않는다. 클라이언트측 재확인은 방어적으로 유지."""
        if not self.core:
            _collect_fail(errors, 'helm: core API 미연결')
            return []
        try:
            seen: dict = {}
            secrets = self.core.list_secret_for_all_namespaces(
                label_selector='owner=helm',
                field_selector='type=helm.sh/release.v1',
            ).items
            for s in secrets:
                if s.type != 'helm.sh/release.v1':
                    continue
                lbl = s.metadata.labels or {}
                if lbl.get('owner') != 'helm':
                    continue
                rname = lbl.get('name', s.metadata.name)
                rns   = s.metadata.namespace
                rev   = int(lbl.get('version', 0))
                key   = (rname, rns)
                if key not in seen or rev > seen[key]['_rev']:
                    seen[key] = {
                        'name':        rname,
                        'namespace':   rns,
                        'chart':       lbl.get('chart', '-'),
                        'app_version': lbl.get('app.kubernetes.io/version', '-'),
                        'status':      lbl.get('status', '-'),
                        'revision':    str(rev),
                        'updated':     _age(s.metadata.creation_timestamp),
                        '_rev':        rev,
                    }
            return [v for v in seen.values()]
        except Exception as e:
            _collect_fail(errors, 'helm', e)
            return []


    def helm_release_secrets_meta(self, extra_selector: str = '') -> list:
        """helm 릴리스 Secret 들의 **metadata 만** (v1.3.42, 성능 P3).

        extra_selector 는 호출하는 쪽이 고정 문자열로 줄 때만 쓴다(사용자 입력 금지).
        metadata 전용 요청이 실패하면(오래된 서버·프록시) 예전처럼 전체를 받는다.
        """
        sel = 'owner=helm' + (f',{extra_selector}' if extra_selector else '')
        try:
            from src.k8s_fast import list_metadata
            return list_metadata(self._api_client, '/api/v1/secrets', label_selector=sel,
                                 field_selector='type=helm.sh/release.v1').items
        except Exception:
            return self.core.list_secret_for_all_namespaces(
                label_selector=sel, field_selector='type=helm.sh/release.v1').items

    def get_helm_releases_by_label(self, label_key: str, label_value: str = None,
                                    extra_meta_key: str = '') -> dict:
        """레이블로 필터링된 helm 릴리스의 최신 리비전 메타.

        plugin 들이 자기 출처를 표시하는 helm --labels 메타데이터를 K8s Secret 에서 읽기 위한
        범용 헬퍼. K8sManager 자체는 도메인 특화 라벨(=특정 기능명)을 알지 못한다.

        Args:
            label_key:      필터링할 레이블 키 (예: 'app.kubernetes.io/part-of')
            label_value:    필터링할 값. None 이면 키 존재만 체크.
            extra_meta_key: 결과 dict 값으로 가져올 추가 레이블 키.

        Returns:
            {(release_name, namespace): extra_meta_value}  — extra_meta_key 없으면 ''
        """
        result: dict = {}
        rev_map: dict = {}
        if not self.core:
            return result
        try:
            # 서버측 선필터(helm 릴리스 Secret 만) — label_key/label_value 자체는 호출부마다 다른
            # 임의 값이라 selector 문자열에 안전하게 넣을 보장이 없어 계속 파이썬에서 필터한다.
            # (v1.3.42) 라벨만 보면 되므로 **metadata 만** 받는다 — 릴리스 Secret 은 차트
            # 전체를 품어 하나에 최대 1MB, 리비전마다 하나씩이다. type 은 서버가 이미 걸렀다.
            secrets = self.helm_release_secrets_meta()
            for s in secrets:
                lbl = s.metadata.labels or {}
                if lbl.get('owner') != 'helm':
                    continue
                if label_value is None:
                    if label_key not in lbl:
                        continue
                else:
                    if lbl.get(label_key) != label_value:
                        continue
                rname = lbl.get('name', s.metadata.name)
                rns   = s.metadata.namespace
                rev   = int(lbl.get('version', 0))
                key   = (rname, rns)
                if key not in result or rev > rev_map.get(key, -1):
                    result[key]   = lbl.get(extra_meta_key, '') if extra_meta_key else ''
                    rev_map[key]  = rev
        except Exception:
            pass
        return result


    # ── 보고서용 확장 getter ─────────────────────────────────────────────────

    def get_node_extended(self, *, errors=None):
        try:
            out = []
            for n in self.core.list_node().items:
                status = n.status or type('', (), {})()
                ni     = getattr(status, 'node_info', None)
                alloc  = getattr(status, 'allocatable', None) or {}
                conds  = [{'type': c.type, 'status': c.status,
                           'reason': c.reason or '', 'message': (c.message or '')[:100]}
                          for c in (getattr(status, 'conditions', None) or [])]
                taints = [f'{t.key}={t.value or ""}:{t.effect}'
                          for t in (getattr(n.spec, 'taints', None) or [])]
                labels = n.metadata.labels or {}
                roles  = ', '.join(
                    k.replace('node-role.kubernetes.io/', '')
                    for k in labels if k.startswith('node-role.kubernetes.io/')
                ) or 'worker'
                ready_cond = next((c for c in conds if c['type'] == 'Ready'), None)
                ready_st   = ready_cond['status'] if ready_cond else 'Unknown'
                out.append({
                    'name':              n.metadata.name,
                    'status':            'Ready' if ready_st == 'True' else 'NotReady',
                    'roles':             roles,
                    'version':           ni.kubelet_version if ni else 'N/A',
                    'age':               _age(n.metadata.creation_timestamp),
                    'conditions':        conds,
                    'taints':            taints,
                    'allocatable_cpu':   alloc.get('cpu', 'N/A'),
                    'allocatable_mem':   alloc.get('memory', 'N/A'),
                    'kernel':            ni.kernel_version if ni else 'N/A',
                    'os':                ni.os_image if ni else 'N/A',
                    'container_runtime': ni.container_runtime_version if ni else 'N/A',
                })
            return out
        except Exception as e:
            _collect_fail(errors, 'nodes', e)
            return []

    def get_namespaces_extended(self, *, errors=None):
        try:
            return [{'name':   n.metadata.name,
                     'status': n.status.phase if n.status else 'Unknown',
                     'age':    _age(n.metadata.creation_timestamp)}
                    for n in self.core.list_namespace().items]
        except Exception as e:
            _collect_fail(errors, 'namespaces', e)
            return []

    def get_pod_metrics_all(self):
        if not self.custom:
            return []
        try:
            r = self.custom.list_cluster_custom_object(
                group='metrics.k8s.io', version='v1beta1', plural='pods')
            out = []
            for pod in r.get('items', []):
                ns   = pod.get('metadata', {}).get('namespace', '')
                name = pod.get('metadata', {}).get('name', '')
                cpu_t = mem_t = 0
                for c in pod.get('containers', []):
                    u = c.get('usage', {})
                    cpu_t += _parse_cpu(u.get('cpu', '0'))
                    mem_t += _parse_mem(u.get('memory', '0'))
                out.append({'namespace': ns, 'name': name,
                            'cpu_m': cpu_t, 'mem_mi': mem_t // (1024 * 1024)})
            out.sort(key=lambda x: x['cpu_m'], reverse=True)
            return out
        except Exception:
            return []

    def get_pod_metrics(self, namespace: str, name: str):
        """단일 파드의 현재 메트릭 (컨테이너별 CPU/MEM).
        반환: {ok, timestamp, window, containers: [{name, cpu_m, mem_mi}],
               total: {cpu_m, mem_mi}, requests: {cpu_m, mem_mi}, limits: {cpu_m, mem_mi}}
        """
        if not self.custom or not self.core:
            return {'ok': False, 'error': 'metrics API 미연결'}
        try:
            r = self.custom.get_namespaced_custom_object(
                group='metrics.k8s.io', version='v1beta1',
                namespace=namespace, plural='pods', name=name)
            containers = []
            cpu_total = 0
            mem_total = 0
            for c in r.get('containers', []):
                u = c.get('usage', {})
                cpu_m  = _parse_cpu(u.get('cpu', '0'))
                mem_mi = _parse_mem(u.get('memory', '0')) // (1024 * 1024)
                containers.append({
                    'name':   c.get('name', ''),
                    'cpu_m':  cpu_m,
                    'mem_mi': mem_mi,
                })
                cpu_total += cpu_m
                mem_total += mem_mi

            # Pod spec에서 requests / limits 가져오기
            req_cpu = req_mem = lim_cpu = lim_mem = 0
            try:
                pod = self.core.read_namespaced_pod(name=name, namespace=namespace)
                for spec_c in (pod.spec.containers or []):
                    res = spec_c.resources
                    if not res:
                        continue
                    req = res.requests or {}
                    lim = res.limits   or {}
                    req_cpu += _parse_cpu(req.get('cpu', '0'))
                    req_mem += _parse_mem(req.get('memory', '0')) // (1024 * 1024)
                    lim_cpu += _parse_cpu(lim.get('cpu', '0'))
                    lim_mem += _parse_mem(lim.get('memory', '0')) // (1024 * 1024)
            except Exception:
                pass

            return {
                'ok':         True,
                'timestamp':  r.get('timestamp', ''),
                'window':     r.get('window', ''),
                'containers': containers,
                'total':      {'cpu_m': cpu_total, 'mem_mi': mem_total},
                'requests':   {'cpu_m': req_cpu,   'mem_mi': req_mem},
                'limits':     {'cpu_m': lim_cpu,   'mem_mi': lim_mem},
            }
        except Exception as e:
            err_str = str(e)
            # metrics-server 미설치 케이스 식별
            if 'NotFound' in err_str or '404' in err_str or 'metrics.k8s.io' in err_str:
                return {'ok': False, 'error': 'metrics-server가 설치되어 있지 않거나 응답하지 않습니다.',
                        'no_metrics_server': True}
            return {'ok': False, 'error': err_str}

    def get_deployments_extended(self, *, meta=False, errors=None):
        """meta=True 면 replicas 를 누가 관리하는지 판단할 근거를 더한다(v1.4.13, 보고서 전용):
        `owners`(ownerReferences kind 목록) · `managed_by`(app.kubernetes.io/managed-by) ·
        `argocd`(Argo CD 추적 표시 여부). 기본값은 기존 반환 형태 그대로 — 스냅샷 diff 대상이다."""
        try:
            items = self.apps.list_deployment_for_all_namespaces().items
            rows = [{'namespace': d.metadata.namespace, 'name': d.metadata.name,
                     'ready':    d.status.ready_replicas or 0,
                     'desired':  d.spec.replicas or 0,
                     'available': d.status.available_replicas or 0,
                     'strategy': d.spec.strategy.type if d.spec and d.spec.strategy else '-',
                     'age':      _age(d.metadata.creation_timestamp)}
                    for d in items]
            if meta:
                for row, d in zip(rows, items):
                    labels = d.metadata.labels or {}
                    ann = d.metadata.annotations or {}
                    row['owners'] = [getattr(r, 'kind', '') or ''
                                     for r in (d.metadata.owner_references or [])]
                    row['managed_by'] = str(labels.get('app.kubernetes.io/managed-by', '') or '')
                    row['argocd'] = bool(ann.get('argocd.argoproj.io/tracking-id')
                                         or labels.get('argocd.argoproj.io/instance'))
            return rows
        except Exception as e:
            _collect_fail(errors, 'deployments', e)
            return []

    def get_statefulsets_extended(self, *, errors=None):
        try:
            items = self.apps.list_stateful_set_for_all_namespaces().items
            return [{'namespace': s.metadata.namespace, 'name': s.metadata.name,
                     'ready':   s.status.ready_replicas or 0,
                     'desired': s.spec.replicas or 0,
                     'service': s.spec.service_name or '-',
                     'age':     _age(s.metadata.creation_timestamp)}
                    for s in items]
        except Exception as e:
            _collect_fail(errors, 'statefulsets', e)
            return []

    def get_daemonsets_extended(self):
        try:
            items = self.apps.list_daemon_set_for_all_namespaces().items
            return [{'namespace': d.metadata.namespace, 'name': d.metadata.name,
                     'desired':  d.status.desired_number_scheduled or 0,
                     'ready':    d.status.number_ready or 0,
                     'available': d.status.number_available or 0,
                     'age':      _age(d.metadata.creation_timestamp)}
                    for d in items]
        except Exception:
            return []

    def get_resource_quotas(self, *, errors=None):
        try:
            return [{'namespace': rq.metadata.namespace, 'name': rq.metadata.name,
                     'hard': {k: str(v) for k, v in (rq.status.hard or {}).items()},
                     'used': {k: str(v) for k, v in (rq.status.used or {}).items()}}
                    for rq in self.core.list_resource_quota_for_all_namespaces().items]
        except Exception as e:
            _collect_fail(errors, 'resource_quotas', e)
            return []

    def get_limit_ranges(self, *, errors=None):
        try:
            out = []
            for lr in self.core.list_limit_range_for_all_namespaces().items:
                limits = []
                for lim in (lr.spec.limits or []) if lr.spec else []:
                    limits.append({
                        'type':            lim.type or '-',
                        'default':         {k: str(v) for k, v in (lim.default or {}).items()},
                        'default_request': {k: str(v) for k, v in (lim.default_request or {}).items()},
                    })
                out.append({'namespace': lr.metadata.namespace,
                            'name': lr.metadata.name, 'limits': limits})
            return out
        except Exception as e:
            _collect_fail(errors, 'limit_ranges', e)
            return []

    def get_hpa_extended(self, *, errors=None):
        if not self.autoscaling:
            _collect_fail(errors, 'hpa: autoscaling API 미연결')
            return []
        try:
            return [{'namespace':   h.metadata.namespace, 'name': h.metadata.name,
                     'reference':   f'{h.spec.scale_target_ref.kind}/{h.spec.scale_target_ref.name}' if h.spec and h.spec.scale_target_ref else '-',
                     'min':         h.spec.min_replicas or 1,
                     'max':         h.spec.max_replicas or 1,
                     'current':     h.status.current_replicas or 0,
                     'desired':     h.status.desired_replicas or 0,
                     'target_cpu':  h.spec.target_cpu_utilization_percentage or '-',
                     'current_cpu': h.status.current_cpu_utilization_percentage or '-',
                     'age':         _age(h.metadata.creation_timestamp)}
                    for h in self.autoscaling.list_horizontal_pod_autoscaler_for_all_namespaces().items]
        except Exception as e:
            _collect_fail(errors, 'hpa', e)
            return []

    def get_pdbs(self, *, meta=False, errors=None):
        """meta=True 면 `labels` · `owners`(ownerReferences kind 목록)를 더한다 — 보고서가
        오퍼레이터(Longhorn · Rook 등)가 만든 PDB 를 가려내는 데 쓴다(v1.4.13)."""
        if not self.policy:
            _collect_fail(errors, 'pdbs: policy API 미연결')
            return []
        try:
            items = self.policy.list_pod_disruption_budget_for_all_namespaces().items
            rows = [{'namespace':           p.metadata.namespace, 'name': p.metadata.name,
                     'min_available':       getattr(p.spec, 'min_available', '-'),
                     'max_unavailable':     getattr(p.spec, 'max_unavailable', '-'),
                     'current_healthy':     getattr(p.status, 'current_healthy', 0),
                     'desired_healthy':     getattr(p.status, 'desired_healthy', 0),
                     'disruptions_allowed': getattr(p.status, 'disruptions_allowed', 0),
                     'age':                 _age(p.metadata.creation_timestamp)}
                    for p in items]
            if meta:
                for row, p in zip(rows, items):
                    row['labels'] = dict(p.metadata.labels or {})
                    row['owners'] = [getattr(r, 'kind', '') or ''
                                     for r in (p.metadata.owner_references or [])]
            return rows
        except Exception as e:
            _collect_fail(errors, 'pdbs', e)
            return []

    def get_network_policies(self, *, errors=None):
        if not self.net:
            _collect_fail(errors, 'network_policies: networking API 미연결')
            return []
        try:
            return [{'namespace':     n.metadata.namespace, 'name': n.metadata.name,
                     'pod_selector':  str(n.spec.pod_selector.match_labels or 'all') if n.spec and n.spec.pod_selector else '-',
                     'ingress_rules': len(n.spec.ingress or []) if n.spec else 0,
                     'egress_rules':  len(n.spec.egress  or []) if n.spec else 0,
                     'age':           _age(n.metadata.creation_timestamp)}
                    for n in self.net.list_network_policy_for_all_namespaces().items]
        except Exception as e:
            _collect_fail(errors, 'network_policies', e)
            return []

    # CNI 전용 정책 — Kubernetes NetworkPolicy 만 세면 Cilium · Calico 로 막아 둔 클러스터를
    # 「트래픽 제한 없음」 으로 잘못 적는다(v1.4.13).
    _CNI_POLICY_KINDS = (
        ('CiliumNetworkPolicy',            'cilium.io',             'v2', 'ciliumnetworkpolicies'),
        ('CiliumClusterwideNetworkPolicy', 'cilium.io',             'v2', 'ciliumclusterwidenetworkpolicies'),
        ('Calico NetworkPolicy',           'crd.projectcalico.org', 'v1', 'networkpolicies'),
        ('Calico GlobalNetworkPolicy',     'crd.projectcalico.org', 'v1', 'globalnetworkpolicies'),
    )

    def get_cni_network_policy_counts(self, *, errors=None) -> dict:
        """Cilium · Calico 정책 개수 (v1.4.13, 보고서 전용).

        반환: {종류: 개수 | None}. CRD 가 없으면(404) 그 종류는 키 자체가 없다 — 쓰지 않는 CNI 다.
        그 밖의 실패(권한 등)는 None = 확인 불가. 「0」 으로 적지 않는다.
        종류마다 1건만 받고 remainingItemCount 로 개수를 센다(정책 본문을 내려받지 않는다).
        """
        out = {}
        if not self.custom:
            _collect_fail(errors, 'cni_network_policies: custom objects API 미연결')
            return out
        for label, group, version, plural in self._CNI_POLICY_KINDS:
            try:
                r = self.custom.list_cluster_custom_object(
                    group=group, version=version, plural=plural, limit=1)
            except Exception as e:
                if getattr(e, 'status', None) == 404:
                    continue
                out[label] = None
                _collect_fail(errors, f'cni_network_policies {label}', e)
                continue
            items = (r or {}).get('items') or []
            remain = ((r or {}).get('metadata') or {}).get('remainingItemCount') or 0
            try:
                out[label] = len(items) + int(remain)
            except (TypeError, ValueError):
                out[label] = len(items)
        return out

    def get_ingress_classes(self):
        if not self.net:
            return []
        try:
            return [{'name':       ic.metadata.name,
                     'controller': ic.spec.controller if ic.spec else '-',
                     'is_default': (ic.metadata.annotations or {}).get(
                         'ingressclass.kubernetes.io/is-default-class', 'false'),
                     'age':        _age(ic.metadata.creation_timestamp)}
                    for ic in self.net.list_ingress_class().items]
        except Exception:
            return []

    def get_storage_classes(self, *, errors=None):
        if not self.storage:
            _collect_fail(errors, 'storage_classes: storage API 미연결')
            return []
        try:
            return [{'name':          sc.metadata.name,
                     'provisioner':   sc.provisioner or '-',
                     'reclaim_policy': sc.reclaim_policy or '-',
                     'binding_mode':  sc.volume_binding_mode or '-',
                     'is_default':    (sc.metadata.annotations or {}).get(
                         'storageclass.kubernetes.io/is-default-class', 'false'),
                     'age':           _age(sc.metadata.creation_timestamp)}
                    for sc in self.storage.list_storage_class().items]
        except Exception as e:
            _collect_fail(errors, 'storage_classes', e)
            return []

    def get_rbac_summary(self, *, errors=None):
        if not self.rbac:
            _collect_fail(errors, 'rbac: rbac API 미연결')
            return {}
        try:
            crs  = self.rbac.list_cluster_role().items
            crbs = self.rbac.list_cluster_role_binding().items
            roles = self.rbac.list_role_for_all_namespaces().items
            rbs  = self.rbac.list_role_binding_for_all_namespaces().items
            sas  = self.core.list_service_account_for_all_namespaces().items
            return {
                'cluster_roles':         len(crs),
                'cluster_role_bindings': len(crbs),
                'roles':                 len(roles),
                'role_bindings':         len(rbs),
                'service_accounts':      len(sas),
                'cluster_roles_list': [{'name': cr.metadata.name,
                                        'age':  _age(cr.metadata.creation_timestamp)}
                                       for cr in crs if not cr.metadata.name.startswith('system:')][:30],
                'cluster_role_bindings_list': [{'name': crb.metadata.name,
                                                'subjects': len(crb.subjects or [])}
                                               for crb in crbs if not crb.metadata.name.startswith('system:')][:30],
            }
        except Exception as e:
            _collect_fail(errors, 'rbac', e)
            return {}

    # ── RBAC 분석 뷰어 ───────────────────────────────────────────────────────

    def get_rbac_roles(self, include_system: bool = False, *, errors=None):
        """Role + ClusterRole 목록 (규칙 포함).

        반환: [{name, namespace('' if cluster), kind('Role'|'ClusterRole'),
                rules:[{verbs, resources, apiGroups}], rule_count, age}]
        """
        if not self.rbac:
            _collect_fail(errors, 'rbac roles: rbac API 미연결')
            return []
        out = []

        def add(items, kind):
            for r in items:
                name = r.metadata.name
                if not include_system and name.startswith('system:'):
                    continue
                rules = []
                for rule in (r.rules or []):
                    rules.append({
                        'verbs':     list(rule.verbs or []),
                        'resources': list(rule.resources or []),
                        'apiGroups': list(rule.api_groups or []),
                    })
                out.append({
                    'name':       name,
                    'namespace':  getattr(r.metadata, 'namespace', '') or '',
                    'kind':       kind,
                    'rules':      rules,
                    'rule_count': len(rules),
                    'age':        _age(r.metadata.creation_timestamp),
                })
        try:
            add(self.rbac.list_cluster_role().items, 'ClusterRole')
            add(self.rbac.list_role_for_all_namespaces().items, 'Role')
        except Exception as e:
            _collect_fail(errors, 'rbac roles', e)
        out.sort(key=lambda x: (x['kind'] != 'ClusterRole', x['name']))
        return out

    def get_rbac_bindings(self, include_system: bool = False, *, errors=None):
        """RoleBinding + ClusterRoleBinding 목록 (roleRef + subjects).

        반환: [{name, namespace, kind, role_ref:{kind,name}, subjects:[{kind,name,namespace}], age}]
        """
        if not self.rbac:
            _collect_fail(errors, 'rbac bindings: rbac API 미연결')
            return []
        out = []

        def add(items, kind):
            for b in items:
                name = b.metadata.name
                if not include_system and name.startswith('system:'):
                    continue
                rr = b.role_ref
                subs = []
                for s in (b.subjects or []):
                    subs.append({
                        'kind':      getattr(s, 'kind', ''),
                        'name':      getattr(s, 'name', ''),
                        'namespace': getattr(s, 'namespace', '') or '',
                    })
                out.append({
                    'name':      name,
                    'namespace': getattr(b.metadata, 'namespace', '') or '',
                    'kind':      kind,
                    'role_ref':  {'kind': getattr(rr, 'kind', ''), 'name': getattr(rr, 'name', '')},
                    'subjects':  subs,
                    'age':       _age(b.metadata.creation_timestamp),
                })
        try:
            add(self.rbac.list_cluster_role_binding().items, 'ClusterRoleBinding')
            add(self.rbac.list_role_binding_for_all_namespaces().items, 'RoleBinding')
        except Exception as e:
            _collect_fail(errors, 'rbac bindings', e)
        out.sort(key=lambda x: (x['kind'] != 'ClusterRoleBinding', x['name']))
        return out

    def get_service_accounts(self):
        """ServiceAccount 목록. 반환: [{name, namespace, secrets, age}]"""
        if not self.core:
            return []
        try:
            return [{
                'name':      sa.metadata.name,
                'namespace': sa.metadata.namespace,
                'secrets':   len(sa.secrets or []),
                'age':       _age(sa.metadata.creation_timestamp),
            } for sa in self.core.list_service_account_for_all_namespaces().items]
        except Exception:
            return []

    def get_rbac_risky_subjects(self, include_system: bool = False, *, errors=None):
        """과도한 권한(클러스터 관리자급) 보유 subject 목록 — 보고서 보안 점검용.

        판정 기준:
          • cluster-admin ClusterRole 에 바인딩된 subject
          • 와일드카드 규칙(apiGroups=*, resources=*, verbs=*) 보유 role 에 바인딩된 subject

        system: 접두 이름(빌드인 system:masters 등)은 기본 제외(노이즈 감소).
        반환: [{subject_kind, name, namespace, role, role_kind,
                binding, binding_kind, reason}]
        """
        try:
            if errors is None:
                roles    = self.get_rbac_roles(include_system)
                bindings = self.get_rbac_bindings(include_system)
            else:
                roles    = self.get_rbac_roles(include_system, errors=errors)
                bindings = self.get_rbac_bindings(include_system, errors=errors)
        except Exception as e:
            _collect_fail(errors, 'rbac_risky', e)
            return []

        role_idx = {(r['kind'], r['name'], r['namespace']): r for r in roles}

        def _is_wildcard(role):
            for rule in (role.get('rules') or []):
                ag  = rule.get('apiGroups') or []
                res = rule.get('resources') or []
                vb  = rule.get('verbs') or []
                if '*' in ag and '*' in res and '*' in vb:
                    return True
            return False

        risky = []
        for b in bindings:
            rr    = b.get('role_ref') or {}
            rname = rr.get('name', '')
            rkind = rr.get('kind', '')
            is_admin = (rkind == 'ClusterRole' and rname == 'cluster-admin')
            role = (role_idx.get(('ClusterRole', rname, ''))
                    or role_idx.get(('Role', rname, b.get('namespace', ''))))
            wild = bool(role and _is_wildcard(role))
            if not (is_admin or wild):
                continue
            reason = 'cluster-admin 바인딩' if is_admin else '와일드카드 권한(*/*/*)'
            for s in (b.get('subjects') or []):
                sname = s.get('name', '')
                if not include_system and sname.startswith('system:'):
                    continue
                risky.append({
                    'subject_kind': s.get('kind', ''),
                    'name':         sname,
                    'namespace':    s.get('namespace', '') or b.get('namespace', '') or '-',
                    'role':         rname,
                    'role_kind':    rkind,
                    'binding':      b.get('name', ''),
                    'binding_kind': b.get('kind', ''),
                    'reason':       reason,
                })
        return risky

    def get_kube_system_info(self, *, errors=None):
        NS = 'kube-system'
        try:
            pods = self.core.list_namespaced_pod(NS).items
            deps = self.apps.list_namespaced_deployment(NS).items
            dss  = self.apps.list_namespaced_daemon_set(NS).items
            return {
                'pods': [{'name': p.metadata.name,
                          'status': p.status.phase or 'Unknown',
                          'restarts': sum(c.restart_count or 0
                                         for c in (p.status.container_statuses or [])),
                          'node': p.spec.node_name or '-'} for p in pods],
                'deployments': [{'name': d.metadata.name,
                                 'ready': f'{d.status.ready_replicas or 0}/{d.spec.replicas or 0}'}
                                for d in deps],
                'daemonsets':  [{'name': ds.metadata.name,
                                 'desired': ds.status.desired_number_scheduled or 0,
                                 'ready':   ds.status.number_ready or 0} for ds in dss],
            }
        except Exception as e:
            _collect_fail(errors, 'kube_system', e)
            return {}
