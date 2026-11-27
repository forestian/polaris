/**
 * v1.3.41 성능 — 겹치지 않는 폴러(P8).
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { startPoll, appendCapped } from './poll.js'

// ── startPoll ────────────────────────────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms))

test('앞 호출이 끝나기 전에는 다음을 부르지 않는다', async () => {
  let active = 0, maxActive = 0, calls = 0
  const stop = startPoll(async () => {
    active++; calls++; maxActive = Math.max(maxActive, active)
    await sleep(25)                      // 간격(1ms)보다 훨씬 느린 응답
    active--
  }, 1, { pauseHidden: false, immediate: true })
  await sleep(160)
  stop()
  assert.equal(maxActive, 1, '겹쳐 뜨면 drain 로그의 순서가 뒤집힌다')
  assert.ok(calls >= 3)
})

test('false 를 돌려주면 멈춘다', async () => {
  let calls = 0
  startPoll(async () => { calls++; return calls < 3 ? undefined : false }, 1,
            { pauseHidden: false, immediate: true })
  await sleep(80)
  assert.equal(calls, 3)
})

test('던져도 다음 차례에 다시 부른다', async () => {
  let calls = 0
  const stop = startPoll(async () => { calls++; if (calls === 1) throw new Error('x') }, 1,
                         { pauseHidden: false, immediate: true })
  await sleep(60)
  stop()
  assert.ok(calls >= 2)
})

test('창이 숨겨진 동안은 부르지 않는다', async () => {
  let visible = false, calls = 0
  const stop = startPoll(async () => { calls++ }, 1, { immediate: true, isVisible: () => visible })
  await sleep(30)
  assert.equal(calls, 0)
  visible = true
  await sleep(700)                       // 숨김 중 재확인 간격(최소 500ms) 뒤
  stop()
  assert.ok(calls >= 1)
})

test('stop 뒤로는 부르지 않는다', async () => {
  let calls = 0
  const stop = startPoll(async () => { calls++ }, 5, { pauseHidden: false })
  stop()
  await sleep(40)
  assert.equal(calls, 0)
})

test('appendCapped', () => {
  const a = [1, 2]
  assert.equal(appendCapped(a, [], 5), a, '붙일 게 없으면 같은 배열')
  assert.deepEqual(appendCapped([1, 2, 3], [4, 5, 6], 4), [3, 4, 5, 6])
  assert.deepEqual(appendCapped(null, [1], 4), [1])
})
