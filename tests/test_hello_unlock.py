# -*- coding: utf-8 -*-
"""Windows Hello 잠금 해제 테스트 (v1.2.167).

이 파일이 잠그는 것:
  1) **확인 실패는 전부 '잠긴 상태 유지'** 로 수렴한다. 취소·시간초과·장치 없음에서
     보관함이 열리면 이 기능의 존재 의미가 없다.
  2) Hello 는 키를 주지 않으므로 **DPAPI 가 없으면 켤 수 없다** — 켜지게 두면
     "확인은 되는데 열리지 않는" 상태가 된다.
  3) 설정은 화이트리스트를 통과해야 한다 — `security` 를 정규화에 넣지 않으면
     save_settings 가 조용히 버려 다음 실행에서 설정이 사라진다(개발 중 실제로 겪었다).

실제 얼굴/지문 확인은 사람이 있어야 하므로, verify 는 대역으로 바꿔 검증한다.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from src.api import PolarisAPI
from src import hello as hello_mod


class SettingsWhitelistTests(unittest.TestCase):
    def test_security_섹션이_정규화를_통과한다(self):
        out = PolarisAPI._normalize_settings({'security': {'require_hello': True}})
        self.assertEqual(out['security'], {'require_hello': True})

    def test_모르는_키는_버린다(self):
        out = PolarisAPI._normalize_settings({'security': {'require_hello': True, 'x': 1}})
        self.assertEqual(out['security'], {'require_hello': True})

    def test_없으면_기본_False(self):
        self.assertEqual(PolarisAPI._normalize_settings({})['security'],
                         {'require_hello': False})


class _FakeVault:
    def __init__(self, exists=True, unlocked=False, dpapi=True):
        self.exists = exists
        self.is_unlocked = unlocked
        self.has_dpapi = dpapi
        self.dpapi_calls = 0

    def unlock_dpapi(self):
        self.dpapi_calls += 1
        self.is_unlocked = True
        return True


class HelloUnlockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='polaris-hello-'))
        self.api = PolarisAPI()
        self.api._SETTINGS_PATH = self.tmp / 'settings.json'
        self.vault = _FakeVault()
        self.api._polaris_vault = self.vault
        self._orig_verify = hello_mod.verify
        self._orig_avail = hello_mod.availability
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        # **진짜 Hello 창이 뜨지 않게** 기본을 대역으로 둔다 — 대역을 깜빡한 테스트가
        # 사용자 화면에 얼굴 인식 창을 띄우고 시간 초과까지 기다린 일이 있었다(v1.3.39).
        self._verify('Canceled')
        self._avail(False, 'DeviceNotPresent')

    def tearDown(self):
        hello_mod.verify = self._orig_verify
        hello_mod.availability = self._orig_avail

    def _verify(self, state):
        hello_mod.verify = lambda *a, **k: {'verified': state == 'Verified',
                                            'state': state, 'error': None}

    def _avail(self, ok=True, state='Available'):
        hello_mod.availability = lambda *a, **k: {'available': ok, 'state': state,
                                                  'error': None}

    def test_확인되면_DPAPI_로_연다(self):
        self._verify('Verified')
        r = self.api.vault_unlock_hello()
        self.assertTrue(r['ok'], r)
        self.assertEqual(self.vault.dpapi_calls, 1)
        self.assertTrue(self.vault.is_unlocked)

    def test_취소되면_열지_않는다(self):
        self._verify('Canceled')
        r = self.api.vault_unlock_hello()
        self.assertFalse(r['ok'])
        self.assertIn('취소', r['error'])
        self.assertEqual(self.vault.dpapi_calls, 0)
        self.assertFalse(self.vault.is_unlocked)

    def test_시간초과도_열지_않는다(self):
        self._verify('Timeout')
        r = self.api.vault_unlock_hello()
        self.assertFalse(r['ok'])
        self.assertEqual(self.vault.dpapi_calls, 0)

    def test_장치_없음_설정_안됨_정책차단_모두_안전하게_실패(self):
        for state in ('DeviceNotPresent', 'NotConfiguredForUser', 'DisabledByPolicy',
                      'RetriesExhausted', 'error', '알 수 없는 값'):
            self.vault.is_unlocked = False
            self.vault.dpapi_calls = 0
            self._verify(state)
            r = self.api.vault_unlock_hello()
            self.assertFalse(r['ok'], state)
            self.assertEqual(self.vault.dpapi_calls, 0, state)
            self.assertTrue(r['error'])

    def test_DPAPI_가_없으면_Hello_를_묻지도_않는다(self):
        self.vault.has_dpapi = False
        called = []
        hello_mod.verify = lambda *a, **k: called.append(1) or {'verified': True,
                                                                'state': 'Verified'}
        r = self.api.vault_unlock_hello()
        self.assertFalse(r['ok'])
        self.assertTrue(r['need_master'])
        self.assertEqual(called, [], '열 수 없는데 확인창을 띄우면 안 된다')

    def test_이미_열려_있으면_그대로(self):
        self.vault.is_unlocked = True
        r = self.api.vault_unlock_hello()
        self.assertTrue(r['ok'])
        self.assertTrue(r['already'])

    def test_vault_가_없으면_생성_안내(self):
        self.vault.exists = False
        r = self.api.vault_unlock_hello()
        self.assertFalse(r['ok'])
        self.assertTrue(r['need_init'])


class RequireHelloSettingTests(HelloUnlockTests):
    def test_설정_저장과_조회(self):
        self._avail(True)
        r = self.api.vault_set_require_hello(True)
        self.assertTrue(r['ok'], r)
        self.assertTrue(self.api._hello_required())
        st = self.api.hello_status()
        self.assertTrue(st['required'])

    def test_Hello_를_못_쓰면_켤_수_없다(self):
        self._avail(False, 'DeviceNotPresent')
        r = self.api.vault_set_require_hello(True)
        self.assertFalse(r['ok'])
        self.assertIn('DeviceNotPresent', r['error'])
        self.assertFalse(self.api._hello_required())

    def test_자동해제가_꺼져_있으면_켤_수_없다(self):
        # Hello 는 확인만 한다 — DPAPI 가 없으면 확인해도 열 수 없다
        self._avail(True)
        self.vault.has_dpapi = False
        r = self.api.vault_set_require_hello(True)
        self.assertFalse(r['ok'])
        self.assertIn('자동 잠금 해제', r['error'])

    # v1.3.39 — 예전에는 「끄는 건 완화」라며 조건 없이 껐다. 그런데 이 기능이 막으려는
    # 사람(자리를 비운 사이 앉은 사람)이 **끄고 → 자동 해제로 여는** 길이 됐다.
    def test_잠긴_채로는_확인_없이_끌_수_없다(self):
        self._avail(True)
        self.api.vault_set_require_hello(True)
        self._verify('Canceled')
        r = self.api.vault_set_require_hello(False)
        self.assertFalse(r['ok'])
        self.assertTrue(self.api._hello_required(), '확인 없이 꺼지면 우회로가 된다')

    def test_잠긴_채라도_Hello_확인을_통과하면_끈다(self):
        self._avail(True)
        self.api.vault_set_require_hello(True)
        self._verify('Verified')
        r = self.api.vault_set_require_hello(False)
        self.assertTrue(r['ok'], r)
        self.assertFalse(self.api._hello_required())

    def test_장치가_사라져도_보관함을_열면_끌_수_있다(self):
        # 마스터 비밀번호 경로는 항상 열려 있다 — 그걸로 연 뒤에는 조건 없이 끈다
        self._avail(True)
        self.api.vault_set_require_hello(True)
        self._avail(False, 'DeviceNotPresent')
        self.vault.is_unlocked = True
        called = []
        hello_mod.verify = lambda *a, **k: called.append(1) or {'verified': False}
        r = self.api.vault_set_require_hello(False)
        self.assertTrue(r['ok'], r)
        self.assertEqual(called, [], '이미 본인 확인을 거쳤으니 다시 묻지 않는다')
        self.assertFalse(self.api._hello_required())

    def test_일반_설정_저장으로는_끌_수_없다(self):
        # save_settings 는 화면이 설정 전체를 보낼 때 쓴다 — 여기로 끌 수 있으면
        # 위의 확인을 그냥 돌아간다.
        self._avail(True)
        self.api.vault_set_require_hello(True)
        cur = self.api.get_settings()
        r = self.api.save_settings({**cur, 'security': {'require_hello': False}})
        self.assertTrue(r['ok'], r)
        self.assertTrue(self.api._hello_required())

    def test_일반_설정_저장으로_켜지지도_않는다(self):
        # 켤 때의 조건(Hello 사용 가능 · 자동 해제 켜짐)도 같은 함수만 본다
        cur = self.api.get_settings()
        self.api.save_settings({**cur, 'security': {'require_hello': True}})
        self.assertFalse(self.api._hello_required())

    def test_설정이_파일에_남는다(self):
        # security 를 화이트리스트에 넣지 않으면 여기서 사라진다
        self._avail(True)
        self.api.vault_set_require_hello(True)
        import json
        raw = json.loads(self.api._SETTINGS_PATH.read_text(encoding='utf-8'))
        self.assertTrue(raw['security']['require_hello'])


class BackendGateTests(HelloUnlockTests):
    """설정의 보장은 화면이 아니라 **실제로 여는 함수**에 붙어 있어야 한다."""

    def _require(self):
        self._avail(True)
        r = self.api.vault_set_require_hello(True)
        self.assertTrue(r['ok'], r)

    def test_요구가_켜지면_DPAPI_직접호출을_거절한다(self):
        # 화면에서만 막으면, 이 메서드를 부르는 호출 지점이 하나 생기는 순간
        # 설정이 조용히 무력화된다
        self._require()
        r = self.api.vault_unlock_dpapi()
        self.assertFalse(r['ok'])
        self.assertTrue(r['need_hello'])
        self.assertEqual(self.vault.dpapi_calls, 0)
        self.assertFalse(self.vault.is_unlocked)

    def test_요구가_켜져도_Hello_경로는_열린다(self):
        # vault_unlock_hello 가 공개 API 를 부르면 자기 자신에게 막힌다 —
        # 설정을 켠 순간 Hello 버튼이 영구히 실패하는 교착이 된다
        self._require()
        self._verify('Verified')
        r = self.api.vault_unlock_hello()
        self.assertTrue(r['ok'], r)
        self.assertEqual(self.vault.dpapi_calls, 1)
        self.assertTrue(self.vault.is_unlocked)

    def test_요구를_끄면_DPAPI_가_다시_열린다(self):
        self._require()
        self._verify('Verified')          # 잠긴 채로 끄려면 본인 확인이 필요하다(v1.3.39)
        self.assertTrue(self.api.vault_set_require_hello(False)['ok'])
        r = self.api.vault_unlock_dpapi()
        self.assertTrue(r['ok'], r)
        self.assertEqual(self.vault.dpapi_calls, 1)

    def test_게이트를_우회하는_공개_메서드가_없다(self):
        # pywebview 는 '_' 접두 이름을 JS 에 노출하지 않는다(webview/util.py).
        # 실제 해제 구현이 공개 이름으로 남아 있으면 화면에서 그냥 부를 수 있다.
        self.assertTrue(hasattr(self.api, '_unlock_dpapi_now'))
        exposed = [n for n in dir(self.api)
                   if not n.startswith('_') and 'dpapi' in n.lower()]
        # 게이트가 붙은 vault_unlock_dpapi 하나만 노출돼야 한다.
        # (마스터 비밀번호 해제 vault_unlock 은 Hello 대상이 아니다 — Hello 는
        #  '확인 없이 조용히 열리는' DPAPI 경로만 막는다.)
        self.assertEqual(sorted(exposed), ['vault_unlock_dpapi'],
                         f'JS 에 노출되는 DPAPI 해제 경로가 늘었다: {exposed} — '
                         f'게이트를 지나지 않는 경로인지 확인할 것')


class HelloModuleTests(unittest.TestCase):
    """PowerShell 호출 계층 — 새 파이썬 의존성 없이 WinRT 를 쓴다."""

    def test_availability_형태(self):
        st = hello_mod.availability()
        for k in ('available', 'state'):
            self.assertIn(k, st)
        self.assertIsInstance(st['available'], bool)

    def test_메시지에_따옴표가_섞여도_스크립트가_깨지지_않는다(self):
        # PowerShell 작은따옴표 문자열 — 그 안에서는 $변수 · $(식)이 펼쳐지지 않고 ' 는 '' 로 겹친다(v1.4.24)
        seen = {}
        real = hello_mod._run_ps
        hello_mod._run_ps = lambda script, timeout: (seen.setdefault('s', script), ('Verified', None))[1]
        try:
            hello_mod.verify("it's \"quoted\" $(calc)\nnewline")
        finally:
            hello_mod._run_ps = real
        line = next(l for l in seen['s'].splitlines() if 'RequestVerificationAsync' in l)
        self.assertIn("'it''s \"quoted\" $(calc) newline'", line)

    def test_확인_창_문구가_한글_그대로(self):
        # 예전엔 json.dumps(ASCII 만)라 확인 창에 \ubcf4\uc548… 이 그대로 보였다
        seen = {}
        real = hello_mod._run_ps
        hello_mod._run_ps = lambda script, timeout: (seen.setdefault('s', script), ('Verified', None))[1]
        try:
            hello_mod.verify()
        finally:
            hello_mod._run_ps = real
        self.assertIn('Polaris 보안 보관함 잠금 해제', seen['s'])
        self.assertNotIn('\\u', seen['s'])

    def test_winrt_바인딩을_import_하지_않는다(self):
        # frozen 빌드에서 네이티브 모듈이 빠지면 조용히 죽는다(v1.2.114 교훈)
        src = Path(hello_mod.__file__).read_text(encoding='utf-8')
        for bad in ('import winsdk', 'import winrt', 'from winsdk', 'from winrt'):
            self.assertNotIn(bad, src)


if __name__ == '__main__':
    unittest.main()
