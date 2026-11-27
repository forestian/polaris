/**
 * aiChatStore — AI 대화 상태를 컴포넌트 밖(모듈)에 보관하는 작은 스토어.
 *
 * 왜? 채팅 컴포넌트(AI 진단)는 다른 탭·세션으로 이동하면 unmount 된다.
 * 요청을 컴포넌트 안에서 await 하면, 응답이 와도 unmount 된 컴포넌트의 setState 는 버려지고
 * 답변이 유실된다. 요청을 이 스토어에서 돌리면 화면을 떠나 있어도 응답이 저장되고, 돌아오면
 * 그대로 보인다. busy/error 도 스토어가 들고 있어 재진입 시 "생성 중" 상태까지 복원된다.
 *
 * key 별로 독립된 대화: 'ai-tab', `ssh-ai:<sid>`, `diag:<source>` 등.
 */
import { useState, useEffect } from 'react'

const store = {}   // key -> { messages: [{role,content,display?,meta?}], busy, error }
const subs  = {}   // key -> Set<fn>

function slot(key) {
  if (!store[key]) store[key] = { messages: [], busy: false, error: null }
  return store[key]
}
function emit(key) { (subs[key] || []).forEach(fn => { try { fn() } catch { /* noop */ } }) }

export function resetChat(key) {
  const s = slot(key)
  if (s.busy) return            // 진행 중에는 초기화 금지(응답이 빈 대화에 붙는 혼란 방지)
  s.messages = []; s.error = null
  emit(key)
}
export function clearChatError(key) { slot(key).error = null; emit(key) }

/**
 * 한 턴 실행. 컴포넌트 mount 여부와 무관하게 동작한다.
 *   userMsg          : 낙관적으로 먼저 추가할 사용자 메시지 {role:'user', content, display?}
 *   call(messages)   : 현재 메시지 배열을 받아 {ok, answer, meta?, prompt?} 를 반환하는 api 호출
 *   deriveUserContent: (선택) 응답에서 직전 user 메시지 content 를 보정(진단 첫 턴: r.prompt)
 */
export async function runChat(key, { userMsg, call, deriveUserContent } = {}) {
  const s = slot(key)
  if (s.busy) return
  if (userMsg) s.messages = [...s.messages, userMsg]
  s.busy = true; s.error = null
  emit(key)
  try {
    const r = await call([...s.messages])
    if (r && r.ok) {
      if (deriveUserContent && s.messages.length) {
        const uc = deriveUserContent(r)
        const last = s.messages.length - 1
        if (uc != null && s.messages[last] && s.messages[last].role === 'user')
          s.messages = s.messages.map((m, i) => (i === last ? { ...m, content: uc } : m))
      }
      s.messages = [...s.messages, { role: 'assistant', content: r.answer, meta: r.meta }]
    } else {
      s.error = (r && r.error) || '응답 실패'
    }
  } catch (e) {
    s.error = String(e)
  } finally {
    s.busy = false
    emit(key)
  }
}

/** key 의 대화 상태를 구독해 반환 (변경 시 리렌더). 반환 객체는 {messages, busy, error}. */
export function useChat(key) {
  const [, force] = useState(0)
  useEffect(() => {
    const fn = () => force(n => n + 1)
    if (!subs[key]) subs[key] = new Set()
    subs[key].add(fn)
    return () => { if (subs[key]) subs[key].delete(fn) }
  }, [key])
  return slot(key)
}
