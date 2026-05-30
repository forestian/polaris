"""클러스터 스냅샷 저장 / 목록 / 로드 / Diff.

운영 점검의 핵심 — 클러스터 상태를 시점별로 저장하고 두 시점을 비교해
"지난 점검 대비 무엇이 추가/삭제/변경됐고, 어떤 이슈가 새로 생겼거나 해결됐는지"
를 자동으로 보여준다.

스냅샷 데이터는 _report_collect() 가 수집한 dict 를 그대로 사용 (별도 수집 로직 없음).
저장 위치:
  ~/.polaris/snapshots/<cluster>_<timestamp>.enc   ← 암호화 (v1.2.1~, 기본)
  ~/.polaris/snapshots/<cluster>_<timestamp>.json  ← 평문 (구버전 / crypto 없음)

암호화(.enc): 민감한 클러스터 상태(data)는 vault DEK 로 AES-256-GCM 암호화되어
raw 파일로 열어도 내용을 알아볼 수 없다. meta(요약)만 평문으로 봉투에 남겨 목록을
빠르게 표시. vault 가 잠금 해제된 상태(앱 실행 중)에서만 load/diff 가능.

이 모듈은 순수 파일/딕셔너리 연산만 — kubernetes API 의존 없음 (테스트 용이).
vault 는 duck-typed 인자로 주입(encrypt_blob/decrypt_blob/is_unlocked) → 직접 의존 X.
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path

from src.paths import polaris_dir

SNAPSHOT_DIR = polaris_dir() / 'snapshots'

_ENC_FORMAT = 'polaris-snap-enc-v1'   # 암호화 봉투 포맷 식별자


def _enc_path(sid: str) -> Path:
    return SNAPSHOT_DIR / f'{sid}.enc'


def _json_path(sid: str) -> Path:
    return SNAPSHOT_DIR / f'{sid}.json'

# diff 대상 리소스 종류 — 각각 (kind 라벨, 데이터 키, 식별 키 함수)
# 식별 키: 같은 리소스인지 판단하는 기준 (보통 namespace/name)
_DIFF_KINDS = [
    ('Node',         'nodes',        ('name',)),
    ('Namespace',    'namespaces',   ('name',)),
    ('Deployment',   'deployments',  ('namespace', 'name')),
    ('StatefulSet',  'statefulsets', ('namespace', 'name')),
    ('DaemonSet',    'daemonsets',   ('namespace', 'name')),
    ('Service',      'services',     ('namespace', 'name')),
    ('Ingress',      'ingresses',    ('namespace', 'name')),
    ('PVC',          'pvcs',         ('namespace', 'name')),
    ('PV',           'pvs',          ('name',)),
    ('CronJob',      'cronjobs',     ('namespace', 'name')),
    ('ConfigMap',    'configmaps',   ('namespace', 'name')),
    ('Secret',       'secrets',      ('namespace', 'name')),
    ('Helm',         'helm',         ('namespace', 'name')),
]

# 변경 감지에서 무시할 필드 (매번 바뀌어 노이즈가 되는 것)
_IGNORE_FIELDS = {'age', '_ns', '_kind', 'collected_at'}


def _safe_name(s: str) -> str:
    """파일명 안전 문자열."""
    return re.sub(r'[^a-zA-Z0-9._-]', '-', str(s or 'cluster'))[:60]


def save_snapshot(data: dict, cluster: str, label: str = '',
                  now: datetime = None, vault=None) -> dict:
    """수집한 data dict 를 스냅샷으로 저장.

    vault 가 주입되고 잠금 해제 상태면 data 를 암호화해 .enc 로 저장한다.
    vault 가 있으나 잠겨 있으면 평문 저장을 거부(에러) — 암호화 누락 방지.
    vault 가 없으면(crypto 미사용 빌드) 평문 .json 으로 저장.

    now 는 테스트 주입용 (Date.now 회피). 기본은 datetime.now().
    반환: {ok, id, path, encrypted, meta} 또는 {ok: False, error}
    """
    try:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = (now or datetime.now())
        stamp = ts.strftime('%Y%m%d-%H%M%S')
        sid = f'{_safe_name(cluster)}_{stamp}'
        meta = {
            'id':           sid,
            'cluster':      cluster,
            'label':        label or '',
            'created_at':   ts.strftime('%Y-%m-%d %H:%M:%S'),
            'cluster_version': data.get('cluster_version', 'N/A'),
            'counts':       _summarize_counts(data),
        }

        if vault is not None:
            # crypto 사용 가능 → 반드시 암호화. 잠겨 있으면 거부.
            if not getattr(vault, 'is_unlocked', False):
                return {'ok': False,
                        'error': 'vault 가 잠겨 있어 스냅샷을 암호화할 수 없습니다.'}
            data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
            blob = vault.encrypt_blob(data_bytes)
            envelope = {'format': _ENC_FORMAT, 'meta': meta, 'enc_data': blob}
            path = _enc_path(sid)
            path.write_text(json.dumps(envelope, ensure_ascii=False, indent=1),
                            encoding='utf-8')
            return {'ok': True, 'id': sid, 'path': str(path),
                    'encrypted': True, 'meta': meta}

        # crypto 미사용 빌드 — 평문 저장 (하위 호환)
        payload = {'meta': meta, 'data': data}
        path = _json_path(sid)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                        encoding='utf-8')
        return {'ok': True, 'id': sid, 'path': str(path),
                'encrypted': False, 'meta': meta}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def _summarize_counts(data: dict) -> dict:
    """스냅샷 요약 카운트 (목록 화면용)."""
    out = {}
    for _, key, _ in _DIFF_KINDS:
        v = data.get(key)
        if isinstance(v, list):
            out[key] = len(v)
    out['pods'] = len(data.get('pods') or [])
    return out


def list_snapshots() -> list:
    """저장된 스냅샷 메타 목록 (최신순).

    meta 는 .enc / .json 모두 평문 봉투에 있으므로 vault 없이도 목록 표시 가능.
    동일 id 가 두 포맷으로 존재하면 .enc 우선.
    """
    out = []
    if not SNAPSHOT_DIR.exists():
        return out
    seen = set()
    # .enc 먼저(우선), 그다음 .json
    files = sorted(SNAPSHOT_DIR.glob('*.enc')) + sorted(SNAPSHOT_DIR.glob('*.json'))
    for f in files:
        try:
            obj = json.loads(f.read_text(encoding='utf-8'))
            meta = dict(obj.get('meta', {}))
            meta['id'] = meta.get('id') or f.stem
            if meta['id'] in seen:
                continue
            seen.add(meta['id'])
            meta['encrypted'] = (f.suffix == '.enc')
            out.append(meta)
        except Exception:
            continue
    out.sort(key=lambda m: m.get('created_at', ''), reverse=True)
    return out


def load_snapshot(sid: str, vault=None) -> dict:
    """스냅샷 전체(payload={meta, data}) 로드. 없거나 복호화 불가면 None.

    .enc 는 vault 가 잠금 해제돼 있어야 복호화 가능. .json 은 평문 로드.
    """
    safe = _safe_name(sid)
    enc = _enc_path(safe)
    if enc.exists():
        try:
            env = json.loads(enc.read_text(encoding='utf-8'))
            if vault is None or not getattr(vault, 'is_unlocked', False):
                return None   # 잠김 — 앱(vault 해제)을 통해서만 열림
            data_bytes = vault.decrypt_blob(env.get('enc_data'))
            data = json.loads(data_bytes.decode('utf-8'))
            return {'meta': env.get('meta', {}), 'data': data}
        except Exception:
            return None
    j = _json_path(safe)
    try:
        return json.loads(j.read_text(encoding='utf-8'))
    except Exception:
        return None


def delete_snapshot(sid: str) -> bool:
    """스냅샷 삭제 (.enc / .json 둘 다 시도)."""
    safe = _safe_name(sid)
    removed = False
    for p in (_enc_path(safe), _json_path(safe)):
        try:
            if p.exists():
                p.unlink()
                removed = True
        except Exception:
            pass
    return removed


def _index_by_key(items: list, key_fields: tuple) -> dict:
    """리스트를 식별 키 → item dict 로 인덱싱."""
    idx = {}
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        key = '/'.join(str(it.get(k, '')) for k in key_fields)
        idx[key] = it
    return idx


def _changed_fields(old: dict, new: dict) -> list:
    """두 item 간 바뀐 필드 목록. [{field, old, new}]"""
    diffs = []
    keys = (set(old) | set(new)) - _IGNORE_FIELDS
    for k in sorted(keys):
        ov, nv = old.get(k), new.get(k)
        # dict/list 는 JSON 문자열로 비교
        if isinstance(ov, (dict, list)) or isinstance(nv, (dict, list)):
            try:
                if json.dumps(ov, sort_keys=True) == json.dumps(nv, sort_keys=True):
                    continue
            except Exception:
                if ov == nv:
                    continue
        elif ov == nv:
            continue
        diffs.append({'field': k, 'old': _short(ov), 'new': _short(nv)})
    return diffs


def _short(v) -> str:
    if isinstance(v, (dict, list)):
        try:
            s = json.dumps(v, ensure_ascii=False)
        except Exception:
            s = str(v)
    else:
        s = str(v)
    return s if len(s) <= 120 else s[:117] + '...'


def diff_snapshots(payload_a: dict, payload_b: dict) -> dict:
    """두 스냅샷 비교. a=이전(기준), b=이후.

    반환: {
      meta_a, meta_b,
      kinds: [{kind, added:[], removed:[], changed:[{key, fields:[]}], same_count}],
      totals: {added, removed, changed},
      finding_delta: {new:[], resolved:[]},   # 이슈 변화
    }
    """
    data_a = (payload_a or {}).get('data', {}) or {}
    data_b = (payload_b or {}).get('data', {}) or {}

    kinds_out = []
    tot_add = tot_rem = tot_chg = 0

    for kind_label, key, key_fields in _DIFF_KINDS:
        idx_a = _index_by_key(data_a.get(key), key_fields)
        idx_b = _index_by_key(data_b.get(key), key_fields)
        keys_a, keys_b = set(idx_a), set(idx_b)

        added   = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        changed = []
        for k in sorted(keys_a & keys_b):
            fields = _changed_fields(idx_a[k], idx_b[k])
            if fields:
                changed.append({'key': k, 'fields': fields})

        if added or removed or changed:
            kinds_out.append({
                'kind':       kind_label,
                'added':      added,
                'removed':    removed,
                'changed':    changed,
                'same_count': len(keys_a & keys_b) - len(changed),
            })
            tot_add += len(added)
            tot_rem += len(removed)
            tot_chg += len(changed)

    return {
        'meta_a': (payload_a or {}).get('meta', {}),
        'meta_b': (payload_b or {}).get('meta', {}),
        'kinds':  kinds_out,
        'totals': {'added': tot_add, 'removed': tot_rem, 'changed': tot_chg},
    }


def diff_findings(findings_a: list, findings_b: list) -> dict:
    """두 시점의 진단 finding 비교 → 새로 생긴/해결된 이슈.

    finding 식별 키: category + namespace + name
    반환: {new: [...], resolved: [...], persisting_count}
    """
    def fkey(f):
        return f"{f.get('category','')}/{f.get('namespace','')}/{f.get('name','')}"

    idx_a = {fkey(f): f for f in (findings_a or [])}
    idx_b = {fkey(f): f for f in (findings_b or [])}
    keys_a, keys_b = set(idx_a), set(idx_b)

    new      = [idx_b[k] for k in sorted(keys_b - keys_a)]
    resolved = [idx_a[k] for k in sorted(keys_a - keys_b)]
    return {
        'new':              new,
        'resolved':         resolved,
        'persisting_count': len(keys_a & keys_b),
    }
