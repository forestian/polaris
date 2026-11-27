import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

// v1.2.131 — --text-dim/--text-mid 가독성 회귀 테스트 (2차 개선 포함).
//
// 1차: --text-dim 대비 2.6~2.8:1(WCAG 최소 4.5:1 미달) → 명도만 올려 4.3~5.4:1.
// 그런데 사용자가 "여전히 흐리다"고 재지적했고, 원인이 두 가지였다:
//   ① index.css 의 :root 블록에 themeRegistry.js 수정 전 값(#5a5878)이 그대로
//      하드코딩돼 남아있었다 — 한쪽만 고치고 다른 쪽을 안 맞춘 회귀.
//   ② 1차 목표치(4.3~5.4:1)가 "겨우 통과" 수준이라 체감 개선이 작았다.
// 2차로 --text-dim/--text-mid 둘 다 더 밝게(6.7~9:1) 올리고, themeRegistry.js 와
// index.css 가 어긋나지 않는지까지 이 테스트가 함께 잠근다.

const themeSrc = readFileSync(new URL('./themeRegistry.js', import.meta.url), 'utf8')
const cssSrc = readFileSync(new URL('./index.css', import.meta.url), 'utf8')

// ── WCAG 2.x 상대 휘도 / 대비비 계산 (독립 구현 — 앱 코드에 안 의존) ─────────────
function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16))
}
function relLum([r, g, b]) {
  const f = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 }
  const [fr, fg, fb] = [f(r), f(g), f(b)]
  return 0.2126 * fr + 0.7152 * fg + 0.0722 * fb
}
function contrastHex(hexA, hexB) {
  const [la, lb] = [relLum(hexToRgb(hexA)), relLum(hexToRgb(hexB))].sort((a, b) => b - a)
  return (la + 0.05) / (lb + 0.05)
}
function hslToHex(h, s, l) {
  s /= 100; l /= 100
  const k = n => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  const toHex = x => Math.round(x * 255).toString(16).padStart(2, '0')
  return `#${toHex(f(0))}${toHex(f(8))}${toHex(f(4))}`
}

function fixedVar(name) {
  const m = themeSrc.match(new RegExp(`'${name}':\\s*'(#[0-9a-fA-F]{6})'`))
  assert.ok(m, `themeRegistry.js 에서 고정 ${name} 값을 찾지 못함`)
  return m[1]
}
function brandVarLightness(name, sat) {
  const m = themeSrc.match(new RegExp('\'' + name + '\':\\s*`hsl\\(\\$\\{th\\},\\s*' + sat + '%,\\s*(\\d+)%\\)`'))
  assert.ok(m, `브랜드 공식의 ${name} 표현식을 찾지 못함(hsl(th,${sat}%,N%) 형태 기대)`)
  return Number(m[1])
}

test('Polaris 고정 팔레트: --text-dim/--text-mid 이 배경(bg-1/2/3) 대비 6.5 이상이다', () => {
  const dim = fixedVar('--text-dim')
  const mid = fixedVar('--text-mid')
  for (const bg of ['#0b1024', '#131734', '#1c2046']) {   // bg-1, bg-2, bg-3
    const cd = contrastHex(dim, bg)
    const cm = contrastHex(mid, bg)
    assert.ok(cd >= 6.5, `text-dim ${dim} vs ${bg} 대비 ${cd.toFixed(2)} — 2차 개선 목표(6.5) 미달`)
    assert.ok(cm >= 7.5, `text-mid ${mid} vs ${bg} 대비 ${cm.toFixed(2)} — 2차 개선 목표(7.5) 미달`)
  }
})

test('Polaris 고정 팔레트: 예전 값들이 남아있지 않다', () => {
  assert.notEqual(fixedVar('--text-dim').toLowerCase(), '#5a5878', '1차 이전 값이 남아있음')
  assert.notEqual(fixedVar('--text-dim').toLowerCase(), '#8684a4', '1차 값에서 2차 개선이 안 됨')
})

test('index.css 의 :root fallback 이 themeRegistry.js 의 Polaris 값과 정확히 일치한다', () => {
  // FOUC 방지용 fallback(:root, data-theme 적용 전)이 실제 테마 값과 어긋나면,
  // 첫 페인트 순간 옛 흐린 색이 그대로 보인다 — 한 번 실제로 발생한 회귀라 잠근다.
  for (const name of ['--text-dim', '--text-mid']) {
    const themeVal = fixedVar(name)
    const m = cssSrc.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6});`))
    assert.ok(m, `index.css 에서 ${name} 를 찾지 못함`)
    assert.equal(m[1].toLowerCase(), themeVal.toLowerCase(),
      `index.css 의 ${name}(${m[1]}) 이 themeRegistry.js(${themeVal}) 와 다르다 — ` +
      `한쪽만 고치면 최초 페인트 순간 옛 값이 보인다`)
  }
})

test('브랜드 테마 공식: --text-dim/--text-mid 명도가 충분히 올라갔다 (실제 배경 대비로 확인)', () => {
  const dimL = brandVarLightness('--text-dim', 20)
  const midL = brandVarLightness('--text-mid', 16)
  assert.ok(dimL >= 65, `text-dim 명도 ${dimL}% — 2차 개선 목표(65%) 미달`)
  assert.ok(midL >= 70, `text-mid 명도 ${midL}% — 2차 개선 목표(70%) 미달`)

  // 대표 테마(argus, h=208, s=45→cs=28) 로 실제 배경 대비까지 확인
  const h = 208, cs = 28
  const bgs = [hslToHex(h, cs, 6), hslToHex(h, cs, 10), hslToHex(h, cs, 15)]
  const dim = hslToHex(h, 20, dimL)
  const mid = hslToHex(h, 16, midL)
  for (const bg of bgs) {
    assert.ok(contrastHex(dim, bg) >= 6.0, `${dim} vs ${bg} 대비 부족`)
    assert.ok(contrastHex(mid, bg) >= 7.0, `${mid} vs ${bg} 대비 부족`)
  }
})

test('--text-dim 이 --text-mid 보다는 여전히 어둡다 (위계 유지)', () => {
  // 가독성을 고치면서 '흐린 텍스트'와 '중간 텍스트'의 구분이 없어지면 안 된다.
  const bg = '#131734'
  assert.ok(contrastHex(fixedVar('--text-dim'), bg) < contrastHex(fixedVar('--text-mid'), bg),
    'text-dim 이 text-mid 보다 더 밝아지면 두 단계의 시각적 위계가 무너진다')
  assert.ok(brandVarLightness('--text-dim', 20) < brandVarLightness('--text-mid', 16))
})

test('--text-mid 가 --text(가장 밝은 보조색) 보다는 여전히 어둡다', () => {
  const bg = '#131734'
  assert.ok(contrastHex(fixedVar('--text-mid'), bg) < contrastHex(fixedVar('--text'), bg),
    'text-mid 가 --text 보다 밝아지면 3단계 위계(dim/mid/text)가 무너진다')
})
