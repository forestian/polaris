import { CUSTOM_DEFAULTS, makeCustomTokens, normalizeCustom } from './customTheme.js'

const POLARIS_TOKENS = {
  '--bg-0': '#060914',
  '--bg-1': '#0b1024',
  '--bg-2': '#131734',
  '--bg-3': '#1c2046',
  '--bg-4': '#252a52',
  '--bg-5': '#2e3360',
  '--border': '#1f254a',
  '--border-bright': '#2f365c',
  '--text': '#c8c4dc',
  // v1.2.131: 대비 2.6~2.8:1(WCAG 최소 4.5:1 미달)이라 사이드바 설명 텍스트 등이
  // 잘 안 보였다. 1차 수정(명도 41%→58%)으로도 사용자가 "여전히 흐리다"고 재지적해
  // 2차로 더 밝게 올렸다(58%→68%, 대비 4.9→7.0). 색조/채도는 그대로 유지.
  // ⚠ ui/src/index.css 의 :root 블록에도 같은 값이 중복 정의돼 있다 — 여기만 고치고
  // index.css 를 안 맞추면 예전 값이 그대로 남는다(실제로 한 번 발생한 회귀).
  // 두 파일을 반드시 함께 갱신할 것. themeContrast.test.mjs 가 동기화 여부를 검사한다.
  '--text-dim': '#a9a7be',
  // text-mid 도 "회색이 눈에 잘 안 들어온다"는 지적 대상이라 76%→7.9~9.6:1 로 함께 올렸다.
  // text-dim 과는 여전히 차이를 둬 두 단계 위계(흐림/중간)는 유지한다.
  '--text-mid': '#b9b6cd',
  '--text-bright': '#f0e8f5',
  '--green': '#7dd3fc',
  '--green-bg': '#07203a',
  '--yellow': '#fbbf24',
  '--yellow-bg': '#451a03',
  '--red': '#f87171',
  '--red-bg': '#450a0a',
  '--blue': '#7dd3fc',
  '--blue-bg': '#0c1f3d',
  '--purple': '#b9b3df',
  '--nimbus': '#f3c969',
  '--nimbus-dark': '#c89a3e',
  '--nimbus-dim': '#2a1f08',
  '--accent-ink': '#1a1208',
}

function makeBrandTokens({ h, s = 30, accent, accentDark, secondary, textHue }) {
  const th = textHue ?? h
  const cs = Math.min(s, 28)
  return {
    '--bg-0': `hsl(${h}, ${Math.min(s, 30)}%, 3%)`,
    '--bg-1': `hsl(${h}, ${cs}%, 6%)`,
    '--bg-2': `hsl(${h}, ${cs}%, 10%)`,
    '--bg-3': `hsl(${h}, ${cs}%, 15%)`,
    '--bg-4': `hsl(${h}, ${cs - 2}%, 22%)`,
    '--bg-5': `hsl(${h}, ${cs - 4}%, 30%)`,
    '--border': `hsl(${h}, ${cs}%, 16%)`,
    '--border-bright': `hsl(${h}, ${cs - 4}%, 24%)`,
    '--text': `hsl(${th}, 14%, 78%)`,
    '--text-bright': `hsl(${th}, 8%, 94%)`,
    // v1.2.131 2차: 60%→74% — 1차(38%→54%)로도 "여전히 흐리다"는 지적이라 더 올렸다.
    '--text-mid': `hsl(${th}, 16%, 78%)`,
    // 명도 38%→70% — 배경(bg-1~3) 대비 2.4~2.8:1 → 7.1~9.0:1.
    // --text-mid 보다는 여전히 어둡게 두어 위계(강조도 차이)는 유지한다.
    '--text-dim': `hsl(${th}, 20%, 70%)`,
    '--nimbus': accent,
    '--nimbus-dark': accentDark,
    '--nimbus-dim': `hsl(${h}, ${cs}%, 9%)`,
    '--green': accent,
    '--green-bg': `hsl(${h}, ${cs}%, 9%)`,
    '--blue': secondary,
    '--blue-bg': `hsl(${h}, ${cs}%, 10%)`,
    '--purple': '#b9b3df',
    '--yellow': '#fbbf24',
    '--yellow-bg': '#3a1a0a',
    '--red': '#f87171',
    '--red-bg': '#3a0a0a',
    '--accent-ink': '#061018',
  }
}

export const THEMES = {
  polaris: {
    label: 'Polaris',
    tone: '현재 기본 테마',
    tokens: POLARIS_TOKENS,
  },
  argus: {
    label: 'Argus',
    tone: '선명한 관측 블루',
    tokens: makeBrandTokens({
      h: 208, s: 45, accent: '#4dd6ff', accentDark: '#2db0d8', secondary: '#a8e5fc',
    }),
  },
  aurora: {
    label: 'Aurora',
    tone: '녹청 오로라와 보랏빛 신호',
    tokens: makeBrandTokens({
      h: 230, s: 55, accent: '#6eddb8', accentDark: '#3e9c80', secondary: '#c484e8',
    }),
  },
  forge: {
    label: 'Forge',
    tone: '무채색 철판과 주황 열감',
    tokens: makeBrandTokens({
      h: 240, s: 5, accent: '#ff7849', accentDark: '#c4582a', secondary: '#e8e6e1',
    }),
  },
  vault: {
    label: 'Vault',
    tone: '저채도 금속과 금빛 포인트',
    tokens: makeBrandTokens({
      h: 232, s: 8, accent: '#d4a858', accentDark: '#a87830', secondary: '#f5d490',
    }),
  },
  pharos: {
    label: 'Pharos',
    tone: '등대처럼 밝은 골드와 딥 시안',
    tokens: makeBrandTokens({
      h: 200, s: 40, accent: '#f8c864', accentDark: '#c89a3e', secondary: '#fff5d0',
    }),
  },
  // ── Forestia (v1.3.35) ──────────────────────────────────────────────
  //
  // 2000년대 국산 2D MMORPG 「Story of Forestia」 에서 색을 가져왔다.
  // 스크린샷 10장의 지배색을 실제로 뽑아 정했다(눈짐작이 아니다):
  //
  //   풀빛   #478632 #5b914a #6ca242   H94~114 S32~47 L33~45  ← 가장 넓은 면
  //   양피지 #b5b88b #bcb8a0           H51~64  S17~25 L63~68  ← 게임 UI 패널
  //   나무   #a37938 #937441           H36~37  S39~49 L42~43
  //   버섯갓 #ad9755 (밝은 것은 #e8b84e)
  //   그늘   #394228                   H81 S25 L21
  //   연못   #6aa1b0                   H193 S31 L55
  //
  // **밝은 테마다.** 게임 UI 자체가 양피지 바탕에 갈색 글자였고, 그 인상이
  // 이 테마의 핵심이다. 그래서 어두운 테마용 makeBrandTokens 가 아니라
  // makeCustomTokens 로 만든다 — 그쪽이 배경 밝기를 보고 쌓는 방향을 뒤집는다.
  forestia: {
    label: 'Forestia',
    tone: '초록빛 도는 종이와 풀빛 — 밝은 테마',
    tokens: makeCustomTokens({
      // 게임 UI 패널의 실측색은 #b9bc91 (H64 S24 L65) — 세 군데를 재도 같았다.
      // 화면 전체 바탕으로 쓰기엔 어두워서 **색조(H64)는 그대로 두고 밝기만**
      // 올렸다. 따뜻한 크림색이 아니라 **초록빛이 도는 종이**여야 그 게임이다.
      bg: '#e7e8d8',
      text: '#33281a',      // 젖은 나무껍질
      // 풀빛. 원본(#4a8b33)은 양피지 위 글자로 3.5:1 이라 15% 어둡게 내렸다 —
      // 색조는 그대로 두고 명도만 낮춰야 「Forestia 인데 읽히는」 색이 된다.
      accent: '#446b23',
      overrides: {
        // 상태색도 숲에서 가져온다. 자동 생성값(일반적인 초록·빨강)을 쓰면
        // 화면이 「밝은 테마」 로만 보이고 Forestia 로는 안 보인다.
        '--green': '#32732c',       // 잎사귀 (4.67:1)
        '--yellow': '#865e0c',      // 버섯갓 (4.68:1)
        '--red': '#a33a26',         // 붉은 흙 · 테라코타 (5.58:1 — 그대로 통과)
        '--blue': '#296d82',        // 연못 (4.70:1)
        '--purple': '#6f5397',      // 들꽃 (5.30:1 — 그대로 통과)
        // 테두리는 나뭇결 쪽으로 — 회색 테두리를 쓰면 종이가 아니라 서류가 된다
        '--border': '#cdd0ae',
        '--border-bright': '#b9bc91',  // ← 게임 패널 실측색 그대로
        // 바탕은 이끼가 살짝 낀 종이
        '--bg-0': '#dcdecb',        // 이끼가 낀 종이
      },
    }),
  },
  // 사용자가 직접 만드는 테마 (v1.3.34). 여기 tokens 는 **기본값 기준 미리보기**고,
  // 실제로 쓰이는 값은 설정에 저장된 색에서 그때그때 만들어 낸다.
  custom: {
    label: '커스텀',
    tone: '배경·글자·강조를 직접 고릅니다 (밝은 배경 지원)',
    tokens: makeCustomTokens(CUSTOM_DEFAULTS),
    custom: true,
  },
}

export const THEME_IDS = Object.keys(THEMES)
export const CUSTOM_THEME_ID = 'custom'

export function normalizeThemeId(themeId) {
  return Object.prototype.hasOwnProperty.call(THEMES, themeId) ? themeId : 'polaris'
}

export function toCssVariableBlock(themeId) {
  const theme = THEMES[normalizeThemeId(themeId)]
  return Object.entries(theme.tokens)
    .map(([name, value]) => `  ${name}: ${value};`)
    .join('\n')
}

/**
 * 모든 테마를 `:root[data-theme="..."]` 규칙으로 <style> 에 심는다.
 *
 * `customCfg` 를 주면 커스텀 테마 블록을 그 색으로 다시 만든다. 설정이 바뀔
 * 때마다 다시 불러야 화면에 반영된다 — 토큰 값을 CSS 로 바꿔 끼우는 방식이라
 * 컴포넌트는 아무것도 몰라도 된다.
 */
export function installThemeStyles(doc = globalThis.document, customCfg = null) {
  if (!doc) return
  if (customCfg) THEMES.custom.tokens = makeCustomTokens(normalizeCustom(customCfg))
  const id = 'polaris-theme-registry'
  let style = doc.getElementById(id)
  if (!style) {
    style = doc.createElement('style')
    style.id = id
    doc.head.appendChild(style)
  }
  style.textContent = THEME_IDS
    .map(themeId => `:root[data-theme="${themeId}"] {\n${toCssVariableBlock(themeId)}\n}`)
    .join('\n\n')
}

export function applyTheme(themeId, root = globalThis.document?.documentElement) {
  const normalized = normalizeThemeId(themeId)
  if (root) root.dataset.theme = normalized
  return normalized
}
