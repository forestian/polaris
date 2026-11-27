/**
 * 보관함 잠금 게이트 판단 테스트 (v1.2.167).
 *
 * 이 파일이 잠그는 것: **Hello 요구가 켜져 있으면 절대 조용히 열리지 않는다.**
 * 개발 중 처음 쓴 조건은 `required && available` 이었는데, 그러면 카메라·지문
 * 인식기가 고장난 순간 아무 알림 없이 예전처럼 자동 개방된다 — 사용자가 막으려던
 * 바로 그 상황이다. 마스터 비밀번호 경로는 항상 있으니 막아도 잠기는 사람은 없다.
 */
import { test } from 'node:test'
import assert from 'node:assert'
import { shouldSilentUnlock, helloButtonReady, canRequireHello } from './vaultGate.js'

const DPAPI = { available: true, exists: true, has_dpapi: true, unlocked: false }
const HELLO = { ok: true, required: false, available: true, has_dpapi: true }

test('자동 해제 설정 + Hello 요구 없음 → 조용히 연다', () => {
  assert.equal(shouldSilentUnlock(DPAPI, HELLO), true)
})

test('Hello 요구가 켜져 있으면 열지 않는다', () => {
  assert.equal(shouldSilentUnlock(DPAPI, { ...HELLO, required: true }), false)
})

test('Hello 장치가 고장나도 요구가 켜져 있으면 열지 않는다 (fail-closed)', () => {
  // 이 한 줄이 이 기능의 존재 의미다 — available 을 조건에 넣으면 여기서 열린다
  const dead = { ...HELLO, required: true, available: false, state: 'DeviceNotPresent' }
  assert.equal(shouldSilentUnlock(DPAPI, dead), false)
})

test('상태 조회 실패(null·ok:false)면 열지 않는다', () => {
  assert.equal(shouldSilentUnlock(DPAPI, null), false)
  assert.equal(shouldSilentUnlock(DPAPI, { ok: false, error: 'x' }), false)
})

test('자동 해제가 설정돼 있지 않으면 애초에 열 수 없다', () => {
  for (const patch of [{ has_dpapi: false }, { exists: false }, { available: false }]) {
    assert.equal(shouldSilentUnlock({ ...DPAPI, ...patch }, HELLO), false,
      JSON.stringify(patch))
  }
})

test('이미 열려 있으면 다시 열지 않는다', () => {
  assert.equal(shouldSilentUnlock({ ...DPAPI, unlocked: true }, HELLO), false)
})

test('status 가 없어도 터지지 않는다', () => {
  assert.equal(shouldSilentUnlock(null, HELLO), false)
  assert.equal(shouldSilentUnlock(undefined, undefined), false)
})

test('버튼: Hello 도 DPAPI 도 있어야 띄운다', () => {
  assert.equal(helloButtonReady(HELLO), true)
  assert.equal(helloButtonReady({ ...HELLO, available: false }), false,
    'Hello 를 못 쓰면 버튼은 눌러도 실패한다')
  assert.equal(helloButtonReady({ ...HELLO, has_dpapi: false }), false,
    '확인해 준 뒤에 "열 수 없다" 고 하면 안 된다')
  assert.equal(helloButtonReady(null), false)
})

test('설정 체크박스 활성 조건은 버튼 조건과 같다', () => {
  assert.equal(canRequireHello(HELLO), true)
  assert.equal(canRequireHello({ ...HELLO, has_dpapi: false }), false)
})
