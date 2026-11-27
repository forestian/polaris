/**
 * AiDiagnose — LLM 기반 진단 + 후속 질의응답 (이벤트 탭 · 로그 뷰어 공용).
 *
 * <AiDiagnoseButton source="events|logs" getPayload={() => ({...})} />
 *   - 1턴: api.aiDiagnose(source, payload, url, model, question) — 컨텍스트 보강 + 진단.
 *   - 2턴+: api.aiChat(messages, url, model) — 같은 대화 맥락에서 후속 질문(수동).
 *   - 대화는 aiChatStore(모듈)에 source 별로 보관 → 창을 닫거나 답 대기 중 떠나도 답변이 유지된다.
 *   - 오버레이는 타이틀바(드래그 영역) 아래에서 시작 → 진단 창이 떠 있어도 윈도우 이동 가능.
 */
import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import { Sparkles, X, Loader, AlertTriangle, Copy, Check, Settings2, Send, RotateCcw } from 'lucide-react'
import { useChat, runChat, resetChat } from '../aiChatStore.js'
import LlmConnectionTest from './LlmConnectionTest.jsx'

const LS_URL = 'polaris.ai.url'
const LS_MODEL = 'polaris.ai.model'

function lsGet(k, def) { try { return localStorage.getItem(k) ?? def } catch { return def } }
function lsSet(k, v) { try { localStorage.setItem(k, v) } catch { /* noop */ } }
function isLocalUrl(u) {
  try { return ['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(new URL(u).hostname) }
  catch { return false }
}

// ── 가벼운 마크다운 렌더 (### 헤딩 · **굵게** · `코드` · ```블록```) ────────────────
function inlineFmt(text, keyBase) {
  const parts = []
  let rest = text, i = 0
  const re = /(\*\*([^*]+)\*\*|`([^`]+)`)/
  let m
  while ((m = re.exec(rest))) {
    if (m.index > 0) parts.push(rest.slice(0, m.index))
    if (m[2] !== undefined) parts.push(<strong key={`${keyBase}-b${i}`}>{m[2]}</strong>)
    else parts.push(<code key={`${keyBase}-c${i}`} style={{
      background: 'var(--bg-3)', padding: '0 4px', borderRadius: 3,
      fontFamily: 'var(--font-mono)', fontSize: '0.92em' }}>{m[3]}</code>)
    rest = rest.slice(m.index + m[0].length); i++
  }
  if (rest) parts.push(rest)
  return parts
}
export function Markdownish({ text }) {
  const segs = String(text || '').split(/```/)
  return (
    <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text)' }}>
      {segs.map((seg, si) => {
        if (si % 2 === 1) {
          const body = seg.replace(/^[a-zA-Z]*\n/, '')
          return (
            <pre key={si} style={{
              background: 'var(--bg-0)', border: '1px solid var(--border)', borderRadius: 6,
              padding: '8px 10px', overflowX: 'auto', fontFamily: 'var(--font-mono)',
              fontSize: 12, margin: '8px 0', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            }}>{body.replace(/\n$/, '')}</pre>
          )
        }
        return seg.split('\n').map((line, li) => {
          const key = `${si}-${li}`
          const h = line.match(/^(#{1,4})\s+(.*)$/)
          if (h) return <div key={key} style={{ fontWeight: 700, color: 'var(--text-bright)',
            fontSize: 14, margin: '10px 0 4px' }}>{inlineFmt(h[2], key)}</div>
          if (!line.trim()) return <div key={key} style={{ height: 6 }} />
          const indent = /^\s*[-*]\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)
          return <div key={key} style={{ paddingLeft: indent ? 12 : 0 }}>{inlineFmt(line, key)}</div>
        })
      })}
    </div>
  )
}
function metaText(source, meta) {
  if (!meta) return ''
  if (source === 'events') {
    let s = `Warning ${meta.warning_events ?? 0}건 중 ${meta.sent ?? 0}건`
    if (meta.abnormal_pods) s += ` · 비정상 파드 ${meta.abnormal_pods}개`
    s += ` · Normal ${meta.normal_skipped ?? 0}건 제외`
    return s
  }
  if (source === 'logs') {
    let s = meta.trimmed
      ? `${meta.total_lines}줄 중 에러/경고 ${meta.error_lines ?? 0}줄 + 최근 줄 발췌`
      : `${meta.total_lines ?? 0}줄 전체 분석`
    if (meta.pod_events) s += ` · 파드 이벤트 ${meta.pod_events}건 포함`
    return s
  }
  return ''
}

function CopyBtn({ text }) {
  const [c, setC] = useState(false)
  return (
    <button className="btn btn-ghost btn-sm" style={{ gap: 4 }} onClick={async () => {
      try { await navigator.clipboard.writeText(text) } catch {}
      setC(true); setTimeout(() => setC(false), 1500)
    }}>
      {c ? <Check size={11} color="var(--green)" /> : <Copy size={11} />}{c ? '복사됨' : '복사'}
    </button>
  )
}

export default function AiDiagnoseButton({ source, getPayload, disabled, label = 'AI 진단', title }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button className="btn btn-ghost btn-sm" onClick={() => setOpen(true)} disabled={disabled}
        title={title || 'LLM 으로 현재 내용을 진단/질의'}
        style={{ gap: 4, color: 'var(--nimbus)', border: '1px solid var(--nimbus)' }}>
        <Sparkles size={11} /> {label}
      </button>
      {open && <AiDiagnoseModal source={source} getPayload={getPayload} onClose={() => setOpen(false)} />}
    </>
  )
}

function AiDiagnoseModal({ source, getPayload, onClose }) {
  const KEY = `diag:${source}`
  const [url, setUrl]       = useState(() => lsGet(LS_URL, 'http://localhost:1234'))
  const [model, setModel]   = useState(() => lsGet(LS_MODEL, 'local-model'))
  const [models, setModels] = useState([])
  const [showCfg, setShowCfg] = useState(() => !lsGet(LS_URL, ''))
  const [question, setQuestion] = useState('')

  function handleModels(list) {
    setModels(list)
    if (list.length && (!model || model === 'local-model')) setModel(list[0])
  }
  const chat = useChat(KEY)          // {messages, busy, error} — 모듈 스토어(창 닫아도/대기 중 떠나도 유지)
  const scrollRef = useRef(null)

  const messages = chat.messages
  const busy = chat.busy
  const started = messages.length > 0
  const srcLabel = source === 'events' ? '이벤트' : source === 'logs' ? '로그' : source

  useEffect(() => { lsSet(LS_URL, url) }, [url])
  useEffect(() => { lsSet(LS_MODEL, model) }, [model])
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape' && !busy) onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onClose])
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages, busy])

  function runDiagnose() {
    if (busy) return
    const q = question.trim()
    setQuestion('')
    runChat(KEY, {
      userMsg: { role: 'user', content: '', display: q ? `🔍 자동 진단 + “${q}”` : '🔍 자동 진단' },
      call: () => api.aiDiagnose(source, getPayload ? getPayload() : {}, url.trim(), model.trim(), q),
      deriveUserContent: (r) => r.prompt,   // user 메시지 content 를 보강된 컨텍스트로 → 후속질문 맥락 유지
    })
  }

  function sendFollowup() {
    const q = question.trim()
    if (!q || busy) return
    setQuestion('')
    runChat(KEY, {
      userMsg: { role: 'user', content: q, display: q },
      call: (msgs) => api.aiChat(msgs.filter(m => m.content).map(m => ({ role: m.role, content: m.content })),
                                 url.trim(), model.trim()),
    })
  }

  function onInputKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      started ? sendFollowup() : runDiagnose()
    }
  }

  return (
    // 타이틀바 아래에서 시작 → 진단 창이 떠 있어도 상단 드래그 영역으로 윈도우 이동 가능
    <div onClick={() => !busy && onClose()} style={{
      position: 'fixed', top: 'var(--titlebar-h)', left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.4)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-1)', border: '1px solid var(--border)', borderRadius: 10,
        width: 'min(820px, 96vw)', height: 'min(80vh, 760px)', display: 'flex', flexDirection: 'column',
        boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
      }}>
        {/* 헤더 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px',
          borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <Sparkles size={15} color="var(--nimbus)" />
          <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-bright)' }}>
            AI 진단 — {srcLabel}
          </span>
          <span style={{ flex: 1 }} />
          {started && (
            <button className="btn btn-ghost btn-sm" onClick={() => resetChat(KEY)} disabled={busy} style={{ gap: 4 }}
              title="대화 지우고 현재 데이터로 새 진단">
              <RotateCcw size={12} /> 새 진단
            </button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={() => setShowCfg(s => !s)} title="LLM 설정">
            <Settings2 size={13} />
          </button>
          <button className="btn btn-ghost btn-sm" onClick={onClose} disabled={busy}><X size={14} /></button>
        </div>

        {/* LLM 설정 (접이식) */}
        {showCfg && (
          <div style={{ flexShrink: 0, background: 'var(--bg-2)', borderBottom: '1px solid var(--border)',
            padding: 12, display: 'grid', gridTemplateColumns: '1fr 200px', gap: 10 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>LLM API URL (OpenAI 호환)</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input className="input" value={url} onChange={e => setUrl(e.target.value)}
                  placeholder="http://localhost:1234" style={{ flex: 1, minWidth: 0 }} />
                <LlmConnectionTest url={url} onModels={handleModels} compact />
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>모델명</div>
              <input className="input" value={model} onChange={e => setModel(e.target.value)}
                placeholder="local-model" list="llm-models-diag" style={{ width: '100%' }} />
              {models.length > 0 && (
                <datalist id="llm-models-diag">
                  {models.map(m => <option key={m} value={m} />)}
                </datalist>
              )}
            </div>
            <div style={{ gridColumn: '1 / -1', fontSize: 10.5,
              color: isLocalUrl(url) ? 'var(--text-dim)' : 'var(--gold)' }}>
              {isLocalUrl(url)
                ? '✓ localhost — 데이터가 외부로 전송되지 않습니다.'
                : `⚠ 현재 ${srcLabel} 내용이 이 LLM 서버로 전송됩니다. 신뢰할 수 있는 내부 서버인지 확인하세요.`}
            </div>
          </div>
        )}

        {/* 본문 (대화 또는 시작 패널) */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {!started ? (
            <div>
              <div style={{ fontSize: 12.5, color: 'var(--text-mid)', lineHeight: 1.6, marginBottom: 12 }}>
                현재 {srcLabel}와 클러스터 상태를 AI가 분석해 원인·조치를 제안합니다.
                추가로 묻고 싶은 점이 있으면 적어주세요(선택).
              </div>
              <textarea className="input" value={question} onChange={e => setQuestion(e.target.value)}
                onKeyDown={onInputKey} disabled={busy}
                placeholder={`예) 이 ${srcLabel}에서 가장 시급한 문제는? (비워두면 자동 진단)`}
                rows={2} style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit', marginBottom: 10 }} />
              <button className="btn btn-primary" onClick={runDiagnose} disabled={busy}
                style={{ gap: 6, width: '100%', justifyContent: 'center' }}>
                {busy ? <><Loader size={13} className="spin" /> 진단 중…</>
                      : <><Sparkles size={13} /> 진단 실행</>}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {messages.map((m, i) => m.role === 'user' ? (
                <div key={i} style={{ alignSelf: 'flex-end', maxWidth: '85%' }}>
                  <div style={{ background: 'var(--nimbus)', color: '#051a0e', borderRadius: '10px 10px 2px 10px',
                    padding: '7px 11px', fontSize: 12.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {m.display || m.content}
                  </div>
                </div>
              ) : (
                <div key={i} style={{ alignSelf: 'stretch' }}>
                  <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)',
                    borderRadius: '10px 10px 10px 2px', padding: '12px 14px' }}>
                    <Markdownish text={m.content} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                    <CopyBtn text={m.content} />
                    {m.meta && <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{metaText(source, m.meta)}</span>}
                  </div>
                </div>
              ))}
              {busy && (
                <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 6,
                  color: 'var(--nimbus)', fontSize: 12 }}>
                  <Loader size={13} className="spin" /> 답변 생성 중…
                </div>
              )}
            </div>
          )}

          {chat.error && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', background: 'var(--red-bg)',
              border: '1px solid var(--red)', borderRadius: 8, padding: '10px 12px', color: 'var(--red)',
              fontSize: 12.5, marginTop: 12 }}>
              <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span style={{ whiteSpace: 'pre-wrap' }}>{chat.error}</span>
            </div>
          )}
        </div>

        {/* 후속 질문 입력 (진단이 나온 뒤에만) */}
        {started && (
          <div style={{ flexShrink: 0, borderTop: '1px solid var(--border)', padding: 12,
            display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <textarea className="input" value={question} onChange={e => setQuestion(e.target.value)}
              onKeyDown={onInputKey} disabled={busy} rows={1}
              placeholder="후속 질문… (Enter 전송 · Shift+Enter 줄바꿈)"
              style={{ flex: 1, resize: 'none', fontFamily: 'inherit', maxHeight: 120 }} />
            <button className="btn btn-primary" onClick={sendFollowup} disabled={busy || !question.trim()}
              style={{ gap: 5, flexShrink: 0 }}>
              <Send size={13} /> 전송
            </button>
          </div>
        )}

        <div style={{ flexShrink: 0, fontSize: 10, color: 'var(--text-dim)', padding: '0 16px 10px' }}>
          ⓘ AI 추론 결과입니다 — 실제 조치 전 명령·영향을 직접 확인하세요.
        </div>
      </div>
    </div>
  )
}
