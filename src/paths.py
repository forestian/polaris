"""Polaris 데이터 디렉터리 위치 해석 (v1.2.2).

기본 위치는 ``~/.polaris-free``. 사용자가 위치를 바꾸면 ``~/.polaris-free/location.json``
포인터에 실제 경로를 기록하고, 모든 모듈은 :func:`polaris_dir` 로 실제 위치를 얻는다.

포인터(항상 기본 위치에 있음)만 먼저 읽어 실제 위치를 정하므로 부트스트랩 순환이
없다. 경로는 import 시 1회 확정(캐시)되며, 런타임 변경은 **재시작 후** 반영된다.

모든 쓰기 측은 기존처럼 직접 ``mkdir(parents=True, exist_ok=True)`` 하므로
여기서는 디렉터리를 만들지 않는다(순수 해석).
"""
import json
from pathlib import Path

DEFAULT_DIR = Path.home() / '.polaris-free'   # 정식판(~/.polaris)과 따로
POINTER_PATH = DEFAULT_DIR / 'location.json'

_cached = None
_fallback_from = None      # 옮긴 데이터 폴더를 못 찾아 기본 폴더로 열었을 때, 찾던 경로(v1.4.24)


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
    global _cached, _fallback_from
    if _cached is not None:
        return _cached
    p = _read_pointer()
    _cached = p if (p is not None and p.is_dir()) else DEFAULT_DIR
    if p is not None and not p.is_dir():
        # 외장 · 네트워크 드라이브가 아직 연결되지 않았다 등 — 기본 폴더의 (오래된) 데이터로 연다.
        # 예전엔 아무 말 없이 열어 두 곳의 데이터가 어긋났다 — 화면이 알릴 수 있게 남긴다
        _fallback_from = p
    return _cached


def fallback_from():
    """옮긴 데이터 폴더를 못 찾아 기본 폴더로 열었으면 그 경로(문자열), 아니면 None"""
    polaris_dir()
    return str(_fallback_from) if _fallback_from is not None else None


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


def atomic_write_text(p, text: str, encoding: str = 'utf-8', retries: int = 6) -> None:
    """임시 파일에 쓰고 바꿔치기한다 — 쓰는 도중에 끊겨도 반쪽 파일이 남지 않게(v1.5.28 검토).

    Windows 에서는 다른 스레드(잠금 없이 읽는 쪽) · 백신이 그 파일을 잠깐 열고 있으면 os.replace 가
    PermissionError 로 실패한다 — 예전엔 그 순간의 쓰기가 사라졌다(작업 실행 결과 · 메모 · 인증서 목록).
    쓰는 쪽마다 다른 임시 이름을 쓰고, 잠깐 기다렸다 다시 바꿔치기한다.
    """
    import os
    import time
    import uuid
    p = Path(p)
    tmp = p.with_name(f'{p.name}.{uuid.uuid4().hex[:8]}.tmp')
    tmp.write_text(text, encoding=encoding)
    for i in range(retries):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i == retries - 1:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                raise
            time.sleep(0.05 * (i + 1))
