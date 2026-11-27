/**
 * 설정 창 탭 줄 (v1.3.52) — 탭이 가로 스크롤 뒤로 숨지 않는다.
 *
 * 탭이 8개(업데이트 추가)가 되자 680px 창에서 마지막 「업데이트」 탭이 스크롤 뒤로 숨어
 * 있는 줄도 몰랐다(사용자 신고). 창을 넓히고, 그래도 좁으면 줄을 바꾼다.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const src = readFileSync(new URL('./components/SettingsModal.jsx', import.meta.url), 'utf8')

test('창이 탭 8개를 한 줄에 담을 만큼 넓다', () => {
  const w = Number(src.match(/className="modal" style=\{\{ width: (\d+)/)[1])
  assert.ok(w >= 800, `설정 창 너비 ${w}px — 탭 8개(약 750px)가 한 줄에 안 들어간다`)
})

test('좁으면 가로 스크롤이 아니라 줄 바꿈', () => {
  const strip = src.slice(src.indexOf("display: 'flex', gap: 6, padding: '10px 14px 0'"),
                          src.indexOf('{TABS.map('))
  assert.match(strip, /flexWrap: 'wrap'/)
  assert.doesNotMatch(strip, /overflowX: 'auto'/)
})
