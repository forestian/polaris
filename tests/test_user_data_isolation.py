# -*- coding: utf-8 -*-
"""테스트가 **사용자의 진짜 데이터**를 건드리지 못하게 막는 가드 (v1.3.26).

## 왜 있는가 (실제 사고)

v1.3.25 개발 중, RDP 테스트가 사용자의 `~/.polaris/servers.json` 에 서버 6대를
써 넣었다. 사용자가 「내 인벤토리에 g 라는 그룹이 막 생겼는데」 라고 알려 줘서야
알았다(지우고 복구함). 테스트는 이렇게 격리했다고 **믿고** 있었다:

    patch('src.api.infra.polaris_dir', return_value=tmp)

그런데 `src/api/infra.py` 의 경로들은 **import 시점에 한 번 계산되는 모듈 상수**다:

    _INVENTORY_PATH = polaris_dir() / 'servers.json'      # ← 여기서 이미 확정

그래서 나중에 `polaris_dir` 을 바꿔도 아무 일도 일어나지 않는다. 오류도 경고도 없이
**진짜 파일에 쓴다.** 이 가드는 그 패턴을 정적으로 잡는다.

## 무엇을 거는가

1. 모듈 상수로 경로를 굳히는 모듈은, 그 모듈의 `polaris_dir` 만 패치해서는 안 된다.
   → 상수 자체(`patch.object(mod, '_INVENTORY_PATH', ...)`)를 갈아끼워야 한다.
2. 테스트 파일이 `Path.home()` 밑을 **쓰기 용도로** 직접 가리키면 안 된다.

사정이 있으면 그 줄 옆에 `# real-data-ok: <이유>` 를 적는다(읽기만 하는 확인 등).
"""
import ast
import io
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'
ALLOW = 'real-data-ok'

# 경로를 import 시점에 굳히는 모듈 → 그 상수 이름들.
# 새 상수가 늘어나면 아래 test_constant_list_is_current 가 먼저 잡는다.
_FROZEN = {}


def _frozen_path_constants(py: Path) -> list:
    """`NAME = polaris_dir() / '...'` 꼴의 **모듈 수준** 상수 이름들."""
    try:
        tree = ast.parse(py.read_text(encoding='utf-8'))
    except (OSError, SyntaxError):
        return []
    out = []
    for node in tree.body:                      # 모듈 수준만 본다
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        src = ast.dump(node.value)
        if "func=Name(id='polaris_dir'" in src or "attr='polaris_dir'" in src:
            out.append(target.id)
    return out


def _scan_modules():
    for py in sorted((ROOT / 'src').rglob('*.py')):
        names = _frozen_path_constants(py)
        if names:
            mod = str(py.relative_to(ROOT).with_suffix('')).replace('\\', '/').replace('/', '.')
            _FROZEN[mod] = names


_scan_modules()

_PATCH_DIR_RE = re.compile(r"""patch(?:\.object)?\s*\(\s*['"]([\w.]+)\.polaris_dir['"]""")
_HOME_RE = re.compile(r'Path\.home\(\)')


def _lines_with_mark(text: str, needle: str):
    """needle 이 나오는 줄 중 **허용 표시가 없는** 줄 번호들."""
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if needle not in line:
            continue
        if line.lstrip().startswith('#'):
            continue            # 주석은 파일을 쓰지 않는다 — 설명하는 줄까지 잡으면 시끄럽다
        window = lines[max(0, i - 1):i + 2]
        if any(ALLOW in w for w in window):
            continue
        out.append(i + 1)
    return out


class TestFrozenPathConstants(unittest.TestCase):
    def test_constant_list_is_current(self):
        """경로를 굳히는 모듈이 실제로 있다 — 이 가드가 헛돌고 있지 않은지."""
        # 변형 빌드에서도 살아남는 **코어** 모듈로 확인한다. 플러그인 모듈
        # (src/api/infra.py 등) 을 여기 적으면 무료 빌드에서 이 가드가 무너진다.
        self.assertIn('src.snapshot', _FROZEN,
                      'src/snapshot.py 의 모듈 상수를 못 찾았다 — 탐지 로직 확인')
        self.assertIn('SNAPSHOT_DIR', _FROZEN['src.snapshot'])

    def test_no_test_patches_polaris_dir_on_frozen_module(self):
        """상수로 굳어 버린 모듈은 `polaris_dir` 패치가 **아무 일도 안 한다**.

        그걸 격리로 믿으면 사용자 실제 파일에 쓴다(v1.3.25 에서 실제로 그랬다).
        """
        bad = {}
        for py in sorted(TESTS.glob('test_*.py')):
            if py.name == Path(__file__).name:
                continue        # 이 파일은 그 패턴을 '설명'한다
            with io.open(py, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
            for mod in set(_PATCH_DIR_RE.findall(text)):
                if mod not in _FROZEN:
                    continue
                hits = _lines_with_mark(text, mod + '.polaris_dir')
                if hits:
                    bad.setdefault(py.name, []).append(
                        f'{mod} (굳은 상수: {", ".join(_FROZEN[mod])}) 줄 {hits}')
        self.assertEqual(
            bad, {},
            '경로가 import 시점에 굳는 모듈인데 polaris_dir 을 패치했다 — '
            '격리가 안 되고 **사용자 실제 파일에 쓴다**:\n'
            + '\n'.join(f'  {k}: {v}' for k, v in sorted(bad.items()))
            + "\n→ patch.object(모듈, '_INVENTORY_PATH', tmp/'servers.json') 처럼 "
              '상수 자체를 갈아끼울 것.')

    def test_no_test_writes_under_home(self):
        """테스트가 `Path.home()` 밑을 직접 가리키지 않는다.

        읽어서 확인만 하는 경우가 있을 수 있어 `# real-data-ok:` 로 열어 둔다.
        """
        bad = {}
        for py in sorted(TESTS.glob('test_*.py')):
            if py.name == Path(__file__).name:
                continue        # 이 파일은 그 패턴을 '설명'한다
            with io.open(py, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
            if not _HOME_RE.search(text):
                continue
            hits = _lines_with_mark(text, 'Path.home()')
            if hits:
                bad[py.name] = hits
        self.assertEqual(
            bad, {},
            '테스트가 사용자 홈(~/.polaris)을 직접 가리킨다:\n'
            + '\n'.join(f'  {k}: 줄 {v}' for k, v in sorted(bad.items()))
            + f'\n→ 임시 폴더를 쓰거나, 읽기만 한다면 `# {ALLOW}: <이유>` 를 적을 것.')


if __name__ == '__main__':
    unittest.main()
