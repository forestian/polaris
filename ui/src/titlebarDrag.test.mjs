import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

// v1.2.151 제목표시줄 드래그 — 최대화 상태에서 끌면 복원.
//
// 왜 pywebview 내장 드래그를 안 쓰는지: 내장 구현은 mousedown 시점의 clientX/Y 를
// '잡은 지점' 으로 고정한다. 최대화 상태에서 드래그를 시작하면 그 순간 창을
// 복원해야 하는데(브라우저와 같은 동작), 복원으로 창이 작아지면 그 고정값이
// 창 밖을 가리켜 창이 커서 옆으로 튄다. 그래서 직접 다룬다.

const read = p => readFileSync(new URL(p, import.meta.url), 'utf8')
const app = read('./App.jsx')
const apijs = read('./api.js')

test('본창 타이틀바가 pywebview 내장 드래그를 쓰지 않는다', () => {
  // 둘 다 걸리면 서로 창을 옮기려 해 좌표가 싸운다
  const titlebar = app.slice(app.indexOf('function Titlebar'), app.indexOf('function ClusterTabStrip'))
  assert.ok(!titlebar.includes('pywebview-drag-region'),
    '본창 타이틀바는 useTitlebarDrag 로만 옮겨야 한다')
})

test('드래그 시작 시 window_drag_begin 을 부른다', () => {
  assert.match(app, /window\.pywebview\.api\.window_drag_begin\(/,
    '최대화 여부 판단과 복원은 백엔드가 한다')
  assert.match(apijs, /windowDragBegin:\s*\(sx, sy\)\s*=>\s*callSafe\('window_drag_begin', sx, sy\)/)
})

// ── v1.2.152 — 클릭만 해도 창이 마우스를 따라다니던 문제 ────────────────────
test('누르는 것만으로는 드래그가 시작되지 않는다', () => {
  // 누르자마자 시작하면 ① 클릭·더블클릭이 드래그가 되고
  // ② 최대화 창이 더블클릭 전에 복원돼 곧바로 다시 최대화된다
  assert.match(app, /const TITLEBAR_DRAG_THRESHOLD = \d+/)
  assert.match(app, /Math\.abs\(ev\.screenX - p\.sx\) < TITLEBAR_DRAG_THRESHOLD/,
    '문턱을 넘는 이동이 있어야 드래그로 본다')
  // pointerdown 안에서 곧바로 드래그를 켜면 안 된다.
  // (존재 확인 `?.window_drag_begin) return` 은 호출이 아니므로 `(` 까지 본다)
  const down = app.slice(app.indexOf('function onPointerDown'), app.indexOf('function onPointerMove'))
  assert.ok(!down.includes('window_drag_begin('),
    'window_drag_begin 은 이동이 확인된 뒤에 불러야 한다')
})

test('응답을 기다리는 사이 손을 떼면 드래그를 시작하지 않는다', () => {
  // 브리지 응답이 pointerup 보다 늦게 오면, 확인 없이는 버튼을 뗀 뒤에
  // 드래그가 켜져 마우스만 올려도 창이 끌려다닌다
  assert.match(app, /if \(press\.current !== p\) return/)
})

test('버튼을 뗀 상태의 이동은 드래그를 끝낸다', () => {
  // 놓친 pointerup 에 대비한 안전장치
  assert.match(app, /if \(ev\.buttons === 0\) \{ endDrag\(\); return \}/)
})

test('pointercancel·캡처 상실도 드래그를 끝낸다', () => {
  assert.match(app, /onPointerCancel: endDrag/)
  assert.match(app, /onLostPointerCapture: endDrag/)
})

test('이동 위치를 백엔드가 준 grab 오프셋으로만 계산한다', () => {
  assert.match(app, /x:\s*Math\.round\(ev\.screenX \* d\.dpr\) - d\.gx/,
    '복원 후 커서가 잡은 지점에 그대로 붙어 있어야 한다')
  assert.match(app, /y:\s*Math\.round\(ev\.screenY \* d\.dpr\) - d\.gy/)
})

test('복원되면 최대화 상태를 프론트에 알린다', () => {
  // 캡션 버튼 아이콘과 리사이즈 핸들이 이 이벤트를 보고 갱신된다
  assert.match(app, /if \(r\.restored\)/)
  assert.match(app, /new CustomEvent\('polaris:maximized', \{ detail: false \}\)/)
})

test('타이틀바 안의 버튼에서 시작한 눌림은 드래그가 아니다', () => {
  // 검색창·설정 버튼을 누르려다 창이 끌려가면 안 된다
  assert.match(app, /ev\.target\.closest\?\.\('button, input, select, a, \[data-no-drag\]'\)/)
})

test('좌클릭만 드래그로 잡는다', () => {
  assert.match(app, /if \(ev\.button !== 0\) return/)
})

test('이동 호출을 rAF 로 합친다', () => {
  // mousemove 는 초당 수십~수백 번 온다 — 매번 브리지를 부르면 창이 끊긴다
  assert.match(app, /if \(!raf\.current\) raf\.current = requestAnimationFrame\(flush\)/)
})

test('더블클릭 최대화는 그대로 유지된다', () => {
  assert.match(app, /onDoubleClick: toggleMaximizeFromTitlebar/)
})
