"""PyPI provenance(누가 어느 저장소에서 빌드해 올렸나) + 코드 안 수상한 동작 찾기."""
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
dl = Path(sys.argv[1])
UA = {'User-Agent': 'polaris-pkgcheck', 'Accept': 'application/vnd.pypi.integrity.v1+json'}


def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'_http': e.code}


SUS = [
    (r'\bexec\s*\(', 'exec('), (r'\beval\s*\(', 'eval('), (r'base64\.b64decode', 'base64 디코드'),
    (r'\bsubprocess\b', 'subprocess'), (r'os\.system|os\.popen', 'os.system/popen'),
    (r'\bsocket\.socket\b|\burllib\.request\b|\bhttp\.client\b', '직접 네트워크'),
    (r'marshal\.loads|zlib\.decompress\(.*b64', '숨긴 코드 풀기'), (r'__import__\(', '__import__('),
    (r'APPDATA|\.ssh[/\\]|Login Data|discord|wallet', '민감 경로 · 정보'),
]
for w in sorted(dl.glob('*.whl')):
    proj, ver = w.name.split('-')[:2]
    p = get(f'https://pypi.org/integrity/{proj}/{ver}/{w.name}/provenance')
    if '_http' in p:
        print(f'\n== {w.name}\n  provenance: 없음 (HTTP {p["_http"]}) — 신뢰 게시(Trusted Publishing)를 쓰지 않은 판')
    else:
        pubs = [b.get('publisher', {}) for b in p.get('attestation_bundles', [])]
        print(f'\n== {w.name}\n  provenance: ' + '; '.join(f'{x.get("kind")} {x.get("repository")} ({x.get("workflow")})' for x in pubs))
    meta = get(f'https://pypi.org/pypi/{proj}/{ver}/json')
    print('  project_urls:', (meta.get('info') or {}).get('project_urls'))
    hits = {}
    with zipfile.ZipFile(w) as z:
        for n in z.namelist():
            if not n.endswith('.py'):
                continue
            src = z.read(n).decode('utf-8', 'replace')
            for rx, label in SUS:
                for m in re.finditer(rx, src):
                    line = src[:m.start()].count('\n') + 1
                    hits.setdefault(label, []).append(f'{n}:{line}')
        bins = [n for n in z.namelist() if n.endswith(('.pyd', '.dll', '.so', '.exe'))]
    print('  컴파일된 파일:', bins or '없음')
    for k, v in hits.items():
        print(f'  [{k}] {len(v)}곳: {", ".join(v[:6])}{" …" if len(v) > 6 else ""}')
    if not hits:
        print('  수상한 패턴: 없음')
