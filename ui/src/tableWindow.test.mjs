import { test } from 'node:test'
import assert from 'node:assert/strict'
import { visibleWindow, rowKey, rowKeys, WINDOW_MIN_ROWS, OVERSCAN } from './tableWindow.js'

test('적은 목록은 전부 그린다', () => {
  assert.deepEqual(visibleWindow(WINDOW_MIN_ROWS, 5000, 600, 31),
                   { start: 0, end: WINDOW_MIN_ROWS, top: 0, bottom: 0 })
})

test('긴 목록은 보이는 구간 + 여유만', () => {
  const w = visibleWindow(5000, 31 * 1000, 620, 31)     // 1000번째 행이 맨 위
  assert.equal(w.start, 1000 - OVERSCAN)
  assert.equal(w.end, 1000 + 20 + OVERSCAN)
  assert.equal(w.top, w.start * 31)
  assert.equal(w.bottom, (5000 - w.end) * 31)
  assert.ok(w.end - w.start < 100, '4만 칸이 아니라 수십 행')
})

test('전체 높이는 창 방식이어도 같다 — 스크롤바가 튀지 않는다', () => {
  for (const top of [0, 999, 31 * 2500, 31 * 4999, 10 ** 9]) {
    const w = visibleWindow(5000, top, 600, 31)
    assert.equal(w.top + (w.end - w.start) * 31 + w.bottom, 5000 * 31, String(top))
    assert.ok(w.start >= 0 && w.end <= 5000 && w.start <= w.end)
  }
})

test('행 key 는 순번이 아니라 이름', () => {
  assert.equal(rowKey({ name: 'p', namespace: 'n', _kind: 'pod' }, 3), 'pod|n|p')
  assert.equal(rowKey({ _uid: 'u' }, 0), 'u')
  assert.equal(rowKey({}, 7), 'i7')
})

test('이름이 겹쳐도 key 는 겹치지 않는다', () => {
  const ks = rowKeys([{ name: 'a' }, { name: 'a' }, { name: 'b' }, { name: 'a' }])
  assert.equal(new Set(ks).size, 4)
})
