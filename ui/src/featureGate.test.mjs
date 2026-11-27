import assert from 'node:assert/strict'
import { test } from 'node:test'

import { normalizeEnabledFeaturesResponse } from './featureGate.js'

test('distinguishes a failed feature response from an empty feature list', () => {
  assert.equal(normalizeEnabledFeaturesResponse({ ok: false, error: 'not ready' }), null)
  assert.deepEqual(normalizeEnabledFeaturesResponse({ features: [] }), [])
  assert.deepEqual(normalizeEnabledFeaturesResponse({ features: ['yamllab'] }), ['yamllab'])
})
