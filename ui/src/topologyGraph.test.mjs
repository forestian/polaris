import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  buildTopologyGraph,
  TOPOLOGY_COLUMNS,
  TOPOLOGY_LAYOUT,
  TYPE_STYLE,
} from './topologyGraph.js'

test('places cronjobs before job workloads with enough horizontal spacing', () => {
  const graph = buildTopologyGraph({
    ingresses: [],
    services: [],
    cronjobs: [
      { id: 'cj/batch/nightly-backup', kind: 'CronJob', name: 'nightly-backup', ns: 'batch' },
    ],
    workloads: [
      { id: 'wl/batch/Job/nightly-backup-28100100', kind: 'Job', name: 'nightly-backup-28100100', ns: 'batch', running: 0, total: 1 },
    ],
    config_nodes: [],
    pv_nodes: [],
    edges: [
      { from: 'cj/batch/nightly-backup', to: 'wl/batch/Job/nightly-backup-28100100' },
    ],
  })

  const cron = graph.nodeMap.get('cj/batch/nightly-backup')
  const job = graph.nodeMap.get('wl/batch/Job/nightly-backup-28100100')

  assert.equal(cron.col, TOPOLOGY_COLUMNS.findIndex(col => col.id === 'schedule'))
  assert.equal(job.col, TOPOLOGY_COLUMNS.findIndex(col => col.id === 'workload'))
  assert.ok(job.x - cron.rx >= TOPOLOGY_LAYOUT.minColumnGap)
  assert.equal(graph.edges[0].from, cron.id)
  assert.equal(graph.edges[0].to, job.id)
})

test('keeps config and pv columns to the right of job workloads', () => {
  const graph = buildTopologyGraph({
    ingresses: [],
    services: [],
    cronjobs: [],
    workloads: [
      { id: 'wl/batch/Job/manual-cleanup', kind: 'Job', name: 'manual-cleanup', ns: 'batch', running: 1, total: 1 },
    ],
    config_nodes: [
      { id: 'configmap/batch/cleanup-config', type: 'configmap', name: 'cleanup-config', ns: 'batch' },
    ],
    pv_nodes: [
      { id: 'pv//backup-pv', type: 'pv', name: 'backup-pv', ns: '' },
    ],
    edges: [
      { from: 'wl/batch/Job/manual-cleanup', to: 'configmap/batch/cleanup-config' },
      { from: 'configmap/batch/cleanup-config', to: 'pv//backup-pv' },
    ],
  })

  const job = graph.nodeMap.get('wl/batch/Job/manual-cleanup')
  const config = graph.nodeMap.get('configmap/batch/cleanup-config')
  const pv = graph.nodeMap.get('pv//backup-pv')

  assert.ok(config.col > job.col)
  assert.ok(pv.col > config.col)
  assert.equal(TYPE_STYLE.job.badge, 'JOB')
  assert.equal(TYPE_STYLE.cronjob.badge, 'CJ')
})
