"""파일/디렉터리 권한 하드닝 (best-effort, v1.2.3).

배경
─────────────────────────────────────────────────────────────────────────
``os.chmod(path, 0o600)`` 은 POSIX 에서만 의미가 있고 **Windows 에서는 읽기전용
비트만 토글**할 뿐 ACL(누가 읽을 수 있는가)에는 영향이 없다. 그래서 Polaris 의
민감 파일(vault.json, session.json,
settings.json, snapshots/, kubeconfigs/)은 사실상 **데이터 폴더의 상속 ACL** 에만
의존한다.

기본 위치 ``~/.polaris-free`` 는 사용자 프로필 하위라 보통 이미 사용자 전용이지만,
v1.2.2 의 데이터 폴더 이전 기능으로 ``D:\\polaris`` 나 공유 폴더처럼 ``Users`` /
``Authenticated Users`` 에 읽기가 열린 위치로 옮겨질 수 있다. 그 경우 같은 PC 의
다른 사용자가 암호문/평문 메타데이터를 읽을 수 있다.

대응
─────────────────────────────────────────────────────────────────────────
:func:`harden_dir` 가 데이터 폴더의 ACL 을 현재 사용자(+SYSTEM/Administrators)
전용으로 조인다. **락아웃이 없도록** 다음 순서를 지킨다:

  1. ``icacls /inheritance:d`` — 상속을 끊되 기존 ACE 를 **명시적으로 복사**
     (소유자 접근 보존 — 폴더 생성자는 CREATOR OWNER 상속분으로 항상 접근 유지)
  2. ``icacls /grant <현재사용자>:(OI)(CI)F`` — 현재 사용자 접근 명시 보장
  3. ``icacls /remove:g <광범위 그룹 SID>`` — BUILTIN\\Users / Authenticated Users
     / Everyone 만 제거 (SID 사용 → 로케일 무관)
  4. ``icacls <dir>\\* /reset /T`` — 기존 하위 항목을 (조여진) 부모 ACL 상속으로 복귀

모두 best-effort. icacls 부재 / FAT32 / 네트워크 공유 등으로 실패하면 조용히
건너뛴다(폴더는 기존 ACL 유지 — 손해 없음). 광범위 그룹만 제거하고 SYSTEM /
Administrators 는 유지하므로 백업·AV·관리 작업에 지장이 없다.
"""
import os
import re
import sys
import getpass
import subprocess
from pathlib import Path

_IS_WIN = sys.platform == 'win32'
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if _IS_WIN else 0

# 제거 대상 광범위 그룹 (well-known SID — 로케일 무관)
_BROAD_GROUP_SIDS = (
    '*S-1-5-32-545',  # BUILTIN\Users
    '*S-1-5-11',      # NT AUTHORITY\Authenticated Users
    '*S-1-1-0',       # Everyone
)
_HARDEN_MARKER = '.polaris_acl'   # 폴더 재귀 하드닝 1회 표식


def _current_user() -> str:
    """icacls 에 줄 현재 사용자 식별자 (DOMAIN\\USER 우선)."""
    user = os.environ.get('USERNAME') or getpass.getuser()
    domain = os.environ.get('USERDOMAIN')
    return f'{domain}\\{user}' if domain else user


_SID_CACHE = []


def _current_sid():
    """현재 사용자의 SID(S-1-5-21-…) — 이름(DOMAIN\\USER)은 로캘 · 도메인에 따라 풀리지 않을 수 있다(v1.4.24). 못 구하면 None"""
    if _SID_CACHE:
        return _SID_CACHE[0]
    sid = None
    try:
        r = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'], capture_output=True, text=True, timeout=10,
                           creationflags=_NO_WINDOW)
        m = re.search(r'"(S-1-[0-9-]+)"', r.stdout or '')
        sid = m.group(1) if m else None
    except Exception:
        sid = None
    _SID_CACHE.append(sid)
    return sid


def _grantee() -> str:
    """icacls 에 줄 현재 사용자 — SID(*S-1-…)가 있으면 그것, 없으면 이름"""
    sid = _current_sid()
    return f'*{sid}' if sid else _current_user()


def chmod_owner_only(path, is_dir: bool = False) -> None:
    """소유자 전용 권한 (POSIX 0600/0700). Windows 에서는 사실상 no-op 이지만 무해."""
    try:
        os.chmod(path, 0o700 if is_dir else 0o600)
    except Exception:
        pass


def _icacls(args, timeout=30) -> bool:
    """icacls 호출 (best-effort). 성공하면 True — 실패/부재는 False(예외를 내지 않는다)."""
    try:
        r = subprocess.run(['icacls', *args],
                           capture_output=True, timeout=timeout,
                           creationflags=_NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


def harden_dir(path, log=None) -> None:
    """데이터 디렉터리 ACL 을 현재 사용자 전용으로 조인다 (best-effort).

    여러 번 호출해도 안전(idempotent). 무거운 재귀(``/reset /T``)는 표식 파일로
    최초 1회만 수행한다. 새로 만들어지는 파일은 조여진 부모 ACL 을 상속한다.
    """
    p = Path(path)
    chmod_owner_only(p, is_dir=True)
    if not _IS_WIN:
        return
    try:
        if not p.is_dir():
            return
        user = _grantee()
        marker = p / _HARDEN_MARKER
        first_time = not marker.exists()

        _icacls([str(p), '/inheritance:d', '/C', '/Q'])                    # 1
        # 2 — 현재 사용자 접근을 **확실히 준 뒤에만** 넓은 그룹을 뺀다. 다른 드라이브(D:\\…)에서는 사용자 접근이
        # Authenticated Users 로만 들어와 있어, 이름으로 주기가 실패한 채 3 을 하면 자기 데이터에 못 들어갔다(v1.4.24)
        if not _icacls([str(p), '/grant', f'{user}:(OI)(CI)F', '/C', '/Q']):
            if log:
                log(f'ACL 하드닝 건너뜀 — 현재 사용자 권한을 주지 못했습니다: {p}')
            return
        _icacls([str(p), '/remove:g', *_BROAD_GROUP_SIDS, '/C', '/Q'])     # 3
        if first_time:
            _icacls([str(p / '*'), '/reset', '/T', '/C', '/Q'])            # 4 (1회)
            try:
                marker.write_text('1', encoding='ascii')
            except Exception:
                pass
    except Exception as e:
        if log:
            log(f'ACL 하드닝 실패(무시): {p}: {e}')


def harden_file(path, log=None) -> None:
    """단일 민감 파일 권한 하드닝 (best-effort). 폴더 하드닝이 우선이며, 이건 보조."""
    p = Path(path)
    chmod_owner_only(p, is_dir=False)
    if not _IS_WIN:
        return
    try:
        if not p.is_file():
            return
        user = _grantee()
        _icacls([str(p), '/inheritance:d', '/C', '/Q'])
        if _icacls([str(p), '/grant', f'{user}:F', '/C', '/Q']):          # 준 뒤에만 뺀다
            _icacls([str(p), '/remove:g', *_BROAD_GROUP_SIDS, '/C', '/Q'])
    except Exception as e:
        if log:
            log(f'ACL 하드닝 실패(무시): {p}: {e}')
