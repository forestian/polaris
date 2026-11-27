# -*- coding: utf-8 -*-
"""무료판 범위 지키기 — K8S + CHECK(클러스터 점검 3종) · AI 진단 · MCP 조회 전용만.

무료판에 없는 기능은 화면에서 숨기는 것이 아니라 **코드부터 없어야** 한다(받은 사람이 코드에서 유료 기능을
찾을 수 없게). 정식판에서 코드를 가져올 때 딸려 들어오면 여기서 멈춘다. build.py 가 빌드마다 돌린다.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 있으면 안 되는 파일 · 폴더 (정식판에만 있는 기능)
ABSENT = [
    'src/api/infra.py', 'src/api/infra_parts', 'src/infra', 'src/api/catalog.py', 'src/catalog.py', 'catalog',
    'src/api/srvcheck.py', 'src/srvcheck.py', 'src/api/memo.py', 'src/memo.py', 'src/api/apitest.py', 'src/apitest.py',
    'src/api/netcheck.py', 'src/netcheck.py', 'src/tcpdump.py', 'src/ops.py', 'src/incident.py', 'src/dailycheck.py',
    'src/updater.py', 'src/features.py', 'src/portable.py', 'src/confrules', 'src/s3lite.py',
    'ui/src/infra', 'ui/src/memo', 'ui/src/ops', 'ui/src/apitest', 'ui/src/catalog',
    'ui/src/pages/AiChatPage.jsx', 'ui/src/pages/MigrationPage.jsx', 'ui/src/pages/BackupPage.jsx',
    'ui/src/pages/DailyCheckPage.jsx', 'ui/src/components/UpdateTab.jsx', 'ui/src/startMode.js',
    'packaging/localshell', 'packaging/axhost', 'scripts/update_signing.py',
]

#: 코드에 나오면 안 되는 낱말 — 유료 기능의 이름 · 모듈 · 라이브러리
FORBIDDEN = re.compile(
    r"\binfra\b|paramiko|[Ww]in[Rr][Mm]|\bRDP\b|\bSFTP\b|\bsftp|seslog|tcpdump|srvcheck|apitest|\bMEMO\b|[Cc]atalog"
    r"|updateInfo|update_check|UPDATE_PUBLIC_KEY|startMode|start_mode|sshCommand|[Bb]areos|[Vv]ersity|S3 ?GATEWAY"
    r"|dailycheck|simplecheck|netcheck|localshell|winpty|comtypes|\bOPS\b|\bSSH\b|\bssh_|polaris_ssh|_guard_write")

#: 코드로 보는 곳(시험 파일 · 생성 데이터 제외)
CODE_ROOTS = ['src', 'ui/src', 'polaris.py', 'build.py', 'packaging/setup-tauri/src',
              'packaging/setup-tauri/src-tauri/src', 'ui/index.html']
CODE_EXT = {'.py', '.js', '.jsx', '.mjs', '.css', '.html', '.rs'}
SKIP = re.compile(r'(\.test\.mjs$|_k8s_upgrade_data\.py$|__pycache__)')


def _code_files():
    for rel in CODE_ROOTS:
        p = ROOT / rel
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in p.rglob('*'):
                if f.is_file() and f.suffix in CODE_EXT and not SKIP.search(f.as_posix()):
                    yield f


class FreeScope(unittest.TestCase):
    def test_유료_기능_파일이_없다(self):
        found = [rel for rel in ABSENT if (ROOT / rel).exists()]
        self.assertEqual(found, [], '무료판에 들어오면 안 되는 파일 · 폴더')

    def test_코드에_유료_기능_낱말이_없다(self):
        hits = []
        for f in _code_files():
            for i, line in enumerate(f.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                m = FORBIDDEN.search(line)
                if m:
                    hits.append(f'{f.relative_to(ROOT).as_posix()}:{i}: [{m.group(0)}] {line.strip()[:90]}')
        self.assertEqual(hits, [], '유료 기능 낱말 — 코드 · 주석 · 화면 문구에서 빼거나 무료판 말로 바꿀 것')

    def test_mcp_는_조회_툴_6개뿐(self):
        from src import mcp_server as M
        names = {t.name for t in M._tool_defs()}
        self.assertEqual(names, {'polaris_list_clusters', 'polaris_use_cluster', 'polaris_list_resources',
                                 'polaris_get_resource', 'polaris_get_logs', 'polaris_get_events'})
        self.assertEqual(set(M._TOOLS), names)

    def test_옵셔널_기능은_알림_YAML_실험실뿐(self):
        from src.api import ENABLED_FEATURES
        self.assertLessEqual(set(ENABLED_FEATURES), {'notifications', 'yamllab'})

    def test_필요_없는_패키지를_받지_않는다(self):
        req = (ROOT / 'requirements.txt').read_text(encoding='utf-8').lower()
        for pkg in ('paramiko', 'comtypes', 'pywinpty', 'pywinrm', 'requests-ntlm', 'pyspnego', 'sspilib', 'xmltodict'):
            self.assertNotIn(pkg, req)

    def test_spec_은_빠진_라이브러리를_묶지_않는다(self):
        spec = (ROOT / 'packaging' / 'specs' / 'Polaris.spec').read_text(encoding='utf-8')
        m = re.search(r'excludes=\[(.*?)\]', spec, re.S)
        self.assertTrue(m)
        for mod in ('paramiko', 'comtypes', 'winpty', 'winrm'):
            self.assertIn(f"'{mod}'", m.group(1), f'{mod} 를 excludes 에')
        self.assertNotIn('update_token', spec, '업데이트 토큰을 묶지 않는다')

    @unittest.skipUnless((ROOT / 'scripts' / 'create_releases.py').exists(), '내부 릴리스 스크립트 없음(공개 저장소)')
    def test_릴리스_스크립트는_정식판_패키지를_건드리지_않는다(self):
        src = (ROOT / 'scripts' / 'create_releases.py').read_text(encoding='utf-8')
        self.assertIn("PKG_NAME = 'polaris-free'", src)
        self.assertNotIn('def publish_latest_alias', src, '정식판 latest · version.txt 를 덮지 않는다')
        self.assertNotIn("'version.txt'", src)


    def test_정식판과_따로_쓴다(self):
        from src import paths
        self.assertEqual(paths.DEFAULT_DIR.name, '.polaris-free')
        rt = (ROOT / 'src' / 'runtime.py').read_text(encoding='utf-8')
        self.assertNotIn('_INSTANCE_PORT = 43711', rt, '정식판 실행 신호 포트')
        rs = (ROOT / 'packaging' / 'setup-tauri' / 'src-tauri' / 'src' / 'main.rs').read_text(encoding='utf-8')
        self.assertIn('const APP_NAME: &str = "Polaris Free";', rs)
        self.assertNotIn('"/IM", "polaris.exe"', rs, '이름으로 끄면 정식판까지 꺼진다')

if __name__ == '__main__':
    unittest.main()
