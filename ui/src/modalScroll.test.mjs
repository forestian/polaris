import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

// v1.2.142 모달 스크롤 회귀 테스트.
//
// 사고: 구성 이식 「가져오기」에서 kubeconfig 목록이 길면 「가져오기 실행」 버튼을
// 누를 수 없었다. 원인은 .modal 에 높이 상한이 없고 overflow:hidden 인데
// .modal-overlay 가 align-items:center 로 가운데 정렬한 것 —
// 내용이 뷰포트보다 커지면 모달이 위아래로 똑같이 밀려나 헤더와 푸터가 화면 밖으로
// 잘리고, 어디에도 스크롤이 없어 버튼에 닿을 방법이 사라진다.
//
// 실측(뷰포트 620px, kubeconfig 18개): 모달 높이 1517px, top -448px,
// 실행 버튼 top 945px(화면 아래), document 스크롤 불가.
//
// .modal 클래스는 설정·연결·ArgoCD·리소스 브라우저 등 7곳이 공유하므로
// 한 곳이라도 아래 속성이 빠지면 같은 사고가 전부에서 재현된다.

const read = p => readFileSync(new URL(p, import.meta.url), 'utf8')
const css = read('./index.css')
const modal = read('./components/SettingsModal.jsx')

/** CSS 규칙 본문만 뽑아낸다 (셀렉터가 정확히 일치하는 첫 블록). */
function ruleBody(selector) {
  const re = new RegExp(`(^|\\})\\s*${selector.replace('.', '\\.')}\\s*\\{([^}]*)\\}`, 'm')
  const m = css.match(re)
  assert.ok(m, `${selector} 규칙을 찾지 못했다`)
  return m[2]
}

test('.modal 은 뷰포트를 넘지 않고 flex 컬럼으로 쌓인다', () => {
  const body = ruleBody('.modal')
  assert.match(body, /max-height:\s*100%/,
    'max-height 가 없으면 내용이 길 때 모달이 화면 밖으로 잘린다')
  assert.match(body, /flex-direction:\s*column/,
    'flex 컬럼이라야 body 만 늘어나고 헤더·푸터가 제자리에 남는다')
})

test('.modal-body 가 실제로 스크롤된다', () => {
  const body = ruleBody('.modal-body')
  assert.match(body, /overflow-y:\s*auto/, '넘치는 내용을 스크롤할 수 있어야 한다')
  assert.match(body, /min-height:\s*0/,
    'min-height:0 이 없으면 flex 자식이 내용 높이 아래로 줄지 않아 스크롤이 안 생긴다')
})

test('헤더·푸터는 줄어들지 않는다', () => {
  assert.match(ruleBody('.modal-header'), /flex-shrink:\s*0/)
  assert.match(ruleBody('.modal-footer'), /flex-shrink:\s*0/,
    '푸터가 눌리면 확인/취소 버튼이 사라진다 — 이 사고의 핵심')
})

test('.modal-overlay 가 여백을 둬 모달이 화면 가장자리에 닿지 않는다', () => {
  assert.match(ruleBody('.modal-overlay'), /padding:\s*24px/,
    'max-height:100% 의 기준이 되는 안쪽 상자를 만드는 여백')
})

test('설정 모달 탭 줄이 flex 컬럼에서 눌리지 않는다', () => {
  assert.match(modal, /borderBottom: '1px solid var\(--border\)',\s*\n\s*flexShrink: 0/,
    '.modal 이 flex 컬럼이라 탭 줄에 flexShrink:0 이 없으면 찌그러진다')
})

