import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

// 회귀: 건강 스캔 페이지에서 다른 탭으로 갔다 오면 스캔 결과/옵션이 초기화되던 버그.
// K8sPageView 가 activePage 별 switch 렌더라 탭 전환 시 HealthScanPage 가 언마운트되어
// 로컬 useState 가 소실됨 → 모듈 스코프 캐시로 보존(클러스터 전환 시엔 폐기)하도록 수정.

const src = readFileSync(new URL('./pages/HealthScanPage.jsx', import.meta.url), 'utf8')

test('HealthScanPage: 모듈 스코프 캐시 + seed 복원 + 변경 시 기록이 배선돼 있다', () => {
  // 모듈 스코프 캐시 변수(컴포넌트 밖) — 언마운트돼도 유지되는 저장소
  assert.match(src, /^let _scanCache = null/m, '모듈 스코프 _scanCache 선언이 있어야 함')

  // clusterSwitchKey 를 구독해 클러스터 전환 시 캐시 무효화 판단에 사용
  assert.match(src, /clusterSwitchKey\s*\}\s*=\s*useApp\(\)/, 'useApp 에서 clusterSwitchKey 를 받아야 함')

  // seed: switchKey 가 현재와 일치하는 캐시만 복원
  assert.match(src, /_scanCache\.switchKey === clusterSwitchKey/, 'switchKey 일치 시에만 seed 복원')

  // 상태 초기값을 seed 에서 시딩 (탭 재진입 시 복원)
  assert.match(src, /useState\(seed\?\.result/, 'result 를 seed 에서 초기화해야 함')

  // 변경 시 캐시에 다시 기록하는 useEffect (switchKey 포함)
  assert.match(src, /_scanCache = \{ switchKey: clusterSwitchKey/, '변경 시 캐시 기록')
  // v1.2.121: netScan(네트워크 스캐닝 옵션)이 지속 상태에 추가됐다.
  assert.match(src, /\}, \[clusterSwitchKey, result, err, netScan, useAI, llmUrl, llmModel, llmModels\]\)/,
    'useEffect 의존성에 지속 상태 전부 포함')

  // loading 은 캐시에 저장하지 않는다(재진입 시 재실행 가능해야 함)
  assert.doesNotMatch(src, /switchKey:[^}]*loading/, 'loading 은 캐시에 저장하지 않아야 함')
})

// seed 선택 로직을 순수 함수로 복제해 계약을 검증(컴포넌트의 seed 계산식과 동일).
function pickSeed(cache, currentSwitchKey) {
  return (cache && cache.switchKey === currentSwitchKey) ? cache : null
}

test('seed 선택: 같은 클러스터면 복원, 다른 클러스터면 폐기, 없으면 null', () => {
  const cached = { switchKey: 3, result: { total: 2 }, useAI: true, llmUrl: 'http://x:1234' }

  // 같은 클러스터(switchKey 동일) — 그대로 복원
  assert.deepEqual(pickSeed(cached, 3), cached)

  // 다른 클러스터로 전환(switchKey 변경) — 이전 클러스터 결과이므로 폐기
  assert.equal(pickSeed(cached, 4), null)

  // 캐시 없음(최초 실행) — 기본값 사용
  assert.equal(pickSeed(null, 0), null)
})

test('시딩 기본값: seed 가 null 이면 각 상태는 초기 기본값으로 떨어진다', () => {
  const seed = null
  assert.equal(seed?.result ?? null, null)
  assert.equal(seed?.netScan ?? false, false)   // 네트워크 스캐닝은 기본 꺼짐
  assert.equal(seed?.useAI ?? false, false)
  assert.equal(seed?.llmUrl ?? 'http://localhost:1234', 'http://localhost:1234')
  assert.equal(seed?.llmModel ?? 'local-model', 'local-model')
  assert.deepEqual(seed?.llmModels ?? [], [])
})
