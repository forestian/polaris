/**
 * v1.3.75 성능 12·13 — 쿠버네티스 쪽(무료판에도 남는 화면).
 * 12: 겹치지 않고 창이 숨으면 쉬는 폴링(startPoll)  13: 표 줄이 실시간 갱신마다 다시 그려지던 것
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8')

test('폴링 — setInterval(api…) 대신 startPoll', () => {
  for (const [f, re] of [
    ['./components/MetricsTab.jsx', /const stop = startPoll\(tick, POLL_MS, \{ immediate: true \}\)/],
    ['./pages/EventsPage.jsx', /return startPoll\(load, 10000\)/],
    ['./pages/PortForwardPage.jsx', /return startPoll\(refreshSessions, 2000\)/],
  ]) {
    const src = read(f)
    assert.match(src, re, f)
    assert.doesNotMatch(src, /setInterval\(/, f)
  }
})

test('ResourceTable — 보이는 칸이 같으면 그 줄은 다시 그리지 않고, 누르면 최신 행', () => {
  const src = read('./components/ResourceTable.jsx')
  assert.match(src, /function sameCells\(a, b, columns\)/)
  assert.match(src, /p\.colsKey === n\.colsKey/)
  assert.match(src, /&& sameCells\(p\.row, n\.row, n\.columns\)\)/)
  assert.match(src, /const row = byKeyRef\.current\.get\(k\)/)
  assert.doesNotMatch(src, /onClick=\{\(\) => onSelect\?\.\(row\)\}/, '옛 행 객체를 넘기지 않는다')
})
