/**
 * CHECK 탭(무료판) — 클러스터 점검 3종만 · 목록 · 배선.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { CHECK_GROUPS, CHECK_PAGES, visibleCheckGroups, resolveCheckPage, checkPage, checkPageItems } from './checkPages.js'

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8')

test('목록 — 클러스터 스캔 · 업그레이드 사전 점검 · 클러스터 보고서 셋뿐', () => {
  assert.deepEqual(CHECK_GROUPS.map(g => g.id), ['cluster'])
  assert.deepEqual(CHECK_PAGES.map(p => p.id), ['health', 'upgrade', 'report'])
  assert.deepEqual(CHECK_PAGES.map(p => p.label), ['클러스터 스캔', '업그레이드 사전 점검', '클러스터 보고서'])
  assert.ok(CHECK_PAGES.every(p => p.cluster), '모두 클러스터 화면')
  assert.deepEqual(visibleCheckGroups(), CHECK_GROUPS)
})

test('저장된 화면이 없으면 첫 화면으로', () => {
  assert.equal(resolveCheckPage('upgrade'), 'upgrade')
  assert.equal(resolveCheckPage('daily'), 'health')
  assert.equal(resolveCheckPage(undefined), 'health')
  assert.equal(checkPage('없음'), null)
})

test('화면 머리 한 줄 안내 — 모든 화면에 무엇을 · 대상 · 결과물', () => {
  for (const p of CHECK_PAGES) {
    assert.ok(p.line && p.target && p.output, p.id)
    assert.ok(p.line.length <= 70, `${p.id} 안내는 한 줄로 짧게 (${p.line.length}자)`)
  }
  for (const f of ['pages/HealthScanPage.jsx', 'pages/UpgradeCheckPage.jsx', 'pages/ReportPage.jsx']) {
    assert.ok(read('./' + f).includes('<CheckPageHead page='), f + ' 는 공통 머리를 쓴다')
  }
})

test('명령 팔레트', () => {
  const items = checkPageItems('')
  assert.equal(items.length, 3)
  assert.ok(items.every(it => it.kind === 'check-page' && it.id.startsWith('check:')))
  assert.deepEqual(checkPageItems('헬스 체크').map(it => it.checkPage), ['health'], '「헬스 체크」 로도')
  assert.deepEqual(checkPageItems('drain').map(it => it.checkPage), ['upgrade'])
})

test('배선 — 탭은 K8S · CHECK 둘', () => {
  const ms = read('./components/ModeSwitcher.jsx')
  assert.deepEqual([...ms.matchAll(/setAppMode\('(\w+)'\)/g)].map(m => m[1]), ['k8s', 'check'])
  assert.match(read('./store.jsx'), /\['k8s', 'check'\]\.includes\(mode\)/)
  const app = read('./App.jsx')
  assert.match(app, /appMode === 'check'\s*\?\s*<CheckPageView \/>/)
  assert.match(app, /appMode === 'check'\s*\?\s*<CheckSidebar \/>/)
  assert.match(app, /appMode === 'check' && checkPage\(checkActivePage\)\?\.cluster\)\) && <ClusterTabStrip \/>/,
               '클러스터 화면에서는 클러스터 탭을 띄운다')
  assert.match(app, /default: return <HealthScanPage key=\{clusterSwitchKey\} \/>/, '클러스터를 바꾸면 다시 그린다')
  assert.doesNotMatch(read('./components/Sidebar.jsx'), /id: 'report'/, '보고서는 CHECK 에만')
})
