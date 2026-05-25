import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildLogStreamArgs,
  canStartLogStream,
  resourceTypeForLogSource,
} from './logTargets.js'

test('maps workload log sources to resource browser API types', () => {
  assert.equal(resourceTypeForLogSource('pod'), 'pods')
  assert.equal(resourceTypeForLogSource('deployment'), 'deployments')
  assert.equal(resourceTypeForLogSource('statefulset'), 'statefulsets')
  assert.equal(resourceTypeForLogSource('daemonset'), 'daemonsets')
  assert.equal(resourceTypeForLogSource('job'), 'jobs')
  assert.equal(resourceTypeForLogSource('ingress'), null)
})

test('builds API args for a workload log stream', () => {
  assert.deepEqual(
    buildLogStreamArgs({
      sourceType: 'deployment',
      namespace: 'default',
      target: 'api',
      container: 'ignored-for-workload',
      tail: 500,
      follow: true,
    }),
    ['default', 'api', '', 500, true, 'deployment'],
  )
})

test('builds API args for a pod log stream', () => {
  assert.deepEqual(
    buildLogStreamArgs({
      sourceType: 'pod',
      namespace: 'default',
      target: 'web-7d9',
      container: 'app',
      tail: 100,
      follow: false,
    }),
    ['default', 'web-7d9', 'app', 100, false, 'pod'],
  )
})

test('builds API args for ingress integrated logs', () => {
  assert.deepEqual(
    buildLogStreamArgs({
      sourceType: 'ingress',
      namespace: 'default',
      target: 'ignored',
      container: 'ignored',
      tail: 200,
      follow: true,
    }),
    ['', '', '', 200, true, 'ingress'],
  )
})

test('requires namespace and target except for ingress integrated logs', () => {
  assert.equal(canStartLogStream({ connected: true, sourceType: 'pod', namespace: 'default', target: 'web' }), true)
  assert.equal(canStartLogStream({ connected: true, sourceType: 'deployment', namespace: 'default', target: 'api' }), true)
  assert.equal(canStartLogStream({ connected: true, sourceType: 'deployment', namespace: '', target: 'api' }), false)
  assert.equal(canStartLogStream({ connected: true, sourceType: 'ingress', namespace: '', target: '' }), true)
  assert.equal(canStartLogStream({ connected: false, sourceType: 'ingress', namespace: '', target: '' }), false)
})
