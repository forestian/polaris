import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  isFeatureEnabled,
  normalizeEnabledFeaturesResponse,
} from './featureGate.js'

test('keeps a bundled feature visible while backend feature discovery is pending', () => {
  assert.equal(isFeatureEnabled('infra', null, true), true)
  assert.equal(isFeatureEnabled('infra', undefined, true), true)
})

test('uses backend feature discovery once it succeeds', () => {
  assert.equal(isFeatureEnabled('infra', ['catalog', 'infra'], true), true)
  assert.equal(isFeatureEnabled('infra', ['catalog'], true), false)
})

test('distinguishes a failed feature response from an empty feature list', () => {
  assert.equal(normalizeEnabledFeaturesResponse({ ok: false, error: 'not ready' }), null)
  assert.deepEqual(normalizeEnabledFeaturesResponse({ features: [] }), [])
})
