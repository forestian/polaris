"""VaultMixin — 코어 비밀 저장소 API (시작 잠금 / kubeconfig 보관).

Vault 는 v1.2.1 부터 코어 기능. 무료/풀 빌드 모두 포함.

정책:
  - 시작 시 항상 마스터 비밀번호 입력 (DPAPI 무프롬프트 자동 해제 비활성)
  - 첫 실행: vault_init 으로 비밀번호 생성 → vault 생성
  - 이후: vault_unlock(master_password) 로 잠금 해제
  - kubeconfig 본문을 vault 에 저장 → 파일 경로 의존 없이 재연결

vault 인스턴스는 self._polaris_vault 에 단일 인스턴스로 보관 (_vault()) →
snapshot 등 모든 mixin 이 같은 잠금 상태를 공유.
"""
import threading

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
        """DPAPI 자동 잠금 해제 시도 (비밀번호 생략 모드). 실패 시 비밀번호 필요.

        Windows Hello 요구(v1.2.167)가 켜져 있으면 **여기서 거절한다.** 화면 쪽에서만
        막으면 이 메서드를 직접 부르는 새 호출 지점이 하나 생기는 순간 설정이 조용히
        무력화된다 — 보장을 실제로 여는 함수에 붙여 둔다.
        """
        if self._hello_required():
            return {'ok': False, 'need_hello': True,
                    'error': 'Windows Hello 확인이 필요합니다.'}
        return self._unlock_dpapi_now()

    def _unlock_dpapi_now(self) -> dict:
        """실제 DPAPI 해제. Hello 확인을 통과한 경로에서만 직접 부른다.

        `_` 접두 — pywebview 는 이런 이름을 JS 에 노출하지 않으므로(util.py 의
        `name.startswith('_')` 필터) 화면에서 게이트를 건너뛸 방법이 없다.
        """
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

    # ── Windows Hello (v1.2.167) ───────────────────────────────────────────
    # DPAPI 자동 해제는 사용자 확인 없이 보관함을 연다 — 잠기지 않은 Windows 세션에
    # 앉은 사람은 누구나 접속정보를 볼 수 있다. 그 앞에 Hello 확인을 세운다.
    #
    # Hello 는 **키를 주지 않는다**(확인 결과만 돌려준다). 복호화는 종전대로 DPAPI 가
    # 하므로 이 기능은 '새 암호 계층' 이 아니라 '사람 확인' 이다 — 화면에도 그렇게 쓴다.
    def hello_status(self) -> dict:
        """Hello 사용 가능 여부 + 이 보관함에 요구 설정이 켜져 있는지."""
        from src import hello as _hello
        st = _hello.availability()
        v = self._vault()
        return {'ok': True, 'available': st['available'], 'state': st['state'],
                'error': st.get('error'),
                'required': bool(self._hello_required()),
                'has_dpapi': bool(v.exists and v.has_dpapi)}

    def _hello_required(self) -> bool:
        """설정값 — 자동 해제 전에 Hello 확인을 요구할지."""
        try:
            return bool((self.get_settings() or {}).get('security', {}).get('require_hello'))
        except Exception:
            return False

    def vault_set_require_hello(self, enable: bool) -> dict:
        """Hello 요구 설정 저장.

        **끌 때도 확인한다** (v1.3.39). 예전에는 「끄는 건 완화」라며 그냥 껐다 —
        그런데 이 기능이 막으려는 사람(자리를 비운 사이 앉은 사람)이 바로 그것을
        할 수 있었다: 끄고 → 자동 잠금 해제로 연다. 그래서 끄려면 **보관함이 열려
        있거나**(이미 본인 확인을 거쳤다) **Hello 확인을 통과**해야 한다.
        """
        enable = bool(enable)
        if not enable and self._hello_required():
            v = self._vault()
            if not v.is_unlocked:
                from src import hello as _hello
                res = _hello.verify('Polaris — Windows Hello 요구 끄기')
                if not res.get('verified'):
                    return {'ok': False, 'state': res.get('state'),
                            'error': '본인 확인이 필요합니다 — 보관함을 먼저 열거나 '
                                     'Windows Hello 확인을 통과해야 끌 수 있습니다.'}
        if enable:
            from src import hello as _hello
            st = _hello.availability()
            if not st['available']:
                return {'ok': False, 'error': f"Windows Hello 를 쓸 수 없습니다 ({st['state']})"}
            v = self._vault()
            if not (v.exists and v.has_dpapi):
                return {'ok': False,
                        'error': '자동 잠금 해제(이 PC)를 먼저 켜야 합니다 — '
                                 'Hello 는 확인만 하고 복호화는 DPAPI 가 합니다.'}
        try:
            cur = self.get_settings() or {}
            sec = dict(cur.get('security') or {})
            sec['require_hello'] = enable
            # save_settings 는 이 값을 일부러 무시한다 — 여기서만 바꾼다
            clean = self._normalize_settings({**cur, 'security': sec})
            r = self._write_settings(clean)
            if not r.get('ok'):
                return r
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        return {'ok': True, 'require_hello': enable}

    def vault_unlock_hello(self) -> dict:
        """Hello 확인 → 성공하면 DPAPI 로 잠금 해제.

        확인이 안 되면(취소·시간초과·장치 없음) **아무것도 열지 않는다** — 실패는
        전부 '잠긴 상태 유지' 하나로 수렴한다.
        """
        v = self._vault()
        if not v.exists:
            return {'ok': False, 'error': 'vault 가 없습니다.', 'need_init': True}
        if v.is_unlocked:
            return {'ok': True, 'already': True}
        if not v.has_dpapi:
            return {'ok': False, 'need_master': True,
                    'error': '자동 잠금 해제가 설정되지 않았습니다 — 마스터 비밀번호로 여세요.'}
        from src import hello as _hello
        res = _hello.verify('Polaris 보안 보관함 잠금 해제')
        if not res['verified']:
            state = res.get('state') or 'error'
            msg = {'Canceled': '확인이 취소됐습니다.',
                   'Timeout': '확인 시간이 지났습니다.',
                   'DeviceNotPresent': 'Windows Hello 장치가 없습니다.',
                   'NotConfiguredForUser': 'Windows Hello 가 설정되지 않았습니다.',
                   'DisabledByPolicy': '정책으로 차단돼 있습니다.',
                   'RetriesExhausted': '확인 시도 횟수를 초과했습니다.'}.get(
                       state, f'확인 실패 ({state})')
            return {'ok': False, 'error': msg, 'state': state, 'need_master': True}
        return self._unlock_dpapi_now()

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

    # ── MCP 액세스 토큰 (v1.2.119) ─────────────────────────────────────────
    # 헤드리스 MCP 서버가 vault 를 여는 유일한 경로. DPAPI 는 GUI 전용이라
    # MCP 에서 쓰지 않는다.
    def vault_issue_mcp_token(self, label: str = '', scope: str = 'read',
                              expires_days: int = 90) -> dict:
        """토큰 발급. 전체 토큰 문자열은 **이 응답에서 딱 한 번만** 반환된다."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        if not v.exists:
            return {'ok': False, 'error': 'vault 가 없습니다.', 'need_init': True}
        if not v.is_unlocked:
            return {'ok': False, 'error': '보안 보관함이 잠겨 있습니다. 먼저 잠금을 해제하세요.'}
        try:
            days = max(0, min(int(expires_days or 0), 3650))
        except Exception:
            days = 90
        try:
            # 이 판의 MCP 는 조회 전용 — 어떤 값이 와도 read 토큰만 발급한다
            token = v.issue_mcp_token(label=label, scope='read', expires_days=days)
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        return {'ok': True, 'token': token, 'tokens': v.list_mcp_tokens(), 'launch': self.mcp_launch_command()}

    @staticmethod
    def mcp_launch_command() -> dict:
        """MCP 클라이언트 설정에 넣을 **이 PC 의 실제** 실행 명령(v1.5.55).

        안내 문서의 예시 경로(Program Files)가 실제 설치 위치(%LOCALAPPDATA%\\Programs\\Polaris)와 달라
        새 PC 에서 연결이 실패했다(사용자 신고). 화면이 이 값으로 설정 전체를 만들어 복사하게 한다.
        """
        import sys
        from pathlib import Path
        if getattr(sys, 'frozen', False):
            return {'command': str(Path(sys.executable).resolve()), 'args': ['--mcp']}
        root = Path(__file__).resolve().parents[2]
        return {'command': str(Path(sys.executable).resolve()), 'args': [str(root / 'polaris.py'), '--mcp']}

    def vault_list_mcp_tokens(self) -> dict:
        """발급된 토큰 목록 (비밀값 미포함)."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.', 'tokens': []}
        try:
            return {'ok': True, 'tokens': self._vault().list_mcp_tokens()}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'tokens': []}

    def vault_revoke_mcp_token(self, token_id: str) -> dict:
        """토큰 폐기. 즉시 그 토큰으로는 vault 를 열 수 없게 된다."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        try:
            removed = v.revoke_mcp_token((token_id or '').strip())
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        if not removed:
            return {'ok': False, 'error': '해당 토큰을 찾을 수 없습니다.',
                    'tokens': v.list_mcp_tokens()}
        return {'ok': True, 'tokens': v.list_mcp_tokens()}

    def vault_unlock_token(self, token: str) -> dict:
        """MCP 토큰으로 잠금 해제 (헤드리스 전용). 토큰 값은 응답에 넣지 않는다."""
        if not HAS_CRYPTO:
            return {'ok': False, 'error': 'cryptography 패키지가 없습니다.'}
        v = self._vault()
        if not v.exists:
            return {'ok': False, 'error': 'vault 가 없습니다.', 'need_init': True}
        if v.is_unlocked:
            return {'ok': True, 'already': True, 'token': None}
        try:
            meta = v.unlock_token(token or '')
        except Exception as e:
            return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        if meta is None:
            return {'ok': False, 'error': '유효하지 않은 토큰입니다.'}
        return {'ok': True, 'token': meta}

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

    def rename_kubeconfig(self, old_name: str, new_name: str) -> dict:
        """보관된 kubeconfig 의 이름(키)을 변경 — 기존 데이터를 새 이름으로 이전하고
        옛 키는 삭제(덮어쓰기 의미). 새 이름이 이미 있으면 충돌 에러(conflict)."""
        v = self._vault()
        if not v.is_unlocked:
            return {'ok': False, 'error': 'vault 가 잠겨 있습니다.'}
        old_name = (old_name or '').strip()
        new_name = (new_name or '').strip()
        if not new_name:
            return {'ok': False, 'error': '이름이 필요합니다.'}
        old_key = _KCFG_PREFIX + old_name
        new_key = _KCFG_PREFIX + new_name
        try:
            if old_key == new_key:
                return {'ok': True, 'name': new_name}
            if not v.has(old_key):
                return {'ok': False, 'error': '보관된 kubeconfig 가 없습니다.', 'missing': True}
            if v.has(new_key):
                return {'ok': False, 'conflict': True,
                        'error': f"'{new_name}' 이름의 보관 항목이 이미 있습니다. 다른 이름을 사용하세요."}
            content = v.retrieve(old_key)
            v.store(new_key, content)   # 새 이름으로 저장
            v.delete(old_key)           # 옛 이름 제거 (이전 완료)
            return {'ok': True, 'name': new_name}
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
        groups = {'kubeconfig': [], 'snapshot': [], 'other': []}
        for k in sorted(keys):
            if k.startswith(_KCFG_PREFIX):
                groups['kubeconfig'].append(k[len(_KCFG_PREFIX):])
            elif k.startswith('snapshot.'):
                groups['snapshot'].append(k)
            else:
                groups['other'].append(k)
        return {'ok': True, 'groups': groups, 'total': len(keys)}
