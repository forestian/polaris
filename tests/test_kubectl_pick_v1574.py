# -*- coding: utf-8 -*-
"""v1.5.74 클러스터 판에 맞는 kubectl 고르기.

사용자 PC 는 PATH 맨 앞이 Docker Desktop 의 kubectl 1.32 라 Rancher Desktop 1.37 과 판 차이가 지원 범위(±1)를 크게 넘었다.
「제일 새 것」 으로 바꾸면 옛 클러스터(고객사 1.2x)에서 새 kubectl 이 서버에 없는 기능을 쓸 수 있다 →
연결한 클러스터마다 판 차이가 가장 적은 kubectl 을 쓴다(같으면 새 판).
"""
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import tools as T  # noqa: E402


class PickTests(unittest.TestCase):
    def test_판_읽기(self):
        self.assertEqual(T._minor_of('v1.37.2+k3s1'), 37)
        self.assertEqual(T._minor_of('1.36'), 36)
        self.assertEqual(T._minor_of('36+'), 36, 'kubectl version -o json 의 minor 는 「36+」 처럼 올 수 있다')
        self.assertIsNone(T._minor_of(''))
        self.assertIsNone(T._minor_of('dev'))

    def test_가장_가까운_판(self):
        c = [('docker', 32), ('home', 36), ('rd', 36)]
        self.assertEqual(T.pick_kubectl(c, 37), 'home', '1.37 클러스터 → 1.36(차이 1)')
        self.assertEqual(T.pick_kubectl(c, 29), 'docker', '고객사 1.29 → 1.32(옛 클러스터에 새 kubectl 을 들이밀지 않는다)')
        self.assertEqual(T.pick_kubectl(c, 34), 'home', '32 와 36 은 둘 다 차이 2 — 새 판')
        self.assertEqual(T.pick_kubectl([('a', 33), ('b', 35)], 34), 'b', '차이가 같으면 새 판(한 판 위 클라이언트는 공식 지원)')
        self.assertIsNone(T.pick_kubectl(c, None), '서버 판을 모르면 예전 방식에 맡긴다')
        self.assertIsNone(T.pick_kubectl([('x', None)], 37), '판을 못 읽은 kubectl 만 있으면')
        self.assertEqual(T.pick_kubectl([('x', None), ('y', 30)], 37), 'y')


class FindTests(unittest.TestCase):
    def setUp(self):
        self._saved = (dict(T._SERVER_MINOR), dict(T._KUBECTL_FOR), T._kubectl_cached)
        T._SERVER_MINOR.clear()
        T._KUBECTL_FOR.clear()

    def tearDown(self):
        T._SERVER_MINOR.clear(); T._SERVER_MINOR.update(self._saved[0])
        T._KUBECTL_FOR.clear(); T._KUBECTL_FOR.update(self._saved[1])
        T._kubectl_cached = self._saved[2]

    def test_클러스터마다_따로_고른다(self):
        minors = {'C:/docker/kubectl.exe': 32, 'C:/home/kubectl.exe': 36}
        T.note_server_version('C:/kc/new.yaml', 'v1.37.2+k3s1')
        T.note_server_version('C:/kc/old.yaml', 'v1.29.9')
        with mock.patch.object(T, '_kubectl_candidates', return_value=list(minors)), \
             mock.patch.object(T, '_client_minor', side_effect=lambda p: minors[p]), \
             mock.patch.object(T.os.path, 'isfile', return_value=True):
            self.assertEqual(T._find_kubectl('C:/kc/new.yaml'), 'C:/home/kubectl.exe')
            self.assertEqual(T._find_kubectl('C:/kc/old.yaml'), 'C:/docker/kubectl.exe')

    def test_판을_모르는_kubeconfig_는_예전_순서(self):
        T._kubectl_cached = None
        with mock.patch.object(T, '_probe', side_effect=lambda c: c == 'kubectl'):
            self.assertEqual(T._find_kubectl('C:/kc/unknown.yaml'), 'kubectl')
            self.assertEqual(T._find_kubectl(), 'kubectl')

    def test_서버_판이_바뀌면_다시_고른다(self):
        T.note_server_version('C:/kc/a.yaml', 'v1.30.0')
        T._KUBECTL_FOR[T._kc_key('C:/kc/a.yaml')] = 'old-choice'
        T.note_server_version('C:/kc/a.yaml', 'v1.37.0')
        self.assertNotIn(T._kc_key('C:/kc/a.yaml'), T._KUBECTL_FOR, '클러스터 업그레이드 뒤 다시 연결하면 새로 고른다')

    def test_클라이언트_판_읽기(self):
        out = 'downloading...\n{"clientVersion": {"major": "1", "minor": "36+", "gitVersion": "v1.36.0"}}'
        r = mock.Mock(stdout=out)
        T._CLIENT_MINOR.pop('X', None)
        with mock.patch.object(T.os.path, 'getmtime', return_value=1.0), \
             mock.patch.object(T.subprocess, 'run', return_value=r) as run:
            self.assertEqual(T._client_minor('X'), 36, '앞에 진행 줄이 있어도')
            self.assertEqual(T._client_minor('X'), 36)
            self.assertEqual(run.call_count, 1, '파일이 그대로면 한 번만 실행')
        T._CLIENT_MINOR.pop('X', None)


class WiringTests(unittest.TestCase):
    def test_연결할_때_서버_판을_적는다(self):
        src = (ROOT / 'src' / 'k8s.py').read_text(encoding='utf-8')
        body = src[src.index('    def connect('):src.index('    def disconnect(')]
        self.assertIn('note_server_version(path, ver.git_version)', body)

    def test_kubectl_을_부르는_곳이_kubeconfig_를_넘긴다(self):
        tools = (ROOT / 'src' / 'tools.py').read_text(encoding='utf-8')
        for fn in ('def _run_kubectl(', 'def _run_kubectl_rc('):
            body = tools[tools.index(fn):]
            body = body[:body.index('\ndef ', 1)]
            self.assertIn('_find_kubectl(kubeconfig)', body, fn)
        left = []
        for f in (ROOT / 'src' / 'api').glob('*.py'):
            for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
                code = line.split('#', 1)[0]          # 주석 안의 글자는 빼고
                if re.search(r'\b_find_kubectl\(\)', code) and 'if _find_kubectl()' not in code:
                    left.append(f'{f.name}:{i}')
        self.assertEqual(left, [], '실행용 kubectl 은 클러스터 판에 맞춰 — 「있는지」 확인(if _find_kubectl())만 예외')


class ThisPcTests(unittest.TestCase):
    def test_이_PC_의_후보_찾기는_안_깨진다(self):
        cands = T._kubectl_candidates()
        self.assertIsInstance(cands, list)
        self.assertEqual(len(cands), len({T.os.path.normcase(T.os.path.realpath(p)) for p in cands}), '같은 파일 중복 없음')


if __name__ == '__main__':
    unittest.main()
