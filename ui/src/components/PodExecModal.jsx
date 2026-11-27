import React, { useEffect, useRef, useState } from 'react'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { api } from '../api.js'
import { startPoll } from '../poll.js'
import { X, TerminalSquare, Loader2, AlertCircle } from 'lucide-react'

// 클러스터 내장 파드 셸 — kubectl exec 을 외부 터미널이 아닌 Polaris 안에서 연다.
// 백엔드 WebSocket exec 스트림(start/recv/send/resize/close)에 xterm.js 를 연결.
export default function PodExecModal({ namespace, pod, container, onClose }) {
  const elRef = useRef(null)
  const termRef = useRef(null)
  const fitRef = useRef(null)
  const sidRef = useRef(null)
  const pollRef = useRef(null)
  const [status, setStatus] = useState('connecting')  // connecting | open | closed | error
  const [errMsg, setErrMsg] = useState('')

  useEffect(() => {
    let disposed = false
    const term = new XTerm({
      cursorBlink: true, fontSize: 13, scrollback: 5000,
      fontFamily: 'Consolas, "Cascadia Mono", "Courier New", monospace',
      theme: { background: '#0b0f14', foreground: '#d6e2f0' },
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(elRef.current)
    try { fit.fit() } catch {}
    termRef.current = term
    fitRef.current = fit

    term.onData(d => { if (sidRef.current) api.sendPodExec(sidRef.current, d) })

    ;(async () => {
      const cols = term.cols || 80, rows = term.rows || 24
      let r
      try { r = await api.startPodExec(namespace, pod, container || '', '', cols, rows) }
      catch (e) { r = { ok: false, error: String(e) } }
      // 응답 전에 창을 닫았으면 방금 연 exec 세션을 닫는다 (v1.3.73)
      if (disposed) { if (r?.ok && r.session_id) { try { api.closePodExec(r.session_id) } catch { /* noop */ } } return }
      if (!r?.ok) { setStatus('error'); setErrMsg(r?.error || 'exec 세션을 열 수 없습니다.'); return }
      sidRef.current = r.session_id
      setStatus('open')
      setTimeout(() => { try { fit.fit(); api.resizePodExec(sidRef.current, term.cols, term.rows) } catch {} }, 30)
      term.focus()
      // 읽으면 비워지는 엔드포인트라 호출이 겹치면 출력 순서가 뒤집힌다 — 겹치지 않는 폴러(v1.3.41)
      pollRef.current = startPoll(async () => {
        const sid = sidRef.current
        if (!sid) return
        let res
        try { res = await api.recvPodExec(sid) } catch { return }
        if (!res?.ok) return
        if (res.data) term.write(res.data)
        if (res.closed) {
          pollRef.current = null
          setStatus('closed')
          const tail = res.exit_msg
            ? `\r\n\x1b[33m[세션 종료: ${res.exit_msg}]\x1b[0m\r\n`
            : `\r\n\x1b[90m[세션이 종료되었습니다 — 닫기]\x1b[0m\r\n`
          try { term.write(tail) } catch {}
          return false
        }
      }, 120)
    })()

    const ro = new ResizeObserver(() => {
      try { fit.fit() } catch {}
      if (sidRef.current) { try { api.resizePodExec(sidRef.current, term.cols, term.rows) } catch {} }
    })
    try { ro.observe(elRef.current) } catch {}

    return () => {
      disposed = true
      try { ro.disconnect() } catch {}
      if (pollRef.current) pollRef.current()
      if (sidRef.current) { try { api.closePodExec(sidRef.current) } catch {} }
      try { term.dispose() } catch {}
    }
  }, [namespace, pod, container])

  const label = `${namespace}/${pod}${container ? ` · ${container}` : ''}`

  return (
    <div onMouseDown={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.55)',
      display: 'grid', placeItems: 'center',
    }}>
      <div onMouseDown={e => e.stopPropagation()} style={{
        width: '82vw', height: '72vh', maxWidth: 1200, display: 'flex',
        flexDirection: 'column', background: '#0b0f14',
        border: '1px solid var(--nimbus)', borderRadius: 10, overflow: 'hidden',
        boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
      }}>
        {/* 헤더 */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
          background: 'var(--bg-2)', borderBottom: '1px solid var(--border)', flexShrink: 0,
        }}>
          <TerminalSquare size={14} style={{ color: 'var(--nimbus)' }} />
          <div style={{ flex: 1, minWidth: 0, fontSize: 12, fontWeight: 600,
                        color: 'var(--text-bright)', fontFamily: 'var(--font-mono)',
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {label}
          </div>
          <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 4,
            background: status === 'open' ? 'rgba(52,211,153,0.15)'
              : status === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(148,163,184,0.15)',
            color: status === 'open' ? 'var(--nimbus)'
              : status === 'error' ? '#fca5a5' : 'var(--text-dim)' }}>
            {status === 'connecting' ? '연결 중' : status === 'open' ? '연결됨'
              : status === 'error' ? '오류' : '종료됨'}
          </span>
          <button onClick={onClose} title="닫기 (세션 종료)"
            style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)',
                     cursor: 'pointer', padding: 2, display: 'grid', placeItems: 'center' }}>
            <X size={15} />
          </button>
        </div>

        {/* 오류 배너 */}
        {status === 'error' && (
          <div style={{ padding: '8px 12px', fontSize: 11.5, color: 'var(--red)',
            background: 'rgba(239,68,68,0.12)', borderBottom: '1px solid rgba(239,68,68,0.3)',
            display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <AlertCircle size={13} style={{ flexShrink: 0 }} />
            <span style={{ wordBreak: 'break-all' }}>{errMsg}</span>
          </div>
        )}

        {/* 터미널 */}
        <div style={{ flex: 1, position: 'relative', minHeight: 0, padding: 6 }}>
          <div ref={elRef} style={{ width: '100%', height: '100%' }} />
          {status === 'connecting' && (
            <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
              color: 'var(--text-dim)', fontSize: 12, pointerEvents: 'none' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Loader2 size={14} className="spin" /> 셸 연결 중…
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
