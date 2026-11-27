/**
 * 토폴로지 — 앱 단위로 묶기 (v1.4.31) — topologyApps.js
 * 입력은 백엔드가 가짜 클러스터로 만든 결과 그대로(topologyApps.sample.json, tests/test_topology_data.py 의 fixture).
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { buildApps, filterApps, workloadHealth } from './topologyApps.js'

const SAMPLE = JSON.parse(readFileSync(new URL('./topologyApps.sample.json', import.meta.url), 'utf8'))

test('이어진 Ingress → Service → 워크로드가 앱 하나 — 함께 쓰는 Secret 으로는 묶지 않는다', () => {
  const { apps } = buildApps(SAMPLE)
  const names = apps.map(a => a.name).sort()
  // web · api 는 Ingress 하나(shop)로 이어져 한 앱, report 는 배치, old-worker 는 혼자
  assert.deepEqual(names, ['api', 'old-worker', 'report'])
  const shop = apps.find(a => a.name === 'api')
  assert.deepEqual(shop.workloads.map(w => w.name), ['api', 'web'])
  assert.deepEqual(shop.services.map(s => s.name), ['api', 'web'])
  assert.deepEqual(shop.hosts, ['shop.example.com'])
  assert.equal(shop.kind, 'exposed')
})

test('쓰는 설정 · 저장소 — PVC 에는 PV, 여러 앱이 쓰면 그 수', () => {
  const shop = buildApps(SAMPLE).apps.find(a => a.name === 'api')
  const u = Object.fromEntries(shop.uses.map(x => [x.type + ':' + x.name, x]))
  assert.ok(u['configmap:web-config'] && u['secret:registry-cred'] && u['pvc:api-data'])
  assert.equal(u['pvc:api-data'].pv.name, 'pv-001')
  assert.equal(u['secret:registry-cred'].sharedBy, 1, '같은 앱 안의 두 워크로드는 한 앱으로 센다')
})

test('여러 앱이 함께 쓰는 설정', () => {
  const d = structuredClone(SAMPLE)
  d.workloads.push({ id: 'wl/shop/Deployment/other', kind: 'Deployment', name: 'other', ns: 'shop', total: 1, running: 1, ready: 1, waiting: [] })
  d.edges.push({ from: 'wl/shop/Deployment/other', to: 'secret/shop/registry-cred' })
  const apps = buildApps(d).apps
  const shop = apps.find(a => a.name === 'api')
  assert.equal(shop.uses.find(x => x.name === 'registry-cred').sharedBy, 2)
})

test('상태 — 대기 사유 · 준비 수 · 0개로 줄여 둔 것 · 배치', () => {
  const { apps, counts } = buildApps(SAMPLE)
  assert.equal(apps[0].name, 'api', '문제 있는 앱이 맨 위')
  assert.equal(apps[0].health.level, 'bad')
  assert.match(apps[0].health.text, /CrashLoopBackOff — 1\/2 준비/)
  assert.equal(apps.find(a => a.name === 'old-worker').health.text, '0개로 줄여 둠')
  const batch = apps.find(a => a.name === 'report')
  assert.equal(batch.kind, 'batch')
  assert.deepEqual(batch.jobs.map(j => j.name), ['report-28811'])
  assert.equal(batch.health.text, '완료')
  assert.deepEqual(counts, { all: 3, problem: 1, exposed: 1, batch: 1 })
})

test('워크로드 상태 낱개', () => {
  assert.equal(workloadHealth({ kind: 'Deployment', total: 3, ready: 3, restarts: 2 }).text, '3/3 준비 · 재시작 2')
  assert.equal(workloadHealth({ kind: 'Deployment', total: 3, ready: 1 }).level, 'warn')
  assert.equal(workloadHealth({ kind: 'Deployment', total: 0, replicas: 2 }).level, 'bad', '바라는 수가 있는데 파드가 없다')
  assert.equal(workloadHealth({ kind: 'Deployment', total: 2, running: 2 }).text, '2/2 준비', '예전 데이터(준비 수 없음)')
  assert.equal(workloadHealth({ kind: 'Job', status: 'Failed' }).level, 'bad')
})

test('거르기 · 찾기 — 호스트 · 리소스 이름 어디로든', () => {
  const { apps } = buildApps(SAMPLE)
  assert.deepEqual(filterApps(apps, 'problem').map(a => a.name), ['api'])
  assert.deepEqual(filterApps(apps, 'batch').map(a => a.name), ['report'])
  assert.deepEqual(filterApps(apps, 'all', 'shop.example').map(a => a.name), ['api'])
  assert.deepEqual(filterApps(apps, 'all', 'api-data').map(a => a.name), ['api'], 'PVC 이름으로도')
  assert.deepEqual(filterApps(apps, 'exposed', 'report'), [])
})

test('화면 — 앱 카드 · 거르기 · 찾기 · 상세 · 리소스 브라우저 열기', () => {
  const page = readFileSync(new URL('./pages/TopologyPage.jsx', import.meta.url), 'utf8')
  assert.match(page, /buildApps\(raw\)/)
  assert.match(page, /filterApps\(apps, filter, q\)/)
  assert.match(page, /<AppCard key=\{app\.id\}/)
  assert.match(page, /navigate\('resources', res\)/)
  assert.match(page, /shown\.slice\(0, limit\)/, '앱이 많으면 나눠서 그린다')
  assert.doesNotMatch(page, /topologyGraph/, '예전 6열 그래프는 쓰지 않는다')
})

test('빈 데이터', () => {
  assert.deepEqual(buildApps({}).apps, [])
  assert.deepEqual(buildApps(null).counts, { all: 0, problem: 0, exposed: 0, batch: 0 })
})
