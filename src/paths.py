"""Polaris 데이터 디렉터리 위치 해석 (v1.2.2).

기본 위치는 ``~/.polaris``. 사용자가 위치를 바꾸면 ``~/.polaris/location.json``
포인터에 실제 경로를 기록하고, 모든 모듈은 :func:`polaris_dir` 로 실제 위치를 얻는다.

포인터(항상 기본 위치에 있음)만 먼저 읽어 실제 위치를 정하므로 부트스트랩 순환이
없다. 경로는 import 시 1회 확정(캐시)되며, 런타임 변경은 **재시작 후** 반영된다.

모든 쓰기 측은 기존처럼 직접 ``mkdir(parents=True, exist_ok=True)`` 하므로
여기서는 디렉터리를 만들지 않는다(순수 해석).
"""
import json
from pathlib import Path

DEFAULT_DIR = Path.home() / '.polaris'
POINTER_PATH = DEFAULT_DIR / 'location.json'

_cached = None


def _read_pointer():
    """location.json 에서 data_dir 경로 추출 (없으면 None)."""
    try:
        if POINTER_PATH.exists():
            obj = json.loads(POINTER_PATH.read_text(encoding='utf-8'))
            d = obj.get('data_dir')
            if d:
                return Path(d)
    except Exception:
        pass
    return None


def polaris_dir() -> Path:
    """실제 데이터 디렉터리 (캐시). 포인터가 가리키는 폴더가 없으면 기본으로 폴백."""
    global _cached
    if _cached is not None:
        return _cached
    p = _read_pointer()
    _cached = p if (p is not None and p.is_dir()) else DEFAULT_DIR
    return _cached


def resolved_dir_uncached() -> Path:
    """캐시 무시하고 현재 포인터 기준 경로 (변경 직후 확인용)."""
    p = _read_pointer()
    return p if (p is not None and p.is_dir()) else DEFAULT_DIR


def write_pointer(new_dir) -> None:
    """location.json 포인터 기록. new_dir 이 기본 위치면 포인터 제거."""
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    new_dir = Path(new_dir)
    if new_dir.resolve() == DEFAULT_DIR.resolve():
        if POINTER_PATH.exists():
            POINTER_PATH.unlink()
        return
    POINTER_PATH.write_text(
        json.dumps({'data_dir': str(new_dir)}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
