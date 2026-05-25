import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildPortForwardStartArgs,
  canStartPortForward,
  normalizePortForwardTarget,
} from './portForwardTargets.js'

test('normalizes service and pod port-forward targets', () => {
  assert.deepEqual(
    normalizePortForwardTarget({
      kind: 'services',
      namespace: 'monitoring',
      name: 'grafana',
      remotePort: '80',
      localPort: '3000',
    }),
    {
      kind: 'service',
      namespace: 'monitoring',
      name: 'grafana',
      remotePort: 80,
      localPort: 3000,
    },
  )

  assert.deepEqual(
    normalizePortForwardTarget({
      kind: 'pod',
      namespace: 'default',
      name: 'api-0',
      remotePort: 8080,
      localPort: '',
    }),
    {
      kind: 'pod',
      namespace: 'default',
      name: 'api-0',
      remotePort: 8080,
      localPort: 8080,
    },
  )
})

test('builds API args for starting a port-forward', () => {
  assert.deepEqual(
    buildPortForwardStartArgs({
      kind: 'service',
      namespace: 'monitoring',
      name: 'grafana',
      localPort: 3000,
      remotePort: 80,
    }),
    ['service', 'monitoring', 'grafana', 3000, 80],
  )
})

test('requires a concrete target and valid ports', () => {
  assert.equal(canStartPortForward({ connected: true, namespace: 'default', name: 'api', remotePort: 8080, localPort: 8080 }), true)
  assert.equal(canStartPortForward({ connected: false, namespace: 'default', name: 'api', remotePort: 8080, localPort: 8080 }), false)
  assert.equal(canStartPortForward({ connected: true, namespace: 'All Namespaces', name: 'api', remotePort: 8080, localPort: 8080 }), false)
  assert.equal(canStartPortForward({ connected: true, namespace: 'default', name: '', remotePort: 8080, localPort: 8080 }), false)
  assert.equal(canStartPortForward({ connected: true, namespace: 'default', name: 'api', remotePort: 0, localPort: 8080 }), false)
  assert.equal(canStartPortForward({ connected: true, namespace: 'default', name: 'api', remotePort: 8080, localPort: 70000 }), false)
})
