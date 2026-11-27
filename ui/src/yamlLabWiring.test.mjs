import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

// v1.2.127 「YAML 실험실」 배선 회귀 테스트.
//
// 잡으려는 사고: 페이지 컴포넌트를 만들어도 Sidebar/App/CommandPalette 중 **한 곳만
// 빠지면** 메뉴가 안 뜨거나 눌러도 대시보드가 나온다. 셋의 페이지 id 가 서로 다르면
// 조용히 어긋나므로 id 일치를 소스 수준에서 고정한다.
// (백엔드 쪽 같은 부류는 tests/test_plugin_spec_sync.py 가 담당)

const read = p => readFileSync(new URL(p, import.meta.url), 'utf8')
const page = read('./pages/YamlLabPage.jsx')
const apijs = read('./api.js')
const sidebar = read('./components/Sidebar.jsx')
const palette = read('./components/CommandPalette.jsx')
const app = read('./App.jsx')

const PAGE_ID = 'yamllab'

test('Sidebar: 도구 그룹에 「YAML 실험실」이 있고 id 가 yamllab', () => {
  assert.match(sidebar, new RegExp(`id:\\s*'${PAGE_ID}',\\s*label:\\s*'YAML 실험실'`),
    'TOOL_PAGES 항목 누락 또는 id/라벨 불일치')
  assert.match(sidebar, /FlaskConical/, '아이콘 import 누락 시 런타임에 빈 화면이 된다')
})

test('CommandPalette: 같은 id 로 등록되고 sub 로도 검색된다', () => {
  assert.match(palette, new RegExp(`id:\\s*'${PAGE_ID}',[^}]*page:\\s*'${PAGE_ID}'`),
    '팔레트 등록 누락 또는 page 값 불일치')
  // 해이스택은 label+sub+id — sub 가 없으면 '내보내기' 같은 말로 못 찾는다
  assert.match(palette, /id:\s*'yamllab',[^}]*sub:\s*'[^']+'/, 'sub 누락')
})

test('App: lazy import 와 라우팅 case 가 둘 다 있다', () => {
  assert.match(app, /const YamlLabPage\s*=\s*lazy\(\(\) => import\('\.\/pages\/YamlLabPage\.jsx'\)\)/,
    'lazy import 누락')
  assert.match(app, new RegExp(`case '${PAGE_ID}':\\s*return connected \\? <YamlLabPage />`),
    '라우팅 case 누락 — 메뉴는 뜨는데 눌러도 대시보드가 나온다')
})

test('api.js: 페이지가 쓰는 lab_* 래퍼가 전부 선언돼 있다', () => {
  for (const [wrapper, bridge] of [
    ['labList', 'lab_list'], ['labGet', 'lab_get'], ['labSave', 'lab_save'],
    ['labDelete', 'lab_delete'], ['labVersionDiff', 'lab_version_diff'],
    ['labPreview', 'lab_preview'], ['labApply', 'lab_apply'],
    ['labApplyStatus', 'lab_apply_status'], ['labApplyCancel', 'lab_apply_cancel'],
    ['labTeardown', 'lab_teardown'], ['labExportText', 'lab_export_text'],
    ['labExportFolder', 'lab_export_folder'],
  ]) {
    assert.match(apijs, new RegExp(`${wrapper}:`), `api.js 에 ${wrapper} 누락`)
    assert.match(apijs, new RegExp(`'${bridge}'`), `api.js 의 ${wrapper} 가 ${bridge} 를 안 부름`)
  }
})

test('페이지가 호출하는 api 메서드는 전부 api.js 에 존재한다', () => {
  const used = [...page.matchAll(/api\.(lab[A-Za-z]+)\(/g)].map(m => m[1])
  assert.ok(used.length >= 8, `lab* 호출이 너무 적다 (${used.length})`)
  for (const m of new Set(used)) {
    assert.match(apijs, new RegExp(`\\b${m}:`), `페이지가 부르는 api.${m} 가 api.js 에 없다`)
  }
})

test('편집 중 내용이 탭 전환으로 날아가지 않도록 모듈 캐시를 쓴다', () => {
  // 이 페이지에서 가장 치명적인 UX 사고 — 붙여넣던 YAML 소실
  assert.match(page, /let _labCache = null/, '모듈 캐시 누락')
  assert.match(page, /_labCache && _labCache\.switchKey === clusterSwitchKey/,
    '다른 클러스터 캐시를 그대로 복원하면 안 된다')
  assert.match(page, /_labCache = \{ switchKey: clusterSwitchKey, editor/,
    'editor 상태가 캐시에 안 들어가면 내용이 날아간다')
})

test('폴링을 언마운트 시 정리한다', () => {
  // 정리 안 하면 탭을 떠난 뒤에도 백그라운드에서 계속 폴링한다.
  // v1.3.41 부터 pollRef 에는 startPoll 이 돌려준 stop 함수가 들어 있다.
  assert.match(page, /useEffect\(\(\) => \(\) => \{ if \(pollRef\.current\) pollRef\.current\(\)/,
    '언마운트 cleanup 누락')
  assert.match(page, /pollRef\.current = startPoll\(/, '겹치지 않는 폴러를 써야 한다')
})
