import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildPodExecCommand,
  buildPodLogTarget,
} from './navigationTargets.js'

test('builds a log viewer target for a selected pod', () => {
  assert.deepEqual(
    buildPodLogTarget({
      namespace: 'kube-system',
      name: 'coredns-abc123',
      container: 'coredns',
      tail: 500,
    }),
    {
      namespace: 'kube-system',
      pod: 'coredns-abc123',
      container: 'coredns',
      tail: 500,
      autoStart: true,
    },
  )
})

test('uses safe defaults for pod log targets', () => {
  assert.deepEqual(
    buildPodLogTarget({
      namespace: 'default',
      name: 'web-7d9',
    }),
    {
      namespace: 'default',
      pod: 'web-7d9',
      container: '',
      tail: 200,
      autoStart: true,
    },
  )
})

test('builds an exec command for a pod container', () => {
  assert.equal(
    buildPodExecCommand({
      namespace: 'default',
      name: 'web-7d9',
      container: 'app',
    }),
    'exec -it -n default web-7d9 -c app -- sh',
  )
})

test('omits the container flag when a pod has no selected container', () => {
  assert.equal(
    buildPodExecCommand({
      namespace: 'default',
      name: 'web-7d9',
      container: '',
    }),
    'exec -it -n default web-7d9 -- sh',
  )
})
