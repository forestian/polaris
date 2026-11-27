# -*- coding: utf-8 -*-
"""Polaris MCP 서버 — stdio 트랜스포트 (Phase 0~1: 조회 전용).

목적: AI(MCP 클라이언트)에게 접속 크리덴셜을 넘기지 않는다. AI 는 "무엇을 하라"는
tool call 만 보내고, Polaris 가 vault 의 크리덴셜로 대신 조회한 뒤 **결과만** 돌려준다.
모든 호출은 감사 로그(mcp-audit.log)에 기록한다.

실행:  polaris.exe --mcp   (개발: python polaris.py --mcp)

전제:
  - 헤드리스 프로세스라 마스터 비밀번호를 대화식으로 입력받을 수 없다 →
    **DPAPI 자동 잠금 해제(같은 Windows 사용자·같은 PC)** 가 켜져 있어야 vault 를 연다.
    꺼져 있으면 툴이 명확한 안내 오류를 반환한다(비밀번호를 파일/환경변수에 저장하지 않음).
  - 신뢰 경계: 같은 사용자·같은 PC·로컬 stdio(네트워크 노출 없음).

조회 툴(조회 전용 — 이 판의 MCP 는 클러스터를 바꾸지 않는다):
  - polaris_list_clusters   : 보관된 클러스터(kubeconfig) 이름 목록 (크리덴셜 값 미반환)
  - polaris_use_cluster     : 이후 호출의 기본 대상 클러스터 지정(연결+활성화)
  - polaris_list_resources  : 지정/활성 클러스터의 특정 kind 리소스 목록
  - polaris_get_resource    : 단일 리소스 상세 (describe | yaml | events) — Secret 마스킹 적용
  - polaris_get_logs        : 파드 로그 (tail)
  - polaris_get_events      : 클러스터 이벤트 (namespace/limit/types)

불변 원칙(P1): 크리덴셜 원문(kubeconfig 본문/토큰)은 응답으로도 감사
로그로도 절대 직렬화하지 않는다. 조회 결과에는 백엔드 Secret 마스킹이 적용된다.
"""
import os
import json
import time
import secrets
import threading
from datetime import datetime, timezone

from src.paths import polaris_dir

SERVER_NAME = 'polaris-mcp'

# PolarisAPI 인스턴스는 스레드에서 호출되므로 클러스터 연결 상태 변경을 직렬화
_LOCK = threading.Lock()
# 감사 로그 인자에서 가릴 키 힌트 (방어적 — 현재 툴엔 크리덴셜 인자가 없지만 규칙으로 고정)
_SECRET_HINT = ('password', 'passphrase', 'token', 'secret', 'credential')

_api = None


# ─────────────────────────────────────────────────────────────────────────────
# 감사 로그
# ─────────────────────────────────────────────────────────────────────────────
def _audit_path():
    d = polaris_dir() / 'logs'
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d / 'mcp-audit.log'


def _redact(args):
    """감사 로그용 인자 세탁 — 크리덴셜류 키 값은 '***' 로. (P1 하드 규칙)"""
    if not isinstance(args, dict):
        return args
    out = {}
    for k, v in args.items():
        kl = str(k).lower()
        if any(h in kl for h in _SECRET_HINT):
            out[k] = '***'
        elif kl in _BODY_KEYS and isinstance(v, str):
            # 명령 · YAML 본문은 평문 감사 로그에 남기지 않는다(v1.5.28 검토 — `mysql -p비번 …` · Secret YAML 이
            # 그대로 남았다). 무엇이 실행됐는지 대조할 수 있게 길이와 해시만
            import hashlib
            out[k] = {'len': len(v), 'sha256': hashlib.sha256(v.encode('utf-8', 'replace')).hexdigest()[:16]}
        else:
            out[k] = v
    return out


_BODY_KEYS = frozenset(('command', 'cmd', 'script', 'yaml', 'manifest', 'content', 'body', 'data', 'values'))


def _audit(record: dict):
    try:
        with open(_audit_path(), 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 헤드리스 PolarisAPI + vault/클러스터 헬퍼
# ─────────────────────────────────────────────────────────────────────────────
def _get_api():
    global _api
    if _api is None:
        from src.api import PolarisAPI
        _api = PolarisAPI()   # 창(window) 없이 헤드리스 생성
    return _api


_TOKEN_ENV = 'POLARIS_MCP_TOKEN'
_token_meta = None      # 이번 프로세스가 해제에 사용한 토큰 {id, scope, label}

_NO_TOKEN_MSG = (
    'MCP 액세스 토큰이 없습니다. Polaris → 설정 → 보안 잠금 → "MCP 액세스 토큰" 에서 '
    '토큰을 발급한 뒤, MCP 클라이언트 설정의 env 에 '
    'POLARIS_MCP_TOKEN 으로 넣고 클라이언트를 재시작하세요.')
_BAD_TOKEN_MSG = (
    'MCP 액세스 토큰이 유효하지 않습니다(형식 오류 · 폐기됨 · 만료됨 중 하나). '
    'Polaris 설정에서 토큰 목록을 확인하고 필요하면 재발급하세요.')


def _ensure_unlocked(api):
    """MCP 액세스 토큰으로만 vault 를 연다. (ok, error).

    ★ DPAPI 자동 잠금 해제는 여기서 쓰지 않는다(v1.2.119). DPAPI 는 Polaris GUI 의
    편의 기능이고, 그걸 켰다는 이유로 외부 AI 가 vault 에 닿을 수 있으면 안 되기
    때문이다. MCP 는 사용자가 명시적으로 발급한 토큰을 제시해야만 열린다 —
    토큰은 개별 폐기·범위 제한·만료가 되고 감사 로그에 주체가 남는다.

    크리덴셜(토큰 값 포함)은 오류 메시지로도 절대 반환하지 않는다.
    """
    global _token_meta
    st = api.vault_status()
    if not st.get('available'):
        return False, 'vault 를 사용할 수 없습니다 (cryptography 패키지 없음).'
    if not st.get('exists'):
        return False, 'vault 가 없습니다. 먼저 Polaris GUI 에서 마스터 비밀번호를 설정하세요.'
    if _token_meta is not None and st.get('unlocked'):
        # 이 프로세스가 이미 토큰으로 열어 뒀다 — 그사이 창에서 폐기 · 만료됐으면 닫는다(v1.5.6).
        # 예전에는 한 번 열면 MCP 가 꺼질 때까지 폐기한 토큰으로도 계속 됐다.
        try:
            toks = {t['id']: t for t in (api.vault_list_mcp_tokens() or {}).get('tokens', [])}
            cur = toks.get(_token_meta.get('id'))
            if cur is None or cur.get('expired'):
                api.vault_lock()
                _token_meta = None
                return False, _BAD_TOKEN_MSG
        except Exception:
            pass
        return True, None

    token = (os.environ.get(_TOKEN_ENV) or '').strip()
    if not token:
        return False, _NO_TOKEN_MSG
    r = api.vault_unlock_token(token)
    if not r.get('ok'):
        return False, _BAD_TOKEN_MSG
    _token_meta = r.get('token') or {}
    return True, None


def _ensure_cluster(api, kc_name):
    """kc_name 보관본을 활성 클러스터로 만든다(이미 연결됐으면 전환). (ok, error)."""
    for cid, info in api._clusters.items():
        if info.get('kc_name') == kc_name:
            api.switch_cluster(cid)
            return True, None
    r = api.add_cluster_from_vault(kc_name)
    if r.get('ok'):
        return True, None
    return False, (r.get('error') or '클러스터 연결 실패')


def _resolve_cluster(api, kc_name):
    """cluster 인자가 있으면 연결/전환, 없으면 현재 활성 클러스터 사용. (ok, error)."""
    kc = (kc_name or '').strip()
    if kc:
        return _ensure_cluster(api, kc)
    if api._active_id and api._active_id in api._clusters:
        return True, None
    return False, ("대상 클러스터가 지정되지 않았습니다. 'cluster' 인자를 주거나 "
                   "먼저 polaris_use_cluster 를 호출하세요.")


def _active_kc(api):
    return api._clusters.get(api._active_id, {}).get('kc_name', '') if api._active_id else ''


# ─────────────────────────────────────────────────────────────────────────────
# 툴 구현 (동기 — 핸들러에서 스레드로 호출)
# ─────────────────────────────────────────────────────────────────────────────
def _tool_list_clusters(args):
    api = _get_api()
    with _LOCK:
        ok, err = _ensure_unlocked(api)
        if not ok:
            return {'ok': False, 'error': err}
        r = api.list_kubeconfigs()
    if not r.get('ok'):
        return {'ok': False, 'error': r.get('error') or 'kubeconfig 목록 조회 실패'}
    items = r.get('items', [])
    return {'ok': True, 'clusters': items, 'count': len(items)}


def _tool_use_cluster(args):
    kc = (args.get('cluster') or '').strip()
    if not kc:
        return {'ok': False, 'error': "필수 인자 'cluster' 가 누락되었습니다."}
    api = _get_api()
    with _LOCK:
        ok, err = _ensure_unlocked(api)
        if not ok:
            return {'ok': False, 'error': err}
        ok, err = _ensure_cluster(api, kc)
        if not ok:
            return {'ok': False, 'error': err}
        info = api._clusters.get(api._active_id, {})
    return {'ok': True, 'active': kc,
            'context': info.get('context', ''), 'version': info.get('version', '')}


def _tool_list_resources(args):
    kind = (args.get('kind') or '').strip()
    ns = (args.get('namespace') or '').strip()
    if not kind:
        return {'ok': False, 'error': "필수 인자 'kind' 가 누락되었습니다."}
    api = _get_api()
    with _LOCK:
        ok, err = _ensure_unlocked(api)
        if not ok:
            return {'ok': False, 'error': err}
        ok, err = _resolve_cluster(api, args.get('cluster'))
        if not ok:
            return {'ok': False, 'error': err}
        try:
            # 어떤 종류든(v1.5.53) — 예전 api.get_resource 는 표에 없는 종류(CRD · 단수 표기)를 조용히 0건으로 돌려줬다
            r = api.list_resources_any(kind, ns)
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        cluster = _active_kc(api)
    if not r.get('ok'):
        return {'ok': False, 'cluster': cluster, 'kind': kind, 'error': r.get('error')}
    rows = r.get('items') or []
    out = {'ok': True, 'cluster': cluster, 'kind': r.get('kind') or kind,
           'namespace': ns or '(all)', 'count': len(rows), 'items': rows}
    for k in ('truncated', 'note'):
        if r.get(k):
            out[k] = r[k]
    return out


def _tool_get_resource(args):
    kind = (args.get('kind') or '').strip()
    name = (args.get('name') or '').strip()
    ns = (args.get('namespace') or '').strip()
    output = (args.get('output') or 'describe').strip().lower()
    if not kind or not name:
        return {'ok': False, 'error': "필수 인자 'kind'/'name' 이 누락되었습니다."}
    if output not in ('describe', 'yaml', 'events'):
        return {'ok': False, 'error': "output 은 describe | yaml | events 중 하나여야 합니다."}
    api = _get_api()
    with _LOCK:
        ok, err = _ensure_unlocked(api)
        if not ok:
            return {'ok': False, 'error': err}
        ok, err = _resolve_cluster(api, args.get('cluster'))
        if not ok:
            return {'ok': False, 'error': err}
        try:
            if output == 'yaml':
                r = api.get_resource_yaml(kind, ns, name)
            elif output == 'describe':
                r = api.get_resource_describe(kind, ns, name)
            else:  # events
                r = {'ok': True, 'events': api.get_resource_events(kind, ns, name)}
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        cluster = _active_kc(api)
    out = {'ok': bool(r.get('ok', True)), 'cluster': cluster, 'kind': kind,
           'name': name, 'namespace': ns or '(none)', 'output': output}
    if not out['ok']:
        out['error'] = r.get('error')
        return out
    for k in ('yaml', 'describe', 'events'):
        if k in r:
            out[k] = r[k]
    return out


def _tool_get_logs(args):
    ns = (args.get('namespace') or '').strip()
    pod = (args.get('pod') or '').strip()
    container = (args.get('container') or '').strip()
    try:
        tail = max(1, min(int(args.get('tail') or 200), 5000))
    except Exception:
        tail = 200
    if not ns or not pod:
        return {'ok': False, 'error': "필수 인자 'namespace'/'pod' 가 누락되었습니다."}
    api = _get_api()
    with _LOCK:
        ok, err = _ensure_unlocked(api)
        if not ok:
            return {'ok': False, 'error': err}
        ok, err = _resolve_cluster(api, args.get('cluster'))
        if not ok:
            return {'ok': False, 'error': err}
        try:
            r = api.get_resource_logs(ns, pod, container, tail)
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        cluster = _active_kc(api)
    if not r.get('ok'):
        return {'ok': False, 'error': r.get('error'), 'cluster': cluster}
    return {'ok': True, 'cluster': cluster, 'namespace': ns, 'pod': pod,
            'container': container or '(default)', 'tail': tail,
            'logs': r.get('logs', ''), 'warning': r.get('error') or None}


def _tool_get_events(args):
    ns = (args.get('namespace') or '').strip()
    try:
        limit = max(1, min(int(args.get('limit') or 200), 1000))
    except Exception:
        limit = 200
    types = args.get('types')
    if isinstance(types, str):
        types = [types]
    api = _get_api()
    with _LOCK:
        ok, err = _ensure_unlocked(api)
        if not ok:
            return {'ok': False, 'error': err}
        ok, err = _resolve_cluster(api, args.get('cluster'))
        if not ok:
            return {'ok': False, 'error': err}
        try:
            r = api.get_cluster_events(ns, limit, types)
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        cluster = _active_kc(api)
    if not r.get('ok'):
        return {'ok': False, 'error': r.get('error'), 'cluster': cluster}
    evs = r.get('events', [])
    return {'ok': True, 'cluster': cluster, 'namespace': ns or '(all)',
            'count': len(evs), 'events': evs, 'source': r.get('source')}


_TOOLS = {
    'polaris_list_clusters': _tool_list_clusters,
    'polaris_use_cluster': _tool_use_cluster,
    'polaris_list_resources': _tool_list_resources,
    'polaris_get_resource': _tool_get_resource,
    'polaris_get_logs': _tool_get_logs,
    'polaris_get_events': _tool_get_events,
}


# 감사 로그에 남길 안전한 요약 키(크리덴셜/대용량 본문 제외 — logs/yaml/describe/items 는 미기록).
_AUDIT_SUMMARY_KEYS = ('cluster', 'kind', 'name', 'namespace', 'pod', 'output',
                       'count', 'source', 'active', 'truncated')


def _tool_defs():
    import mcp.types as types
    _cluster_prop = {'type': 'string',
                     'description': '클러스터 이름(polaris_list_clusters 값). 생략 시 '
                                    'polaris_use_cluster 로 지정한 활성 클러스터 사용'}
    _kind_desc = ('리소스 종류 — pods, deployments, statefulsets, daemonsets, replicasets, jobs, cronjobs, services, '
                  'ingresses, nodes, namespaces, configmaps, secrets, pvcs, pvs(단수 · 줄임 표기도 됨) 와 '
                  'CRD 를 포함한 **그 밖의 모든 종류**(예: helmchartconfigs, addons.k3s.cattle.io, certificates) — '
                  '그 밖의 종류는 이름 · 네임스페이스 · 만든 시각만 돌려준다. 이 클러스터에 없는 종류면 0건이 아니라 오류.')
    return [
        types.Tool(
            name='polaris_list_clusters',
            description=('Polaris 보안 보관함에 저장된(연결 가능한) 쿠버네티스 클러스터 '
                         '(kubeconfig) 이름 목록을 반환한다. 크리덴셜 값은 반환하지 않는다. '
                         '다른 툴의 cluster 인자로 이 이름을 사용한다.'),
            inputSchema={'type': 'object', 'properties': {}, 'required': []},
        ),
        types.Tool(
            name='polaris_use_cluster',
            description=('이후 호출들의 기본 대상 클러스터를 지정한다(연결 후 활성화). '
                         '지정하면 다른 툴에서 cluster 인자를 생략할 수 있다.'),
            inputSchema={'type': 'object',
                         'properties': {'cluster': {'type': 'string',
                                                    'description': '활성화할 클러스터 이름'}},
                         'required': ['cluster']},
        ),
        types.Tool(
            name='polaris_list_resources',
            description=('지정/활성 클러스터의 특정 종류(kind) 리소스 목록을 반환한다. '
                         'Polaris 가 보관된 크리덴셜로 조회하며, 크리덴셜은 노출되지 않는다.'),
            inputSchema={
                'type': 'object',
                'properties': {
                    'cluster': _cluster_prop,
                    'kind': {'type': 'string', 'description': _kind_desc},
                    'namespace': {'type': 'string', 'description': '네임스페이스 (비우면 전체)'},
                },
                'required': ['kind'],
            },
        ),
        types.Tool(
            name='polaris_get_resource',
            description=('단일 리소스의 상세 정보를 반환한다. output=describe(기본)|yaml|events. '
                         'Secret/자격증명 필드는 자동 마스킹된다.'),
            inputSchema={
                'type': 'object',
                'properties': {
                    'cluster': _cluster_prop,
                    'kind': {'type': 'string', 'description': _kind_desc},
                    'name': {'type': 'string', 'description': '리소스 이름'},
                    'namespace': {'type': 'string', 'description': '네임스페이스 (클러스터 범위면 생략)'},
                    'output': {'type': 'string', 'enum': ['describe', 'yaml', 'events'],
                               'description': '반환 형식 (기본 describe)'},
                },
                'required': ['kind', 'name'],
            },
        ),
        types.Tool(
            name='polaris_get_logs',
            description='지정 파드의 로그(tail)를 반환한다.',
            inputSchema={
                'type': 'object',
                'properties': {
                    'cluster': _cluster_prop,
                    'namespace': {'type': 'string', 'description': '파드 네임스페이스'},
                    'pod': {'type': 'string', 'description': '파드 이름'},
                    'container': {'type': 'string', 'description': '컨테이너 (여러 개일 때, 생략 가능)'},
                    'tail': {'type': 'integer', 'description': '마지막 N줄 (기본 200, 최대 5000)'},
                },
                'required': ['namespace', 'pod'],
            },
        ),
        types.Tool(
            name='polaris_get_events',
            description='클러스터 이벤트를 반환한다(최근순).',
            inputSchema={
                'type': 'object',
                'properties': {
                    'cluster': _cluster_prop,
                    'namespace': {'type': 'string', 'description': '네임스페이스 (비우면 전체)'},
                    'limit': {'type': 'integer', 'description': '최대 건수 (기본 200, 최대 1000)'},
                    'types': {'type': 'array', 'items': {'type': 'string'},
                              'description': '필터 (예: ["Warning"]). 생략 시 전부'},
                },
                'required': [],
            },
        ),
    ]


def _harden_sdk():
    """한 요청에 두 번 응답하려다 **서버 전체가 죽는** 것을 막는다(v1.5.52, 사용자 신고).

    Claude Desktop 은 툴 호출이 오래 걸리면(약 4분) 「취소」 알림을 보내고, SDK 는 그 요청에 오류로 대신 답한다.
    그런데 툴은 끊을 수 없는 스레드에서 끝까지 돌고, 끝나면 SDK 가 같은 요청에 다시 답하려다
    `AssertionError: Request already responded to` 를 내고 TaskGroup 째 무너졌다 — 그 뒤 모든 호출이 응답 없음.
    `_call_tool` 이 취소를 제대로 넘기도록 고쳤고(아래 checkpoint), 이것은 그래도 두 번째 응답이 오면 버리는 안전망이다.
    """
    from mcp.shared import session as _S
    orig = _S.RequestResponder.respond
    if getattr(orig, '_polaris_guard', False):
        return

    async def respond(self, response):
        if getattr(self, '_completed', False):
            _audit({'ts': datetime.now(timezone.utc).isoformat(), 'event': 'mcp_duplicate_response_dropped',
                    'request_id': str(getattr(self, 'request_id', ''))})
            return
        return await orig(self, response)

    respond._polaris_guard = True
    _S.RequestResponder.respond = respond


def build_server():
    """MCP 서버 객체(툴 목록 · 호출) — run() 과 테스트가 함께 쓴다."""
    import anyio
    from mcp.server import Server
    import mcp.types as types

    _harden_sdk()
    server = Server(SERVER_NAME)

    @server.list_tools()
    async def _list_tools():
        return _tool_defs()

    @server.call_tool()
    async def _call_tool(name, arguments):
        arguments = arguments or {}
        started = time.monotonic()
        rec = {'ts': datetime.now(timezone.utc).isoformat(),
               'id': secrets.token_hex(4),      # 상관관계 id
               'tool': name, 'args': _redact(arguments)}
        fn = _TOOLS.get(name)
        if fn is None:
            rec.update(status='error', error='unknown tool',
                       ms=round((time.monotonic() - started) * 1000))
            _audit(rec)
            return [types.TextContent(type='text', text=json.dumps(
                {'ok': False, 'error': f'알 수 없는 툴: {name}'}, ensure_ascii=False))]
        try:
            result = await anyio.to_thread.run_sync(fn, arguments)
            rec['status'] = 'ok' if result.get('ok') else 'fail'
            if not result.get('ok'):
                rec['error'] = result.get('error')
        except Exception as e:
            result = {'ok': False, 'error': f'{type(e).__name__}: {e}'}
            rec['status'] = 'error'
            rec['error'] = str(e)
        rec['ms'] = round((time.monotonic() - started) * 1000)
        if _token_meta:                      # 어느 토큰이 호출했는지 (비밀값 아님)
            rec['token'] = _token_meta.get('id')
            rec['scope'] = _token_meta.get('scope')
        for k in _AUDIT_SUMMARY_KEYS:
            if isinstance(result, dict) and k in result:
                rec[k] = result[k]
        _audit(rec)
        # 툴 스레드는 끊을 수 없어 그동안 클라이언트가 취소했어도 여기까지 정상으로 온다 — 한 번 양보해서
        # 취소됐으면 취소로 끝낸다. 그래야 SDK 가 「이미 오류로 답한 요청」 으로 보고 두 번째 응답을 하지 않는다.
        await anyio.lowlevel.checkpoint()
        return [types.TextContent(type='text',
                                  text=json.dumps(result, ensure_ascii=False))]

    return server


def run() -> int:
    """--mcp 진입점. GUI 없이 stdio MCP 서버를 실행한다."""
    import sys
    try:
        import anyio
        from mcp.server.stdio import stdio_server
        server = build_server()
    except ImportError as e:
        print(f'[ERROR] MCP 서버 실행에 필요한 패키지가 없습니다: {e}\n'
              f'  pip install mcp', file=sys.stderr)
        return 1

    async def _serve():
        _audit({'ts': datetime.now(timezone.utc).isoformat(),
                'event': 'mcp_server_start', 'server': SERVER_NAME})
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream,
                             server.create_initialization_options())

    anyio.run(_serve)
    return 0
