/**
 * 업그레이드 사전 점검 화면 (v1.4.1) — upgradeModel.js · UpgradeCheckPage 배선
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { verdictText, resultText, SEV_STYLE, CATEGORY_KO } from './upgradeModel.js'

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8')
const R = {
  version: 'v1.24.17', target: '1.25', target_minor: 25, verdict: 'blocked', counts: { block: 2, warn: 1, info: 0 },
  findings: [{ severity: 'block', category: 'api', title: 'Helm 릴리스가 제거될 API 를 씁니다 — 1건', detail: 'd', action: 'a', items: ['web/app'], more: 3 }],
  passed: ['모든 노드가 Ready 입니다'], checklist: ['etcd 스냅샷을 먼저 남기세요', '한 대씩'],
}

test('판정 문구', () => {
  assert.match(verdictText(R).title, /먼저 해결해야 할 문제가 2건/)
  assert.match(verdictText(R).sub, /주의 1건/)
  assert.match(verdictText({ ...R, verdict: 'caution', counts: { warn: 3 } }).title, /주의할 항목이 3건/)
  assert.equal(verdictText({ ...R, verdict: 'ready', counts: {} }).title, '업그레이드를 막는 문제가 없습니다')
  for (const k of ['block', 'warn', 'info']) assert.ok(SEV_STYLE[k].label)
  for (const k of ['version', 'api', 'skew', 'health', 'drain', 'addon', 'scope']) assert.ok(CATEGORY_KO[k])
})

test('결과 복사 글', () => {
  const t = resultText(R)
  assert.match(t, /^\[업그레이드 사전 점검\] v1\.24\.17 → 1\.25/)
  assert.match(t, /■ \[먼저 해결\] Helm 릴리스가/)
  assert.match(t, /  조치: a/)
  assert.match(t, /  - 그 밖에 3건/)
  assert.match(t, /■ 업그레이드 순서\n  1\. etcd 스냅샷을 먼저 남기세요\n  2\. 한 대씩/)
  assert.equal(resultText(null), '')
})

test('배선', () => {
  const page = read('./pages/UpgradeCheckPage.jsx')
  assert.match(page, /api\.upgradeCheckVersions\(\)/)
  assert.match(page, /api\.upgradeCheck\(target\)/)
  assert.match(page, /_cache\.key === clusterSwitchKey/, '클러스터가 바뀌면 결과를 버린다')
  assert.doesNotMatch(page, /color: '#[0-9a-f]{6}'/i)
  const app = read('./App.jsx')
  assert.match(app, /case 'upgrade': return <UpgradeCheckPage key=\{clusterSwitchKey\} \/>/)
  const a = read('./api.js')
  assert.match(a, /upgradeCheck:\s+\(target\)\s+=> callSafe\('upgrade_check', target\)/)
})
