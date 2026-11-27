import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  CUSTOM_DEFAULTS, CUSTOM_PRESETS, TOKEN_ORDER,
  contrast, customWarnings, isLightColor, makeCustomTokens, mix,
  normalizeCustom, parseHex,
} from './customTheme.js'

// v1.3.34 — 커스텀 테마. 「배경을 하얗게 쓰고 싶다」는 요청에서 나왔다.
//
// 여기서 잠그는 것은 **읽을 수 있는가**다. 색 취향은 사용자 몫이지만, 우리가
// 자동으로 만들어 주는 값들이 읽을 수 없게 나오면 그건 우리 잘못이다.

test('배경 밝기에 따라 쌓는 방향이 뒤집힌다', () => {
  // 어두운 테마는 단계가 올라갈수록 밝아지고, 밝은 테마는 어두워진다.
  // 이걸 안 뒤집으면 흰 배경에 흰 카드가 얹혀 아무것도 안 보인다.
  const dark = makeCustomTokens({ bg: '#14161a', text: '#e6e6ea', accent: '#e0b64c' })
  const light = makeCustomTokens({ bg: '#ffffff', text: '#18181b', accent: '#1d4ed8' })
  const lum = h => parseHex(h).reduce((a, b) => a + b, 0)
  assert.ok(lum(dark['--bg-5']) > lum(dark['--bg-1']), '어두운 테마는 위로 갈수록 밝아야 한다')
  assert.ok(lum(light['--bg-5']) < lum(light['--bg-1']), '밝은 테마는 위로 갈수록 어두워야 한다')
})

test('페이지 바탕은 본문 면보다 어둡다 (밝든 어둡든)', () => {
  for (const bg of ['#ffffff', '#f4f1e8', '#14161a']) {
    const tk = makeCustomTokens({ bg, text: '#808080', accent: '#888888' })
    const lum = h => parseHex(h).reduce((a, b) => a + b, 0)
    assert.ok(lum(tk['--bg-0']) < lum(tk['--bg-1']), `${bg}: bg-0 가 bg-1 보다 어두워야 한다`)
  }
})

test('기본 프리셋은 모두 본문 대비 4.5:1 을 넘는다', () => {
  for (const p of CUSTOM_PRESETS) {
    const tk = makeCustomTokens(p)
    const r = contrast(tk['--bg-1'], tk['--text'])
    assert.ok(r >= 4.5, `${p.label}: 본문 대비 ${r.toFixed(2)}:1`)
  }
})

test('흐린 글자도 읽을 수 있어야 한다', () => {
  // 밝은 테마에서 어두운 테마와 같은 비율로 물리면 4.5 밑으로 떨어졌다(실측 4.04).
  for (const p of CUSTOM_PRESETS) {
    const tk = makeCustomTokens(p)
    const r = contrast(tk['--bg-1'], tk['--text-dim'])
    assert.ok(r >= 4.5, `${p.label}: 흐린 글자 대비 ${r.toFixed(2)}:1`)
  }
})

test('강조색 위 글자는 검정·흰색 중 더 잘 보이는 쪽을 고른다', () => {
  // 밝기 임계값으로 고르면 중간 톤에서 틀린다 — 금색(#a9741a)에 흰 글자를
  // 얹어 4.0:1 이 나왔던 실측 사고.
  for (const accent of ['#a9741a', '#1d4ed8', '#e0b64c', '#0f766e', '#888888']) {
    const tk = makeCustomTokens({ bg: '#ffffff', text: '#000000', accent })
    const ink = tk['--accent-ink']
    const other = ink === '#ffffff' ? '#17130a' : '#ffffff'
    assert.ok(contrast(accent, ink) >= contrast(accent, other),
      `${accent}: 덜 보이는 쪽(${ink})을 골랐다`)
  }
})

test('이상한 값을 넣어도 기본값으로 버틴다', () => {
  for (const bad of [null, undefined, 42, 'red', { bg: 'nope' }, { bg: '#12345' }]) {
    const c = normalizeCustom(bad)
    assert.ok(parseHex(c.bg) && parseHex(c.text) && parseHex(c.accent))
  }
  assert.equal(normalizeCustom({ bg: '#FFF' }).bg, '#ffffff', '3자리 표기도 받아야 한다')
})

test('덮어쓰기는 토큰 이름과 색 형식이 맞는 것만 받는다', () => {
  const c = normalizeCustom({
    overrides: {
      '--bg-2': '#123456',        // OK
      '--bg-3': 'javascript:x',   // 색이 아니다
      'bg-4': '#000000',          // 토큰 이름이 아니다
      '--x; color: red': '#000',  // CSS 주입 시도
    },
  })
  assert.deepEqual(Object.keys(c.overrides), ['--bg-2'])
})

test('덮어쓴 토큰이 자동값을 이긴다', () => {
  const tk = makeCustomTokens({ bg: '#ffffff', text: '#000000', accent: '#1d4ed8',
                                overrides: { '--bg-2': '#abcdef' } })
  assert.equal(tk['--bg-2'], '#abcdef')
})

test('편집기가 보여 주는 토큰 목록이 실제 토큰과 일치한다', () => {
  // 목록에만 있고 실제로는 안 만들어지는 토큰이 있으면 색을 골라도 아무 일이 없다
  const tk = makeCustomTokens(CUSTOM_DEFAULTS)
  for (const name of TOKEN_ORDER) {
    assert.ok(tk[name], `${name} 를 편집기는 보여 주는데 토큰은 안 만든다`)
  }
})

test('읽기 힘든 조합은 경고한다 (막지는 않는다)', () => {
  const warns = customWarnings({ bg: '#ffffff', text: '#eeeeee', accent: '#fafafa' })
  assert.ok(warns.length >= 1)
  assert.equal(customWarnings({ bg: '#ffffff', text: '#111111', accent: '#1d4ed8' }).length, 0)
})

test('색 계산 기본기', () => {
  assert.equal(mix('#000000', '#ffffff', 0.5), '#808080')
  assert.equal(mix('#ff0000', '#0000ff', 0), '#ff0000')
  assert.ok(isLightColor('#ffffff'))
  assert.ok(!isLightColor('#000000'))
  assert.ok(Math.abs(contrast('#ffffff', '#000000') - 21) < 0.1)
})
