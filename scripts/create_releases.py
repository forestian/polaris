#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab 릴리스 생성 스크립트
CHANGELOG.md를 파싱하여 누락된 버전의 릴리스를 생성합니다.

사용:
  $env:GITLAB_TOKEN = '<GitLab private token>'
  python scripts/create_releases.py
  python scripts/create_releases.py v3.7.5 v3.7.6  # 특정 버전만
"""
import os
import re
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

HOST      = 'https://mhub.nimbusnetworks.co.kr'
PROJECT   = 'claud/nimbus-bastion'
PROJ_URL  = urllib.parse.quote(PROJECT, safe='')
API       = f'{HOST}/api/v4/projects/{PROJ_URL}'
CHANGELOG = Path(__file__).parent.parent / 'CHANGELOG.md'


def get_token():
    token = os.environ.get('GITLAB_TOKEN') or os.environ.get('PRIVATE_TOKEN')
    if not token:
        print(
            '[ERROR] GitLab token이 필요합니다. '
            'GITLAB_TOKEN 환경변수를 설정한 뒤 다시 실행하세요.',
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def api_request(method, path, body=None):
    url = f'{API}{path}'
    data = None
    headers = {'PRIVATE-TOKEN': get_token()}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return {'error': str(e), 'status': e.code, 'body': body}


def parse_changelog():
    """CHANGELOG.md를 섹션별로 파싱하여 {tag: {title, body}} 반환."""
    text = CHANGELOG.read_text(encoding='utf-8')
    sections = re.split(r'\n(?=## v)', text)
    result = {}
    for s in sections:
        m = re.match(r'## (v[\d\.\-a-z]+)\s+—\s+(.+?)\n', s)
        if not m:
            continue
        tag = m.group(1)
        title_line = m.group(2).strip()
        # title_line은 "2026-05-15  ·  파드 메트릭..." 형식 → 뒷부분만 사용
        parts = re.split(r'\s+[·•]\s+', title_line, maxsplit=1)
        title = parts[1].strip() if len(parts) == 2 else title_line
        # 본문은 첫 줄 제외하고 다음 '---' 또는 끝까지
        body = s
        # '---' 이후 자르기
        body = re.split(r'\n---\s*\n', body, maxsplit=1)[0].rstrip()
        result[tag] = {'title': title, 'body': body, 'date': parts[0].strip() if len(parts) == 2 else ''}
    return result


def get_existing_releases():
    """기존 릴리스 태그 목록."""
    r = api_request('GET', '/releases?per_page=100')
    if isinstance(r, dict) and r.get('error'):
        print(f'[ERROR] release 목록 조회 실패: {r}')
        return set()
    return {x['tag_name'] for x in r}


def get_existing_tags():
    """기존 git tag 목록."""
    r = api_request('GET', '/repository/tags?per_page=100')
    if isinstance(r, dict) and r.get('error'):
        return set()
    return {x['name'] for x in r}


def create_release(tag, title, body):
    """릴리스 생성. EXE 다운로드 링크를 asset으로 추가."""
    exe_path = 'dist/polaris.exe'
    exe_url  = f'{HOST}/{PROJECT}/-/raw/{tag}/{exe_path}?inline=false'

    release_body = body + f'\n\n## 다운로드\n\n- [polaris.exe]({exe_url}) (Windows 64-bit)\n'

    payload = {
        'tag_name':    tag,
        'name':        f'Polaris {tag} — {title}',
        'description': release_body,
        'ref':         tag,
        'assets': {
            'links': [
                {
                    'name':      'polaris.exe',
                    'url':       exe_url,
                    'link_type': 'package',
                }
            ]
        }
    }
    return api_request('POST', '/releases', payload)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    target_tags = sys.argv[1:] if len(sys.argv) > 1 else None

    sections   = parse_changelog()
    existing   = get_existing_releases()
    tags_avail = get_existing_tags()

    print(f'CHANGELOG에서 발견된 버전: {sorted(sections.keys())}')
    print(f'기존 릴리스: {sorted(existing)}')
    print(f'기존 태그:   {sorted(tags_avail)}')
    print()

    to_create = []
    for tag in sections:
        if target_tags and tag not in target_tags:
            continue
        if tag in existing:
            print(f'[SKIP] {tag} — 이미 릴리스 존재')
            continue
        if tag not in tags_avail:
            print(f'[SKIP] {tag} — git tag 없음')
            continue
        to_create.append(tag)

    if not to_create:
        print('생성할 릴리스 없음')
        return

    print()
    print(f'생성 대상: {to_create}')
    print()

    for tag in to_create:
        sec = sections[tag]
        print(f'[CREATE] {tag} — {sec["title"]}')
        result = create_release(tag, sec['title'], sec['body'])
        if isinstance(result, dict) and result.get('error'):
            print(f'  [FAIL] {result}')
        else:
            print(f'  [OK] {result.get("_links", {}).get("self", "")}')


if __name__ == '__main__':
    main()
