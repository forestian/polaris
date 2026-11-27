import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

// v1.2.121 「네트워크 스캐닝」 옵트인 배선 회귀 테스트.
//
// 잡으려는 사고: api.healthScan 은 **positional** 호출이라(callSafe('health_scan', a, b, c, d))
// 인자 순서가 프론트/백엔드에서 어긋나면 조용히 오결합된다 — 예컨대 netscan 을 3번째로
// 끼워넣으면 llmModel 자리에 boolean 이 들어가고 아무 에러도 안 난다.
// 그래서 "4번째 인자"라는 계약을 소스 수준에서 고정한다.

const read = p => readFileSync(new URL(p, import.meta.url), 'utf8')
const health = read('./pages/HealthScanPage.jsx')
const report = read('./pages/ReportPage.jsx')
const apijs = read('./api.js')
const sidebar = read('./components/Sidebar.jsx')
const palette = read('./components/CommandPalette.jsx')

test('api.js: healthScan 이 netscan 을 4번째 파라미터로 선언하고 그대로 전달한다', () => {
  assert.match(apijs,
    /healthScan:\s*\(explain=false,\s*llmUrl='',\s*llmModel='local-model',\s*netscan=false\)/,
    'netscan 은 반드시 4번째(맨 뒤) 파라미터')
  assert.match(apijs,
    /callSafe\('health_scan',\s*explain,\s*llmUrl,\s*llmModel,\s*netscan\)/,
    'bridge 호출 인자 순서가 선언과 같아야 함')
})

test('HealthScanPage: 체크박스 상태를 4번째 인자로 넘긴다', () => {
  assert.match(health, /const \[netScan, setNetScan\] = useState\(seed\?\.netScan \?\? false\)/,
    'netScan 상태가 seed 에서 복원되고 기본 false')
  assert.match(health, /checked=\{netScan\}\s+onChange=\{e => setNetScan\(e\.target\.checked\)\}/,
    '체크박스가 netScan 에 바인딩')
  assert.match(health, /api\.healthScan\(useAI,\s*useAI \? llmUrl : '',\s*llmModel,\s*netScan\)/,
    'netScan 이 4번째 인자로 전달')
  // 캐시에도 들어가야 탭 전환 후 선택이 유지된다
  assert.match(health, /_scanCache = \{ switchKey: clusterSwitchKey, result, err, netScan,/,
    'netScan 이 모듈 캐시에 포함')
})

test('HealthScanPage: 점검 범위(잘림·권한)를 결과에 노출한다', () => {
  // 상한에 걸려 일부만 봤는데 "발견 없음"으로 읽히면 오독 — 반드시 표시해야 한다
  assert.match(health, /result\.netscan &&/, 'netscan 요약 블록이 조건부 렌더')
  assert.match(health, /result\.netscan\.truncated/, '잘림 여부 노출')
  assert.match(health, /result\.netscan\.permission === 'denied'/, '권한 거부 노출')
})

test('ReportPage: netscan 을 startReport payload 에 넣는다', () => {
  assert.match(report, /const \[netScan, setNetScan\]\s*=\s*useState\(false\)/,
    'netScan 상태 (이 페이지는 캐시 없음 — 매번 꺼진 상태로 시작)')
  assert.match(report, /netscan:\s*netScan,/, 'startReport cfg 에 netscan 키')
  assert.match(report, /checked=\{netScan\}/, '체크박스 바인딩')
  // 생성 요약에도 반영 — 사용자가 무엇을 켜고 생성하는지 확인 가능해야 한다
  assert.match(report, /네트워크 스캔: <span/, '생성 요약에 표시')
})

test('메뉴명은 클러스터 스캔, 라우팅 id 는 health — v1.4.0 부터 CHECK 탭에', () => {
  // id 를 바꾸면 라우팅·저장된 화면 상태가 깨진다. 사이드바와 팔레트는 같은 목록(checkPages.js)을 쓴다
  const pages = read('./checkPages.js')
  assert.match(pages, /\{ id: 'health', label: '클러스터 스캔', sub: '헬스 체크 · 네트워크 스캔', cluster: true,/,
    '라벨 · id 유지 + 「헬스 체크」 로도 검색되게 sub 유지')
  assert.doesNotMatch(sidebar, /id: 'health'/, 'K8S 사이드바에서는 빠졌다')
  assert.match(palette, /checkPageItems\(q\)/, '팔레트는 CHECK 목록으로 찾는다')
  assert.match(health, /<CheckPageHead page="health"/, '페이지 제목은 공통 머리가 checkPages 의 label(클러스터 스캔)로 (v1.5.60)')
})
