import React, { useState, useRef, useEffect } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Terminal, Send, Trash2, ChevronRight } from 'lucide-react'

const PROMPT = '$ kubectl '

const QUICK_COMMANDS = [
  { label: 'get pods -A',        cmd: 'get pods --all-namespaces' },
  { label: 'get nodes',          cmd: 'get nodes -o wide' },
  { label: 'get deployments -A', cmd: 'get deployments --all-namespaces' },
  { label: 'get services -A',    cmd: 'get services --all-namespaces' },
  { label: 'get events -A',      cmd: 'get events --all-namespaces --sort-by=.lastTimestamp' },
  { label: 'get namespaces',     cmd: 'get namespaces' },
  { label: 'top nodes',          cmd: 'top nodes' },
  { label: 'top pods -A',        cmd: 'top pods --all-namespaces' },
  { label: 'get ingresses -A',   cmd: 'get ingresses --all-namespaces' },
  { label: 'get pvc -A',         cmd: 'get pvc --all-namespaces' },
]

function OutputLine({ line }) {
  const isErr  = /error|failed|not found/i.test(line)
  const isWarn = /warn|deprecated/i.test(line)
  return (
    <div style={{
      fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.7,
      color: isErr ? 'var(--red)' : isWarn ? 'var(--yellow)' : 'var(--text)',
      whiteSpace: 'pre-wrap', wordBreak: 'break-all',
    }}>
      {line}
    </div>
  )
}

export default function TerminalPage() {
  const { connected, terminalCommand, setTerminalCommand } = useApp()
  const [input, setInput]         = useState('')
  const [history, setHistory]     = useState([])
  const [cmdHistory, setCmdHistory] = useState([])
  const [histIdx, setHistIdx]     = useState(-1)
  const [loading, setLoading]     = useState(false)
  const outputRef = useRef(null)
  const inputRef  = useRef(null)

  useEffect(() => {
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight
  }, [history])

  useEffect(() => {
    if (!terminalCommand) return
    setInput(terminalCommand)
    setTerminalCommand('')
    setTimeout(() => inputRef.current?.focus(), 0)
  }, [terminalCommand, setTerminalCommand])

  async function runCommand(raw) {
    const txt = (raw ?? input).trim()
    if (!txt || loading) return
    const cmd = txt.replace(/^kubectl\s+/, '')
    setInput('')
    setHistIdx(-1)
    setCmdHistory(prev => [txt, ...prev.slice(0, 49)])
    setLoading(true)
    try {
      const result = await api.runKubectl(cmd)
      setHistory(prev => [...prev, { cmd, output: result?.output || '', err: result?.error || '' }])
    } catch (e) {
      setHistory(prev => [...prev, { cmd, output: '', err: String(e) }])
    }
    setLoading(false)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault(); runCommand()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const next = Math.min(histIdx + 1, cmdHistory.length - 1)
      setHistIdx(next)
      if (cmdHistory[next] !== undefined) setInput(cmdHistory[next])
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = Math.max(histIdx - 1, -1)
      setHistIdx(next)
      setInput(next === -1 ? '' : (cmdHistory[next] || ''))
    }
  }

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Terminal size={40} opacity={0.3} />
      <p>클러스터에 연결되지 않았습니다.</p>
    </div>
  )

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── 터미널 메인 영역 ── */}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: 'var(--bg-0)' }}>

        {/* 헤더 */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 14px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-1)', flexShrink: 0,
        }}>
          <Terminal size={14} color="var(--nimbus)" />
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>
            kubectl 터미널
          </span>
          <span style={{ flex: 1 }} />
          <button className="btn btn-ghost btn-sm" onClick={() => setHistory([])} title="출력 지우기">
            <Trash2 size={12} /> 지우기
          </button>
        </div>

        {/* 출력 영역 */}
        <div
          ref={outputRef}
          style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', fontFamily: 'var(--font-mono)' }}
          onClick={() => inputRef.current?.focus()}
        >
          {history.length === 0 && (
            <div style={{ color: 'var(--text-dim)', fontSize: 12, lineHeight: 2 }}>
              <div># kubectl 명령어를 입력하세요 (kubectl 접두어 생략)</div>
              <div># 예: get pods -n kube-system</div>
              <div># 예: describe node my-node</div>
              <div># ↑↓ 방향키로 이전 명령어 탐색</div>
              <div># 오른쪽 패널의 빠른 명령어를 클릭하면 바로 실행</div>
            </div>
          )}

          {history.map((entry, i) => (
            <div key={i} style={{ marginBottom: 12 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--nimbus)', marginBottom: 4 }}>
                {PROMPT}{entry.cmd}
              </div>
              {entry.output && entry.output.split('\n').map((line, j) => (
                <OutputLine key={j} line={line} />
              ))}
              {entry.err && (
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--red)', whiteSpace: 'pre-wrap' }}>
                  {entry.err}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-dim)', fontSize: 12 }}>
              <div className="spinner" style={{ width: 12, height: 12 }} />
              실행 중...
            </div>
          )}
        </div>

        {/* 입력 영역 */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 14px', borderTop: '1px solid var(--border)',
          background: 'var(--bg-2)', flexShrink: 0,
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--nimbus)', whiteSpace: 'nowrap', flexShrink: 0 }}>
            {PROMPT}
          </span>
          <input
            ref={inputRef}
            className="input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="명령어 입력 후 Enter..."
            disabled={loading}
            autoFocus
            spellCheck={false}
            style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 12, background: 'var(--bg-3)' }}
          />
          <button className="btn btn-primary btn-sm" onClick={() => runCommand()} disabled={loading || !input.trim()}>
            <Send size={12} />
          </button>
        </div>
      </div>

      {/* ── 오른쪽 패널 ── */}
      <div style={{
        width: 210, flexShrink: 0,
        borderLeft: '1px solid var(--border)',
        background: 'var(--bg-1)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        {/* 빠른 명령어 */}
        <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>
            빠른 명령어
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {QUICK_COMMANDS.map(({ label, cmd }) => (
              <button
                key={cmd}
                onClick={() => runCommand(cmd)}
                disabled={loading}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '5px 8px', background: 'transparent',
                  border: '1px solid transparent', borderRadius: 5,
                  cursor: 'pointer', textAlign: 'left', width: '100%',
                  transition: 'background 0.15s, border-color 0.15s',
                  fontFamily: 'var(--font-mono)', fontSize: 10.5,
                  color: 'var(--text-dim)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(52,211,153,0.08)'
                  e.currentTarget.style.borderColor = 'rgba(52,211,153,0.2)'
                  e.currentTarget.style.color = 'var(--nimbus)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.borderColor = 'transparent'
                  e.currentTarget.style.color = 'var(--text-dim)'
                }}
              >
                <ChevronRight size={10} style={{ flexShrink: 0 }} />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* 최근 명령어 이력 */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: '10px 12px' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8, flexShrink: 0 }}>
            최근 이력
          </div>
          {cmdHistory.length === 0 ? (
            <div style={{ fontSize: 11, color: 'var(--text-dim)', fontStyle: 'italic' }}>없음</div>
          ) : (
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
              {cmdHistory.slice(0, 20).map((c, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(c.replace(/^kubectl\s+/, '')); inputRef.current?.focus() }}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '4px 6px', background: 'transparent',
                    border: 'none', borderRadius: 4, cursor: 'pointer',
                    fontFamily: 'var(--font-mono)', fontSize: 10,
                    color: 'var(--text-dim)', overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--text)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-dim)' }}
                  title={c}
                >
                  {c}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
