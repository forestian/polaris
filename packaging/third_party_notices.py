# -*- coding: utf-8 -*-
"""오픈소스 고지 파일(THIRD_PARTY_NOTICES.txt) 생성 — build.py 가 PyInstaller 직후에 부른다(v1.4.19).

**실제로 번들에 들어간 것만** 적는다:
  · Python 패키지 — PyInstaller 의 PYZ 목록(build/Polaris/PYZ-00.toc) + _internal 폴더에 놓인 것
  · Python 런타임 — 설치 폴더의 LICENSE.txt (OpenSSL · libffi · SQLite 등 Python 이 함께 싣는 것 포함)
  · 화면(ui) · 설치 프로그램(setup-tauri) 의 npm 실행 의존성 — devDependencies 는 배포되지 않아 뺀다
  · 설치 프로그램의 Rust 크레이트 — Cargo.lock 중 이 PC 레지스트리에 실제로 받아진 것(=Windows 빌드에 쓰인 것)
  · 로컬 셸(Cygwin · BusyBox) — 번들 폴더의 MANIFEST.json 이 있으면
라이선스 전문은 같은 글이면 한 번만 싣고, 어떤 구성 요소가 그 글을 쓰는지 적는다.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import os
import re
import sys
from pathlib import Path

# LGPL — 사용자가 바꿔 끼울 수 있도록 실행 파일 밖에 일반 .py 로 둔다(Polaris.spec module_collection_mode)
LGPL_REPLACEABLE = ('pystray',)

_LIC_NAME = re.compile(r'^(LICEN[CS]E|COPYING|NOTICE|UNLICENSE|COPYRIGHT)', re.I)

# 패키지 메타데이터에 없는 번들 바이너리 — 출처와 라이선스를 직접 적는다
STATIC = [
    {'group': 'Native components', 'name': 'Microsoft WebView2 SDK (Microsoft.Web.WebView2.Core/WinForms.dll, WebView2Loader.dll)',
     'version': '', 'license': 'Microsoft WebView2 SDK license',
     'url': 'https://www.nuget.org/packages/Microsoft.Web.WebView2',
     'text': 'Copyright (C) Microsoft Corporation. Redistributed with pywebview under the terms of the '
             'Microsoft WebView2 SDK license (https://www.nuget.org/packages/Microsoft.Web.WebView2/License).'},
]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding='utf-8', errors='replace').strip()
    except OSError:
        return ''


# ── Python ──────────────────────────────────────────────────────────────────
def bundled_top_names(appdir: Path, toc: Path | None) -> set[str]:
    names = set()
    if toc and toc.is_file():
        for m in re.findall(r"\('([A-Za-z0-9_\.]+)',", _read(toc)):
            names.add(m.split('.')[0])
    internal = appdir / '_internal'
    if internal.is_dir():
        for n in os.listdir(internal):
            if n.endswith(('.dist-info', '.egg-info')):
                continue
            names.add(n.split('.')[0])
    return names


def python_components(appdir: Path, toc: Path | None) -> list[dict]:
    pd = md.packages_distributions()
    dists = {}
    for top in bundled_top_names(appdir, toc):
        for d in pd.get(top, []):
            dists.setdefault(d.lower(), d)
    dists.setdefault('pyinstaller', 'pyinstaller')      # 실행 파일의 부트로더(GPL + 예외 조항)
    out = []
    for key in sorted(dists):
        try:
            dist = md.distribution(dists[key])
        except md.PackageNotFoundError:
            continue
        m = dist.metadata
        lic = (m.get('License-Expression') or '').strip()
        if not lic:
            raw = (m.get('License') or '').strip()
            lic = raw.splitlines()[0][:80] if raw and len(raw) < 200 else ''
        if not lic:
            cls = [c.split('::')[-1].strip() for c in (m.get_all('Classifier') or []) if c.startswith('License ::')]
            lic = ' / '.join(cls)
        url = m.get('Home-page') or ''
        for pu in m.get_all('Project-URL') or []:
            if not url and ',' in pu:
                url = pu.split(',', 1)[1].strip()
        texts = []
        for f in dist.files or []:
            if _LIC_NAME.match(Path(str(f)).name) and '.dist-info' in str(f):
                t = _read(Path(dist.locate_file(f)))
                if t:
                    texts.append(t)
        if not texts:
            raw = (m.get('License') or '').strip()
            if len(raw) >= 200:
                texts.append(raw)
        name = m.get('Name') or dists[key]
        note = ''
        if name.lower() in LGPL_REPLACEABLE:
            note = (f'Installed as plain source files under _internal\\{name.lower()}\\ so that it can be '
                    f'replaced with a modified version. Source: https://pypi.org/project/{name}/{dist.version}/')
        if name.lower() == 'pyinstaller':
            name = 'PyInstaller bootloader'
        authors = m.get('Author') or re.sub(r'\s*<[^>]*>', '', m.get('Author-email') or '')
        out.append({'group': 'Python packages', 'name': name, 'version': dist.version,
                    'license': lic or 'see license text', 'url': url, 'texts': list(dict.fromkeys(texts)),
                    'note': note, 'authors': authors})
    return out


def python_runtime() -> dict:
    p = Path(sys.base_prefix) / 'LICENSE.txt'
    v = '.'.join(map(str, sys.version_info[:3]))
    return {'group': 'Python runtime', 'name': 'Python (with OpenSSL, libffi, SQLite and other bundled libraries)',
            'version': v, 'license': 'PSF-2.0 and others (see text)', 'url': 'https://www.python.org/',
            'texts': [_read(p)] if p.is_file() else []}


# ── npm ─────────────────────────────────────────────────────────────────────
def npm_components(project: Path, group: str) -> list[dict]:
    pkg = json.loads(_read(project / 'package.json') or '{}')
    seen: dict[str, dict] = {}

    def find(name: str, start: Path) -> Path | None:
        d = start
        while True:
            p = d / 'node_modules' / name / 'package.json'
            if p.is_file():
                return p
            if d == project or d.parent == d:
                return None
            d = d.parent

    def walk(name: str, start: Path):
        p = find(name, start)
        if not p or str(p) in seen:
            return
        j = json.loads(_read(p) or '{}')
        lic = j.get('license') or ''
        if isinstance(lic, dict):
            lic = lic.get('type', '')
        if not lic and isinstance(j.get('licenses'), list):
            lic = ' OR '.join(x.get('type', '') if isinstance(x, dict) else str(x) for x in j['licenses'])
        texts = [_read(f) for f in sorted(p.parent.iterdir()) if f.is_file() and _LIC_NAME.match(f.name)]
        repo = j.get('repository')
        url = j.get('homepage') or (repo.get('url') if isinstance(repo, dict) else repo) or ''
        seen[str(p)] = {'group': group, 'name': j.get('name', name), 'version': j.get('version', ''),
                        'license': lic or 'see license text', 'url': url, 'texts': [t for t in texts if t]}
        for dep in (j.get('dependencies') or {}):
            walk(dep, p.parent)

    for dep in (pkg.get('dependencies') or {}):
        walk(dep, project)
    return sorted(seen.values(), key=lambda c: c['name'].lower())


# ── Rust ────────────────────────────────────────────────────────────────────
def rust_components(lock: Path, registry: Path | None = None) -> list[dict]:
    registry = registry or Path(os.path.expanduser('~')) / '.cargo' / 'registry' / 'src'
    if not lock.is_file() or not registry.is_dir():
        return []
    dirs = {}
    for idx in registry.iterdir():
        if idx.is_dir():
            for d in idx.iterdir():
                dirs.setdefault(d.name, d)
    out = []
    for name, ver in re.findall(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"\nsource = "registry',
                                _read(lock).replace('\r\n', '\n')):
        d = dirs.get(f'{name}-{ver}')
        if not d:
            continue                            # 다른 OS 전용 — Windows 빌드에 들어가지 않았다
        toml = _read(d / 'Cargo.toml')
        m = re.search(r'^license\s*=\s*"([^"]+)"', toml, re.M)
        u = re.search(r'^repository\s*=\s*"([^"]+)"', toml, re.M)
        a = re.search(r'^authors\s*=\s*\[([^\]]*)\]', toml, re.M)
        authors = ', '.join(re.sub(r'\s*<[^>]*>', '', x) for x in re.findall(r'"([^"]+)"', a.group(1))) if a else ''
        texts = [_read(f) for f in sorted(d.iterdir()) if f.is_file() and _LIC_NAME.match(f.name)]
        out.append({'group': 'Installer (Rust crates)', 'name': name, 'version': ver,
                    'license': m.group(1) if m else 'see license text', 'url': u.group(1) if u else '',
                    'texts': [t for t in texts if t], 'authors': authors})
    return out


# ── 로컬 셸(Cygwin · BusyBox) ────────────────────────────────────────────────
def manifest_components(manifest: Path) -> list[dict]:
    """번들 폴더의 MANIFEST.json — [{name, version, license, url, source, license_files:[상대 경로]}]"""
    if not manifest.is_file():
        return []
    data = json.loads(_read(manifest) or '{}')
    out = []
    for c in data.get('components', []):
        texts = [_read(manifest.parent / f) for f in c.get('license_files', [])]
        out.append({'group': data.get('group', 'Bundled programs'), 'name': c['name'], 'version': c.get('version', ''),
                    'license': c.get('license', ''), 'url': c.get('url', ''), 'texts': [t for t in texts if t],
                    'note': c.get('note', '')})
    return out


# ── 전문이 없는 것 — 표준 전문 + 메타데이터의 저작자 ───────────────────────────────
def _canonical(comps: list[dict]) -> dict[str, str]:
    """다른 구성 요소가 실은 표준 전문에서 본문을 얻는다(외워 적지 않는다)"""
    allt = [t for c in comps for t in c.get('texts') or []]

    def pick(pred, cut=None):
        cands = [t for t in allt if pred(t)]
        if not cands:
            return ''
        t = max(cands, key=lambda x: (cands.count(x), -len(x)))
        if cut and cut in t:
            t = t[t.index(cut):]
        return t

    return {
        'Apache-2.0': pick(lambda t: t.lstrip().startswith('Apache License') and 'Version 2.0, January 2004' in t
                           and 'END OF TERMS AND CONDITIONS' in t),
        'MPL-2.0': pick(lambda t: t.lstrip().startswith('Mozilla Public License Version 2.0')),
        'MIT': pick(lambda t: 'Permission is hereby granted, free of charge' in t and len(t) < 1400,
                    'Permission is hereby granted'),
        'BSD-3-Clause': pick(lambda t: 'Redistribution and use in source and binary forms' in t
                             and 'Neither the name' in t and len(t) < 2000, 'Redistribution and use'),
    }


def fill_missing(comps: list[dict]) -> None:
    canon = _canonical(comps)
    for c in comps:
        if c.get('texts') or c.get('text'):
            continue
        ids = [x for x in re.split(r'\s*(?:\bOR\b|\bAND\b|/|\(|\))\s*', c.get('license') or '') if x]
        ids = ['MIT' if x.upper().startswith('MIT') else x for x in ids]
        who = (c.get('authors') or '').strip('"\' ') or f"the {c['name']} authors"
        parts = []
        for x in dict.fromkeys(ids):
            body = canon.get(x)
            if not body:
                continue
            if x in ('MIT', 'BSD-3-Clause'):
                body = f'{x} License\n\nCopyright (c) {who}\n\n{body}'
            parts.append(body)
        if parts:
            c['texts'] = ['\n\n'.join(parts)]
            c['note'] = ((c.get('note') or '') + ' (The package ships no license file; standard text with '
                         'the copyright holder from its metadata.)').strip()


# ── 쓰기 ────────────────────────────────────────────────────────────────────
HEADER = """Polaris {version} — 오픈소스 고지 (Third-Party Notices)
=====================================================================

Polaris 에는 아래 오픈소스 구성 요소가 함께 들어 있습니다. 각 구성 요소는 해당 라이선스를 따르며,
Polaris 자체의 저작권 · 라이선스와는 별개입니다.

This product includes the open source components listed below. Each component is
licensed under its own terms, reproduced in section 2.

LGPL 구성 요소 (pystray)
  실행 파일에 묶지 않고 _internal\\pystray\\ 에 일반 소스 파일(.py)로 설치됩니다.
  고친 버전으로 바꿔 넣어 쓸 수 있습니다. This LGPL library is installed as plain source
  files under _internal\\ and may be replaced with a modified version.
{extra}
"""


def render(version: str, comps: list[dict], extra: str = '') -> str:
    lines = [HEADER.format(version=version, extra=extra), '', '1. 구성 요소 목록 (Components)', '-' * 69]
    texts: dict[str, tuple[int, str, list[str]]] = {}
    for c in comps:
        for t in c.get('texts') or []:
            h = hashlib.sha1(t.encode('utf-8')).hexdigest()
            if h not in texts:
                texts[h] = (len(texts) + 1, t, [])
            texts[h][2].append(f"{c['name']} {c['version']}".strip())
    group = None
    for c in comps:
        if c['group'] != group:
            group = c['group']
            lines += ['', f'[{group}]']
        refs = sorted({texts[hashlib.sha1(t.encode('utf-8')).hexdigest()][0] for t in c.get('texts') or []})
        ref = (' — license text ' + ', '.join(f'#{r}' for r in refs)) if refs else ''
        lines.append(f"  {c['name']} {c['version']}  ({c['license']}){ref}")
        if c.get('url'):
            lines.append(f"      {c['url']}")
        if c.get('note'):
            lines.append(f"      {c['note']}")
        if not refs and c.get('text'):
            lines.append(f"      {c['text']}")
    lines += ['', '', '2. 라이선스 전문 (License texts)', '-' * 69]
    for n, t, users in sorted(texts.values()):
        lines += ['', f'=== #{n} — used by: {", ".join(users)}', '', t, '']
    return '\n'.join(lines).replace('\r\n', '\n') + '\n'


def collect(root: Path, appdir: Path) -> list[dict]:
    comps = python_components(appdir, root / 'build' / 'Polaris' / 'PYZ-00.toc')
    comps.append(python_runtime())
    comps += STATIC
    comps += npm_components(root / 'ui', 'User interface (npm)')
    comps += npm_components(root / 'packaging' / 'setup-tauri', 'Installer UI (npm)')
    comps += rust_components(root / 'packaging' / 'setup-tauri' / 'src-tauri' / 'Cargo.lock')
    fill_missing(comps)
    return comps


def write(root: Path, appdir: Path, version: str, extra: str = '') -> tuple[Path, list[dict]]:
    comps = collect(root, appdir)
    out = appdir / 'THIRD_PARTY_NOTICES.txt'
    out.write_text(render(version, comps, extra), encoding='utf-8')
    return out, comps


def missing_texts(comps: list[dict]) -> list[str]:
    """라이선스 전문을 찾지 못한 것 — 고지 문구(text)라도 있으면 통과"""
    return [f"{c['group']}: {c['name']} {c['version']}" for c in comps if not c.get('texts') and not c.get('text')]
