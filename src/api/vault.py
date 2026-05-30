"""VaultMixin — 코어 비밀 저장소 API (시작 잠금 / kubeconfig 보관).

Vault 는 v1.2.1 부터 코어 기능. 무료/풀 빌드 모두 포함.

정책:
  - 시작 시 항상 마스터 비밀번호 입력 (DPAPI 무프롬프트 자동 해제 비활성)
  - 첫 실행: vault_init 으로 비밀번호 생성 → vault 생성
  - 이후: vault_unlock(master_password) 로 잠금 해제
  - kubeconfig 본문을 vault 에 저장 → 파일 경로 의존 없이 재연결

vault 인스턴스는 self._polaris_vault 에 단일 인스턴스로 보관 (_vault()) →
infra(SSH) / snapshot 등 모든 mixin 이 같은 잠금 상태를 공유.
"""
from src.vault import (
    Vault, VaultError, VaultLocked, VaultNotFound,
    VaultCorrupted, InvalidMasterPassword, IncompatibleFormat,
    DPAPIUnavailable, HAS_CRYPTO,
)
from src.paths import polaris_dir

# kubeconfig vault 키 접두사
_KCFG_PREFIX = 'kubeconfig.'


class VaultMixin:
    # ── vault 인스턴스 (APIBase 공유) ────────────────────────────────────────
    def _vault(self) -> Vault:
        """모든 mixin 이 공유하는 단일 Vault 인스턴스.

        데이터 디렉터리 위치(polaris_dir)를 따른다 — 사용자가 위치를 바꾸면
        vault.json 도 그 위치에서 읽힘 (v1.2.2)."""
        v = getattr(self, '_polaris_vault', None)
        if v is None:
            v = Vault(polaris_dir() / 'vault.json')
            self._polaris_vault = v
        return v

    # ── 상태 / 잠금 ──────────────────────────────────────────────────────────
    def vault_status(self) -> dict:
        if not HAS_CRYPTO:
            return {'ok': False, 'available': False,
                    'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        return {
            'ok': True, 'available': True,
            'exists': v.exists, 'unlocked': v.is_unlocked,
            # has_dpapi True = 자동 잠금 해제(DPAPI) 모드 (v1.2.2)
            'has_dpapi': v.has_dpapi,
        }

    def vault_init(self, master_password: str, auto_unlock: bool = False) -> dict:
        """첫 실행 — 마스터 비밀번호로 새 vault 생성 (즉시 잠금 해제 상태).

        auto_unlock=True → DPAPI 자동 잠금 해제 활성(이 PC 에서 비밀번호 생략).
        False → 항상 비밀번호 (dpapi blob 미보관)."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        if v.exists:
            return {'ok': False, 'error': '이미 vault 가 존재합니다.'}
        if not master_password or len(master_password) < 4:
            return {'ok': False, 'error': '비밀번호는 4자 이상이어야 합니다.'}
        try:
            v.create(master_password)
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        # 모드 적용 (DPAPI 실패해도 vault 자체는 유지 — 비밀번호 모드로 동작)
        try:
            if auto_unlock:
                v.enable_dpapi()
            else:
                v.disable_dpapi()
        except Exception:
            pass
        return {'ok': True, 'has_dpapi': v.has_dpapi}

    def vault_unlock(self, master_password: str) -> dict:
        """마스터 비밀번호로 잠금 해제 (로그인)."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        if not v.exists:
            return {'ok': False, 'error': 'vault 가 없습니다.', 'need_init': True}
        if v.is_unlocked:
            return {'ok': True, 'already': True}
        if not master_password:
            return {'ok': False, 'error': '비밀번호를 입력하세요.'}
        try:
            v.unlock_master(master_password)
            return {'ok': True}
        except InvalidMasterPassword:
            return {'ok': False, 'error': '비밀번호가 일치하지 않습니다.'}
        except (VaultCorrupted, IncompatibleFormat) as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'잠금 해제 오류: {e}'}

    def vault_unlock_dpapi(self) -> dict:
        """DPAPI 자동 잠금 해제 시도 (비밀번호 생략 모드). 실패 시 비밀번호 필요."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        if not v.exists:
            return {'ok': False, 'error': 'vault 가 없습니다.', 'need_init': True}
        if v.is_unlocked:
            return {'ok': True, 'already': True}
        if not v.has_dpapi:
            return {'ok': False, 'error': '자동 잠금 해제가 설정되지 않았습니다.',
                    'need_master': True}
        try:
            if v.unlock_dpapi():
                return {'ok': True, 'used_dpapi': True}
            return {'ok': False, 'error': 'DPAPI 자동 해제 불가 (다른 PC/사용자?)',
                    'need_master': True}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'need_master': True}

    def vault_set_auto_unlock(self, enable: bool) -> dict:
        """잠금 방식 전환 (설정). enable=True → DPAPI 자동, False → 항상 비밀번호.

        vault 가 잠금 해제된 상태에서만 가능 (DEK 필요)."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        if not v.is_unlocked:
            return {'ok': False, 'error': 'vault 가 잠겨 있습니다. 먼저 잠금 해제하세요.'}
        try:
            if enable:
                v.enable_dpapi()
            else:
                v.disable_dpapi()
            return {'ok': True, 'has_dpapi': v.has_dpapi}
        except DPAPIUnavailable as e:
            return {'ok': False, 'error': f'DPAPI 사용 불가: {e}'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def vault_lock(self) -> dict:
        try:
            self._vault().lock()
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def vault_change_password(self, old: str, new: str) -> dict:
        if not new or len(new) < 4:
            return {'ok': False, 'error': '새 비밀번호는 4자 이상이어야 합니다.'}
        try:
            self._vault().change_master_password(old, new)
            return {'ok': True}
        except InvalidMasterPassword:
            return {'ok': False, 'error': '현재 비밀번호가 일치하지 않습니다.'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # ── kubeconfig 보관 ──────────────────────────────────────────────────────
    def store_kubeconfig(self, name: str, content: str) -> dict:
        """kubeconfig 본문을 vault 에 저장. name 은 표시용 식별자."""
        v = self._vault()
        if not v.is_unlocked:
            return {'ok': False, 'error': 'vault 가 잠겨 있습니다.'}
        name = (name or '').strip()
        if not name:
            return {'ok': False, 'error': '이름이 필요합니다.'}
        if not content:
            return {'ok': False, 'error': 'kubeconfig 내용이 비어 있습니다.'}
        try:
            v.store(_KCFG_PREFIX + name, content)
            return {'ok': True, 'name': name}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def list_kubeconfigs(self) -> dict:
        """vault 에 저장된 kubeconfig 이름 목록."""
        v = self._vault()
        if not v.is_unlocked:
            return {'ok': False, 'error': 'vault 가 잠겨 있습니다.', 'items': []}
        try:
            names = [k[len(_KCFG_PREFIX):] for k in v.list_keys()
                     if k.startswith(_KCFG_PREFIX)]
            return {'ok': True, 'items': sorted(names)}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'items': []}

    def get_kubeconfig(self, name: str) -> dict:
        """vault 에서 kubeconfig 본문 로드."""
        v = self._vault()
        if not v.is_unlocked:
            return {'ok': False, 'error': 'vault 가 잠겨 있습니다.'}
        key = _KCFG_PREFIX + (name or '').strip()
        try:
            if not v.has(key):
                return {'ok': False, 'error': '저장된 kubeconfig 가 없습니다.'}
            return {'ok': True, 'content': v.retrieve(key)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def delete_kubeconfig(self, name: str) -> dict:
        v = self._vault()
        if not v.is_unlocked:
            return {'ok': False, 'error': 'vault 가 잠겨 있습니다.'}
        try:
            v.delete(_KCFG_PREFIX + (name or '').strip())
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # ── 보안 보관함 (전체 키 목록 — 보안 보관함 패널용) ──────────────────────
    def vault_entries(self) -> dict:
        """vault 에 저장된 모든 항목의 분류된 목록 (값은 노출 안 함)."""
        v = self._vault()
        if not v.is_unlocked:
            return {'ok': False, 'error': 'vault 가 잠겨 있습니다.', 'groups': {}}
        try:
            keys = v.list_keys()
        except Exception as e:
            return {'ok': False, 'error': str(e), 'groups': {}}
        groups = {'kubeconfig': [], 'ssh': [], 'snapshot': [], 'other': []}
        for k in sorted(keys):
            if k.startswith(_KCFG_PREFIX):
                groups['kubeconfig'].append(k[len(_KCFG_PREFIX):])
            elif k.startswith('host.') or k.startswith('server.'):
                groups['ssh'].append(k)
            elif k.startswith('snapshot.'):
                groups['snapshot'].append(k)
            else:
                groups['other'].append(k)
        return {'ok': True, 'groups': groups, 'total': len(keys)}
