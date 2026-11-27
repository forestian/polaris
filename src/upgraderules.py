# -*- coding: utf-8 -*-
"""K8s 업그레이드 사전 점검 — 공식 데이터 표로 하는 판정 · 설치된 애플리케이션 점검 (v1.5.24).

표: src/_k8s_upgrade_data.py (scripts/gen_k8supgrade.py 가 공식 출처에서 만든다 — 사람이 고치지 않는다)
  · 기능 게이트(kubernetes/website): 언제 없어지나(removed_in) · 단계별 기본값 · 잠김(locked)
  · 버전별 공식 CHANGELOG 의 Urgent Upgrade Notes · Deprecation · ACTION REQUIRED · 없어진 플래그
  · PersistentVolume 종류: 없어진 종류(not available) · CSI 로 넘어간 종류(migration)
  · Longhorn 릴리스 노트: 버전별 최소 쿠버네티스 · RWX fast failover · RWX 관련 수정

판정은 「표의 사실 × 이 클러스터에서 본 것」 만 — 클러스터에 해당이 없으면 나오지 않는다(그래서 클러스터마다 결과가 다르다).
설치된 애플리케이션 점검은 실제 장애(Longhorn RWX share-manager 재생성 뒤 NFS 연결 미복구 → kubelet 멈춤 → 클러스터 안
Harbor 중단으로 ImagePullBackOff 확산)에서 나온 구조적 위험을 찾는다. 클러스터는 바꾸지 않는다(GET 만).
"""
from __future__ import annotations

import re

try:
    from src._k8s_upgrade_data import DATA
except Exception:                                  # 표가 없는 빌드 — 기존 판정만 한다
    DATA = {}

CONTROL_PLANE = ('kube-apiserver', 'kube-controller-manager', 'kube-scheduler', 'kube-proxy')
MAX_CONFIGZ_NODES = 30
DB_IMAGE = re.compile(r'(^|/)(postgres|postgresql|mysql|mariadb|redis|valkey|mongo|mongodb|elasticsearch|opensearch|kafka|zookeeper|etcd|rabbitmq|'
                      r'harbor-db|cassandra|clickhouse|minio)([:@-]|$)', re.I)
# CSI 로 넘어간 인트리 종류 → 그 CSI 드라이버 이름(공식 CSI migration 문서)
CSI_FOR = {'awsElasticBlockStore': 'ebs.csi.aws.com', 'azureDisk': 'disk.csi.azure.com', 'azureFile': 'file.csi.azure.com',
           'cinder': 'cinder.csi.openstack.org', 'gcePersistentDisk': 'pd.csi.storage.gke.io', 'portworxVolume': 'pxd.portworx.com',
           'vsphereVolume': 'csi.vsphere.vmware.com'}


def available() -> bool:
    return bool(DATA.get('feature_gates'))


def removed_apis() -> list:
    return [tuple(r) for r in DATA.get('removed_apis') or []]


def latest_minor():
    return DATA.get('latest_minor')


# ── 수집 ────────────────────────────────────────────────────────────────────
def parse_flags(cmd: list) -> dict:
    """['kube-apiserver', '--a=b', '--c', 'd', '--e'] → {'--a': 'b', '--c': 'd', '--e': ''}."""
    out, i = {}, 0
    toks = [str(t) for t in cmd or []]
    while i < len(toks):
        t = toks[i]
        if t.startswith('--'):
            if '=' in t:
                k, v = t.split('=', 1)
                out[k] = v
            elif i + 1 < len(toks) and not toks[i + 1].startswith('-'):
                out[t] = toks[i + 1]
                i += 1
            else:
                out[t] = ''
        i += 1
    return out


def parse_gates(s: str) -> dict:
    out = {}
    for part in str(s or '').split(','):
        if '=' in part:
            k, v = part.split('=', 1)
            out[k.strip()] = v.strip().lower() == 'true'
    return out


def component_of(pod: dict) -> str:
    md = pod.get('metadata') or {}
    if md.get('namespace') != 'kube-system':
        return ''
    comp = (md.get('labels') or {}).get('component') or (md.get('labels') or {}).get('k8s-app') or ''
    for c in CONTROL_PLANE:
        if comp == c or (md.get('name') or '').startswith(c + '-') or (md.get('name') or '') == c:
            return c
    return ''


def image_host(img: str) -> str:
    first = str(img or '').split('/', 1)[0]
    if '/' in str(img or '') and ('.' in first or ':' in first or first == 'localhost'):
        return first.lower()
    return 'docker.io'


def collect_extra(api, get, items, data: dict, raw_pods: list, errors: list, progress=lambda *_: None):
    """표 판정 · 애플리케이션 점검에 쓸 것(GET 만). get/items 는 upgradecheck 의 _get/_items."""
    progress('컨트롤 플레인 설정(플래그 · 기능 게이트)')
    comps = {}
    for p in raw_pods:
        c = component_of(p)
        if not c:
            continue
        ctr = ((p.get('spec') or {}).get('containers') or [{}])[0]
        flags = parse_flags((ctr.get('command') or []) + (ctr.get('args') or []))
        node = (p.get('spec') or {}).get('nodeName', '')
        comps.setdefault(c, []).append({'node': node, 'flags': flags, 'pod': (p.get('metadata') or {}).get('name', '')})
    data['components'] = comps

    progress('kubelet 설정')
    kubelets = []
    for n in (data.get('nodes') or [])[:MAX_CONFIGZ_NODES]:
        try:
            cz = get(api, f"/api/v1/nodes/{n['name']}/proxy/configz", timeout=10)
            kc = cz.get('kubeletconfig') or {}
            kubelets.append({'node': n['name'], 'gates': {k: bool(v) for k, v in (kc.get('featureGates') or {}).items()},
                             'cgroup_driver': kc.get('cgroupDriver', ''), 'fail_cgroup_v1': kc.get('failCgroupV1')})
        except Exception as e:
            errors.append(f"kubelet 설정({n['name']}): {_err(e)}")
            if len([x for x in errors if x.startswith('kubelet 설정')]) >= 3:
                break                                 # 권한이 없으면 노드마다 같은 오류 — 세 번에서 그만
    data['kubelets'] = kubelets

    progress('kube-proxy 모드')
    mode = ''
    try:
        cm = get(api, '/api/v1/namespaces/kube-system/configmaps/kube-proxy')
        m = re.search(r'^\s*mode:\s*"?(\w*)"?', (cm.get('data') or {}).get('config.conf', ''), re.M)
        mode = (m.group(1) if m else '') or ''
    except Exception:
        pass
    for x in comps.get('kube-proxy', []):
        mode = x['flags'].get('--proxy-mode') or mode
    data['proxy_mode'] = mode

    progress('스토리지(PV · PVC · StorageClass · CSI)')
    data['pvs'] = []
    for pv in items(api, '/api/v1/persistentvolumes', errors, 'PersistentVolume'):
        sp = pv.get('spec') or {}
        kinds = [k for k in sp if k not in ('accessModes', 'capacity', 'claimRef', 'persistentVolumeReclaimPolicy', 'storageClassName',
                                            'volumeMode', 'nodeAffinity', 'mountOptions', 'volumeAttributesClassName')]
        cr = sp.get('claimRef') or {}
        data['pvs'].append({'name': (pv.get('metadata') or {}).get('name', ''), 'types': kinds,
                            'driver': (sp.get('csi') or {}).get('driver', ''), 'modes': sp.get('accessModes') or [],
                            'claim': f"{cr.get('namespace', '')}/{cr.get('name', '')}" if cr else '', 'sc': sp.get('storageClassName', '')})
    data['pvcs'] = [{'namespace': (c.get('metadata') or {}).get('namespace', ''), 'name': (c.get('metadata') or {}).get('name', ''),
                     'modes': (c.get('spec') or {}).get('accessModes') or [], 'sc': (c.get('spec') or {}).get('storageClassName') or '',
                     'volume': (c.get('spec') or {}).get('volumeName', '')}
                    for c in items(api, '/api/v1/persistentvolumeclaims', errors, 'PersistentVolumeClaim')]
    data['storageclasses'] = {(s.get('metadata') or {}).get('name', ''): s.get('provisioner', '')
                              for s in items(api, '/apis/storage.k8s.io/v1/storageclasses', errors, 'StorageClass')}
    data['csidrivers'] = [(d.get('metadata') or {}).get('name', '') for d in items(api, '/apis/storage.k8s.io/v1/csidrivers', errors, 'CSIDriver')]

    progress('애플리케이션(이미지 저장소 · 인그레스 · Longhorn)')
    pods = []
    for p in raw_pods:
        md, sp, st = p.get('metadata') or {}, p.get('spec') or {}, p.get('status') or {}
        owners = md.get('ownerReferences') or []
        ctrs = (sp.get('containers') or []) + (sp.get('initContainers') or [])
        pods.append({'namespace': md.get('namespace', ''), 'name': md.get('name', ''), 'node': sp.get('nodeName', ''),
                     'phase': st.get('phase', ''), 'owner': f"{owners[0].get('kind')}/{owners[0].get('name')}" if owners else '',
                     'labels': md.get('labels') or {},
                     'images': [c.get('image', '') for c in ctrs if c.get('image')],
                     'pull_always': any(c.get('imagePullPolicy') == 'Always' for c in ctrs),
                     'claims': [v['persistentVolumeClaim'].get('claimName', '') for v in sp.get('volumes') or [] if v.get('persistentVolumeClaim')],
                     'flex': any('flexVolume' in v for v in sp.get('volumes') or []),
                     'selinux': bool(((sp.get('securityContext') or {}).get('seLinuxOptions'))
                                     or any((c.get('securityContext') or {}).get('seLinuxOptions') for c in ctrs))})
    data['apods'] = pods
    hosts = set()
    for ing in items(api, '/apis/networking.k8s.io/v1/ingresses', errors, 'Ingress'):
        for r in (ing.get('spec') or {}).get('rules') or []:
            if r.get('host'):
                hosts.add(r['host'].lower())
    data['ingress_hosts'] = sorted(hosts)
    data['longhorn_settings'] = {}
    if any('longhornio/longhorn-manager' in i for p in pods for i in p['images']):
        for ver in ('v1beta2', 'v1beta1'):
            try:
                st = get(api, f'/apis/longhorn.io/{ver}/namespaces/longhorn-system/settings')
                data['longhorn_settings'] = {(s.get('metadata') or {}).get('name', ''): s.get('value') for s in st.get('items') or []}
                break
            except Exception:
                continue
    if '+rke2' in (data.get('version') or ''):
        progress('RKE2 번들 차트 설정 · 업그레이드 Plan')
        collect_rke2(api, get, data, errors)


def _err(e):
    s = getattr(e, 'status', None)
    return '권한 없음(403)' if s == 403 else '없음(404)' if s == 404 else f'{type(e).__name__}'


# ── 판정 ────────────────────────────────────────────────────────────────────
def gate_stage(gate: dict, minor: int):
    for s in gate.get('stages') or []:
        if (s.get('from') or 0) <= minor and (s.get('to') is None or minor <= s['to']):
            return s
    return None


def _chlog(n):
    return (DATA.get('url') or {}).get('changelog', '').replace('{n}', str(n))


def evaluate_extra(data: dict, add, passed: list):
    cur, tgt = data.get('cur_minor'), data.get('target_minor')
    if not available() or cur is None or tgt is None or tgt <= cur:
        return
    path = list(range(cur + 1, tgt + 1))
    rel = DATA.get('releases') or {}
    gates_tbl = DATA.get('feature_gates') or {}

    # 1) 기능 게이트 — 컨트롤 플레인 플래그 · kubelet 설정 ───────────────────
    set_gates = []                                    # (어디, 게이트, 값)
    for comp, lst in (data.get('components') or {}).items():
        for x in lst:
            for g, v in parse_gates(x['flags'].get('--feature-gates', '')).items():
                set_gates.append((f"{comp} ({x['node']})", g, v))
    for k in data.get('kubelets') or []:
        for g, v in (k.get('gates') or {}).items():
            set_gates.append((f"kubelet ({k['node']})", g, v))
    gone, locked, deprec, unknown = [], [], [], []
    for where, g, v in set_gates:
        info = gates_tbl.get(g)
        if info is None:
            unknown.append(f'{where} — {g}={str(v).lower()}')
            continue
        r = info.get('removed_in')
        if r and r <= tgt:
            gone.append(f"{where} — {g}={str(v).lower()} (1.{r} 에서 없어짐)")
            continue
        st = gate_stage(info, tgt)
        if st and st.get('locked') and v != st.get('default'):
            locked.append(f"{where} — {g}={str(v).lower()} (1.{tgt} 에서 {str(st['default']).lower()} 로 고정)")
        elif st and st.get('stage') == 'deprecated':
            deprec.append(f'{where} — {g}={str(v).lower()}')
    url_g = (DATA.get('url') or {}).get('gates', '')
    if gone:
        add('block', 'gate', f'목표 버전에 없는 기능 게이트를 설정했습니다 — {len(gone)}건',
            '없어진 기능 게이트가 플래그 · 설정에 남아 있으면 그 컴포넌트가 「unrecognized feature gate」 로 시작하지 않습니다.',
            sorted(set(gone)), f'업그레이드 전에 해당 컴포넌트의 --feature-gates · kubelet 설정(featureGates)에서 지우세요. 공식 표: {url_g}')
    if locked:
        add('block', 'gate', f'목표 버전에서 값이 고정되는 기능 게이트를 반대로 설정했습니다 — {len(locked)}건',
            'GA(정식)로 잠긴 기능 게이트를 기본값과 다르게 두면 컴포넌트가 시작하지 않습니다.', sorted(set(locked)),
            f'설정을 지우거나 고정값으로 바꾸세요. 공식 표: {url_g}')
    if deprec:
        add('warn', 'gate', f'목표 버전에서 지원 중단(deprecated) 단계인 기능 게이트 — {len(deprec)}건', '다음 버전에서 없어질 수 있습니다.', sorted(set(deprec)))
    if unknown:
        add('warn', 'gate', f'공식 목록에 없는 기능 게이트 — {len(unknown)}건',
            '오래전에 없어졌거나 이름이 틀렸을 수 있습니다. 지금 버전에서 무시되는지 컴포넌트 로그를 확인하세요.', sorted(set(unknown)))
    if set_gates and not (gone or locked):
        passed.append(f'설정된 기능 게이트 {len(set_gates)}건: 목표 버전에서 없어지거나 고정되는 것이 없습니다(공식 표 기준)')

    # 2) 없어진 플래그 — 컨트롤 플레인 · kube-proxy ──────────────────────────
    removed = {}
    for n in path:
        for f in (rel.get(str(n)) or rel.get(n) or {}).get('removed_flags') or []:
            removed.setdefault((f['component'], f['flag']), (n, f.get('prs') or []))
    hits = []
    for comp, lst in (data.get('components') or {}).items():
        for x in lst:
            for fl in x['flags']:
                key = (comp, fl)
                if key in removed:
                    n, prs = removed[key]
                    hits.append(f"{comp} ({x['node']}) — {fl} (1.{n} 에서 제거{', PR #' + str(prs[0]) if prs else ''})")
    if hits:
        add('block', 'gate', f'목표 버전에서 없어지는 플래그를 쓰고 있습니다 — {len(hits)}건',
            '없어진 플래그가 남아 있으면 그 컴포넌트가 「unknown flag」 로 시작하지 않습니다(공식 CHANGELOG).', sorted(set(hits)),
            '업그레이드 전에 static pod 매니페스트(RKE2 는 config.yaml 의 *-arg)에서 지우거나 설정 파일 항목으로 옮기세요.')
    kubelet_removed = sorted({f"{fl} (1.{n})" for (c, fl), (n, _) in removed.items() if c == 'kubelet'})
    if kubelet_removed:
        add('info', 'gate', f'이번 경로에서 없어지는 kubelet 플래그 — {len(kubelet_removed)}개(노드에서 확인)',
            'kubelet 플래그는 API 로 볼 수 없습니다. 각 노드의 kubelet 설정(RKE2: /etc/rancher/rke2/config.yaml 의 kubelet-arg, '
            'kubeadm: /var/lib/kubelet/kubeadm-flags.env)에 아래 플래그가 없는지 확인하세요 — 남아 있으면 kubelet 이 시작하지 않습니다.',
            kubelet_removed)

    # 3) 볼륨 종류 ─────────────────────────────────────────────────────────
    vt = DATA.get('volume_types') or {}
    bad_now, bad_new, need_csi = [], [], []
    drivers = set(data.get('csidrivers') or [])
    for pv in data.get('pvs') or []:
        for t in pv['types']:
            info = vt.get(t)
            if not info:
                continue
            label = f"{pv['name']} — {t}" + (f" ({pv['claim']})" if pv['claim'] else '')
            if info['state'] == 'removed':
                (bad_new if cur < info['since'] <= tgt else bad_now if info['since'] <= cur else []).append(label + f" · 1.{info['since']} 부터 없음")
            elif info['state'] == 'migrated' and CSI_FOR.get(t) and CSI_FOR[t] not in drivers:
                need_csi.append(label + f" · CSI 드라이버 {CSI_FOR[t]} 없음")
    if bad_new:
        add('block', 'storage', f'목표 버전에서 없어지는 볼륨 종류를 쓰는 PV — {len(bad_new)}개',
            '인트리 볼륨 드라이버가 빠져 이 볼륨을 붙이지 못합니다. 업그레이드 전에 CSI 드라이버로 옮겨야 합니다.', bad_new,
            (DATA.get('url') or {}).get('volumes', ''))
    if bad_now:
        add('warn', 'storage', f'이미 지원하지 않는 볼륨 종류가 남은 PV — {len(bad_now)}개', '쓰지 않는 PV 인지 확인하세요.', bad_now)
    if need_csi:
        add('warn', 'storage', f'CSI 로 넘어간 인트리 볼륨인데 CSI 드라이버가 없습니다 — {len(need_csi)}개',
            '인트리 볼륨 요청은 CSI 드라이버로 넘겨 처리됩니다(migration). 드라이버가 없으면 붙이지 못합니다.', need_csi)

    # 4) 공식 안내의 주제 × 이 클러스터 ──────────────────────────────────────
    notes = []                                        # (버전, 종류, 글, PR)
    for n in path:
        r = rel.get(str(n)) or rel.get(n) or {}
        for kind in ('urgent', 'action', 'deprecations'):
            for it in r.get(kind) or []:
                notes.append((n, kind, it['text'], (it.get('prs') or [None])[0]))
    used = set()

    def topic(pattern, title, sev, detail_fn, items_fn):
        hit = [x for x in notes if re.search(pattern, x[2], re.I)]
        if not hit:
            return
        items = items_fn()
        if not items:
            return
        for x in hit:
            used.add(x[2])
        src = '; '.join(f"1.{x[0]} — {x[2][:220]}{' (PR #' + str(x[3]) + ')' if x[3] else ''}" for x in hit[:3])
        add(sev, 'notes', title, detail_fn() + f' 공식 안내: {src}', items, _chlog(hit[0][0]))

    nodes = data.get('nodes') or []

    def old_kernel(n):
        m = re.match(r'(\d+)\.(\d+)', n.get('kernel') or '')
        return bool(m) and (int(m.group(1)), int(m.group(2))) < (4, 15)

    if tgt >= 35:
        def cg_items():
            out = [f"{n['name']} — 커널 {n.get('kernel')} · {n.get('os')} (cgroup v2 를 쓸 수 없는 커널)" for n in nodes if old_kernel(n)]
            if not out:
                out = [f"{n['name']} — {n.get('os')} · 커널 {n.get('kernel')}: 노드에서 stat -fc %T /sys/fs/cgroup 이 cgroup2fs 인지 확인" for n in nodes[:50]]
            return out
        topic(r'cgroup', '1.35 부터 cgroup v1 노드에서 kubelet 이 시작하지 않습니다(기본)',
              'block' if any(old_kernel(n) for n in nodes) else 'warn',
              lambda: 'failCgroupV1 이 기본 true 가 되어 cgroup v1 호스트에서는 kubelet 이 뜨지 않습니다. 노드 OS 를 cgroup v2 로 바꾸거나, '
                      '불가피하면 업그레이드 전에 kubelet 설정에 failCgroupV1: false 를 넣어야 합니다.', cg_items)
    topic(r'\bipvs\b', 'kube-proxy 의 ipvs 모드는 지원 중단입니다', 'warn',
          lambda: '지금 이 클러스터가 ipvs 모드를 씁니다. 앞으로 없어지니 nftables(또는 iptables)로 옮길 계획을 세우세요.',
          lambda: [f'kube-proxy mode={data.get("proxy_mode")}'] if (data.get('proxy_mode') or '').lower() == 'ipvs' else [])
    topic(r'containerd (?:v?1\.|1\.x)|containerd 1', 'containerd 1.x 지원 종료 안내가 있습니다', 'warn',
          lambda: '이 클러스터에 containerd 1.x 로 도는 노드가 있습니다.',
          lambda: [f"{n['name']} — {n['runtime']}" for n in nodes if re.match(r'containerd://v?1\.', n.get('runtime') or '')])
    topic(r'SELinux', 'SELinux 마운트 동작이 바뀝니다', 'warn',
          lambda: 'seLinuxOptions 를 지정한 파드가 있습니다. 같은 볼륨을 다른 SELinux 라벨로 쓰는 파드가 있으면 시작하지 못할 수 있습니다.',
          lambda: [f"{p['namespace']}/{p['name']}" for p in data.get('apods') or [] if p.get('selinux')][:100])
    topic(r'flex-?volume', 'FlexVolume 관련 변경이 있습니다', 'warn', lambda: 'FlexVolume 을 쓰는 파드가 있습니다.',
          lambda: [f"{p['namespace']}/{p['name']}" for p in data.get('apods') or [] if p.get('flex')][:100])

    # 나머지 공식 긴급 안내는 원문 그대로 버전별로(경로마다 다르다)
    for n in path:
        r = rel.get(str(n)) or rel.get(n) or {}
        rest = [it for k in ('urgent', 'action') for it in r.get(k) or [] if it['text'] not in used]
        if rest:
            add('info', 'notes', f'1.{n} 공식 업그레이드 주의 사항 — {len(rest)}건(원문)',
                '쿠버네티스 CHANGELOG 의 「Urgent Upgrade Notes」 · 「ACTION REQUIRED」 입니다. 이 클러스터에 해당하는지 확인하세요.',
                [it['text'][:600] + (f" (PR #{it['prs'][0]})" if it.get('prs') else '') for it in rest], _chlog(n))
        elif r and not r.get('released', True):
            add('info', 'notes', f'1.{n} 은 아직 정식 출시 전입니다', '정식 릴리스가 나온 뒤 다시 점검하세요.')


# ── 설치된 애플리케이션 ──────────────────────────────────────────────────────
def _ver_tuple(v):
    m = re.match(r'v?(\d+)\.(\d+)\.(\d+)', str(v or ''))
    return tuple(int(x) for x in m.groups()) if m else None


def longhorn_version(data) -> str:
    for p in data.get('apods') or []:
        for i in p['images']:
            if 'longhornio/longhorn-manager' in i:
                m = re.search(r':v?(\d+\.\d+\.\d+)', i)
                if m:
                    return m.group(1)
    return ''


def rwx_usage(data) -> list:
    """Longhorn RWX PVC → 쓰는 워크로드 · 파드. [{pvc, consumers:[owner|pod], pods:[...]}]"""
    lh_sc = {n for n, prov in (data.get('storageclasses') or {}).items() if prov == 'driver.longhorn.io'}
    rwx = [c for c in data.get('pvcs') or [] if 'ReadWriteMany' in c['modes'] and (c['sc'] in lh_sc)]
    out = []
    for c in rwx:
        users = [p for p in data.get('apods') or [] if p['namespace'] == c['namespace'] and c['name'] in p['claims']]
        out.append({'pvc': f"{c['namespace']}/{c['name']}", 'consumers': sorted({p['owner'] or p['name'] for p in users}),
                    'pods': users, 'db': any(DB_IMAGE.search(i) for p in users for i in p['images'])})
    return out


def registry_inside(data) -> dict:
    """클러스터 안 이미지 저장소 — Harbor(goharbor) 가 있고, 다른 파드가 이 클러스터 인그레스 호스트에서 이미지를 받는가."""
    pods = data.get('apods') or []
    harbor = [p for p in pods if any('goharbor/' in i for i in p['images'])]
    hosts = set(data.get('ingress_hosts') or [])
    users, always = {}, 0
    for p in pods:
        for i in p['images']:
            h = image_host(i)
            if h.split(':')[0] in hosts:
                users.setdefault(h, set()).add(p['owner'] or f"{p['namespace']}/{p['name']}")
                if p['pull_always']:
                    always += 1
    return {'harbor': bool(harbor), 'harbor_ns': sorted({p['namespace'] for p in harbor}), 'hosts': {k: sorted(v) for k, v in users.items()},
            'pull_always': always, 'harbor_claims': sorted({f"{p['namespace']}/{c}" for p in harbor for c in p['claims']})}


def evaluate_apps(data: dict, add, passed: list):
    pods = data.get('apods') or []
    if not pods:
        return
    nodes = data.get('nodes') or []
    lhv = longhorn_version(data)
    rwx = rwx_usage(data)
    reg = registry_inside(data)
    rwx_pvcs = {u['pvc'] for u in rwx}
    lh = (DATA.get('apps') or {}).get('longhorn') or {}

    # A) Longhorn RWX(share-manager · NFS) ────────────────────────────────
    if lhv and rwx:
        cur = _ver_tuple(lhv)
        rels = lh.get('releases') or {}
        newer = sorted((v for v in rels if _ver_tuple(v) and cur and _ver_tuple(v) > cur), key=_ver_tuple)
        ff_since = next((v for v in sorted(rels, key=_ver_tuple) if rels[v].get('fast_failover')), '')
        has_ff = bool(ff_since and cur and cur >= _ver_tuple(ff_since))
        # 이후 판의 RWX 버그 수정 — 재시작 · 재연결 · 복구 관련(이번 장애 유형)을 앞에
        top = re.compile(r'kubelet|reconnect|stale|reboot|node.*(restart|down|shutdown)|share manager is recreated', re.I)
        prio = re.compile(r'recover|restart|drain|hang|stuck|sleep|unavailable|failover|shutdown', re.I)
        fixes = sorted((f"{v} — {f['title']} (#{f['issue']})" for v in newer for f in rels[v].get('rwx_fixes') or [] if f['kind'] == 'bug'),
                       key=lambda s: 0 if top.search(s) else 1 if prio.search(s) else 2)
        ff_on = str((data.get('longhorn_settings') or {}).get('rwx-volume-fast-failover', '')).lower() == 'true'
        items = [f"{u['pvc']} → {', '.join(u['consumers']) or '(지금 쓰는 파드 없음)'}" + (' · DB' if u['db'] else '') for u in rwx]
        sev = 'warn'
        detail = (f'Longhorn {lhv} 의 공유 볼륨(RWX) {len(rwx)}개를 쓰고 있습니다. RWX 는 share-manager 파드가 NFS 서버로 동작하고, 노드는 NFS 로 붙습니다. '
                  '노드를 재시작 · 비우면 share-manager 가 다른 노드에 새로 생기는데, 기존 NFS 연결이 새 서버로 넘어가지 못하고 응답 없는(stale) '
                  '상태로 남으면 그 노드의 kubelet 볼륨 처리가 멈춰 NotReady → 파드 eviction 으로 번질 수 있습니다(실제 장애 사례).')
        if not has_ff:
            detail += f' 이 판에는 RWX fast failover(공식: {ff_since} 부터)가 없습니다.'
        elif not ff_on:
            detail += ' fast failover 를 쓸 수 있는 판이지만 설정(rwx-volume-fast-failover)이 꺼져 있습니다.'
        if fixes:
            detail += f' 이후 판에서 고쳐진 RWX 관련 문제가 {len(fixes)}건 있습니다(아래 목록 끝).'
        if reg['harbor'] and set(reg['harbor_claims']) & rwx_pvcs:
            sev = 'block'
            detail += ' 특히 이미지 저장소(Harbor)가 RWX 볼륨 위에 있어, 연결이 멈추면 저장소까지 중단되어 옮겨 간 파드가 이미지를 받지 못합니다.'
        add(sev, 'app', f'Longhorn 공유 볼륨(RWX) 의 노드 재시작 위험 — {len(rwx)}개', detail,
            items + [f'[이후 판 수정] {x}' for x in fixes[:20]],
            '업그레이드 · 재시작은 노드 한 대씩: 그 노드를 비운 뒤 share-manager 파드가 다른 노드에서 모두 Running 이고 RWX 를 쓰는 파드가 정상인지 '
            '확인하고 다음 노드로. 노드에서 응답 없는 NFS 마운트(df 가 멈춤)가 보이면 umount -f -l 로 풀고 kubelet 을 확인하세요. '
            + ('Longhorn 을 먼저 fast failover 가 있는 판으로 올리는 것을 검토하세요(Longhorn 은 한 단계씩 올림). ' if not has_ff else
               'rwx-volume-fast-failover 설정을 켜는 것을 검토하세요. ' if not ff_on else '')
            + f"릴리스 노트: {lh.get('url', '')}")
    elif lhv:
        passed.append(f'Longhorn {lhv}: 공유 볼륨(RWX)을 쓰는 PVC 가 없습니다(share-manager · NFS 재연결 위험 없음)')
    if lhv:
        dp = (data.get('longhorn_settings') or {}).get('node-drain-policy')
        rels = lh.get('releases') or {}
        mk = (rels.get(lhv) or {}).get('min_k8s')
        if mk and data.get('target_minor') and data['target_minor'] < mk:
            add('warn', 'app', f'Longhorn {lhv} 의 최소 쿠버네티스 버전은 1.{mk} 입니다', '목표 버전이 그보다 낮습니다.', [])
        if dp:
            passed.append(f'Longhorn 노드 비우기 정책(node-drain-policy): {dp}')

    # B) 이미지 저장소가 클러스터 안 ──────────────────────────────────────
    if reg['hosts']:
        n_users = sum(len(v) for v in reg['hosts'].values())
        add('warn', 'app', f'이미지 저장소가 이 클러스터 안에 있습니다 — {", ".join(reg["hosts"])}',
            f'워크로드 {n_users}개가 이 클러스터의 인그레스 주소에서 이미지를 받습니다. 업그레이드 · 재시작 중에 저장소(Harbor 등)가 내려가면 '
            '다른 노드로 옮겨 간 파드가 이미지를 받지 못해 ImagePullBackOff 로 장애가 커집니다(폐쇄망이면 대신 받을 곳도 없음).'
            + (f' imagePullPolicy: Always 인 파드가 {reg["pull_always"]}개 있어 다시 뜰 때마다 저장소가 필요합니다.' if reg['pull_always'] else ''),
            [f'{h} ← {", ".join(v[:15])}{" …" if len(v) > 15 else ""}' for h, v in reg['hosts'].items()],
            '업그레이드 전에 모든 노드에 필요한 이미지를 미리 받아 두고(pre-pull), imagePullPolicy 를 IfNotPresent 로 두세요. '
            '저장소가 있는 노드는 맨 마지막에 올리고, 저장소의 DB · 스토리지가 RWX 볼륨이면 먼저 정상인지 확인하세요. 가능하면 클러스터 밖 미러를 두세요.')
    elif reg['harbor']:
        passed.append(f"Harbor({', '.join(reg['harbor_ns'])}) 가 있지만 이 클러스터 워크로드가 그 주소에서 이미지를 받지는 않습니다")

    # C) DB 가 공유 볼륨(RWX · NFS) 위 ──────────────────────────────────────
    db_rwx = [u for u in rwx if u['db']]
    other_rwx = []
    nfs_pv = {pv['name'] for pv in data.get('pvs') or [] if 'nfs' in pv['types']}     # NFS 서버에 붙는 PV(nfs-subdir 등) — 같은 위험
    for c in data.get('pvcs') or []:
        shared = 'ReadWriteMany' in c['modes'] or c.get('volume') in nfs_pv
        if shared and f"{c['namespace']}/{c['name']}" not in rwx_pvcs:
            users = [p for p in pods if p['namespace'] == c['namespace'] and c['name'] in p['claims'] and any(DB_IMAGE.search(i) for i in p['images'])]
            if users:
                other_rwx.append(f"{c['namespace']}/{c['name']} → {', '.join(sorted({p['owner'] or p['name'] for p in users}))}")
    db_items = [f"{u['pvc']} → {', '.join(u['consumers'])}" for u in db_rwx] + other_rwx
    if db_items:
        add('warn', 'app', f'DB · 상태 저장 서비스가 공유 볼륨(RWX · NFS) 위에 있습니다 — {len(db_items)}개',
            'NFS 기반 공유 볼륨은 연결이 끊기면 쓰기가 멈추고, 다시 붙어도 DB 가 정상인지 따로 확인해야 합니다(Redis 클러스터 · PostgreSQL 등).',
            db_items, '업그레이드 뒤 각 서비스의 정합성을 확인하는 단계를 작업 계획에 넣으세요(예: redis-cli cluster info 의 cluster_state:ok, DB 접속 · 복제 상태).')

    # D) 컨트롤 플레인 재시작 간격 ───────────────────────────────────────────
    cps = [n for n in nodes if n.get('control_plane')]
    if len(cps) >= 2 and (rwx or reg['hosts']):
        add('info', 'app', f'서버(컨트롤 플레인) 노드 {len(cps)}대를 짧은 간격으로 재시작하지 마세요',
            '여러 서버 노드를 잇달아 재시작하면 그 위의 share-manager · 저장소 파드가 한꺼번에 다시 만들어져 복구가 꼬일 수 있습니다(실제 장애 사례). '
            'etcd 는 과반이 살아 있어야 하므로 한 번에 한 대씩만 내립니다.', [n['name'] for n in cps])


def extra_checklist(data: dict) -> list:
    out = []
    rwx = rwx_usage(data) if data.get('apods') else []
    reg = registry_inside(data) if data.get('apods') else {'hosts': {}}
    cps = [n for n in data.get('nodes') or [] if n.get('control_plane')]
    if len(cps) >= 2:
        out.append('서버 노드는 한 대씩: 재시작 → 노드 Ready · etcd 정상 확인 → 다음 노드(잇달아 재시작하지 않는다)')
    if rwx:
        out.append('Longhorn RWX: 노드마다 비운 뒤 share-manager 파드가 모두 Running 이고 RWX 를 쓰는 파드가 정상인지 확인 — '
                   '응답 없는 NFS 마운트가 있으면 umount -f -l 로 푼다')
    if reg.get('hosts'):
        out.append('이미지 저장소(클러스터 안): 업그레이드 전에 모든 노드에 이미지를 미리 받아 두고, 노드마다 작업 뒤 이미지 받기(pull)가 되는지 확인')
    if any(u['db'] for u in rwx):
        out.append('RWX 위 DB · Redis: 작업 뒤 정합성 확인(redis-cli cluster info → cluster_state:ok, DB 접속)')
    return out


# ── 애드온 공식 호환표 (v1.5.29) ─────────────────────────────────────────────
def _vt(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v or '')))


def addon_supports(e: dict, minor: int) -> bool:
    if not e:
        return False
    if e.get('k8s'):
        return minor in e['k8s']
    return minor >= (e.get('min') or 0) and (e.get('max') is None or minor <= e['max'])


def _range_text(e: dict) -> str:
    if e.get('k8s'):
        ks = e['k8s']
        return ', '.join(f'1.{k}' for k in ks) if len(ks) <= 6 else f'1.{ks[0]} ~ 1.{ks[-1]}'
    return f"1.{e.get('min')}" + (f" ~ 1.{e['max']}" if e.get('max') is not None else ' 이상')


def detect_addons(data) -> list:
    """이미지에서 설치된 애드온과 판 — [{name, version, key, images, bundled}]. 같은 애드온이 여러 판이면 가장 낮은 것."""
    tbl = DATA.get('addons') or {}
    rke2 = '+rke2' in (data.get('version') or '') or '+k3s' in (data.get('version') or '')
    images = sorted({i for p in data.get('apods') or [] for i in p['images']}) or list(data.get('images') or [])
    out = []
    for name, info in tbl.items():
        found = {}
        for img in images:
            m = re.search(info.get('image') or r'^$', img)
            if m:
                found.setdefault(m.group(1), []).append(img)
        if not found:
            continue
        ver = min(found, key=_vt)
        imgs = found[ver]
        key = ver if info.get('key') == 'exact' else '.'.join(ver.split('.')[:2])
        bundled = rke2 and all(re.match(r'(docker\.io/)?rancher/', i) for i in imgs)
        out.append({'name': name, 'version': ver, 'key': key, 'images': imgs, 'bundled': bundled})
    return out


def addon_plan(name: str, key: str, cur: int, tgt: int) -> dict:
    """→ {state: ok|upgrade|two_step|unknown_old|unknown_new|no_table, entry, first, steps, newest}"""
    info = (DATA.get('addons') or {}).get(name) or {}
    vers = info.get('versions') or {}
    if not vers:
        return {'state': 'no_table'}
    e = vers.get(key)
    if e is None and info.get('key') == 'exact':                 # 정확한 판이 표에 없으면 같은 주.부 줄
        same = [k for k in vers if k.rsplit('.', 1)[0] == key.rsplit('.', 1)[0]]
        e = vers[max(same, key=_vt)] if same else None
    order = sorted(vers, key=_vt)
    if e is None:
        if _vt(key) < _vt(order[0]):
            return {'state': 'unknown_old', 'oldest': order[0]}
        return {'state': 'unknown_new'}
    if addon_supports(e, tgt):
        return {'state': 'ok', 'entry': e}
    newer = [k for k in order if _vt(k) > _vt(key)]
    both = [k for k in newer if addon_supports(vers[k], cur) and addon_supports(vers[k], tgt)]
    if both:
        return {'state': 'upgrade', 'entry': e, 'first': both[0], 'first_entry': vers[both[0]]}
    for_tgt = [k for k in newer if addon_supports(vers[k], tgt)]
    if not for_tgt:
        # 표의 어느 판도 목표를 아직 지원한다고 밝히지 않았다(목표가 막 나왔거나 출시 전) — 「먼저 올려라」 가 아니라 「기다려라」
        return {'state': 'none_yet', 'entry': e, 'latest': order[-1]}
    return {'state': 'two_step', 'entry': e, 'newest': for_tgt[0], 'newest_entry': vers[for_tgt[0]]}


def evaluate_addons(data: dict, add, passed: list):
    cur, tgt = data.get('cur_minor'), data.get('target_minor')
    if cur is None or tgt is None or tgt <= cur or not DATA.get('addons'):
        return
    tbl = DATA['addons']
    try:
        rke2p = rke2_plan(data) or {}
    except Exception:
        rke2p = {}
    rke2t = rke2p.get('target_components')
    for a in detect_addons(data):
        info = tbl.get(a['name']) or {}
        p = addon_plan(a['name'], a['key'], cur, tgt)
        url = info.get('url', '')
        label = f"{a['name']} {a['version']}"
        bundle = ('RKE2 · K3s 가 함께 설치한 것입니다 — 보통 RKE2 · K3s 를 올리면 그 판에 맞는 버전으로 함께 바뀝니다. '
                  '목표 RKE2 · K3s 판의 릴리스 노트에서 들어 있는 버전을 확인하세요. ') if a['bundled'] else ''
        tv = _bundled_ver(rke2t or {}, a['name'])
        if a['bundled'] and tv:                       # v1.5.30 — RKE2 표로 목표 판에 든 버전을 바로 알려 준다
            bundle = (f"RKE2 가 함께 설치한 것입니다 — 목표 RKE2 {rke2p['target']} 에는 {a['name']} {tv} 이(가) 들어 있어 "
                      'RKE2 를 올리면 함께 바뀝니다. ')
        if p['state'] == 'ok':
            passed.append(f"{label}: 1.{tgt} 을(를) 지원합니다(공식 표: {_range_text(p['entry'])})")
            continue
        if p['state'] in ('no_table', 'unknown_new'):
            continue
        if p['state'] == 'unknown_old':
            add('info' if a['bundled'] else 'warn', 'addon', f'{label} — 공식 호환표에 없는 옛 버전입니다',
                bundle + f"공식 표는 {p['oldest']} 부터 있습니다. 지원이 끝난 버전일 수 있어 1.{tgt} 에서 동작한다는 보장이 없습니다.",
                a['images'][:5], f'업그레이드 전에 최신 지원 버전으로 올리는 것을 검토하세요. 공식 표: {url}')
            continue
        sev = 'info' if a['bundled'] else ('block' if info.get('cni') else 'warn')
        why = f"{label} 의 공식 지원 범위는 {_range_text(p['entry'])} 입니다 — 목표 1.{tgt} 이(가) 들어 있지 않습니다."
        if info.get('cni'):
            why += ' 네트워크(CNI)가 맞지 않으면 노드 · 파드 통신이 끊길 수 있습니다.'
        if p['state'] == 'none_yet':
            add('info' if a['bundled'] else 'warn', 'addon', f"{a['name']} — 1.{tgt} 을 지원한다고 밝힌 판이 아직 없습니다",
                bundle + why + f" 공식 표의 가장 새 판({p['latest']})도 1.{tgt} 을 적지 않았습니다.", a['images'][:5],
                f"{a['name']} 의 새 판이 1.{tgt} 지원을 밝힐 때까지 기다리거나, 시험 환경에서 먼저 확인하세요. 공식 표: {url}")
            continue
        if p['state'] == 'upgrade':
            add(sev, 'addon', f"{a['name']} 를 먼저 {p['first']} 이상으로 올려야 합니다(지금 {a['version']})",
                bundle + why + f" {p['first']} 은(는) 지금 1.{cur} 와 목표 1.{tgt} 를 모두 지원합니다({_range_text(p['first_entry'])}).",
                a['images'][:5],
                f"순서: {a['name']} {p['first']} 로 업그레이드 → 정상 확인 → 쿠버네티스 1.{tgt}. 애드온은 자기 업그레이드 경로(한 단계씩 등)를 따르세요. 공식 표: {url}")
        else:
            nv = p.get('newest') or ''
            add(sev, 'addon', f"{a['name']} {a['version']} 은(는) 1.{tgt} 을 지원하지 않고, 지금 버전과 목표를 함께 지원하는 판도 없습니다",
                bundle + why + (f" 1.{tgt} 을 지원하는 판은 {nv}({_range_text(p['newest_entry'])}) 부터입니다." if p.get('newest_entry') else ''),
                a['images'][:5],
                f"쿠버네티스와 {a['name']} 를 번갈아 한 단계씩 올려야 합니다 — 각 단계마다 두 쪽이 모두 지원 범위 안인지 공식 표로 확인하세요. 공식 표: {url}")


def addon_checklist(data: dict) -> list:
    cur, tgt = data.get('cur_minor'), data.get('target_minor')
    if cur is None or tgt is None or tgt <= cur:
        return []
    out = []
    for a in detect_addons(data):
        if a['bundled']:
            continue
        p = addon_plan(a['name'], a['key'], cur, tgt)
        if p['state'] == 'upgrade':
            out.append(f"쿠버네티스보다 먼저: {a['name']} {a['version']} → {p['first']} 이상으로 올리고 정상인지 확인")
        elif p['state'] == 'two_step':
            out.append(f"{a['name']} 와 쿠버네티스를 번갈아 한 단계씩 — 단계마다 공식 호환표 확인")
    return out


# ── RKE2 업그레이드 경로 (v1.5.30) ───────────────────────────────────────────
# 표: RKE2 공식 릴리스 노트(판마다 함께 든 구성 요소 · 번들 차트 판 · 경고 · 중요 안내) + etcd 「먼저 이 판까지」 경고.
RKE2_TAG = re.compile(r'v1\.(\d+)\.(\d+)\+rke2r(\d+)$')
_ETCD_BRIDGE_NOTE = re.compile(r'no safe path|zombie member|etcd cluster membership|include etcd \d+\.\d+', re.I)
ADDON_RKE2_COMP = {'Calico': ('Calico', 'Canal'), 'Cilium': ('Cilium',), 'ingress-nginx': ('Ingress-Nginx',),
                   'metrics-server': ('Metrics-server',)}


def _bundled_ver(comps: dict, addon: str) -> str:
    """RKE2 구성 요소 표에서 애드온 판 — Canal 은 「Flannel v0.28 + Calico v3.32」 꼴이라 Calico 쪽만."""
    for key in ADDON_RKE2_COMP.get(addon, ()):
        v = comps.get(key) or ''
        if ' + ' in v or key == 'Canal':
            v = next((x.split(' ', 1)[1] for x in v.split(' + ') if x.startswith(addon + ' ')), '')
        if v:
            return v
    return ''
RKE2_BASE = ('Kubernetes', 'Etcd', 'Containerd', 'Runc')
RKE2_BY_CHART = {'rke2-coredns': 'CoreDNS', 'rke2-metrics-server': 'Metrics-server', 'rke2-ingress-nginx': 'Ingress-Nginx',
                 'rke2-traefik': 'Traefik', 'rke2-canal': 'Canal', 'rke2-calico': 'Calico', 'rke2-cilium': 'Cilium',
                 'rke2-multus': 'Multus'}
# 안내 문구가 특정 번들 구성 요소 얘기면 그것을 쓸 때만 보여 준다
RKE2_NOTE_TOPIC = {'traefik': ('rke2-traefik', 'rke2-ingress-nginx'), 'ingress-nginx': ('rke2-traefik', 'rke2-ingress-nginx'),
                   'cilium': ('rke2-cilium',), 'canal': ('rke2-canal',), 'flannel': ('rke2-canal',),
                   'calico': ('rke2-calico', 'rke2-canal'), 'multus': ('rke2-multus',)}


def rke2_key(tag: str):
    m = RKE2_TAG.match(tag or '')
    return tuple(int(x) for x in m.groups()) if m else None


def _rke2_rel() -> dict:
    return (DATA.get('rke2') or {}).get('releases') or {}


def rke2_latest(minor: int):
    """그 마이너의 최신 커뮤니티 판 — Prime 전용 · 회수된(pulled) 판은 고르지 않는다."""
    c = [t for t, e in _rke2_rel().items() if rke2_key(t) and rke2_key(t)[0] == minor
         and not e.get('prime_only') and not e.get('pulled')]
    return max(c, key=rke2_key) if c else None


def rke2_installed(data) -> dict | None:
    """kube-system 의 rke2-* Helm 릴리스 → {차트 이름: 판}. Helm 을 못 봤으면 None(모름)."""
    if data.get('helm') is None:
        return None
    out = {}
    for h in data['helm']:
        r = h.get('release') or ''
        if h.get('namespace') == 'kube-system' and r.startswith('rke2-'):
            ch = h.get('chart') or ''
            out[r] = ch[len(r) + 1:] if ch.startswith(r + '-') else ch
    return out


def _major(v: str):
    m = re.search(r'(\d+)', str(v or ''))
    return int(m.group(1)) if m else None


def _series(v: str) -> str:
    return '.'.join(str(x) for x in _vt(v)[:2])


def rke2_plan(data: dict) -> dict | None:
    """지금 판 → 목표 마이너까지의 RKE2 경로 · 구성 요소 변화 · etcd 다리 판. RKE2 가 아니거나 표가 없으면 None."""
    cur = data.get('version') or ''
    ck = rke2_key(cur)
    tgt = data.get('target_minor')
    rel = _rke2_rel()
    if not ck or not rel or tgt is None or tgt <= ck[0]:
        return None
    path = [rke2_latest(m) for m in range(ck[0] + 1, tgt + 1)]
    if not all(path):
        missing = [f'1.{m}' for m, t in zip(range(ck[0] + 1, tgt + 1), path) if not t]
        return {'cur': cur, 'missing': missing}
    target = path[-1]
    ce, te = rel.get(cur) or {}, rel[target]
    comps_c, comps_t = dict(ce.get('components') or {}), dict(te.get('components') or {})
    # 지금 판은 표보다 클러스터에서 본 것이 정확하다(etcd 이미지 · 노드 containerd)
    etcd_img = next((m.group(1) for p in data.get('apods') or [] for i in p['images']
                     for m in [re.search(r'(?:hardened-)?etcd:(v\d+\.\d+\.\d+)', i)] if m), None)
    if etcd_img:
        comps_c['Etcd'] = etcd_img
    rt = [n.get('runtime', '') for n in data.get('nodes') or [] if (n.get('runtime') or '').startswith('containerd://')]
    if rt and not comps_c.get('Containerd'):          # 판을 아는 RKE2 는 함께 든 containerd 가 정해져 있다 — 모를 때만 노드 값
        comps_c['Containerd'] = 'v' + min((r.split('://', 1)[1] for r in rt), key=_vt).lstrip('v')
    inst = rke2_installed(data)
    show = list(RKE2_BASE) + [c for ch, c in RKE2_BY_CHART.items() if inst is None or ch in inst]
    diff = [(n, comps_c.get(n, ''), comps_t.get(n, '')) for n in show
            if (comps_c.get(n) or comps_t.get(n)) and comps_c.get(n) != comps_t.get(n)]
    # etcd 다리: 「3.5 → 3.6 은 3.5.26 을 거쳐야 안전」 같은 공식 경고
    bridge = None
    for b in (DATA.get('rke2') or {}).get('etcd_bridges') or []:
        ce_v = comps_c.get('Etcd', '')
        if not ce_v or _series(ce_v) != b['from'] or _vt(ce_v) >= _vt(b['min']):
            continue
        if not any(_vt(_series((rel[t].get('components') or {}).get('Etcd', ''))) >= _vt(b['to']) for t in path):
            continue
        cand = sorted((t for t, e in rel.items() if rke2_key(t) and rke2_key(t) >= ck and not e.get('pulled')
                       and not e.get('prime_only') and _series((e.get('components') or {}).get('Etcd', '')) == b['from']
                       and _vt((e.get('components') or {}).get('Etcd', '')) >= _vt(b['min'])), key=rke2_key)
        bridge = {**b, 'etcd': ce_v, 'via': cand[0] if cand else None,
                  'via_etcd': (rel[cand[0]].get('components') or {}).get('Etcd', '') if cand else ''}
        break
    if bridge and bridge['via']:
        vk = rke2_key(bridge['via'])
        path = [bridge['via']] + [t for t in path if rke2_key(t)[0] > vk[0]]
    # 지금 판 이후 ~ 목표까지 공식 안내(같은 문구는 한 번, 쓰지 않는 구성 요소 얘기는 뺀다)
    notes, seen = [], set()
    bridges_all = (DATA.get('rke2') or {}).get('etcd_bridges') or []
    for t in sorted(rel, key=lambda x: rke2_key(x) or (0,)):
        k = rke2_key(t)
        if not k or k <= ck or k[0] > tgt or k > rke2_key(target) or rel[t].get('pulled'):
            continue
        for n in rel[t].get('notes') or []:
            low = n.lower()
            if n in seen or 'removed this rke2 release from the channel server' in low:
                continue
            # etcd 다리 경고(3.5 → 3.6 은 3.5.26 을 거쳐야)는 위 판정이 이 클러스터의 etcd 로 따로 본다 — 원문을 또 띄우지 않는다
            if 'etcd' in low and (_ETCD_BRIDGE_NOTE.search(n) or any(b['min'] in n for b in bridges_all)):
                continue
            topics = [v for w, v in RKE2_NOTE_TOPIC.items() if w in low]
            if inst is not None and topics and not any(ch in inst for v in topics for ch in v):
                continue
            seen.add(n)
            notes.append((t, n))
    charts = []
    for name, cv in (inst or {}).items():
        tv = (te.get('charts') or {}).get(name)
        if tv and cv and tv != cv:
            charts.append({'name': name, 'cur': cv, 'tgt': tv, 'major': _major(cv) != _major(tv),
                           'config': name in set(data.get('rke2_configs') or [])})
    return {'cur': cur, 'cur_known': bool(ce), 'cur_pulled': bool(ce.get('pulled')), 'path': path, 'target': target,
            'diff': diff, 'bridge': bridge, 'notes': notes, 'charts': charts, 'installed': inst,
            'target_components': comps_t, 'plans': data.get('rke2_plans') or []}


def collect_rke2(api, get, data: dict, errors: list):
    """HelmChartConfig(번들 차트를 고쳐 쓴 것) 이름 · system-upgrade-controller Plan — 없으면(404) 조용히 넘어간다."""
    data['rke2_configs'], data['rke2_plans'] = [], []
    try:
        r = get(api, '/apis/helm.cattle.io/v1/helmchartconfigs')
        data['rke2_configs'] = sorted({(x.get('metadata') or {}).get('name', '') for x in r.get('items') or []} - {''})
    except Exception as e:
        if getattr(e, 'status', None) != 404:
            errors.append(f'HelmChartConfig: {_err(e)}')
    try:
        r = get(api, '/apis/upgrade.cattle.io/v1/plans')
        for x in r.get('items') or []:
            md, sp = x.get('metadata') or {}, x.get('spec') or {}
            data['rke2_plans'].append({'namespace': md.get('namespace', ''), 'name': md.get('name', ''),
                                       'version': sp.get('version') or '', 'channel': sp.get('channel') or '',
                                       'concurrency': sp.get('concurrency')})
    except Exception as e:
        if getattr(e, 'status', None) != 404:
            errors.append(f'system-upgrade-controller Plan: {_err(e)}')


def evaluate_rke2(data: dict, add, passed: list):
    p = rke2_plan(data)
    if not p:
        return
    url = (DATA.get('rke2') or {}).get('url', 'https://github.com/rancher/rke2/releases')
    if p.get('missing'):
        add('warn', 'rke2', f"RKE2 공식 판 정보에 {', '.join(p['missing'])} 이(가) 없습니다",
            '아직 나오지 않았거나 표가 오래됐습니다. 목표 마이너의 RKE2 판이 나왔는지 확인하세요.', [], f'RKE2 릴리스: {url}')
        return
    cur, target = p['cur'], p['target']
    if p['cur_pulled']:
        add('warn', 'rke2', f'지금 판 {cur} 은(는) 공식 채널에서 회수된 판입니다',
            '릴리스 노트에 문제가 있어 회수했다고 적힌 판입니다. 같은 줄의 다음 판으로 올리는 것을 먼저 검토하세요.', [], f'RKE2 릴리스: {url}')
    steps = ' → '.join(p['path'])
    detail = ('마이너마다 그 줄의 최신 커뮤니티 판을 거칩니다(Prime 전용 · 회수된 판은 고르지 않음). '
              + ('' if p['cur_known'] else f'지금 판 {cur} 은(는) 공식 표에 없어 구성 요소를 비교하지 못한 항목이 있습니다. ')
              + '아래는 지금 → 목표 판에서 바뀌는 함께 든 구성 요소입니다.')
    add('info', 'rke2', f'RKE2 경로: {cur} → {steps}', detail,
        [f'{n}: {a or "—"} → {b or "(목표 판에 없음)"}' for n, a, b in p['diff']], f'RKE2 릴리스 노트: {url}')
    b = p['bridge']
    if b:
        add('warn', 'rke2', f"etcd {b['from']} → {b['to']}: RKE2 를 먼저 {b['via'] or 'etcd ' + b['min'] + ' 이상을 담은 판'} 으로 올려야 합니다",
            f"지금 etcd {b['etcd']}. RKE2 공식 경고: etcd {b['from']} 에서 {b['to']} 로 가는 안전한 길은 {b['min']} 을 먼저 거치는 것뿐입니다. "
            '그러지 않으면 예전에 뺀 etcd 멤버가 다시 나타나 쿼럼을 잃을 수 있습니다(특히 노드를 새로 넣고 빼는 방식으로 올릴 때).',
            [f"{b['via']} — etcd {b['via_etcd']}"] if b['via'] else [],
            f"순서: {b['via'] or '해당 판'} 으로 모든 서버 노드 업그레이드 → etcd 판 · 멤버 목록 확인 → 다음 마이너. 출처: {url}")
    tc = {n: (a, bb) for n, a, bb in p['diff']}
    if 'Containerd' in tc and _major(tc['Containerd'][0]) and _major(tc['Containerd'][0]) != _major(tc['Containerd'][1]):
        # 템플릿이 있는지는 API 로 볼 수 없다 — 못 본 것을 「주의」 로 단정하지 않는다(대부분 템플릿이 없다)
        add('info', 'rke2', f"containerd 메이저 판이 바뀝니다 ({tc['Containerd'][0]} → {tc['Containerd'][1]}) — 직접 만든 설정 템플릿이 있으면 확인",
            'containerd 설정을 템플릿으로 직접 고쳐 쓰고 있다면 새 메이저 판의 설정 형식에 맞는지 확인해야 합니다. '
            '템플릿이 없으면 RKE2 가 새 형식으로 만들어 주므로 해당이 없습니다.', [],
            '노드마다 ls /var/lib/rancher/rke2/agent/etc/containerd/*.tmpl — 파일이 있으면 목표 판 문서의 containerd 설정 안내와 비교하세요.')
    inst = p['installed']
    if inst is not None and 'rke2-ingress-nginx' in inst and not p['target_components'].get('Ingress-Nginx'):
        add('block', 'rke2', f'목표 판 {target} 에는 ingress-nginx 가 들어 있지 않습니다',
            '지금 RKE2 번들 ingress-nginx 를 쓰고 있습니다. 올리면 인그레스가 동작하지 않을 수 있습니다.', [],
            f'업그레이드 전에 Traefik 등으로 옮기는 계획을 세우세요. 릴리스 노트: {url}')
    if p['notes']:
        hard = [x for x in p['notes'] if re.search(r'breaking|must|fail|no safe path|quorum|no longer|removed|will not', x[1], re.I)]
        add('warn' if hard else 'info', 'rke2', f'RKE2 공식 안내 — {len(p["notes"])}건 (지금 판 이후 ~ {target})',
            '판별 릴리스 노트의 경고 · 중요 안내입니다(원문). 쓰지 않는 번들 구성 요소에 관한 것은 뺐습니다.',
            [f'{t}: {n}' for t, n in p['notes'][:15]], f'RKE2 릴리스 노트: {url}')
    else:
        passed.append(f'RKE2 {cur} → {target}: 릴리스 노트에 이 클러스터에 해당하는 경고 · 중요 안내가 없습니다')
    big = [c for c in p['charts'] if c['config'] and c['major']]
    if big:
        add('warn', 'rke2', f'HelmChartConfig 로 고친 번들 차트의 주 판이 바뀝니다 — {len(big)}개',
            'HelmChartConfig 의 valuesContent 는 차트 판에 맞춰 쓴 값입니다. 차트 주 판이 바뀌면 값 이름 · 구조가 달라져 무시되거나 설치가 실패할 수 있습니다.',
            [f"{c['name']}: {c['cur']} → {c['tgt']}" for c in big],
            '목표 판 차트의 values 와 비교해 HelmChartConfig 를 미리 고쳐 두세요(kubectl -n kube-system get helmchartconfig <이름> -o yaml).')
    for c in p['charts']:
        if c['config'] and not c['major']:
            passed.append(f"HelmChartConfig {c['name']}: 차트 주 판 그대로({c['cur']} → {c['tgt']})")


def rke2_checklist(data: dict) -> list:
    """RKE2 일반 안내 한 줄을 이 클러스터의 실제 경로로 바꾼다. 표가 없으면 빈 목록(기존 안내 그대로)."""
    p = rke2_plan(data)
    if not p or p.get('missing'):
        return []
    out = ['서버 토큰을 따로 보관하세요 — /var/lib/rancher/rke2/server/token (스냅샷 복원에 필요)']
    b = p['bridge']
    if b and b['via']:
        out.append(f"RKE2 먼저 {b['via']}(etcd {b['via_etcd']}) 로 — 모든 서버 노드의 etcd 판과 멤버 목록을 확인한 뒤 다음 단계")
    out.append(f"RKE2 판 순서: {p['cur']} → {' → '.join(p['path'])} (단계마다 서버 노드 → 에이전트 노드)")
    nxt = p['path'][0]
    if p['plans']:
        out.append(f"system-upgrade-controller: server Plan 의 version 을 {nxt} 로(concurrency 1) → 서버 노드가 모두 끝난 뒤 agent Plan — "
                   f"Plan {len(p['plans'])}개: " + ', '.join(f"{x['name']}({x['version'] or x['channel'] or '판 없음'})" for x in p['plans'][:4]))
    else:
        out.append(f'업그레이드 단계 명령(노드마다, 비운 뒤): curl -sfL https://get.rke2.io | INSTALL_RKE2_VERSION={nxt} sh - → systemctl restart rke2-server (에이전트는 rke2-agent)')
    return out
