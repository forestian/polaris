"""받은 파이썬 패키지 검사 — PyPI 공식 해시 · 설치 파일 무결성 · OSV 악성/취약 DB · 올라온 날짜 · 설치 훅.

사용: python -I check_pkgs.py <dl_dir> name==ver ...
  dl_dir 에는 `pip download --no-deps --only-binary=:all:` 로 받은 휠이 있어야 한다(검사용 격리 폴더).
"""
import base64
import csv
import hashlib
import json
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
dl = Path(sys.argv[1])
pkgs = [a.split('==') for a in sys.argv[2:]]
UA = {'User-Agent': 'polaris-pkgcheck'}


def get_json(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={**UA, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


now = datetime.now(timezone.utc)
for name, ver in pkgs:
    print(f'\n== {name} {ver}')
    info = get_json(f'https://pypi.org/pypi/{name}/{ver}/json')
    files = {f['filename']: f for f in info['urls']}
    up = min(datetime.fromisoformat(f['upload_time_iso_8601'].replace('Z', '+00:00')) for f in info['urls'])
    print(f'  올라온 날: {up.date()} ({(now - up).days}일 전)  · 홈: {info["info"].get("home_page") or (info["info"].get("project_urls") or {}).get("Source") or (info["info"].get("project_urls") or {}).get("Homepage")}')
    print(f'  올린 사람(메타): {info["info"].get("author") or info["info"].get("maintainer")} · 받은 수 정보 없음')
    print(f'  yanked: {any(f.get("yanked") for f in info["urls"])}')
    # 1) 받은 휠 해시 == PyPI 공식 해시
    want = name.lower().replace('-', '_') + '-' + ver + '-'
    wheels = [p for p in dl.glob('*.whl') if p.name.lower().startswith(want)]
    if not wheels:
        print('  !! 검사용으로 받은 휠이 없음')
        continue
    w = wheels[0]
    h = hashlib.sha256(w.read_bytes()).hexdigest()
    pub = files.get(w.name, {}).get('digests', {}).get('sha256')
    print(f'  휠 {w.name}: sha256 {"PyPI 와 일치" if h == pub else "!! 불일치 — " + str(pub)}')
    # 2) 설치된 파일 == 휠 안의 파일 (RECORD 해시)
    with zipfile.ZipFile(w) as z:
        rec_name = next(n for n in z.namelist() if n.endswith('.dist-info/RECORD'))
        wheel_rec = {row[0]: row[1] for row in csv.reader(z.read(rec_name).decode().splitlines()) if row and row[1]}
        names = z.namelist()
    dist = metadata.distribution(name)
    bad = 0
    checked = 0
    for f in dist.files or []:
        key = str(f).replace('\\', '/')
        if key not in wheel_rec:
            continue
        p = Path(dist.locate_file(f))
        dg = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(p.read_bytes()).digest()).rstrip(b'=').decode()
        checked += 1
        if dg != wheel_rec[key]:
            bad += 1
            print(f'  !! 설치 파일이 휠과 다름: {key}')
    print(f'  설치 파일 {checked}개를 휠과 비교 — {"모두 같음" if not bad else f"{bad}개 다름"}')
    pth = [n for n in names if n.endswith('.pth')]
    print(f'  .pth(파이썬 시작 때 자동 실행되는 파일): {pth or "없음"}')
    # 3) OSV — 악성(MAL-) · 취약점
    osv = get_json('https://api.osv.dev/v1/query', {'package': {'name': name, 'ecosystem': 'PyPI'}, 'version': ver})
    vulns = [v['id'] for v in osv.get('vulns', [])]
    print(f'  OSV: {vulns or "등록된 악성 · 취약점 없음"}')
