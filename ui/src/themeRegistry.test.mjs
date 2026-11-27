import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  THEMES,
  THEME_IDS,
  normalizeThemeId,
  toCssVariableBlock,
} from './themeRegistry.js'

test('defines Polaris plus the five requested background themes', () => {
  // v1.3.34: 사용자가 직접 만드는 'custom' 이 마지막에 붙는다.
  // 순서는 화면 카드 배열 순서와 같다 — 커스텀은 항상 맨 뒤.
  assert.deepEqual(
    THEME_IDS,
    ['polaris', 'argus', 'aurora', 'forge', 'vault', 'pharos', 'forestia', 'custom'],
  )
  assert.equal(THEMES.polaris.label, 'Polaris')
  assert.equal(THEMES.argus.label, 'Argus')
  assert.equal(THEMES.aurora.label, 'Aurora')
  assert.equal(THEMES.forge.label, 'Forge')
  assert.equal(THEMES.vault.label, 'Vault')
  assert.equal(THEMES.pharos.label, 'Pharos')
  assert.equal(THEMES.forestia.label, 'Forestia')
  assert.equal(THEMES.custom.label, '커스텀')
})

test('normalizes unknown or empty theme ids to Polaris', () => {
  assert.equal(normalizeThemeId('aurora'), 'aurora')
  assert.equal(normalizeThemeId(''), 'polaris')
  assert.equal(normalizeThemeId(null), 'polaris')
  assert.equal(normalizeThemeId('brand-name-not-installed'), 'polaris')
})

test('exports only color CSS variables, leaving brand identity untouched', () => {
  const css = toCssVariableBlock('argus')

  assert.match(css, /--bg-0:/)
  assert.match(css, /--text-bright:/)
  assert.match(css, /--nimbus:/)
  assert.doesNotMatch(css, /POLARIS/)
  assert.doesNotMatch(css, /logo/i)
  assert.doesNotMatch(css, /icon/i)
})

// ── Forestia (v1.3.35) ──────────────────────────────────────────────────────
// 게임 스크린샷에서 뽑은 색이라 「분위기」 가 목적이지만, 그렇다고 안 읽히면
// 테마가 아니라 그림이다. 밝은 배경 위에서 글자로 쓰이는 색들을 전부 잠근다.

test('Forestia 는 밝은 테마다', async () => {
  const { isLightColor } = await import('./customTheme.js')
  const t = THEMES.forestia.tokens
  assert.ok(isLightColor(t['--bg-1']), '양피지 바탕이 밝아야 게임 UI 인상이 산다')
  // 밝은 테마이므로 단계가 올라갈수록 어두워져야 한다
  const sum = h => [1, 3, 5].reduce((a, i) => a + parseInt(h.slice(i, i + 2), 16), 0)
  assert.ok(sum(t['--bg-5']) < sum(t['--bg-1']))
  assert.ok(sum(t['--bg-0']) < sum(t['--bg-1']), '페이지 바탕은 본문 면보다 어둡다')
})

test('Forestia 의 글자·상태색이 모두 4.5:1 이상이다', async () => {
  const { contrast } = await import('./customTheme.js')
  const t = THEMES.forestia.tokens
  const bg = t['--bg-1']
  for (const k of ['--text', '--text-mid', '--text-dim', '--nimbus',
                   '--green', '--yellow', '--red', '--blue', '--purple']) {
    const r = contrast(bg, t[k])
    assert.ok(r >= 4.5, `${k} = ${t[k]} → ${r.toFixed(2)}:1`)
  }
})

test('Forestia 의 버튼 글자가 강조색 위에서 읽힌다', async () => {
  const { contrast } = await import('./customTheme.js')
  const t = THEMES.forestia.tokens
  assert.ok(contrast(t['--nimbus'], t['--accent-ink']) >= 4.5)
})

test('Forestia 색이 실제 스크린샷 계열에서 왔다', async () => {
  // 색조(hue)만 본다 — 명도는 읽히게 조정했지만 계열은 바뀌면 안 된다.
  const hue = (hex) => {
    const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn
    if (!d) return 0
    let h
    if (mx === r) h = ((g - b) / d) % 6
    else if (mx === g) h = (b - r) / d + 2
    else h = (r - g) / d + 4
    return (h * 60 + 360) % 360
  }
  const t = THEMES.forestia.tokens
  // 풀빛 H94~114 (스크린샷 실측), 버섯갓/나무 H36~45, 연못 H193
  assert.ok(hue(t['--nimbus']) > 80 && hue(t['--nimbus']) < 130, '강조는 풀빛이어야 한다')
  assert.ok(hue(t['--green']) > 80 && hue(t['--green']) < 130)
  assert.ok(hue(t['--yellow']) > 25 && hue(t['--yellow']) < 60, '경고는 버섯갓/나무 계열')
  assert.ok(hue(t['--blue']) > 170 && hue(t['--blue']) < 215, '정보는 연못 계열')
})
