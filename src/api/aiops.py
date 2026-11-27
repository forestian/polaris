"""AIOps — LLM 기반 이벤트/로그 진단 (자연어 질의응답).

이벤트 탭·로그 뷰어에서 "AI 진단" 버튼으로 호출. 프론트가 현재 보고 있는
이벤트/로그를 그대로 넘기면, 여기서 **컨텍스트를 정리(trim)** 한 뒤
OpenAI 호환 LLM(예: LM Studio gemma-4-e4b)에 보내 한국어 진단을 받는다.

설계 근거(gemma-4-e4b 실측 테스트):
  - 이벤트: Warning 만, (reason,obj) 중복 제거, 최대 30개 → Normal 노이즈 제거.
  - 로그: 작으면 그대로, 크면 에러/경고 줄 + 최근 줄만 발췌(~40줄/4KB).
    19k 토큰 raw 도 답은 맞췄으나 79초 → 트림 시 동일 답을 35초로 단축.
  - 빈/메타에러("unable to retrieve container logs") 로그는 LLM 에 보내지 않음(GIGO 차단).
  - system 프롬프트에 "Ready+진행중 경고 없으면 누적 재시작만으로 단정 말 것" 가드 →
    정상/양성 클러스터 오탐(환각) 제거.

보고서(reports)의 LLM 호출(_llm_ask)을 그대로 재사용하되, system 프롬프트만
교체한다. 보고서 동작에는 영향 없음(인자는 모두 선택, 기본값=기존 동작).
"""
import json
import re
import urllib.error

from src.reports import _llm_ask, _LLM_TIMEOUT_S, llm_scrub


# ── 진단 system 프롬프트 (실측으로 검증된 형식 + 오탐 가드) ─────────────────────
_AIOPS_SYSTEM = (
    "당신은 Kubernetes 운영 전문가입니다. 아래에 주어진 정보(이벤트/로그)만 근거로 "
    "한국어로 간결하게 진단하세요.\n"
    "형식:\n1) 핵심 문제 (한 줄)\n2) 원인\n3) 조치 (필요하면 kubectl 명령 포함)\n"
    "규칙:\n"
    "- 주어진 정보에 근거가 없으면 추측하지 말고 '정보 부족' 이라고 쓰세요.\n"
    "- 문제가 없어 보이면 다른 설명 없이 '✅ 특이사항 없음' 만 답하세요.\n"
    "- 파드가 현재 Ready 이고 진행 중인 Warning 이벤트가 없다면, 과거 누적 재시작 "
    "횟수(restarts)만으로 문제라고 단정하지 마세요. 노드 재부팅/절전 복귀로도 늘어납니다.\n"
    "- 각 문제는 핵심만 2~4줄로, 같은 말 반복·긴 서론/결론 요약은 생략하세요. 문제가 여러 개면 "
    "가장 심각한 것부터 최대 6개까지만 다루고 나머지는 '그 외 N건'으로 한 줄 요약하세요."
)

# 후속 질의응답(멀티턴) system — 진단 1)2)3) 고정형식 대신 질문에 자유롭게 답하게 완화.
_AIOPS_SYSTEM_CHAT = (
    "당신은 Kubernetes 운영 전문가입니다. 대화에 주어진 클러스터 정보(이벤트·로그·상태)를 근거로 "
    "한국어로 정확하고 간결하게 답하세요. 근거가 없으면 추측하지 말고 '주어진 정보로는 알 수 없다'고 "
    "하세요. 핵심 위주로 짧게, 필요하면 kubectl 명령을 포함하세요."
)


def _aiops_post_chat(url, model, messages, temperature=0.2, max_tokens=2600, timeout=None):
    """OpenAI 호환 /v1/chat/completions 에 messages 배열을 그대로 보내 답을 받는다(멀티턴 대화).

    timeout 기본값은 _llm_ask 와 같은 _LLM_TIMEOUT_S — 첫 진단(_llm_ask)은 되는데
    후속 대화만 끊기거나 그 반대가 되지 않도록 한쪽에서만 관리한다.
    """
    if timeout is None:
        timeout = _LLM_TIMEOUT_S
    import urllib.request
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme not in ('http', 'https') or not p.netloc:
        raise ValueError(f'허용되지 않는 LLM URL입니다: {url!r} (http/https 만 허용)')
    messages = [{**m, 'content': llm_scrub(m.get('content'))} if isinstance(m, dict) else m
                for m in (messages or [])]
    from src.reports import _llm_complete
    return _llm_complete(url, {'model': model, 'messages': messages, 'temperature': temperature,
                               'max_tokens': max_tokens}, timeout)

_AIOPS_ERR_RE = re.compile(
    r'(error|err\b|fail|fatal|panic|exception|traceback|refused|timeout|timed out|'
    r'denied|cannot|unable|crash|oom|killed|\bwarn)', re.I)


def _aiops_looks_useless_log(text):
    """로그가 비었거나 'unable to retrieve' 류 메타-에러면 LLM 에 보내지 않는다."""
    t = (text or '').strip()
    if len(t) < 5:
        return True
    if 'unable to retrieve container logs' in t.lower():
        return True
    return False


def _aiops_trim_log(text, max_lines=40, max_chars=4000):
    """큰 로그를 에러/경고 줄 + 최근 줄 위주로 발췌. (작으면 원본 그대로)"""
    text = text or ''
    lines = text.splitlines()
    if len(lines) <= max_lines and len(text) <= max_chars:
        return text, {'total_lines': len(lines), 'sent_lines': len(lines), 'trimmed': False}
    hit = [i for i, ln in enumerate(lines) if _AIOPS_ERR_RE.search(ln)]
    keep = set(hit) | set(range(max(0, len(lines) - 10), len(lines)))  # 에러줄 + 마지막 10줄
    sel = sorted(keep)[-max_lines:]
    body = '\n'.join(lines[i] for i in sel)[:max_chars]
    note = f'(원본 {len(lines)}줄 중 에러/경고 {len(hit)}줄 + 최근 줄 발췌)\n'
    return note + body, {'total_lines': len(lines), 'sent_lines': len(sel),
                         'error_lines': len(hit), 'trimmed': True}


def _aiops_trim_events(events, cap=30):
    """이벤트를 Warning 만, (reason,obj) 중복 제거 후 컴팩트 문자열로."""
    events = events or []
    warn = [e for e in events if (e.get('type') == 'Warning')]
    seen, out = set(), []
    for e in warn:
        key = (e.get('reason'), e.get('obj'))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    out = out[:cap]
    lines = []
    for e in out:
        cnt = e.get('count') or 1
        msg = re.sub(r'\s+', ' ', str(e.get('message') or '')).strip()
        ns = e.get('namespace')
        lines.append(f"[Warning] {e.get('reason')} {e.get('obj')}"
                     + (f" @{ns}" if ns else '')
                     + f" (x{cnt}): {msg}")
    return '\n'.join(lines), {'warning_events': len(warn), 'sent': len(out),
                              'normal_skipped': len(events) - len(warn)}


class AIOpsMixin:
    """LLM 기반 진단 API (window.pywebview.api.ai_diagnose)."""

    # ── 컨텍스트 보강 헬퍼 — 모두 try/except 로 감싸 실패해도 진단은 계속된다 ─────────
    def _aiops_cluster_brief(self):
        """배포판(k3s/RKE2/…)·K8s 버전·노드·런타임·CNI·OS 한 줄. 300초 인스턴스 캐시.

        작은 LLM 일수록 '여기가 k3s냐 RKE2냐'를 알면 조치가 정확해진다(예: k3s=traefik/flannel
        내장, RKE2=nginx/canal·cilium). 클러스터마다 거의 고정값이라 캐시한다.
        """
        try:
            k = self.k8s
            if not getattr(k, 'connected', False):
                return ''
        except Exception:
            return ''
        import time as _t
        ctxkey = getattr(k, 'kubeconfig', '') or ''
        cache = getattr(self, '_aiops_cc', None)
        if cache and cache[0] == ctxkey and (_t.time() - cache[1]) < 300:
            return cache[2]
        brief = ''
        try:
            distro, kver, runtime, osimg, readys = 'vanilla/기타', '', '', '', []
            try:
                for n in k.core.list_node().items:
                    readys.append(any(c.type == 'Ready' and c.status == 'True'
                                      for c in (n.status.conditions or [])))
                    ni = n.status.node_info
                    if ni and not kver:
                        kver, runtime, osimg = (ni.kubelet_version or '',
                                                ni.container_runtime_version or '',
                                                ni.os_image or '')
                low = kver.lower()
                for key, name in (('+k3s', 'k3s'), ('+rke2', 'RKE2'), ('gke', 'GKE'),
                                  ('eks', 'EKS'), ('aks', 'AKS')):
                    if key in low:
                        distro = name
                        break
            except Exception:
                pass
            cni = ''
            try:
                names = ' '.join(d.metadata.name.lower()
                                 for d in k.apps.list_namespaced_daemon_set('kube-system').items)
                for key, name in (('cilium', 'Cilium'), ('calico', 'Calico'), ('canal', 'Canal'),
                                  ('flannel', 'Flannel'), ('kube-router', 'kube-router'),
                                  ('weave', 'Weave'), ('antrea', 'Antrea')):
                    if key in names:
                        cni = name
                        break
            except Exception:
                pass
            if not cni and distro == 'k3s':
                cni = 'Flannel(k3s 내장)'
            parts = [f'배포판={distro}']
            if kver:    parts.append(f'Kubernetes {kver}')
            if readys:  parts.append(f'노드 {len(readys)}개(Ready {sum(readys)})')
            if runtime: parts.append(f'런타임 {runtime}')
            if cni:     parts.append(f'CNI={cni}')
            if osimg:   parts.append(f'OS={osimg}')
            brief = '[클러스터] ' + ' · '.join(parts)
        except Exception:
            brief = ''
        try:
            self._aiops_cc = (ctxkey, _t.time(), brief)
        except Exception:
            pass
        return brief

    def _aiops_pod_status_lines(self, ns, cap=20, only_pod=None):
        """비정상 파드 상태 요약 — Ready=false / waiting 사유 / 비정상 종료(OOMKilled·exit≠0) / 재시작.

        이벤트만으로는 안 드러나는 'OOMKilled exit=137' 같은 결정적 신호가 여기 담긴다(실측).
        """
        out = []
        try:
            k = self.k8s
            if not getattr(k, 'connected', False):
                return out
            items = (k.core.list_namespaced_pod(ns).items if ns
                     else k.core.list_pod_for_all_namespaces().items)
        except Exception:
            return out
        for p in items:
            try:
                name = p.metadata.name
                if only_pod and name != only_pod:
                    continue
                css = p.status.container_statuses or []
                reasons, restarts, allready = [], 0, True
                for cs in css:
                    restarts += cs.restart_count or 0
                    if not cs.ready:
                        allready = False
                    st = cs.state
                    if st and st.waiting and st.waiting.reason not in (
                            None, 'ContainerCreating', 'PodInitializing'):
                        reasons.append(f'{cs.name}: {st.waiting.reason}')
                    if st and st.terminated and (st.terminated.exit_code or 0) != 0:
                        reasons.append(f'{cs.name}: {st.terminated.reason or "Error"} '
                                       f'exit={st.terminated.exit_code}')
                    ls = cs.last_state
                    if ls and ls.terminated and ls.terminated.reason and \
                            ls.terminated.reason != 'Completed':
                        reasons.append(f'{cs.name}: 직전 {ls.terminated.reason} '
                                       f'exit={ls.terminated.exit_code}')
                phase = p.status.phase or '?'
                if not (reasons or phase not in ('Running', 'Succeeded')
                        or (not allready and phase != 'Succeeded')):
                    continue
                nm = name if (ns or only_pod) else f'{p.metadata.namespace}/{name}'
                line = f'- {nm}: phase={phase} Ready={allready} restarts={restarts}'
                if reasons:
                    line += ' | ' + '; '.join(dict.fromkeys(reasons))
                out.append(line)
                if len(out) >= cap:
                    break
            except Exception:
                continue
        return out

    def _aiops_pod_events(self, ns, pod, cap=8):
        """해당 파드의 최근 Warning 이벤트(이유별 1개)."""
        out = []
        try:
            k = self.k8s
            if not getattr(k, 'connected', False) or not ns or not pod:
                return out
            evs = k.core.list_namespaced_event(
                ns, field_selector=f'involvedObject.name={pod}').items
            warn = sorted((e for e in evs if e.type == 'Warning'),
                          key=lambda e: e.last_timestamp or '', reverse=True)
            seen = set()
            for e in warn:
                if e.reason in seen:
                    continue
                seen.add(e.reason)
                msg = ' '.join((e.message or '').split())
                out.append(f'[Warning] {e.reason} (x{e.count or 1}): {msg}')
                if len(out) >= cap:
                    break
        except Exception:
            return out
        return out

    def ai_diagnose(self, source, payload, llm_url, llm_model='local-model', question=''):
        """이벤트/로그를 LLM 에 보내 진단 결과(한국어)를 받는다.

        source  : 'events' | 'logs'
        payload : events → {namespace, events:[{type,reason,obj,namespace,message,count}]}
                  logs   → {namespace, pod, container, text}
        반환    : {ok, answer, meta} | {ok:False, error}
        """
        try:
            payload = payload or {}
            llm_url = (llm_url or '').strip()
            llm_model = (llm_model or 'local-model').strip() or 'local-model'
            question = (question or '').strip()
            if not llm_url:
                return {'ok': False, 'error': 'LLM API URL이 설정되지 않았습니다. (예: http://localhost:1234)'}

            if source == 'events':
                ctx, meta = _aiops_trim_events(payload.get('events'))
                ns = payload.get('namespace') or ''
                pod_lines = self._aiops_pod_status_lines(ns)   # 컨텍스트 보강: 비정상 파드 상태
                if not ctx.strip() and not pod_lines:
                    return {'ok': True, 'short_circuit': True, 'meta': meta,
                            'prompt': f"네임스페이스 {ns or '전체'} 진단 — 분석 결과 특이사항 없음.",
                            'answer': '✅ 특이사항 없음 — Warning 이벤트도, 비정상 파드도 없습니다.'}
                scope = f'네임스페이스 {ns}' if ns else '전체 네임스페이스'
                blocks = []
                brief = self._aiops_cluster_brief()
                if brief:
                    blocks.append(brief)
                if pod_lines:
                    blocks.append('[비정상 파드 상태]\n' + '\n'.join(pod_lines))
                blocks.append('[Warning 이벤트]\n' + (ctx if ctx.strip() else '(없음)'))
                user = f'{scope} 진단 요청. 무슨 문제가 있고 어떻게 조치하나요?\n\n' + '\n\n'.join(blocks)
                meta = {**meta, 'abnormal_pods': len(pod_lines)}

            elif source == 'logs':
                text = payload.get('text') or ''
                if _aiops_looks_useless_log(text):
                    return {'ok': False,
                            'error': '로그 내용이 비어 있거나 분석할 수 없습니다. 로그를 먼저 불러온 뒤 시도하세요.'}
                body, meta = _aiops_trim_log(text)
                pod = payload.get('pod') or ''
                ns = payload.get('namespace') or ''
                ctr = payload.get('container') or ''
                hdr = (f'파드 {ns}/{pod}' if pod else '로그') + (f' 컨테이너 {ctr}' if ctr else '')
                blocks = []
                brief = self._aiops_cluster_brief()
                if brief:
                    blocks.append(brief)
                pod_lines = self._aiops_pod_status_lines(ns, only_pod=pod) if (ns and pod) else []
                if pod_lines:
                    blocks.append('[대상 파드 상태]\n' + '\n'.join(pod_lines))
                pev = self._aiops_pod_events(ns, pod)
                if pev:
                    blocks.append('[해당 파드 최근 이벤트]\n' + '\n'.join(pev))
                blocks.append(f'[로그] {hdr}\n```\n{body}\n```')
                user = '아래 정보를 근거로 로그의 오류 원인과 조치를 알려주세요.\n\n' + '\n\n'.join(blocks)
                meta = {**meta, 'pod_events': len(pev), 'pod_status': len(pod_lines)}

            else:
                return {'ok': False, 'error': f'알 수 없는 진단 소스: {source!r}'}

            if question:
                user += f'\n\n[추가 질문] {question}'

            # max_tokens=2600: 이 모델은 LM Studio 에서 답 외에 '사고(reasoning)' 토큰을
            # ~800~1000 개 생성한다(우리가 화면에 안 쓰지만 예산은 소모). 1600 이면 사고가
            # 예산을 까먹어 답이 'finish=length' 로 잘렸음 → 넉넉히 올려 항상 완결되게 한다.
            # (시스템 프롬프트의 간결 규칙으로 답 자체도 짧아져 보통 1500 안에서 끝난다)
            answer = _llm_ask(llm_url, llm_model, user,
                              system=_AIOPS_SYSTEM, temperature=0.2, max_tokens=2600)
            # prompt 는 프론트가 후속 질문(ai_chat) 의 대화 history 첫 user 메시지로 재사용한다.
            return {'ok': True, 'answer': answer, 'meta': meta, 'prompt': user}

        except urllib.error.URLError as e:
            return {'ok': False,
                    'error': f'LLM 서버({llm_url})에 연결할 수 없습니다: {getattr(e, "reason", e)}'}
        except (ValueError, RuntimeError) as e:   # RuntimeError: 빈 답 이유(v1.5.62)
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    def ai_chat(self, messages, llm_url, llm_model='local-model', system=None):
        """멀티턴 자유 대화. messages=[{role,content},...].

        - AI 진단 후속 질문: system 생략 → K8s 운영 전문가(_AIOPS_SYSTEM_CHAT).
        - 자유 AI 탭: system 으로 일반 어시스턴트 프롬프트를 넘김.
        진단 첫 턴(ai_diagnose)이 돌려준 prompt/answer 를 history 로 쌓아 보내면
        그 컨텍스트 위에서 이어 답한다(private LLM · OpenAI 호환).
        """
        try:
            llm_url = (llm_url or '').strip()
            llm_model = (llm_model or 'local-model').strip() or 'local-model'
            if not llm_url:
                return {'ok': False, 'error': 'LLM API URL이 설정되지 않았습니다.'}
            hist = [{'role': ('assistant' if m.get('role') == 'assistant' else 'user'),
                     'content': str(m.get('content') or '')}
                    for m in (messages or []) if str(m.get('content') or '').strip()]
            if not hist:
                return {'ok': False, 'error': '질문 내용이 없습니다.'}
            sys_prompt = (system or '').strip() or _AIOPS_SYSTEM_CHAT
            msgs = [{'role': 'system', 'content': sys_prompt}] + hist
            answer = _aiops_post_chat(llm_url, llm_model, msgs)
            return {'ok': True, 'answer': answer}
        except urllib.error.URLError as e:
            return {'ok': False, 'error': f'LLM 서버({llm_url})에 연결할 수 없습니다: {getattr(e, "reason", e)}'}
        except (ValueError, RuntimeError) as e:   # RuntimeError: 빈 답 이유(v1.5.62)
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    def test_llm_connection(self, llm_url, timeout=20) -> dict:
        """OpenAI 호환 LLM 서버 도달성 확인 + 모델 목록 조회 (GET /v1/models).

        로컬 모델 UX — URL 이 맞는지, 어떤 모델명을 써야 하는지 UI 가 바로 알려준다.
        크리덴셜을 다루지 않으며(로컬 추론 서버), 응답 본문은 모델 id 만 추출한다.
        반환: {ok, reachable, models:[id...], count, endpoint, warning?, error?}

        생성(_llm_ask)과 달리 여기는 **짧게 유지한다** — 도달성 판정이 목적이라 오래
        매달릴 이유가 없다. 다만 대형 모델을 VRAM 에 올리는 중이면 HTTP 응답 자체가
        수십 초 늦을 수 있어 8→20 초로 뒀다(살아 있는 서버는 1초 안에 답한다).
        """
        import urllib.request
        from urllib.parse import urlparse
        url = (llm_url or '').strip()
        if not url:
            return {'ok': False, 'error': 'LLM API URL이 설정되지 않았습니다.'}
        p = urlparse(url)
        if p.scheme not in ('http', 'https') or not p.netloc:
            return {'ok': False, 'error': 'http:// 또는 https:// 로 시작하는 URL만 사용할 수 있습니다.'}
        try:
            timeout = max(1.0, min(float(timeout or 20), 60.0))
        except Exception:
            timeout = 20.0
        endpoint = url.rstrip('/') + '/v1/models'
        try:
            req = urllib.request.Request(endpoint, method='GET',
                                         headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            models = []
            items = data.get('data') if isinstance(data, dict) else None
            if isinstance(items, list):
                for m in items:
                    mid = m.get('id') if isinstance(m, dict) else None
                    if mid:
                        models.append(str(mid))
            return {'ok': True, 'reachable': True, 'models': models,
                    'count': len(models), 'endpoint': endpoint}
        except urllib.error.HTTPError as e:
            # 서버는 응답하지만 /v1/models 미지원(일부 게이트웨이) — 도달은 됨
            return {'ok': True, 'reachable': True, 'models': [], 'count': 0,
                    'endpoint': endpoint,
                    'warning': f'/v1/models 가 HTTP {e.code} 응답 — 서버는 살아있으나 '
                               f'모델 목록을 못 받았습니다. 모델명을 직접 입력하세요.'}
        except urllib.error.URLError as e:
            return {'ok': False, 'reachable': False,
                    'error': f'{url} 에 연결할 수 없습니다: {getattr(e, "reason", e)}'}
        except Exception as e:
            return {'ok': False, 'reachable': False, 'error': f'{type(e).__name__}: {e}'}
