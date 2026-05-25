import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  THEMES,
  THEME_IDS,
  normalizeThemeId,
  toCssVariableBlock,
} from './themeRegistry.js'

test('defines Polaris plus the five requested background themes', () => {
  assert.deepEqual(
    THEME_IDS,
    ['polaris', 'argus', 'aurora', 'forge', 'vault', 'pharos'],
  )
  assert.equal(THEMES.polaris.label, 'Polaris')
  assert.equal(THEMES.argus.label, 'Argus')
  assert.equal(THEMES.aurora.label, 'Aurora')
  assert.equal(THEMES.forge.label, 'Forge')
  assert.equal(THEMES.vault.label, 'Vault')
  assert.equal(THEMES.pharos.label, 'Pharos')
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
