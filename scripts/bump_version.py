"""무료판 버전 올리기 — polaris.py 의 VERSION 을 바꾼다.

    python scripts/bump_version.py 1.5.74-f1 1.5.74-f2

설치 프로그램 쪽 버전(package.json · Cargo.toml · tauri.conf.json · main.rs · App.jsx)은
build.py 가 빌드할 때 VERSION 에 맞춰 고친다. 맞는 자리가 정확히 한 곳이 아니면 아무것도 쓰지 않고 멈춘다.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMAT = r'\d+\.\d+\.\d+-f\d+'


def main(old: str, new: str) -> int:
    if not re.fullmatch(FORMAT, old) or not re.fullmatch(FORMAT, new):
        print('버전은 1.2.3-f1 꼴로 적으세요.')
        return 2
    p = ROOT / 'polaris.py'
    raw = p.read_bytes().decode('utf-8')
    pat = rf"VERSION = '{re.escape(old)}'"
    n = len(re.findall(pat, raw))
    if n != 1:
        print(f'멈춤 — polaris.py: 맞는 자리가 {n}곳입니다(1곳이어야 함). 아무것도 바꾸지 않았습니다.')
        return 1
    p.write_bytes(re.sub(pat, f"VERSION = '{new}'", raw, count=1).encode('utf-8'))
    print('bumped polaris.py')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
