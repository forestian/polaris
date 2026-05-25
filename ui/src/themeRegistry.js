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
  '--text-dim': '#5a5878',
  '--text-mid': '#9a96b8',
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
    '--text-mid': `hsl(${th}, 16%, 60%)`,
    '--text-dim': `hsl(${th}, 20%, 38%)`,
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
}

export const THEME_IDS = Object.keys(THEMES)

export function normalizeThemeId(themeId) {
  return Object.prototype.hasOwnProperty.call(THEMES, themeId) ? themeId : 'polaris'
}

export function toCssVariableBlock(themeId) {
  const theme = THEMES[normalizeThemeId(themeId)]
  return Object.entries(theme.tokens)
    .map(([name, value]) => `  ${name}: ${value};`)
    .join('\n')
}

export function installThemeStyles(doc = globalThis.document) {
  if (!doc) return
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
