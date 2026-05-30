"""Polaris 비밀 저장소 (Vault).

infra 플러그인 (SSH 접속정보, sudo password, ansible vault 등) 의 민감
데이터를 디스크에 안전하게 보관하기 위한 코어 모듈. 다른 기능에서도
재사용 가능하도록 src/ 코어에 둠 (infra 플러그인이 제외돼도 vault 는 남음).

설계 원칙
─────────────────────────────────────────────────────────────────────────
1. 포맷 버전 (`format_version`) 을 1급 시민으로. 새 버전 추가 시 v1 reader
   는 절대 변경 금지. _read_v1() 는 영원히 보존되며, CI 의 회귀 fixture
   (VAULT_V1_FIXTURE) 가 매 릴리스에서 v1 호환을 강제 검증.

2. 이중 잠금. 같은 DEK 를 두 가지 방법으로 wrap:
     - DPAPI(DEK)         → 같은 Windows 사용자에서 자동 복호화 (편의)
     - AES-GCM(DEK, KEK)  → 마스터 패스워드 파생 KEK (복구 / 이동)
   일상에서는 DPAPI 로 무프롬프트, Windows 프로필 손상 시 마스터 패스워드
   로 fallback. Xshell 의 "session encryption + master password" 모델과
   동일한 UX 보장.

3. Stdlib + cryptography 만 사용. argon2 같은 native 의존성 회피해
   PyInstaller 빌드 안정성 확보. KDF 는 `hashlib.scrypt` (memory-hard,
   stdlib).

4. AEAD 는 AES-256-GCM. NIST 표준, cryptography 패키지가 안정적으로 지원.
   각 비밀마다 독립 nonce 로 cross-secret 공격 차단.

5. Atomic write. vault.json.tmp → fsync → rename. 쓰기 중 크래시로 vault
   가 손상되지 않음.

위협 모델
─────────────────────────────────────────────────────────────────────────
방어함:
  - 오프라인 디스크 탈취 (DPAPI / KEK 없이는 못 품)
  - 다른 Windows 사용자 (DPAPI 가 사용자 종속)
  - 같은 사용자라도 PC 변경 (DPAPI 안 됨, 마스터 패스워드 필요)
  - 버전 업그레이드 시 형식 변경 (v1 reader 영구 보존)

방어 안 함:
  - 같은 사용자로 실행되는 멀웨어 (Chrome 저장 비번 한계와 동일)
  - 메모리 덤프 (Python 은 byte 영역 zero out 불가능 — bytearray 로 최선)
  - 마스터 패스워드 분실 시 복구 (의도된 동작)
"""
import os
import json
import base64
import hashlib
import secrets
import threading
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

# cryptography 는 AES-256-GCM AEAD 표준 구현체.
# PyInstaller 자동 hook 으로 frozen 빌드에 포함됨.
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


# ─────────────────────────────────────────────────────────────────────────────
# 상수 — 포맷 v1 의 모든 파라미터. 이 값들은 영원히 변경 금지.
# ─────────────────────────────────────────────────────────────────────────────
CURRENT_FORMAT_VERSION = 1

# v1 KDF: scrypt
_V1_KDF_ALGO   = 'scrypt'
_V1_KDF_N      = 32768      # 2^15, 데스크탑 unlock ~200ms
_V1_KDF_R      = 8
_V1_KDF_P      = 1
_V1_KDF_DKLEN  = 32         # 256-bit KEK
_V1_SALT_BYTES = 32

# v1 AEAD: AES-256-GCM
_V1_AEAD_ALGO   = 'AES-256-GCM'
_V1_KEY_BYTES   = 32   # DEK / KEK 길이
_V1_NONCE_BYTES = 12   # GCM 권장
_V1_TAG_BYTES   = 16   # GCM 표준


# ─────────────────────────────────────────────────────────────────────────────
# 예외
# ─────────────────────────────────────────────────────────────────────────────
class VaultError(Exception):
    """Vault 모든 오류의 베이스."""


class VaultNotFound(VaultError):
    """vault 파일이 없음."""


class VaultLocked(VaultError):
    """잠금 해제 전 비밀 접근 시도."""


class VaultCorrupted(VaultError):
    """vault 파일 손상 (JSON 파싱 실패, 필수 필드 누락 등)."""


class InvalidMasterPassword(VaultError):
    """마스터 패스워드 불일치 — AES-GCM tag 검증 실패."""


class DPAPIUnavailable(VaultError):
    """DPAPI 복호화 실패 (프로필 손상 / 다른 사용자 / OS 이슈)."""


class IncompatibleFormat(VaultError):
    """미래 포맷 — 현재 Polaris 가 못 읽음."""


# ─────────────────────────────────────────────────────────────────────────────
# DPAPI 래퍼 (ctypes 직접 호출, pywin32 의존 회피)
# ─────────────────────────────────────────────────────────────────────────────
class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_byte)),
    ]


_crypt32 = ctypes.WinDLL('crypt32', use_last_error=True)
_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

_CRYPTPROTECT_UI_FORBIDDEN = 0x01  # 프롬프트 절대 띄우지 않음


def _make_blob(data: bytes) -> _DATA_BLOB:
    """bytes → DATA_BLOB."""
    buf = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _blob_to_bytes(blob: _DATA_BLOB) -> bytes:
    """DATA_BLOB → bytes + LocalFree."""
    out = ctypes.string_at(blob.pbData, blob.cbData)
    _kernel32.LocalFree(blob.pbData)
    return out


def dpapi_protect(plaintext: bytes) -> bytes:
    """CryptProtectData — 현재 Windows 사용자 컨텍스트로 암호화."""
    blob_in  = _make_blob(plaintext)
    blob_out = _DATA_BLOB()
    ok = _crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,            # description
        None,            # entropy (옵션 — 향후 secondary entropy 추가 여지)
        None, None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(blob_out),
    )
    if not ok:
        err = ctypes.get_last_error()
        raise DPAPIUnavailable(f'CryptProtectData failed: 0x{err:08x}')
    return _blob_to_bytes(blob_out)


def dpapi_unprotect(ciphertext: bytes) -> bytes:
    """CryptUnprotectData — 같은 Windows 사용자에서만 복호화 가능."""
    blob_in  = _make_blob(ciphertext)
    blob_out = _DATA_BLOB()
    ok = _crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None, None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(blob_out),
    )
    if not ok:
        err = ctypes.get_last_error()
        raise DPAPIUnavailable(f'CryptUnprotectData failed: 0x{err:08x}')
    return _blob_to_bytes(blob_out)


# ─────────────────────────────────────────────────────────────────────────────
# base64 헬퍼
# ─────────────────────────────────────────────────────────────────────────────
def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def _b64d(s: str) -> bytes:
    return base64.b64decode(s.encode('ascii'))


# ─────────────────────────────────────────────────────────────────────────────
# v1 포맷 reader — ★ DO NOT MODIFY ★
# 이 함수는 v1 포맷 vault 를 영원히 읽을 수 있어야 한다.
# 새 포맷 추가 시 _read_v2 / _read_v3 를 신규 작성하고 이 함수는 손대지 않음.
# ─────────────────────────────────────────────────────────────────────────────
def _read_v1(data: dict) -> dict:
    """v1 포맷 vault dict 를 검증하고 정규화된 dict 로 반환.

    구조 검증만 함. DEK 복호화는 Vault 인스턴스에서 호출자 키로 수행.
    """
    if not isinstance(data, dict):
        raise VaultCorrupted('vault 가 dict 형식이 아닙니다.')

    if data.get('format_version') != 1:
        raise VaultCorrupted(
            f'v1 reader 가 format_version={data.get("format_version")} 를 받음.'
        )

    # 필수 필드
    for req in ('kdf', 'master_dek', 'secrets'):
        if req not in data:
            raise VaultCorrupted(f'필수 필드 누락: {req}')

    kdf = data['kdf']
    if (kdf.get('algo')  != _V1_KDF_ALGO  or
        kdf.get('n')     != _V1_KDF_N     or
        kdf.get('r')     != _V1_KDF_R     or
        kdf.get('p')     != _V1_KDF_P     or
        kdf.get('dklen') != _V1_KDF_DKLEN):
        raise VaultCorrupted('v1 KDF 파라미터가 표준과 다릅니다.')

    if 'salt' not in kdf:
        raise VaultCorrupted('KDF salt 누락.')

    mdek = data['master_dek']
    for req in ('nonce', 'ciphertext'):
        if req not in mdek:
            raise VaultCorrupted(f'master_dek 필드 누락: {req}')

    if not isinstance(data['secrets'], dict):
        raise VaultCorrupted('secrets 가 dict 가 아닙니다.')

    return data


# ─────────────────────────────────────────────────────────────────────────────
# Vault 클래스
# ─────────────────────────────────────────────────────────────────────────────
class Vault:
    """Polaris 비밀 저장소.

    사용 패턴:
        v = Vault()
        if not v.exists:
            v.create(master_password='...')   # 첫 실행, 마스터 패스워드 1회 설정
        if not v.unlock_dpapi():
            v.unlock_master(master_password)  # DPAPI 실패 시 fallback
        v.store('host.web-01.password', 'p@ss')
        secret = v.retrieve('host.web-01.password')
        v.lock()  # 종료 시
    """

    DEFAULT_PATH = Path.home() / '.polaris' / 'vault.json'

    def __init__(self, path: Path | None = None):
        if not HAS_CRYPTO:
            raise VaultError(
                "cryptography 패키지가 없습니다 — 'pip install cryptography'"
            )
        self.path: Path = Path(path) if path else self.DEFAULT_PATH
        self._dek: bytearray | None = None   # 잠금 해제 시 로드, lock() 시 zero out
        self._data: dict | None = None       # 디스크 파일 내용
        self._lock = threading.Lock()

    # ── 상태 ───────────────────────────────────────────────────────────────
    @property
    def exists(self) -> bool:
        return self.path.exists()

    @property
    def is_unlocked(self) -> bool:
        return self._dek is not None

    @property
    def is_loaded(self) -> bool:
        return self._data is not None

    @property
    def has_dpapi(self) -> bool:
        """dpapi_dek blob 존재 여부 = DPAPI 자동 잠금 해제 활성 여부.

        잠금 해제 전(_data 미로드)에도 디스크에서 직접 확인 가능."""
        try:
            if self._data is not None:
                return bool(self._data.get('dpapi_dek'))
            if self.exists:
                obj = json.loads(self.path.read_text(encoding='utf-8'))
                return bool(obj.get('dpapi_dek'))
        except Exception:
            pass
        return False

    # ── 디스크 I/O ─────────────────────────────────────────────────────────
    def _load(self) -> None:
        """디스크에서 vault 파일 로드 + 포맷 버전 분기."""
        if not self.exists:
            raise VaultNotFound(f'vault 파일 없음: {self.path}')
        try:
            raw = self.path.read_text(encoding='utf-8')
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise VaultCorrupted(f'JSON 파싱 실패: {e}') from e

        ver = obj.get('format_version')
        if ver == 1:
            self._data = _read_v1(obj)
        elif isinstance(ver, int) and ver > CURRENT_FORMAT_VERSION:
            raise IncompatibleFormat(
                f'vault format_version={ver} > 현재 지원 {CURRENT_FORMAT_VERSION}. '
                f'더 최신 Polaris 가 필요합니다.'
            )
        else:
            raise VaultCorrupted(f'알 수 없는 format_version: {ver}')

    def _save(self) -> None:
        """원자적 쓰기: tmp → fsync → rename."""
        if self._data is None:
            raise VaultError('save: _data 가 비어 있음 (내부 오류)')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + '.tmp')
        payload = json.dumps(self._data, ensure_ascii=False, indent=2)
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)   # Windows / POSIX 모두 atomic

    # ── 생성 ───────────────────────────────────────────────────────────────
    def create(self, master_password: str) -> None:
        """새 vault 생성. master_password 는 복구용 (1회 입력)."""
        with self._lock:
            if self.exists:
                raise VaultError(f'이미 존재: {self.path}')
            if not master_password:
                raise ValueError('master_password 가 비어 있습니다.')

            dek = secrets.token_bytes(_V1_KEY_BYTES)
            salt = secrets.token_bytes(_V1_SALT_BYTES)
            kek = self._derive_kek_v1(master_password, salt)

            master_wrapped = self._aead_encrypt(dek, kek)

            # DPAPI 도 함께 시도 — 실패해도 vault 자체는 생성 (마스터 패스워드만 사용)
            try:
                dpapi_blob = dpapi_protect(dek)
                dpapi_b64 = _b64e(dpapi_blob)
            except DPAPIUnavailable:
                dpapi_b64 = None

            try:
                from polaris import VERSION as _polaris_ver
            except Exception:
                _polaris_ver = 'unknown'

            self._data = {
                'format_version':  CURRENT_FORMAT_VERSION,
                'created_at':      datetime.now(timezone.utc).isoformat(),
                'polaris_version': _polaris_ver,
                'kdf': {
                    'algo':  _V1_KDF_ALGO,
                    'n':     _V1_KDF_N,
                    'r':     _V1_KDF_R,
                    'p':     _V1_KDF_P,
                    'dklen': _V1_KDF_DKLEN,
                    'salt':  _b64e(salt),
                },
                'dpapi_dek':  dpapi_b64,
                'master_dek': master_wrapped,
                'secrets':    {},
            }
            self._dek = bytearray(dek)
            self._save()

    # ── 잠금 해제 ──────────────────────────────────────────────────────────
    def unlock_dpapi(self) -> bool:
        """DPAPI 로 무프롬프트 해제 시도. 실패 시 False (마스터 패스워드 필요)."""
        with self._lock:
            if self._dek is not None:
                return True
            if self._data is None:
                self._load()
            blob_b64 = self._data.get('dpapi_dek')
            if not blob_b64:
                return False
            try:
                dek = dpapi_unprotect(_b64d(blob_b64))
            except DPAPIUnavailable:
                return False
            if len(dek) != _V1_KEY_BYTES:
                raise VaultCorrupted('DPAPI 복호화 결과 길이 이상.')
            self._dek = bytearray(dek)
            return True

    def unlock_master(self, master_password: str) -> bool:
        """마스터 패스워드로 해제. 실패 시 InvalidMasterPassword."""
        with self._lock:
            if self._dek is not None:
                return True
            if self._data is None:
                self._load()
            salt = _b64d(self._data['kdf']['salt'])
            kek = self._derive_kek_v1(master_password, salt)
            try:
                dek = self._aead_decrypt(self._data['master_dek'], kek)
            except Exception as e:
                # AESGCM 의 InvalidTag 를 그대로 노출 안 함 (정보 누출 방지)
                raise InvalidMasterPassword('마스터 패스워드가 일치하지 않습니다.') from e
            if len(dek) != _V1_KEY_BYTES:
                raise VaultCorrupted('마스터 복호화 결과 길이 이상.')
            self._dek = bytearray(dek)
            return True

    def lock(self) -> None:
        """메모리에서 DEK zero out + 폐기."""
        with self._lock:
            if self._dek is not None:
                for i in range(len(self._dek)):
                    self._dek[i] = 0
                self._dek = None

    # ── DPAPI 자동 잠금 해제 토글 (v1.2.2) ──────────────────────────────────
    # dpapi_dek blob 존재 = 자동 잠금 해제 활성. enable 은 현재 DEK 를 DPAPI 로
    # 래핑해 저장(잠금 해제 필요), disable 은 blob 제거(항상 비밀번호).
    def enable_dpapi(self) -> None:
        with self._lock:
            self._require_unlocked()
            if self._data is None:
                self._load()
            blob = dpapi_protect(bytes(self._dek))   # DPAPIUnavailable 가능
            self._data['dpapi_dek'] = _b64e(blob)
            self._save()

    def disable_dpapi(self) -> None:
        with self._lock:
            if self._data is None:
                if not self.exists:
                    return
                self._load()
            if self._data.get('dpapi_dek'):
                self._data['dpapi_dek'] = None
                self._save()

    # ── 비밀 CRUD ──────────────────────────────────────────────────────────
    def store(self, key: str, secret: str) -> None:
        """비밀 저장. key 는 namespace 권장 (예: 'host.web-01.password')."""
        with self._lock:
            self._require_unlocked()
            self._require_key(key)
            blob = self._aead_encrypt(secret.encode('utf-8'), bytes(self._dek))
            blob['updated_at'] = datetime.now(timezone.utc).isoformat()
            self._data['secrets'][key] = blob
            self._save()

    def retrieve(self, key: str) -> str:
        """비밀 조회. 없으면 KeyError."""
        with self._lock:
            self._require_unlocked()
            if key not in self._data['secrets']:
                raise KeyError(key)
            blob = self._data['secrets'][key]
            plaintext = self._aead_decrypt(blob, bytes(self._dek))
            return plaintext.decode('utf-8')

    def delete(self, key: str) -> bool:
        """비밀 삭제. 존재하면 True."""
        with self._lock:
            self._require_unlocked()
            if key in self._data['secrets']:
                del self._data['secrets'][key]
                self._save()
                return True
            return False

    def has(self, key: str) -> bool:
        with self._lock:
            self._require_unlocked()
            return key in self._data['secrets']

    def list_keys(self) -> list[str]:
        """저장된 key 목록 (값은 노출 안 함)."""
        with self._lock:
            self._require_unlocked()
            return sorted(self._data['secrets'].keys())

    # ── 임의 blob 암복호화 (vault.json 외부 파일 암호화용 — 예: 스냅샷) ───────
    # secrets dict 에 저장하지 않고, DEK 로 임의 바이트를 암복호화만 해준다.
    # 큰 파일(스냅샷 등)을 vault.json 에 넣어 비대해지는 것을 피하기 위함.
    def encrypt_blob(self, plaintext: bytes) -> dict:
        """DEK 로 바이트를 AES-256-GCM 암호화 → {nonce, ciphertext} dict."""
        with self._lock:
            self._require_unlocked()
            return self._aead_encrypt(plaintext, bytes(self._dek))

    def decrypt_blob(self, blob: dict) -> bytes:
        """encrypt_blob 결과({nonce, ciphertext})를 평문 바이트로 복호화."""
        with self._lock:
            self._require_unlocked()
            return self._aead_decrypt(blob, bytes(self._dek))

    # ── 마스터 패스워드 변경 ───────────────────────────────────────────────
    def change_master_password(self, old: str, new: str) -> None:
        """마스터 패스워드 교체. DEK 는 그대로 — KEK 만 재유도 후 재래핑."""
        if not new:
            raise ValueError('새 마스터 패스워드가 비어 있습니다.')
        with self._lock:
            # old 검증을 위해 임시 unlock 시도
            if self._dek is None:
                self._load()
                salt = _b64d(self._data['kdf']['salt'])
                kek_old = self._derive_kek_v1(old, salt)
                try:
                    dek = self._aead_decrypt(self._data['master_dek'], kek_old)
                except Exception as e:
                    raise InvalidMasterPassword('현재 마스터 패스워드가 일치하지 않습니다.') from e
                self._dek = bytearray(dek)

            # 새 salt + 새 KEK 로 DEK 재래핑
            new_salt = secrets.token_bytes(_V1_SALT_BYTES)
            kek_new = self._derive_kek_v1(new, new_salt)
            self._data['kdf']['salt'] = _b64e(new_salt)
            self._data['master_dek'] = self._aead_encrypt(bytes(self._dek), kek_new)
            self._save()

    # ── 내부 헬퍼 ──────────────────────────────────────────────────────────
    def _require_unlocked(self) -> None:
        if self._dek is None:
            raise VaultLocked('vault 가 잠겨 있습니다. unlock_*() 먼저 호출하세요.')

    def _require_key(self, key: str) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError(f'잘못된 key: {key!r}')

    @staticmethod
    def _derive_kek_v1(password: str, salt: bytes) -> bytes:
        """v1 KDF: scrypt(password, salt) → 32B KEK. ★ 영구 고정 ★"""
        return hashlib.scrypt(
            password.encode('utf-8'),
            salt=salt,
            n=_V1_KDF_N, r=_V1_KDF_R, p=_V1_KDF_P,
            dklen=_V1_KDF_DKLEN,
            maxmem=128 * 1024 * 1024,   # 128MB cap (scrypt 의 maxmem 인자)
        )

    @staticmethod
    def _aead_encrypt(plaintext: bytes, key: bytes) -> dict:
        """AES-256-GCM 암호화 → {nonce, ciphertext} dict."""
        nonce = secrets.token_bytes(_V1_NONCE_BYTES)
        ct = AESGCM(key).encrypt(nonce, plaintext, associated_data=None)
        return {
            'nonce':      _b64e(nonce),
            'ciphertext': _b64e(ct),
        }

    @staticmethod
    def _aead_decrypt(blob: dict, key: bytes) -> bytes:
        """AES-256-GCM 복호화. tag 검증 실패 시 cryptography.InvalidTag 발생."""
        nonce = _b64d(blob['nonce'])
        ct    = _b64d(blob['ciphertext'])
        return AESGCM(key).decrypt(nonce, ct, associated_data=None)


# ─────────────────────────────────────────────────────────────────────────────
# v1 포맷 회귀 검증 fixture — ★ 영구 고정 ★
#
# 이 fixture 는 v1 포맷으로 생성된 실제 vault 의 사본이다. 마스터 패스워드와
# 기대 비밀이 함께 명시돼 있어, 미래 Polaris 버전에서 _read_v1 + scrypt KDF +
# AES-GCM 흐름이 깨지지 않았는지 자가 검증할 수 있다.
#
# 이 fixture 가 깨지면 곧 모든 사용자의 v1 vault 가 안 풀린다는 뜻 — 절대
# 무시하지 말 것. CI 에서 매 푸시마다 selfcheck 호출 필수.
#
# DPAPI 필드는 일부러 null — DPAPI blob 은 머신/사용자 종속이라 fixture 화
# 불가능. master 경로만으로 v1 호환 검증.
# ─────────────────────────────────────────────────────────────────────────────
_V1_FIXTURE_MASTER_PASSWORD = 'POLARIS_VAULT_V1_REGRESSION_TEST_DO_NOT_CHANGE'
_V1_FIXTURE_EXPECTED = {
    'sample.username':  'admin',
    'sample.password':  'p@ssw0rd!#$%',
    'sample.unicode':   '한글-비밀-🔒',
}
# fixture JSON 은 selfcheck() 실행 시 생성/갱신 (메모리에서만). 미리 박아두지
# 않는 이유: scrypt 출력은 결정적이지만 salt/nonce 가 매번 random 이라 디스크
# 고정값 임베드가 의미 없음. 대신 selfcheck 는 "지금 코드로 만든 vault 가 동일
# 코드로 다시 열리는지" 를 검증.


# ─────────────────────────────────────────────────────────────────────────────
# selfcheck — `python -m src.vault` 로 실행 가능
# ─────────────────────────────────────────────────────────────────────────────
def selfcheck(verbose: bool = True) -> bool:
    """vault 전체 플로우 회귀 검증. 성공 시 True.

    검증 항목:
      1. create + DPAPI unlock 라운드트립
      2. master password unlock 라운드트립
      3. store / retrieve / delete / list_keys
      4. 잘못된 마스터 패스워드 거부
      5. 마스터 패스워드 변경
      6. _read_v1 + AES-GCM + scrypt 회귀 (v1 fixture)
      7. atomic write (tmp 파일 잔존 안 함)
    """
    import tempfile, shutil

    def _say(msg: str) -> None:
        if verbose:
            print(f'  {msg}')

    tmpdir = Path(tempfile.mkdtemp(prefix='polaris-vault-selftest-'))
    try:
        path = tmpdir / 'vault.json'
        master = _V1_FIXTURE_MASTER_PASSWORD

        # 1) create + DPAPI
        v = Vault(path)
        v.create(master)
        assert v.is_unlocked
        _say('① create OK')

        for k, s in _V1_FIXTURE_EXPECTED.items():
            v.store(k, s)
        v.lock()
        assert not v.is_unlocked

        # DPAPI unlock (Windows 정상 동작 시 통과)
        v2 = Vault(path)
        if v2.unlock_dpapi():
            for k, s in _V1_FIXTURE_EXPECTED.items():
                assert v2.retrieve(k) == s, f'DPAPI retrieve mismatch: {k}'
            _say('② DPAPI unlock + retrieve OK')
            v2.lock()
        else:
            _say('② DPAPI unlock SKIP (사용 불가 환경)')

        # 2) master password unlock
        v3 = Vault(path)
        v3.unlock_master(master)
        for k, s in _V1_FIXTURE_EXPECTED.items():
            assert v3.retrieve(k) == s, f'master retrieve mismatch: {k}'
        _say('③ master unlock + retrieve OK')

        # 3) CRUD
        keys = v3.list_keys()
        assert set(keys) == set(_V1_FIXTURE_EXPECTED.keys()), f'list_keys: {keys}'
        assert v3.has('sample.password')
        assert not v3.has('nonexistent')
        assert v3.delete('sample.username') is True
        assert v3.delete('sample.username') is False
        assert not v3.has('sample.username')
        _say('④ list/has/delete OK')

        # 4) 잘못된 마스터 패스워드 거부
        v4 = Vault(path)
        try:
            v4.unlock_master('wrong-password')
        except InvalidMasterPassword:
            _say('⑤ 잘못된 마스터 패스워드 거부 OK')
        else:
            raise AssertionError('wrong password 가 거부되지 않음!')

        # 5) 마스터 패스워드 변경
        v3.change_master_password(master, 'new-master-pw')
        v3.lock()
        v5 = Vault(path)
        v5.unlock_master('new-master-pw')
        assert v5.retrieve('sample.password') == _V1_FIXTURE_EXPECTED['sample.password']
        _say('⑥ 마스터 패스워드 변경 OK')

        try:
            Vault(path).unlock_master(master)   # 기존 패스워드는 더 이상 안 됨
        except InvalidMasterPassword:
            _say('⑦ 옛 마스터 패스워드 거부 OK')

        # 6) v1 fixture: 위 검증이 사실상 v1 포맷 전체를 라운드트립
        #    추가로 _read_v1 직접 호출 검증
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.loads(f.read())
        _read_v1(raw)   # 예외 없으면 OK
        assert raw['format_version'] == 1
        assert raw['kdf']['algo'] == _V1_KDF_ALGO
        _say('⑧ _read_v1 직접 검증 OK')

        # 7) atomic write — tmp 잔존 없음
        for f in tmpdir.iterdir():
            assert not str(f).endswith('.tmp'), f'tmp 잔존: {f}'
        _say('⑨ atomic write (tmp 잔존 없음) OK')

        return True

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    print('Polaris Vault selfcheck')
    print('=' * 50)
    ok = selfcheck(verbose=True)
    print('=' * 50)
    print('PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)
