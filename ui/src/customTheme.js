/**
 * 커스텀 테마 — 배경·글자·강조 세 색에서 **전체 토큰 세트**를 만들어 낸다 (v1.3.34).
 *
 * ## 왜 토큰을 30개 다 물어보지 않는가
 *
 * 다 물어보면 고르다 지치고, 무엇보다 **읽을 수 없는 조합**이 쉽게 나온다
 * (흰 배경에 연노랑 글씨 같은 것). 그래서 세 가지만 받고 나머지는 관계로 만든다.
 * 그래도 끝까지 만지고 싶은 사람을 위해 `overrides` 로 개별 토큰을 덮어쓸 수 있다.
 *
 * ## 밝은 배경을 고르면 자동으로 밝은 테마가 된다
 *
 * 기존 테마는 전부 어두운 배경 기준이라 「단계가 올라갈수록 밝아진다」로 만들어졌다
 * (bg-0 가 제일 어둡고 bg-5 가 제일 밝다). 밝은 배경에서 그대로 하면 흰 위에 흰
 * 카드가 얹혀 아무것도 안 보인다. 그래서 **배경의 밝기를 보고 방향을 뒤집는다** —
 * 밝은 배경에서는 단계가 올라갈수록 어두워진다.
 */

// ── 색 계산 (RGB 혼합 — HSL 로 돌리면 색조가 미끄러진다) ────────────────────
function clamp255(v) {
  return Math.max(0, Math.min(255, Math.round(v)))
}

/** '#rgb' · '#rrggbb' → [r,g,b]. 못 읽으면 null. */
export function parseHex(hex) {
  const s = String(hex || '').trim().replace(/^#/, '')
  if (/^[0-9a-f]{3}$/i.test(s)) {
    return [0, 1, 2].map(i => parseInt(s[i] + s[i], 16))
  }
  if (/^[0-9a-f]{6}$/i.test(s)) {
    return [0, 2, 4].map(i => parseInt(s.slice(i, i + 2), 16))
  }
  return null
}

export function toHex(rgb) {
  return '#' + rgb.map(v => clamp255(v).toString(16).padStart(2, '0')).join('')
}

/** a 를 b 쪽으로 t(0~1) 만큼 섞는다. */
export function mix(a, b, t) {
  const A = parseHex(a) || [0, 0, 0]
  const B = parseHex(b) || [0, 0, 0]
  return toHex(A.map((v, i) => v + (B[i] - v) * t))
}

/** 상대 휘도 (WCAG). 0=검정 1=흰색. */
export function luminance(hex) {
  const rgb = parseHex(hex) || [0, 0, 0]
  const [r, g, b] = rgb.map(v => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** 두 색의 대비비 (1~21). 4.5 이상이면 본문으로 쓸 만하다. */
export function contrast(a, b) {
  const la = luminance(a)
  const lb = luminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

export function isLightColor(hex) {
  return luminance(hex) > 0.42
}

// ── 기본값 ───────────────────────────────────────────────────────────────
/** 밝은 상아색 — 「어두운 게 기본인데 하얗게 쓰고 싶다」는 요청에서 출발했다. */
export const CUSTOM_DEFAULTS = Object.freeze({
  bg: '#f4f1e8',
  text: '#201d17',
  accent: '#a9741a',
  overrides: {},
})

/** 한 번에 고르기 좋은 조합. 직접 만지기 전에 출발점으로 쓴다. */
export const CUSTOM_PRESETS = Object.freeze([
  { id: 'ivory', label: '상아', bg: '#f4f1e8', text: '#201d17', accent: '#a9741a' },
  { id: 'paper', label: '흰 종이', bg: '#ffffff', text: '#18181b', accent: '#1d4ed8' },
  { id: 'mist', label: '옅은 회색', bg: '#eef1f4', text: '#15191e', accent: '#0f766e' },
  { id: 'sand', label: '따뜻한 모래', bg: '#efe6d8', text: '#2b2118', accent: '#9a5b1c' },
  { id: 'ink', label: '먹빛(어두움)', bg: '#14161a', text: '#e6e6ea', accent: '#e0b64c' },
])

export function normalizeCustom(cfg) {
  const c = cfg && typeof cfg === 'object' ? cfg : {}
  const pick = (v, dflt) => (parseHex(v) ? toHex(parseHex(v)) : dflt)
  const ov = {}
  if (c.overrides && typeof c.overrides === 'object') {
    for (const [k, v] of Object.entries(c.overrides)) {
      // 토큰 이름과 색 형식이 맞는 것만 — 아무 문자열이나 CSS 에 흘리지 않는다
      if (/^--[a-z0-9-]+$/.test(k) && parseHex(v)) ov[k] = toHex(parseHex(v))
    }
  }
  return {
    bg: pick(c.bg, CUSTOM_DEFAULTS.bg),
    text: pick(c.text, CUSTOM_DEFAULTS.text),
    accent: pick(c.accent, CUSTOM_DEFAULTS.accent),
    overrides: ov,
  }
}

// ── 토큰 만들기 ──────────────────────────────────────────────────────────
/** 밝은 테마용 상태색 — 어두운 테마의 파스텔은 흰 배경에서 안 보인다. */
const STATUS_LIGHT = { green: '#0f7b5f', yellow: '#8a5a00', red: '#b42318', blue: '#0b5cc0', purple: '#6941c6' }
const STATUS_DARK = { green: '#7dd3fc', yellow: '#fbbf24', red: '#f87171', blue: '#7dd3fc', purple: '#b9b3df' }

export function makeCustomTokens(cfg) {
  const { bg, text, accent, overrides } = normalizeCustom(cfg)
  const light = isLightColor(bg)

  // 「쌓아 올리는」 방향. 어두우면 밝은 쪽으로, 밝으면 어두운 쪽으로 간다.
  const raise = light ? '#000000' : '#ffffff'
  const up = t => mix(bg, raise, t)

  const status = light ? STATUS_LIGHT : STATUS_DARK
  const tint = (c, t = 0.13) => mix(bg, c, t)

  const tokens = {
    // 페이지 바탕은 본문 면보다 살짝 어둡게 — 밝든 어둡든 이 관계는 같다
    '--bg-0': mix(bg, '#000000', light ? 0.05 : 0.34),
    '--bg-1': bg,
    '--bg-2': up(0.06),
    '--bg-3': up(0.13),
    '--bg-4': up(0.22),
    '--bg-5': up(0.32),
    '--border': up(0.14),
    '--border-bright': up(0.26),

    '--text': text,
    // 강조는 더 또렷하게, 보조는 배경 쪽으로 물러나게 — 위계는 밝기와 무관하다
    '--text-bright': mix(text, raise, 0.22),
    // 보조 글자를 배경 쪽으로 얼마나 물릴지. 밝은 테마에서 어두운 테마와 같은
    // 비율로 물리면 **대비가 4.5:1 밑으로 떨어진다**(실측: 사이드바 설명 4.04:1).
    // 밝은 쪽에서는 덜 물려서 위계는 남기되 읽히게 한다.
    '--text-mid': mix(text, bg, light ? 0.13 : 0.16),
    '--text-dim': mix(text, bg, light ? 0.22 : 0.3),

    '--nimbus': accent,
    '--nimbus-dark': mix(accent, '#000000', 0.26),
    '--nimbus-dim': tint(accent, 0.16),
    // 강조색 **위에** 얹는 글자. 밝기 임계값으로 고르면 중간 톤에서 틀린 쪽을
    // 고른다 — 금색(#a9741a)에 흰 글자를 얹어 4.0:1 이 나왔다(실측). 임계값 대신
    // **둘 다 재보고 더 잘 보이는 쪽**을 쓴다.
    '--accent-ink': contrast(accent, '#17130a') >= contrast(accent, '#ffffff')
      ? '#17130a' : '#ffffff',

    '--green': status.green,
    '--green-bg': tint(status.green),
    '--yellow': status.yellow,
    '--yellow-bg': tint(status.yellow),
    '--red': status.red,
    '--red-bg': tint(status.red),
    '--blue': status.blue,
    '--blue-bg': tint(status.blue),
    '--purple': status.purple,
  }
  return { ...tokens, ...overrides }
}

/** 화면에 띄울 경고 — 읽기 힘든 조합을 고르면 알려 준다(막지는 않는다). */
export function customWarnings(cfg) {
  const { bg, text, accent } = normalizeCustom(cfg)
  const out = []
  const cText = contrast(bg, text)
  if (cText < 4.5) {
    out.push(`글자와 배경의 대비가 낮습니다 (${cText.toFixed(1)}:1). `
             + '본문은 4.5:1 이상을 권합니다 — 글자색을 더 진하게(또는 더 밝게) 해 보세요.')
  }
  if (contrast(bg, accent) < 2.2) {
    out.push('강조색이 배경에 묻힙니다 — 버튼·선택 표시가 잘 안 보일 수 있습니다.')
  }
  return out
}

/** 토큰 이름 → 사람이 읽는 이름 (고급 편집기에서 쓴다). */
export const TOKEN_LABELS = Object.freeze({
  '--bg-0': '페이지 바탕',
  '--bg-1': '본문 면',
  '--bg-2': '패널',
  '--bg-3': '카드 · 입력칸',
  '--bg-4': '올라온 면',
  '--bg-5': '가장 올라온 면',
  '--border': '테두리',
  '--border-bright': '밝은 테두리',
  '--text': '본문 글자',
  '--text-bright': '강조 글자',
  '--text-mid': '중간 글자',
  '--text-dim': '흐린 글자',
  '--nimbus': '강조색',
  '--nimbus-dark': '강조색(진한)',
  '--nimbus-dim': '강조 배경',
  '--accent-ink': '강조색 위 글자',
  '--green': '성공',
  '--green-bg': '성공 배경',
  '--yellow': '경고',
  '--yellow-bg': '경고 배경',
  '--red': '오류',
  '--red-bg': '오류 배경',
  '--blue': '정보',
  '--blue-bg': '정보 배경',
  '--purple': '보조',
})

export const TOKEN_ORDER = Object.freeze(Object.keys(TOKEN_LABELS))
