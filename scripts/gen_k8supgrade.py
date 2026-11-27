# -*- coding: utf-8 -*-
"""쿠버네티스 업그레이드 사전 점검 데이터 생성기 (v1.5.24) — 공식 출처에서 사실만 뽑는다.

출처
  · kubernetes/website  — 기능 게이트(content/en/docs/reference/command-line-tools-reference/feature-gates/*.md,
                          stages · locked · removed), 사라지는 API 안내(using-api/deprecation-guide.md),
                          PersistentVolume 종류(concepts/storage/persistent-volumes.md 의 「not available starting」 · 「migration on by default」)
  · kubernetes/kubernetes — CHANGELOG/CHANGELOG-1.NN.md 의 v1.NN.0 절: Urgent Upgrade Notes · Deprecation · ACTION REQUIRED 항목,
                          거기서 「flag 제거」 문장을 골라 (컴포넌트, 플래그) 표로

쓰는 법
  python scripts/gen_k8supgrade.py [--web <website 저장소 폴더>] [--out src/_k8s_upgrade_data.py]
  --web 를 안 주면 임시 폴더에 sparse clone 한다(git 필요).
결과는 src/_k8s_upgrade_data.py 의 DATA = {...} — 판정 엔진(src/upgradecheck.py)이 읽는다. 사람이 고치지 않는다(다시 생성).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

MIN_MINOR = 24
COMPONENTS = ('kube-apiserver', 'kubelet', 'kube-controller-manager', 'kube-scheduler', 'kube-proxy', 'kubeadm', 'kubectl')
CHANGELOG = 'https://raw.githubusercontent.com/kubernetes/kubernetes/master/CHANGELOG/CHANGELOG-1.{n}.md'
GV = r'[a-z0-9.\-]+/v\d\w*'


def get(url: str) -> str:
    import http.client
    import time
    req = urllib.request.Request(url, headers={'User-Agent': 'polaris-datagen'})
    for i in range(3):                               # 큰 응답(RKE2 릴리스 목록 ~1MB)이 중간에 끊기는 일이 있다
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except (http.client.IncompleteRead, ConnectionError, TimeoutError):
            if i == 2:
                raise
            time.sleep(3)


def sparse_clone(dest: str) -> str:
    subprocess.run(['git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse',
                    'https://github.com/kubernetes/website', dest], check=True)
    subprocess.run(['git', '-C', dest, 'sparse-checkout', 'set',
                    'content/en/docs/reference/command-line-tools-reference/feature-gates',
                    'content/en/docs/reference/using-api', 'content/en/docs/concepts/storage'], check=True)
    return dest


# ── 기능 게이트 ──
def _minor(v) -> int | None:
    m = re.match(r'"?1\.(\d+)', str(v or '').strip())
    return int(m.group(1)) if m else None


def feature_gates(web: Path) -> dict:
    out = {}
    for f in sorted((web / 'content/en/docs/reference/command-line-tools-reference/feature-gates').glob('*.md')):
        txt = f.read_text(encoding='utf-8')
        m = re.match(r'^---\n(.*?)\n---', txt, re.S)
        if not m:
            continue
        fm = m.group(1)
        title = re.search(r'^title:\s*(\S+)', fm, re.M)
        if not title or not re.search(r'content_type:\s*feature_gate', fm):
            continue
        stages = []
        for blk in re.split(r'\n\s*-\s*stage:', '\n' + fm.split('stages:', 1)[-1])[1:]:
            st = blk.split('\n', 1)[0].strip()

            def g(k):
                mm = re.search(rf'^\s*{k}:\s*(.+?)\s*$', blk, re.M)
                return mm.group(1) if mm else ''
            stages.append({'stage': st, 'default': g('defaultValue').strip('"').lower() == 'true',
                           'from': _minor(g('fromVersion')), 'to': _minor(g('toVersion')),
                           'locked': g('locked').strip('"').lower() == 'true'})
        removed = bool(re.search(r'^removed:\s*true', fm, re.M))
        last_to = max((s['to'] for s in stages if s['to'] is not None), default=None)
        out[title.group(1)] = {'stages': stages, 'removed_in': (last_to + 1) if removed and last_to else None}
    return out


# ── 사라지는 API(공식 안내) ──
def removed_apis(web: Path) -> list:
    """「The **g/v** API version(s) of Kind, Kind is/are no longer served as of v1.NN」 · 「Kind in the **g/v** API version is …」."""
    txt = (web / 'content/en/docs/reference/using-api/deprecation-guide.md').read_text(encoding='utf-8')
    out = []
    for sub in re.split(r'\n#{3,4} ', txt):
        para = re.sub(r'\s+', ' ', sub)
        repl = re.search(r'Migrate manifests and API clients to use the \*\*(' + GV + r')\*\* API version', para)
        found = []
        for m in re.finditer(r'The ((?:\*\*' + GV + r'\*\*(?:,? and |, )?)+) API versions? of (.+?) (?:is|are) no longer served as of v1\.(\d+)', para):
            gvs = re.findall(r'\*\*([^*]+)\*\*', m.group(1))
            kinds = [k.strip() for k in re.split(r',\s*(?:and\s+)?|\s+and\s+', m.group(2)) if re.fullmatch(r'[A-Z]\w+', k.strip())]
            found.append((int(m.group(3)), gvs, kinds))
        for m in re.finditer(r'([A-Z]\w+) in the \*\*(' + GV + r')\*\* API version is no longer served as of v1\.(\d+)', para):
            found.append((int(m.group(3)), [m.group(2)], [m.group(1)]))
        for minor, gvs, kinds in found:
            for gv in gvs:
                for k in kinds:
                    row = [minor, gv, k, repl.group(1) if repl else '']
                    if row not in out:
                        out.append(row)
    return sorted(out)


# ── PersistentVolume 종류 ──
def volume_types(web: Path) -> dict:
    txt = (web / 'content/en/docs/concepts/storage/persistent-volumes.md').read_text(encoding='utf-8')
    out = {}
    for m in re.finditer(r'^\*\s*(?:\[`([A-Za-z]+)`\]\([^)]*\)|`([A-Za-z]+)`)[^\n]*\n?(?:\s+[^\n*][^\n]*\n)*?\s*\(\*\*(not available|migration on by default)\*\* starting v1\.(\d+)\)',
                         txt, re.M):
        name = m.group(1) or m.group(2)
        out[name] = {'state': 'removed' if m.group(3) == 'not available' else 'migrated', 'since': int(m.group(4))}
    return out


# ── CHANGELOG ──
def _clean(s: str) -> str:
    s = re.sub(r'\(\[#\d+\]\([^)]*\)(?:, \[@[\w-]+\]\([^)]*\))*\)', '', s)     # (PR, 작성자) 꼬리
    s = re.sub(r'\[SIG [^\]]*\]', '', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _bullets(block: str) -> list:
    """맨 위 단계 「- 」 만 항목 — 들여 쓴 하위 목록은 앞 항목에 붙인다."""
    items, cur = [], None
    for ln in block.splitlines():
        if re.match(r'^\s{0,1}-\s', ln):
            if cur:
                items.append(cur)
            cur = ln.split('-', 1)[1]
        elif cur is not None and ln.strip() and not ln.startswith('#'):
            cur += ' ' + ln.strip()
        elif ln.startswith('#') and cur:
            items.append(cur)
            cur = None
    if cur:
        items.append(cur)
    return items


def changelog(n: int) -> dict | None:
    try:
        txt = get(CHANGELOG.format(n=n))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    i = txt.find(f'\n# v1.{n}.0\n')
    if i < 0:
        return {'released': False, 'urgent': [], 'deprecations': [], 'action': [], 'removed_flags': []}
    nxt = txt.find('\n# v1.', i + 10)
    sec = txt[i: nxt if nxt > 0 else len(txt)]

    def part(title):
        a = sec.find(title)
        if a < 0:
            return ''
        b = sec.find('\n## ', a + len(title))
        c = sec.find('\n### ', a + len(title)) if title.startswith('### ') else -1
        ends = [x for x in (b, c) if x > 0]
        return sec[a: min(ends) if ends else len(sec)]

    def prs(s):
        return sorted(set(int(x) for x in re.findall(r'kubernetes/pull/(\d+)', s)))[:4]

    urgent = [{'text': _clean(b), 'prs': prs(b)} for b in _bullets(part('## Urgent Upgrade Notes').split('\n', 3)[-1])]
    deprec = [{'text': _clean(b), 'prs': prs(b)} for b in _bullets(part('### Deprecation'))]
    action = []
    seen = {u['text'] for u in urgent + deprec}
    for b in _bullets(sec):
        if 'ACTION REQUIRED' in b and _clean(b) not in seen:
            action.append({'text': _clean(b), 'prs': prs(b)})
            seen.add(_clean(b))
    flags = []
    for item in urgent + deprec + action + [{'text': _clean(b), 'prs': prs(b)} for b in _bullets(sec)]:
        t = item['text']
        if not re.search(r'\b[Rr]emov', t):
            continue
        # 「X 를 제거했다」 문장만 — 「곧 제거 예정(will be removed)」 은 뺀다
        if re.search(r'will be removed|to be removed|scheduled for removal|planned for removal', t) \
                and not re.search(r'\b[Rr]emoved the\b|\bhas been removed\b|\bwere removed\b|\bwas removed\b', t):
            continue
        # 제거 동사가 그 플래그를 바로 가리킬 때만 — 「…문서에서 잘못된 문장을 removing」(1.37 kube-proxy) 같은 오탐을 막는다
        fl = []
        if re.search(r'no longer (?:accepted|supported|recognized)|will fail to start', t):
            # 「…flags are no longer accepted and the kubelet will fail to start if any are set (only `--x` is kept): `--a`, `--b` …」(1.37)
            fl += re.findall(r'`(--[a-z0-9][a-z0-9-]+)`', re.sub(r'\(only[^)]*\)', '', t))
        # 문장 단위: 「Removed/Removes the … `--x`」 로 시작하는 변경 문장 · 「`--x` … has been removed」 만.
        # 「removing the unnecessary `--node-ip` from the kubelet arguments」(1.26 — 사람이 할 일) 같은 문장은 뺀다
        for sent in re.split(r'(?<=[.;])\s+', t):
            starts = re.match(r'\s*(?:ACTION REQUIRED:\s*)?(?:[\w-]+:\s*)?(?:\d+\.\s*)?[Rr]emov(?:ed|es|e)\b', sent)
            passive = re.search(r'\b(?:has been|have been|was|were|is now|are now)\s+removed', sent)
            if starts or passive:
                fl += [f for f in re.findall(r'`(--[a-z0-9][a-z0-9-]+)`', sent) if f not in fl]
        # 경로 안 글자(/var/lib/kubelet/…)는 컴포넌트 이름이 아니다 — 1.34 의 kubeadm 문장이 kubelet 플래그로 잡혔다
        comps = [c for c in COMPONENTS if re.search(r'(?<![\w/-])' + re.escape(c) + r'(?![\w/-])', t)]
        if re.match(r'(ACTION REQUIRED:\s*)?kubeadm\b', t, re.I) or 'kubeadm-flags.env' in t:
            comps = ['kubeadm']                      # kubeadm 이 하는 일(파일에서 플래그를 빼 줌)이지 그 컴포넌트에서 없어진 것이 아니다
        for f in fl:
            for c in (comps or ['?']):
                flags.append({'component': c, 'flag': f, 'prs': item['prs']})
    uniq = {(f['component'], f['flag']): f for f in flags}
    return {'released': True, 'urgent': urgent[:40], 'deprecations': deprec[:60], 'action': action[:40],
            'removed_flags': sorted(uniq.values(), key=lambda f: (f['component'], f['flag']))}


# ── 설치된 애플리케이션: Longhorn(공식 GitHub 릴리스 노트) ──
_RWX = re.compile(r'RWX|ReadWriteMany|share.manager|nfs', re.I)
_RECOVER = re.compile(r'recover|restart|reconnect|stuck|unavailable|faulted|hang|sleep|read-only|detach|attach|failover|drain|reboot|timeout|timed out', re.I)


def longhorn_releases() -> dict:
    """태그마다 {date, min_k8s, fast_failover, rwx_fixes:[{title, issue}]} — rc · dev 빼고. GitHub API(인증 없음, 3쪽)."""
    import json as _json
    out = {}
    for page in (1, 2, 3):
        rel = _json.loads(get(f'https://api.github.com/repos/longhorn/longhorn/releases?per_page=100&page={page}'))
        if not rel:
            break
        for r in rel:
            tag = r.get('tag_name', '')
            if not re.fullmatch(r'v\d+\.\d+\.\d+', tag) or r.get('prerelease'):
                continue
            body = r.get('body') or ''
            mk = re.search(r'running Kubernetes v1\.(\d+) or later before (?:installing|upgrading)', body)
            fixes = []
            for ln in body.splitlines():
                m = re.match(r'\s*-\s*\[(BUG|FEATURE|IMPROVEMENT)\]\s*(.+?)\s*\[(\d+)\]\(https://github\.com/longhorn/longhorn/issues/\d+\)', ln)
                if m and _RWX.search(m.group(2)) and (m.group(1) != 'BUG' or _RECOVER.search(m.group(2))):
                    if 'v2' in m.group(2).lower().split() or re.search(r'v2 (data engine|rwx)', m.group(2), re.I):
                        continue                                     # v2 데이터 엔진 전용은 뺀다(대부분 v1 엔진)
                    fixes.append({'kind': m.group(1).lower(), 'title': m.group(2)[:200], 'issue': int(m.group(3))})
            out[tag[1:]] = {'date': (r.get('published_at') or '')[:10], 'min_k8s': int(mk.group(1)) if mk else None,
                            'fast_failover': bool(re.search(r'RWX volumes? fast failover|Share manager HA', body, re.I)),
                            'rwx_fixes': fixes[:30]}
    return out


# ── RKE2 릴리스 노트 (v1.5.30) ──
# 판마다: 함께 들어 있는 구성 요소(Packaged Component Versions · Available CNIs) · 번들 차트 판(Charts Versions) ·
# 머리말의 경고 · 중요 안내(토큰 보관 같은 매번 같은 문구는 뺀다) · .0 판의 변경 항목 아래 설명.
RKE2_TAG = re.compile(r'v1\.(\d+)\.(\d+)\+rke2r(\d+)')
_RKE2_SKIP = re.compile(r'If your server \(control-plane\) nodes were not started|You may retrieve the token value|'
                        r'fixes a number of|first in the v1\.\d+ line|be sure to read the (?:Kubernetes )?\[?(?:Kubernetes Changelog|Urgent Upgrade)|'
                        r'For more details on what.s new|is a Prime-only release|will not make v1\.\d+ available via the stable|'
                        r'^This release updates? Kubernetes to|^\s*(?:,|and |to )|^\*\*Important Notes?\*\*$|^#+ |^\[!(?:WARNING|NOTE|IMPORTANT)\]$', re.I)
_RKE2_HARD = re.compile(r'breaking|must|will fail|fail to start|no safe path|lose quorum|incompatible|removed|no longer|'
                        r'instead|default for new clusters|is now the default|default[- ][\w-]+ is now|not be affected|before upgrading|prior to upgrading', re.I)


def _md_text(s: str) -> str:
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'[*`]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def _md_table(sec: str) -> dict:
    out = {}
    for m in re.finditer(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', sec, re.M):
        name = _md_text(m.group(1)).replace('(Default)', '').strip()
        if not name or name.lower() == 'component' or set(name) <= set('-: '):
            continue
        parts = [_md_text(x) for x in re.findall(r'\[([^\]]+)\]', m.group(2))] or [_md_text(m.group(2))]
        out[name] = ' + '.join(p for p in parts if p)
    return out


def _section(body: str, head: str) -> str:
    i = body.find(head)
    if i < 0:
        return ''
    rest = body[i + len(head):]
    m = re.search(r'^## ', rest, re.M)
    return rest[:m.start()] if m else rest


def parse_rke2_release(tag: str, body: str) -> dict:
    body = (body or '').replace('\r\n', '\n')
    comps = _md_table(_section(body, '## Packaged Component Versions'))
    canal = comps.get('Canal', '')
    fl = re.search(r'Flannel (v[\d.]+)', canal)
    if fl:
        comps['Flannel'] = fl.group(1)
    charts = {k: v for k, v in _md_table(_section(body, '## Charts Versions')).items() if k.startswith('rke2-')}
    head = re.sub(r'<!--.*?-->', '', body.split('## Changes since', 1)[0], flags=re.S)
    head = re.sub(r'```.*?```', '', head, flags=re.S)
    notes = []
    for para in re.split(r'\n\s*\n|\n(?=>?\s*(?:\d+\.|\*|-)\s)', head):
        lines = [re.sub(r'^\s*>\s?', '', x) for x in para.splitlines()]
        t = _md_text(' '.join(x for x in lines if not re.fullmatch(r'\s*(?:\[!\w+\]|#+.*⚠️.*|bash)?\s*', x)))
        t = re.sub(r'^(?:\d+\.|-)\s+', '', t)
        t = re.sub(r'Prime Customers: Please refer to the official product documentation for specific Prime considerations\.\s*', '', t).strip()
        if len(t) < 25 or _RKE2_SKIP.search(t) or not _RKE2_HARD.search(t):
            continue
        notes.append(t[:600])
    # 변경 항목 아래 들여쓴 설명(사람이 읽으라고 적은 것) — 주의할 말(바뀜 · 없어짐 · 기본값 …)이 있는 것만
    ch = body.split('## Changes since', 1)[-1].split('\n## ', 1)[0] if '## Changes since' in body else ''
    for m in re.finditer(r'^[ \t]{2,}[*-]\s+(.+)$', ch, re.M):
        t = _md_text(m.group(1))
        t = re.sub(r'\(#\d+\)', '', t).strip()
        if len(t) >= 25 and _RKE2_HARD.search(t) and not re.match(r'(?:Fix|Fixed|Fixes|Print|Bump|Add|Update)\b', t):
            notes.append(t[:600])                            # 고친 것 · 올린 것 알림은 할 일이 아니다
    seen, uniq = set(), []
    for n in notes:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return {'components': comps, 'charts': charts, 'notes': uniq[:12],
            'prime_only': bool(re.search(r'is a Prime-only release', body)),
            'pulled': bool(re.search(r'removed this RKE2 release from the channel server', body))}


def rke2_releases(raw: list | None = None) -> dict:
    """{'releases': {태그: {...}}, 'etcd_bridges': [{from, to, min}]} — GitHub API 는 목록을 1000건까지만 준다(1.21 무렵까지 — 충분)."""
    import json as _json
    if raw is None:
        raw = []
        for page in range(1, 11):
            try:
                rel = _json.loads(get(f'https://api.github.com/repos/rancher/rke2/releases?per_page=100&page={page}'))
            except urllib.error.HTTPError:
                break
            if not rel:
                break
            raw += rel
    out, bridges = {}, {}
    for r in raw:
        tag = r.get('tag_name', '')
        m = RKE2_TAG.fullmatch(tag)
        body = r.get('body') or ''
        # etcd 3.5 → 3.6 처럼 「먼저 이 판까지 올려야 안전」 하다는 공식 경고(어느 판 노트에 있든)
        for b in re.finditer(r'no safe path from etcd (\d+\.\d+) to (\d+\.\d+) except by upgrading to v?(\d+\.\d+\.\d+) first', body, re.I):
            bridges[(b.group(1), b.group(2))] = b.group(3)
        if not m or r.get('prerelease') or int(m.group(1)) < MIN_MINOR:
            continue
        e = parse_rke2_release(tag, body)
        e['date'] = (r.get('published_at') or '')[:10]
        out[tag] = e
    return {'releases': out, 'etcd_bridges': [{'from': k[0], 'to': k[1], 'min': v} for k, v in sorted(bridges.items())],
            'url': 'https://github.com/rancher/rke2/releases'}


# ── 애드온 공식 호환표 (v1.5.29) ──
# 버전 키는 「주.부」(cert-manager 1.18) 또는 정확한 판(ingress-nginx 1.14.2). 값 = {'k8s': [부 버전 목록] | None, 'min': 부, 'max': 부 | None}
#   k8s  : 공식 표가 적은 지원 · 시험 버전 목록(있으면 이것으로 판단)
#   min/max: 범위(cert-manager 「1.33 → 1.36」 · metrics-server 「1.31+」 · Velero 「1.18-latest」)
def _minors(s: str) -> list:
    # 「v1.34」(Argo CD) · 「1.36.5」(Velero 시험 판) 도 — \b 는 v 와 1 사이에서 안 걸린다
    return sorted({int(x) for x in re.findall(r'(?<![\d.])1\.(\d{1,2})(?!\d)', s or '')})


def _safe(get_fn, url):
    try:
        return get_fn(url)
    except Exception:
        return ''


def addon_ingress_nginx() -> dict:
    t = _safe(get, 'https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/README.md')
    out = {}
    for m in re.finditer(r'^\|[^|]*\|\s*\*\*v(\d+\.\d+\.\d+)\*\*\s*\|([^|]*)\|', t, re.M):
        ks = _minors(m.group(2))
        if ks:
            out[m.group(1)] = {'k8s': ks, 'min': min(ks), 'max': max(ks)}
    return out


def addon_cert_manager() -> dict:
    t = _safe(get, 'https://raw.githubusercontent.com/cert-manager/website/master/content/docs/releases/README.md')
    out = {}
    for m in re.finditer(r'^\|\s*\[?(\d+\.\d+)\]?[^|]*\|[^|]*\|[^|]*\|\s*(1\.\d+)\s*(?:→|->|-|to)\s*(1\.\d+)', t, re.M):
        lo, hi = int(m.group(2).split('.')[1]), int(m.group(3).split('.')[1])
        out.setdefault(m.group(1), {'k8s': list(range(lo, hi + 1)), 'min': lo, 'max': hi})
    return out


def addon_cilium() -> dict:
    out, miss = {}, 0
    for n in range(10, 40):
        t = _safe(get, f'https://raw.githubusercontent.com/cilium/cilium/v1.{n}/Documentation/network/kubernetes/compatibility.rst')
        if not t:
            miss += 1
            if miss >= 3 and n > 15:
                break
            continue
        miss = 0
        row = re.search(r'^\|\s*(1\.\d+(?:,\s*1\.\d+)*)\s*\|', t, re.M)
        ks = _minors(row.group(1)) if row else []
        if ks:
            out[f'1.{n}'] = {'k8s': ks, 'min': min(ks), 'max': max(ks)}
    return out


def addon_calico() -> dict:
    out = {}
    for n in range(20, 50):
        t = _safe(get, f'https://raw.githubusercontent.com/tigera/docs/main/calico_versioned_docs/version-3.{n}/_includes/partials/_system-requirements.mdx')
        if not t:
            continue
        sec = t.split('## Kubernetes requirements', 1)[-1].split('#### CNI', 1)[0]
        ks = sorted({int(x) for x in re.findall(r'^\*\s*1\.(\d+)\s*$', sec, re.M)})
        if ks:
            out[f'3.{n}'] = {'k8s': ks, 'min': min(ks), 'max': max(ks)}
    return out


def addon_argocd() -> dict:
    out = {}
    for major, rng in ((2, range(4, 20)), (3, range(0, 20))):
        for n in rng:
            t = _safe(get, f'https://raw.githubusercontent.com/argoproj/argo-cd/release-{major}.{n}/docs/operator-manual/tested-kubernetes-versions.md')
            for m in re.finditer(r'^\|\s*(\d+\.\d+)\s*\|([^|]+)\|', t, re.M):
                ks = _minors(m.group(2))
                if ks and m.group(1) not in out:
                    out[m.group(1)] = {'k8s': ks, 'min': min(ks), 'max': max(ks)}
    return out


def addon_istio() -> dict:
    t = _safe(get, 'https://raw.githubusercontent.com/istio/istio.io/master/data/compatibility/supportStatus.yml')
    out = {}
    for blk in re.split(r'\n-\s+version:', '\n' + t)[1:]:
        v = blk.split('\n', 1)[0].strip().strip('"')
        m = re.search(r'k8sVersions:\s*\[([^\]]*)\]', blk)
        if re.fullmatch(r'\d+\.\d+', v) and m:
            ks = _minors(m.group(1))
            if ks:
                out[v] = {'k8s': ks, 'min': min(ks), 'max': max(ks)}
    return out


def addon_metrics_server() -> dict:
    t = _safe(get, 'https://raw.githubusercontent.com/kubernetes-sigs/metrics-server/master/README.md')
    out = {}
    for m in re.finditer(r'^(\d+\.\d+)\.x\s*\|[^|]*\|\s*\*?1\.(\d+)(\+|-1\.(\d+))', t, re.M):
        out[m.group(1)] = {'k8s': None, 'min': int(m.group(2)), 'max': int(m.group(4)) if m.group(4) else None}
    return out


def addon_velero() -> dict:
    t = _safe(get, 'https://raw.githubusercontent.com/vmware-tanzu/velero/main/README.md')
    out = {}
    for m in re.finditer(r'^\|\s*(\d+\.\d+)\s*\|\s*1\.(\d+)-(latest|1\.(\d+))\s*\|([^|]*)\|', t, re.M):
        out[m.group(1)] = {'k8s': None, 'min': int(m.group(2)), 'max': int(m.group(4)) if m.group(4) else None,
                           'tested': _minors(m.group(5))}
    return out


ADDONS = {
    # 이름: (만드는 함수, 공식 출처, 이미지 정규식(판 뽑기), 키 단위 — exact | minor, CNI 인가)
    'ingress-nginx': (addon_ingress_nginx, 'https://github.com/kubernetes/ingress-nginx#supported-versions-table',
                      r'ingress-nginx[^:@]*controller[^:@]*:v?(\d+\.\d+\.\d+)', 'exact', False),
    'cert-manager': (addon_cert_manager, 'https://cert-manager.io/docs/releases/',
                     r'cert-manager-controller:v?(\d+\.\d+)', 'minor', False),
    'Cilium': (addon_cilium, 'https://docs.cilium.io/en/stable/network/kubernetes/compatibility/',
               r'cilium(?:-cilium)?:v?(\d+\.\d+)', 'minor', True),
    'Calico': (addon_calico, 'https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements',
               r'calico(?:-|/)node:v?(\d+\.\d+)', 'minor', True),
    'Argo CD': (addon_argocd, 'https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/#tested-versions',
                r'argoproj/argocd:v?(\d+\.\d+)', 'minor', False),
    'Istio': (addon_istio, 'https://istio.io/latest/docs/releases/supported-releases/',
              r'istio/pilot:v?(\d+\.\d+)', 'minor', False),
    'metrics-server': (addon_metrics_server, 'https://github.com/kubernetes-sigs/metrics-server#compatibility-matrix',
                       r'metrics-server:v?(\d+\.\d+)', 'minor', False),
    'Velero': (addon_velero, 'https://github.com/vmware-tanzu/velero#velero-compatibility-matrix',
               r'velero/velero:v?(\d+\.\d+)', 'minor', False),
}


def addons() -> dict:
    out = {}
    for name, (fn, url, img, key, cni) in ADDONS.items():
        vers = fn()
        out[name] = {'versions': vers, 'url': url, 'image': img, 'key': key, 'cni': cni}
        print(f'addon {name}: {len(vers)}', file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--web', default='')
    ap.add_argument('--out', default=str(Path(__file__).resolve().parent.parent / 'src' / '_k8s_upgrade_data.py'))
    a = ap.parse_args()
    web = a.web
    if not web:
        web = sparse_clone(os.path.join(tempfile.mkdtemp(prefix='k8sweb-'), 'web'))
    web = Path(web)
    data = {'generated': date.today().isoformat(), 'feature_gates': feature_gates(web), 'removed_apis': removed_apis(web),
            'volume_types': volume_types(web), 'releases': {}}
    n = MIN_MINOR
    while True:
        r = changelog(n)
        if r is None:
            break
        data['releases'][n] = r
        print(f'1.{n}: urgent {len(r["urgent"])} / deprecation {len(r["deprecations"])} / action {len(r["action"])} / flags {len(r["removed_flags"])}',
              file=sys.stderr)
        n += 1
    data['latest_minor'] = max((k for k, v in data['releases'].items() if v['released']), default=None)
    data['apps'] = {'longhorn': {'releases': longhorn_releases(), 'url': 'https://github.com/longhorn/longhorn/releases'}}
    print(f'longhorn: {len(data["apps"]["longhorn"]["releases"])} releases', file=sys.stderr)
    data['addons'] = addons()
    data['rke2'] = rke2_releases()
    print(f'rke2: {len(data["rke2"]["releases"])} releases / etcd bridges {data["rke2"]["etcd_bridges"]}', file=sys.stderr)
    data['url'] = {'changelog': 'https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.{n}.md',
                   'gates': 'https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/',
                   'apis': 'https://kubernetes.io/docs/reference/using-api/deprecation-guide/',
                   'volumes': 'https://kubernetes.io/docs/concepts/storage/persistent-volumes/#types-of-persistent-volumes'}
    body = ('# -*- coding: utf-8 -*-\n'
            '"""쿠버네티스 업그레이드 사전 점검 데이터 — scripts/gen_k8supgrade.py 가 공식 출처에서 만든다(손으로 고치지 않는다)."""\n'
            f'DATA = {json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)}\n')
    body = body.replace(': true', ': True').replace(': false', ': False').replace(': null', ': None')
    Path(a.out).write_bytes(body.encode('utf-8'))
    print(f'-> {a.out} / gates {len(data["feature_gates"])} / apis {len(data["removed_apis"])} / volumes {len(data["volume_types"])} / '
          f'1.{MIN_MINOR}~1.{n - 1}', file=sys.stderr)


if __name__ == '__main__':
    main()
