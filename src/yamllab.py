"""YAML 실험실 — 테스트 매니페스트 저장소 + 순수 판정 함수.

기존 흐름(노드에 접속 → vi → kubectl apply)의 문제는 파일이 어느 노드에 남았는지 추적이 안 되고
"몇 번째 시도가 잘 됐는지"가 기록되지 않는다는 것이다. 여기서 붙여넣기·저장·버전 이력·
반출까지 처리한다.

────────────────────────────────────────────────────────────────────────────
저장소를 SQLite 로 한 이유 (MongoDB 를 쓰지 않은 이유)
────────────────────────────────────────────────────────────────────────────
Polaris 는 단일 exe 데스크톱 앱이다. 서버형 DB 를 끌어들이면 설치가 깨지고, 특히
**클러스터 안에 DB 를 두면 클러스터가 죽었을 때 저장해둔 YAML 을 못 본다** — 고치는
도구로서 자기모순이다. 데이터도 건당 KB · 수백 건 · 단일 사용자 · 매번 같은 모양이라
문서 DB 의 강점이 걸리지 않는다.

sqlite3 는 표준 라이브러리이고(추가 의존성 0, 설치기 증가 0, spec 등록 불필요),
번들 SQLite 3.49 는 JSON·FTS5·WAL 을 전부 지원한다. FTS5 로 저장해둔 YAML 전문 검색까지
공짜로 얻는다.

────────────────────────────────────────────────────────────────────────────
GitLab 자동 승격을 하지 않는 이유
────────────────────────────────────────────────────────────────────────────
클러스터마다 GitLab 서버도 프로젝트도 다르다. 승격 대상이 하나로 정해지지 않고, 자동화
하려면 클러스터별 인증을 전부 받아야 해서 규모가 폭발한다. 그래서 여기서는 **선택분을
복사/폴더로 내보내기**까지만 하고 형상관리 반영은 사용자가 수동으로 한다. 내보낸 결과는
그대로 `git add` 가능한 평범한 파일 트리다.

순수/부작용 분리는 netscan(v1.2.121) 과 같은 구조 — 판정은 순수 함수, I/O 는 호출자.
"""
import difflib
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.paths import polaris_dir
# diff 계산은 스냅샷 쪽 헬퍼를 그대로 쓴다 — 같은 규칙으로 판정해야 화면 간 결과가 어긋나지 않음.
from src.snapshot import _index_by_key, _changed_fields

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

LAB_DIRNAME = 'yaml-lab'
DB_FILENAME = 'lab.db'

# 적용 후 '파급'을 관찰할 kind. src/snapshot.py 의 _DIFF_KINDS 를 쓰지 않는 이유:
# 거기엔 Pod·ReplicaSet 이 없어서 Deployment 적용 시 가장 보고 싶은 변화(새 RS, 뜨는 Pod)가
# 정확히 빠진다. 전부 namespace 한정 조회라 전역 수집보다 훨씬 싸다.
LAB_KINDS = [
    ('Deployment',  'deployments',  ('namespace', 'name')),
    ('StatefulSet', 'statefulsets', ('namespace', 'name')),
    ('DaemonSet',   'daemonsets',   ('namespace', 'name')),
    ('ReplicaSet',  'replicasets',  ('namespace', 'name')),
    ('Pod',         'pods',         ('namespace', 'name')),
    ('Service',     'services',     ('namespace', 'name')),
    ('Ingress',     'ingresses',    ('namespace', 'name')),
    ('ConfigMap',   'configmaps',   ('namespace', 'name')),
    ('Job',         'jobs',         ('namespace', 'name')),
]

# 평문 비밀 경고용 키 패턴. 저장을 **막지는 않는다**(사용자 결정) — 알려만 준다.
#
# 단어 경계(\b)를 쓰지 않는다: 실제 매니페스트의 키는 `DB_PASSWORD`·`apiToken` 처럼
# 합성어라 \b 를 걸면 정작 잡아야 할 것을 전부 놓친다(밑줄·대문자 전환은 경계가 아님).
_SECRET_KEY_RE = re.compile(
    r'(pass(?:word|wd)|token|secret|api[_-]?key|access[_-]?key|private[_-]?key|'
    r'client[_-]?secret|credential)', re.I)

# 위에 걸려도 **참조**일 뿐 값이 아닌 키 — Ingress 의 secretName, secretKeyRef 등.
# 경고하면 정상 사용법을 나무라는 꼴이라 노이즈만 된다.
# `key$` 는 넣지 않는다 — api_key·private_key 처럼 진짜 비밀인 키가 통째로 빠진다.
# secretKeyRef 는 `ref$` 로 이미 걸린다.
_SECRET_KEY_REF_RE = re.compile(r'(name|ref|path|file)$', re.I)

# 값이 이 모양이면 경고하지 않는다 — 참조/플레이스홀더라 실제 비밀이 아니다.
_SECRET_VALUE_SAFE = re.compile(
    r'^\s*(\{\{.*\}\}|\$\(.*\)|\$\{.*\}|<.*>|""|\'\'|null|~|\||>|'
    r'valueFrom|secretKeyRef|configMapKeyRef)\s*$', re.I)

_FILENAME_SAFE_RE = re.compile(r'[^A-Za-z0-9._-]+')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


# ═════════════════════════════════════════════════════════════════════════════
# 순수 함수 — 클러스터도 디스크도 필요 없음
# ═════════════════════════════════════════════════════════════════════════════

def parse_targets(yaml_text: str) -> list:
    """YAML 에서 적용 대상 목록 추출. 멀티 문서(`---`) 지원.

    반환: [{kind, namespace, name, api_version}]
    파싱 불가 문서는 조용히 건너뛴다 — 여기서 실패해도 kubectl dry-run 이 진짜 검증을 한다.
    namespace 미지정은 빈 문자열로 둔다(호출자가 현재 컨텍스트 기본값을 채움).
    """
    out = []
    try:
        import yaml as _yaml
    except Exception:
        return out
    try:
        docs = list(_yaml.safe_load_all(yaml_text or ''))
    except Exception:
        return out
    for d in docs:
        if not isinstance(d, dict):
            continue
        kind = str(d.get('kind') or '').strip()
        if not kind:
            continue
        meta = d.get('metadata') if isinstance(d.get('metadata'), dict) else {}
        out.append({
            'kind':        kind,
            'api_version': str(d.get('apiVersion') or '').strip(),
            'namespace':   str(meta.get('namespace') or '').strip(),
            'name':        str(meta.get('name') or '').strip(),
        })
    return out


def target_namespaces(targets: list, default_ns: str = 'default') -> list:
    """대상들이 건드리는 네임스페이스 집합 (파급 관찰 범위).

    클러스터 스코프 리소스(Namespace/PV/ClusterRole 등)는 namespace 가 비어 있는데,
    그 경우 default 를 넣지 않는다 — 엉뚱한 ns 를 관찰하게 된다.
    """
    _CLUSTER_SCOPED = {'namespace', 'node', 'persistentvolume', 'clusterrole',
                       'clusterrolebinding', 'storageclass', 'customresourcedefinition',
                       'priorityclass', 'ingressclass'}
    out = []
    for t in (targets or []):
        ns = (t.get('namespace') or '').strip()
        if not ns:
            if (t.get('kind') or '').lower() in _CLUSTER_SCOPED:
                continue
            ns = default_ns
        if ns not in out:
            out.append(ns)
    return out


def _is_secret_key(key: str) -> bool:
    """이 키 이름이 '비밀 값'을 담을 자리인가. 참조용 키(secretName 등)는 제외."""
    k = str(key or '')
    if not _SECRET_KEY_RE.search(k):
        return False
    return not _SECRET_KEY_REF_RE.search(k)


def scan_secrets(yaml_text: str) -> list:
    """평문 비밀로 보이는 줄 찾기. 저장을 막지 않고 경고만 한다.

    반환: [{line, key, hint}]  (line 은 1부터)

    두 가지 형태를 본다:
      1) 직접형 —  `apiToken: abc123`
      2) env 쌍형 — `- name: DB_PASSWORD` 다음 줄 `value: hunter2`
         컨테이너 env 는 대부분 이 형태라, 이걸 놓치면 사실상 아무것도 못 잡는다.

    오탐 방지:
      - `valueFrom`/`secretKeyRef` 참조는 올바른 사용법이므로 경고하지 않는다.
      - `{{ }}`·`${ }`·`<...>` 같은 플레이스홀더도 제외.
      - base64 인 `kind: Secret` 의 data 블록은 통째로 건너뛴다 — Secret 적용 자체를
        apply_resource_yaml 이 이미 차단하므로 여기서 또 경고하면 노이즈만 된다.
    """
    hits = []
    in_secret_data = False
    data_indent = 0
    pending = None          # (line_no, key) — env 쌍형에서 name 을 본 상태

    def _flag(line_no, key):
        hits.append({
            'line': line_no,
            'key':  key,
            'hint': '평문 값으로 보입니다 — Secret 참조(valueFrom.secretKeyRef)를 권장합니다.',
        })

    for i, raw in enumerate((yaml_text or '').splitlines(), start=1):
        line = raw.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Secret 의 data:/stringData: 블록 진입·이탈 추적
        if re.match(r'^(data|stringData)\s*:\s*$', stripped):
            in_secret_data, data_indent, pending = True, indent, None
            continue
        if in_secret_data and indent <= data_indent:
            in_secret_data = False
        if in_secret_data:
            continue

        # ① env 쌍형 —  `- name: DB_PASSWORD`
        m_name = re.match(r'^\s*-?\s*name\s*:\s*["\']?([A-Za-z0-9_.-]+)["\']?\s*$', line)
        if m_name:
            pending = (i, m_name.group(1)) if _is_secret_key(m_name.group(1)) else None
            continue

        # ②    그 다음의 `value: hunter2`  (valueFrom 은 여기 안 걸린다)
        m_val = re.match(r'^\s*value\s*:\s*(.*)$', line)
        if m_val:
            v = m_val.group(1).strip()
            if pending and v and not _SECRET_VALUE_SAFE.match(v):
                _flag(pending[0], pending[1])
            pending = None
            continue
        pending = None   # name 과 value 사이에 다른 게 끼면 쌍이 아니다

        # ③ 직접형 — `apiToken: abc123`
        m = re.match(r'^\s*-?\s*["\']?([A-Za-z0-9_.-]+)["\']?\s*:\s*(.*)$', line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if not _is_secret_key(key):
            continue
        if not value or _SECRET_VALUE_SAFE.match(value):
            continue
        _flag(i, key)
    return hits


def version_diff(text_a: str, text_b: str,
                 label_a: str = '이전', label_b: str = '현재') -> str:
    """두 버전의 unified diff 문자열."""
    a = (text_a or '').splitlines(keepends=True)
    b = (text_b or '').splitlines(keepends=True)
    return ''.join(difflib.unified_diff(a, b, fromfile=label_a, tofile=label_b, n=3))


def scope_diff(before: dict, after: dict) -> dict:
    """범위 한정 수집 두 개를 비교 → 적용으로 실제 무엇이 바뀌었는지.

    before/after 는 {kind_key: [item, ...]} 모양. src/snapshot.py 의 인덱싱·필드비교
    헬퍼를 그대로 재사용하므로 스냅샷 화면과 판정 규칙이 어긋나지 않는다.

    반환: {kinds: [{kind, added, removed, changed, same_count}], totals: {...}}
    """
    before = before or {}
    after = after or {}
    kinds_out, tot_add, tot_rem, tot_chg = [], 0, 0, 0

    for kind_label, key, key_fields in LAB_KINDS:
        idx_a = _index_by_key(before.get(key), key_fields)
        idx_b = _index_by_key(after.get(key), key_fields)
        keys_a, keys_b = set(idx_a), set(idx_b)

        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        changed = []
        for k in sorted(keys_a & keys_b):
            fields = _changed_fields(idx_a[k], idx_b[k])
            if fields:
                changed.append({'key': k, 'fields': fields})

        if added or removed or changed:
            kinds_out.append({
                'kind': kind_label, 'added': added, 'removed': removed,
                'changed': changed,
                'same_count': len(keys_a & keys_b) - len(changed),
            })
            tot_add += len(added)
            tot_rem += len(removed)
            tot_chg += len(changed)

    return {
        'kinds': kinds_out,
        'totals': {'added': tot_add, 'removed': tot_rem, 'changed': tot_chg},
    }


def safe_filename(name: str, fallback: str = 'manifest') -> str:
    """임의 문자열 → 파일명 안전 문자열.

    경로 구분자·`..` 를 전부 제거한다. 내보내기가 **선택한 폴더 밖에 쓰는 사고**를 막는
    1차 방어선이다(2차는 plan_export 의 중복 해소).
    """
    s = _FILENAME_SAFE_RE.sub('-', str(name or '')).strip('-. ')
    s = s.replace('..', '-')
    return s[:80] or fallback


def plan_export(items: list, by_cluster: bool = True) -> list:
    """내보낼 파일 트리 계획. **디스크를 건드리지 않는 순수 함수.**

    items: [{name, cluster, content}]
    반환:  [{rel_path, content}]  — rel_path 는 항상 선택 폴더 기준 상대 경로

    순수 함수로 뺀 이유: 파일명 충돌과 경로 정규화는 조용히 남의 파일을 덮어쓰는 사고로
    이어지기 쉬운데, 디스크 없이 테스트로 잠글 수 있다.

    - 같은 이름이 겹치면 `-2`, `-3` 을 붙인다 (덮어쓰지 않는다)
    - by_cluster 면 `<cluster>/<name>.yaml`, 아니면 `<name>.yaml`
    """
    used = set()
    out = []
    for it in (items or []):
        base = safe_filename((it or {}).get('name'))
        folder = safe_filename((it or {}).get('cluster'), fallback='cluster') if by_cluster else ''

        candidate = f'{base}.yaml'
        rel = f'{folder}/{candidate}' if folder else candidate
        n = 2
        while rel.lower() in used:
            candidate = f'{base}-{n}.yaml'
            rel = f'{folder}/{candidate}' if folder else candidate
            n += 1
        used.add(rel.lower())

        content = (it or {}).get('content') or ''
        if not content.endswith('\n'):
            content += '\n'
        out.append({'rel_path': rel, 'content': content})
    return out


def join_documents(items: list) -> str:
    """선택분을 하나의 멀티 문서 YAML 로 이어붙이기 (클립보드 복사용).

    각 문서 앞에 어떤 매니페스트인지 주석을 남긴다 — 붙여넣은 쪽에서 출처를 알 수 있게.
    """
    parts = []
    for it in (items or []):
        name = (it or {}).get('name') or 'manifest'
        cluster = (it or {}).get('cluster') or ''
        body = ((it or {}).get('content') or '').strip('\n')
        head = f'# {name}' + (f'  (tested on: {cluster})' if cluster else '')
        parts.append(f'{head}\n{body}')
    return '\n---\n'.join(parts) + ('\n' if parts else '')


# ═════════════════════════════════════════════════════════════════════════════
# 저장소 (SQLite)
# ═════════════════════════════════════════════════════════════════════════════

_SCHEMA = """
CREATE TABLE IF NOT EXISTS manifests (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    cluster    TEXT    NOT NULL DEFAULT '',
    namespace  TEXT    NOT NULL DEFAULT '',
    tags       TEXT    NOT NULL DEFAULT '',
    notes      TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    manifest_id INTEGER NOT NULL REFERENCES manifests(id) ON DELETE CASCADE,
    version_no  INTEGER NOT NULL,
    content     TEXT    NOT NULL,
    sha256      TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    UNIQUE(manifest_id, version_no)
);
CREATE TABLE IF NOT EXISTS applies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
    cluster    TEXT    NOT NULL DEFAULT '',
    applied_at TEXT    NOT NULL,
    ok         INTEGER NOT NULL DEFAULT 0,
    output     TEXT    NOT NULL DEFAULT '',
    diff_json  TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_versions_manifest ON versions(manifest_id);
CREATE INDEX IF NOT EXISTS idx_applies_version   ON applies(version_id);
CREATE VIRTUAL TABLE IF NOT EXISTS versions_fts
    USING fts5(content, content='versions', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS versions_ai AFTER INSERT ON versions BEGIN
    INSERT INTO versions_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS versions_ad AFTER DELETE ON versions BEGIN
    INSERT INTO versions_fts(versions_fts, rowid, content)
        VALUES ('delete', old.id, old.content);
END;
"""


def lab_dir() -> Path:
    return polaris_dir() / LAB_DIRNAME


def open_db(path=None) -> sqlite3.Connection:
    """DB 연결 + 스키마 보장. path 미지정 시 실제 데이터 디렉터리(테스트는 주입).

    WAL 로 두어 조회 중 저장이 막히지 않게 한다. foreign_keys 는 연결마다 켜야
    ON DELETE CASCADE 가 동작한다(SQLite 기본값 OFF).
    """
    if path is None:
        d = lab_dir()
        d.mkdir(parents=True, exist_ok=True)
        try:
            from src import winsec
            winsec.harden_dir(d)
        except Exception:
            pass   # ACL 실패는 치명적이지 않음 — 부모(~/.polaris-free)가 이미 조여져 있다
        path = d / DB_FILENAME
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        conn.execute('PRAGMA journal_mode = WAL')
    except Exception:
        pass
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def list_manifests(conn, query: str = '') -> list:
    """목록. query 가 있으면 이름/태그 + **본문 전문검색(FTS5)** 까지 훑는다."""
    q = (query or '').strip()
    if not q:
        rows = conn.execute("""
            SELECT m.*, (SELECT COUNT(*) FROM versions v WHERE v.manifest_id = m.id) AS versions
            FROM manifests m ORDER BY m.updated_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

    like = f'%{q}%'
    ids = {r['id'] for r in conn.execute(
        'SELECT id FROM manifests WHERE name LIKE ? OR tags LIKE ? OR notes LIKE ?',
        (like, like, like)).fetchall()}
    try:
        # FTS5 특수문자(따옴표 등)가 들어오면 구문 오류 → 통째로 인용해 리터럴 취급
        fts_q = '"' + q.replace('"', '""') + '"'
        ids |= {r['manifest_id'] for r in conn.execute("""
            SELECT DISTINCT v.manifest_id FROM versions_fts f
            JOIN versions v ON v.id = f.rowid WHERE versions_fts MATCH ?
        """, (fts_q,)).fetchall()}
    except Exception:
        pass
    if not ids:
        return []
    marks = ','.join('?' * len(ids))
    rows = conn.execute(f"""
        SELECT m.*, (SELECT COUNT(*) FROM versions v WHERE v.manifest_id = m.id) AS versions
        FROM manifests m WHERE m.id IN ({marks}) ORDER BY m.updated_at DESC
    """, tuple(ids)).fetchall()
    return [dict(r) for r in rows]


def get_manifest(conn, mid) -> dict:
    """본문(최신 버전) + 버전 이력 + 적용 이력."""
    row = conn.execute('SELECT * FROM manifests WHERE id = ?', (mid,)).fetchone()
    if not row:
        return {}
    out = dict(row)
    vrows = conn.execute(
        'SELECT id, version_no, sha256, created_at, content FROM versions '
        'WHERE manifest_id = ? ORDER BY version_no DESC', (mid,)).fetchall()
    versions = [dict(v) for v in vrows]
    out['versions'] = [{k: v[k] for k in ('id', 'version_no', 'sha256', 'created_at')}
                       for v in versions]
    out['content'] = versions[0]['content'] if versions else ''
    out['current_version_id'] = versions[0]['id'] if versions else None
    arows = conn.execute("""
        SELECT a.id, a.cluster, a.applied_at, a.ok, a.output, v.version_no
        FROM applies a JOIN versions v ON v.id = a.version_id
        WHERE v.manifest_id = ? ORDER BY a.applied_at DESC LIMIT 20
    """, (mid,)).fetchall()
    out['applies'] = [dict(a) for a in arows]
    return out


def get_version_content(conn, version_id) -> str:
    row = conn.execute('SELECT content FROM versions WHERE id = ?', (version_id,)).fetchone()
    return row['content'] if row else ''


def save_manifest(conn, mid, name: str, content: str, cluster: str = '',
                  tags: str = '', notes: str = '') -> dict:
    """신규 생성 또는 **새 버전 추가**. 덮어쓰지 않는다.

    본문이 직전 버전과 동일하면 새 버전을 만들지 않는다 — 저장 버튼 연타로 이력이
    쓰레기로 차는 걸 막는다(메타데이터만 갱신).
    """
    name = (name or '').strip() or '이름없음'
    content = content or ''
    now = _now()
    sha = hashlib.sha256(content.encode('utf-8')).hexdigest()
    targets = parse_targets(content)
    namespace = next((t['namespace'] for t in targets if t.get('namespace')), '')

    if mid:
        cur = conn.execute('SELECT id FROM manifests WHERE id = ?', (mid,)).fetchone()
        if not cur:
            return {'ok': False, 'error': '대상을 찾을 수 없습니다.'}
        conn.execute(
            'UPDATE manifests SET name=?, cluster=?, namespace=?, tags=?, notes=?, updated_at=? '
            'WHERE id=?',
            (name, cluster, namespace, tags, notes, now, mid))
    else:
        cur = conn.execute(
            'INSERT INTO manifests (name, cluster, namespace, tags, notes, created_at, updated_at) '
            'VALUES (?,?,?,?,?,?,?)',
            (name, cluster, namespace, tags, notes, now, now))
        mid = cur.lastrowid

    last = conn.execute(
        'SELECT version_no, sha256 FROM versions WHERE manifest_id=? '
        'ORDER BY version_no DESC LIMIT 1', (mid,)).fetchone()
    new_version = False
    if last is None or last['sha256'] != sha:
        next_no = (last['version_no'] + 1) if last else 1
        conn.execute(
            'INSERT INTO versions (manifest_id, version_no, content, sha256, created_at) '
            'VALUES (?,?,?,?,?)', (mid, next_no, content, sha, now))
        new_version = True
    conn.commit()
    return {'ok': True, 'id': mid, 'new_version': new_version,
            'warnings': scan_secrets(content)}


def delete_manifest(conn, mid) -> bool:
    cur = conn.execute('DELETE FROM manifests WHERE id = ?', (mid,))
    conn.commit()
    return cur.rowcount > 0


def record_apply(conn, version_id, cluster: str, ok: bool,
                 output: str = '', diff: dict = None) -> None:
    conn.execute(
        'INSERT INTO applies (version_id, cluster, applied_at, ok, output, diff_json) '
        'VALUES (?,?,?,?,?,?)',
        (version_id, cluster or '', _now(), 1 if ok else 0, (output or '')[:4000],
         json.dumps(diff or {}, ensure_ascii=False)))
    conn.commit()


def export_items(conn, ids: list) -> list:
    """내보낼 항목들의 {name, cluster, content} — 항상 **최신 버전**.

    ids 순서가 아니라 목록 순서(updated_at DESC)를 따른다 — 화면에서 본 순서와 같게.
    """
    if not ids:
        return []
    marks = ','.join('?' * len(ids))
    rows = conn.execute(f"""
        SELECT m.id, m.name, m.cluster,
               (SELECT v.content FROM versions v WHERE v.manifest_id = m.id
                ORDER BY v.version_no DESC LIMIT 1) AS content
        FROM manifests m WHERE m.id IN ({marks}) ORDER BY m.updated_at DESC
    """, tuple(ids)).fetchall()
    return [dict(r) for r in rows]
