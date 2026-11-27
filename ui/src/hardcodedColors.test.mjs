import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import { THEMES } from './themeRegistry.js'
import { contrast } from './customTheme.js'

// v1.3.36 — 밝은 테마에서 **사라지는 글자색** 가드.
//
// 사용자 신고: Forestia(밝은 종이) 에서 메모의 코드블록이 안 보였다. 원인은
// `color: '#c3e88d'` — 어두운 배경을 전제로 고른 연두를 박아 둔 것이었다.
// 밝은 배경 위에서 대비가 **1.11:1**, 즉 사실상 투명이었다.
//
// 테마가 늘어날수록 이런 자리는 반드시 또 생긴다. 사람이 눈으로 찾을 수 없으므로
// (어두운 테마에서는 멀쩡해 보인다) 계산으로 잡는다.

// 저장소 경로에 한글이 들어 있어 URL 이 퍼센트 인코딩된다 —
// pathname 을 직접 자르면 '%ED%81%B4…' 가 그대로 남아 폴더를 못 찾는다.
const SRC = path.dirname(fileURLToPath(import.meta.url))
const LIGHT_BG = THEMES.forestia.tokens['--bg-1']
const MIN = 3.0   // 본문 기준 4.5 보다 느슨하게 — 아이콘·배지도 섞여 있다

// 색이 **데이터이거나** 배경이 따로 있는 곳. 이유를 적어 두지 않으면
// 다음 사람이 "왜 여기만 예외지?" 에서 멈춘다.
const ALLOW = [
  {
    color: '#fff',
    why: '색이 채워진 버튼 위의 흰 글자 — 배경이 --red/--nimbus 라 읽힌다. '
       + '이 검사는 페이지 배경과만 비교하므로 여기서는 오탐이다.',
  },
]

function walk(dir) {
  const out = []
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name)
    if (statSync(full).isDirectory()) out.push(...walk(full))
    else if (name.endsWith('.jsx')) out.push(full)
  }
  return out
}

function parseHex(hex) {
  let s = hex.replace('#', '')
  if (s.length === 3) s = [...s].map(c => c + c).join('')
  if (s.length !== 6) return null
  return '#' + s.toLowerCase()
}

test('밝은 테마에서 안 보이게 될 하드코딩 글자색이 없다', () => {
  const re = /\bcolor\s*:\s*'(#[0-9a-fA-F]{3,6})'/g
  const bad = []
  for (const full of walk(SRC)) {
    const rel = path.relative(SRC, full).split(path.sep).join('/')
    if (ALLOW.some(a => a.file === rel)) continue
    const lines = readFileSync(full, 'utf8').split('\n')
    lines.forEach((line, i) => {
      const s = line.trim()
      if (s.startsWith('//') || s.startsWith('*')) return
      for (const m of line.matchAll(re)) {
        if (ALLOW.some(a => a.color === m[1])) continue
        const hex = parseHex(m[1])
        if (!hex) continue
        const r = contrast(LIGHT_BG, hex)
        if (r < MIN) bad.push(`${rel}:${i + 1} ${m[1]} → ${r.toFixed(2)}:1`)
      }
    })
  }
  assert.deepEqual(
    bad, [],
    `밝은 테마(${LIGHT_BG}) 위에서 ${MIN}:1 미만인 하드코딩 색이 있다. `
    + `토큰(var(--red) 등)으로 바꾸거나, 색이 데이터라면 이 파일의 ALLOW 에 `
    + `이유와 함께 적을 것:\n  ` + bad.join('\n  '))
})

test('가드가 실제로 잡는지', () => {
  // 사고 났던 그 색 그대로 — 이 값이 통과하면 가드가 헛돌고 있는 것이다
  assert.ok(contrast(LIGHT_BG, '#c3e88d') < MIN)
  assert.ok(contrast(LIGHT_BG, '#33281a') > MIN)
})
