/**
 * 타이틀바 새로고침(↻)·상태바 「F5 새로고침」 제거 (v1.3.46).
 *
 * ↻ 는 백엔드가 들고 있는 클러스터 목록만 다시 받았고 보고 있는 화면은 그대로였다.
 * 「F5 새로고침」 은 배포판에서 F5 가 아무 일도 하지 않는데 적혀 있었다.
 * 사용자 결정으로 둘 다(그리고 같은 동작인 Ctrl+K 의 「새로고침」 명령도) 뺐다.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = p => readFileSync(new URL(p, import.meta.url), 'utf8')

test('타이틀바에 새로고침 버튼이 없다', () => {
  const src = read('./App.jsx')
  assert.doesNotMatch(src, /title="새로고침"/)
  assert.doesNotMatch(src, />↻</)
  assert.doesNotMatch(src, /refreshStatus/)
  // 설정 버튼은 남아 있다
  assert.match(src, /title="설정"/)
})

test('상태바에 「F5 새로고침」 이 없다', () => {
  // 주석(왜 뺐는지)에는 F5 가 남아 있으므로 걷어 내고 본다
  const src = read('./components/StatusBar.jsx').replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
  assert.doesNotMatch(src, /F5/)
  assert.match(src, />Ctrl\+K 검색</)
})

test('명령 팔레트에 새로고침 명령이 없다', () => {
  const src = read('./components/CommandPalette.jsx')
  assert.doesNotMatch(src, /cmd:refresh/)
  assert.doesNotMatch(src, /refreshStatus/)
})

test('store 가 refreshStatus 를 더 내보내지 않는다', () => {
  assert.doesNotMatch(read('./store.jsx'), /refreshStatus/)
})
