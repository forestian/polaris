import React, { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import {
  LOG_SOURCE_OPTIONS,
  buildLogStreamArgs,
  canStartLogStream,
  isIngressLogSource,
  isPodLogSource,
  resourceTypeForLogSource,
} from '../logTargets.js'
import {
  Play, Square, RefreshCw, Search, Trash2,
  ChevronDown, ScrollText, ToggleLeft, ToggleRight,
  ArrowDown, Copy, Check,
} from 'lucide-react'

function lineColor(line) {
  const lo = line.toLowerCase()
  if (/\b(error|exception|fatal|critical|panic)\b/.test(lo)) return 'var(--red)'
  if (/\b(warn(ing)?)\b/.test(lo)) return 'var(--yellow)'
  if (/\b(debug|trace)\b/.test(lo)) return 'var(--text-dim)'
  return 'var(--text)'
}

function Sel({ value, onChange, children, style, disabled = false }) {
  return (
    <div style={{ position: 'relative', ...style }}>
      <select
        className="select"
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        style={{ paddingRight: 26, minWidth: 0, width: '100%' }}
      >
        {children}
      </select>
      <ChevronDown size={10} style={{
        position: 'absolute', right: 7, top: '50%',
        transform: 'translateY(-50%)', pointerEvents: 'none',
        color: 'var(--text-dim)',
      }} />
    </div>
  )
}

function Toggle({ value, onChange, label }) {
  return (
    <button
      className="btn btn-ghost btn-sm"
      onClick={() => onChange(!value)}
      style={{ gap: 5, color: value ? 'var(--nimbus)' : 'var(--text-dim)' }}
    >
      {value ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
      {label}
    </button>
  )
}

function highlightFilter(line, filter) {
  if (!filter) return line
  const idx = line.toLowerCase().indexOf(filter.toLowerCase())
  if (idx === -1) return line
  return (
    <>
      {line.slice(0, idx)}
      <mark style={{ background: 'var(--yellow)', color: '#000', borderRadius: 2, padding: '0 1px' }}>
        {line.slice(idx, idx + filter.length)}
      </mark>
      {line.slice(idx + filter.length)}
    </>
  )
}

export default function LogPage() {
  const { namespaces, namespace: globalNs, connected, logTarget, setLogTarget, windowVisible } = useApp()

  const [sourceType, setSourceType] = useState('pod')
  const [ns, setNs] = useState(() => globalNs === 'All Namespaces' ? '' : globalNs)
  const [targets, setTargets] = useState([])
  const [pod, setPod] = useState('')
  const [ctrs, setCtrs] = useState([])
  const [ctr, setCtr] = useState('')
  const [tail, setTail] = useState(200)
  const [follow, setFollow] = useState(false)

  const [lines, setLines] = useState([])
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const [errMsg, setErrMsg] = useState('')
  const [filter, setFilter] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const [copied, setCopied] = useState(false)

  const jobRef = useRef(null)
  const pollRef = useRef(null)
  const logEndRef = useRef(null)
  const logBoxRef = useRef(null)
  const autoStartKeyRef = useRef('')
  // 트레이로 hide된 동안 폴링 콜백 스킵 (v3.7.11)
  const visibleRef = useRef(true)
  useEffect(() => { visibleRef.current = windowVisible }, [windowVisible])

  useEffect(() => {
    if (!logTarget) return
    setSourceType('pod')
    setNs(logTarget.namespace || '')
    setPod(logTarget.pod || '')
    setCtr(logTarget.container || '')
    setTail(Number(logTarget.tail) || 200)
    setFollow(false)
    setLines([])
    setErrMsg('')
    setDone(false)
  }, [logTarget])

  useEffect(() => {
    const resourceType = resourceTypeForLogSource(sourceType)
    if (isIngressLogSource(sourceType)) {
      setTargets([])
      setPod('')
      setCtr('')
      return
    }
    if (!ns || !connected || !resourceType) {
      setTargets([])
      setPod('')
      return
    }
    api.getResource(resourceType, ns)
      .then(data => {
        const names = Array.isArray(data) ? data.map(item => item.name).sort() : []
        const targetPod = isPodLogSource(sourceType) && logTarget?.namespace === ns ? logTarget.pod : ''
        setTargets(names)
        setPod(prev => {
          if (prev && names.includes(prev)) return prev
          if (targetPod && names.includes(targetPod)) return targetPod
          return names[0] || ''
        })
      })
      .catch(() => {
        setTargets([])
        setPod('')
      })
  }, [ns, connected, sourceType, logTarget])

  useEffect(() => {
    if (!isPodLogSource(sourceType) || !ns || !pod) {
      setCtrs([])
      setCtr('')
      return
    }
    api.getPodDetail(ns, pod)
      .then(data => {
        const ctrList = (data?.containers || []).map(c => c.name)
        const targetCtr = logTarget?.namespace === ns && logTarget?.pod === pod
          ? logTarget.container : ''
        setCtrs(ctrList)
        setCtr(prev => {
          if (targetCtr && ctrList.includes(targetCtr)) return targetCtr
          if (prev && ctrList.includes(prev)) return prev
          return ctrList[0] || ''
        })
      })
      .catch(() => {
        setCtrs([])
        setCtr('')
      })
  }, [ns, pod, sourceType, logTarget])

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'auto' })
    }
  }, [lines, autoScroll])

  function handleScroll() {
    const box = logBoxRef.current
    if (!box) return
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40
    setAutoScroll(atBottom)
  }

  const stopStream = useCallback(async () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    if (jobRef.current) {
      await api.stopLogStream(jobRef.current)
      jobRef.current = null
    }
    setRunning(false)
  }, [])

  useEffect(() => () => { stopStream() }, [stopStream])

  async function startStream() {
    if (!canStartLogStream({ connected, sourceType, namespace: ns, target: pod })) return
    await stopStream()
    setLines([])
    setErrMsg('')
    setDone(false)
    setRunning(true)
    setAutoScroll(true)

    const args = buildLogStreamArgs({
      sourceType,
      namespace: ns,
      target: pod,
      container: ctr,
      tail,
      follow,
    })
    const res = await api.startLogStream(...args)
    if (!res?.ok) {
      setErrMsg(res?.error || '시작 실패')
      setRunning(false)
      return
    }
    jobRef.current = res.job_id

    pollRef.current = setInterval(async () => {
      // 트레이로 hide된 상태면 폴링 스킵 (백엔드 job은 살림)
      if (!visibleRef.current) return
      const chunk = await api.getLogChunk(jobRef.current)
      if (!chunk?.ok) {
        await stopStream()
        return
      }

      if (chunk.lines?.length > 0) {
        setLines(prev => {
          const merged = [...prev, ...chunk.lines]
          return merged.length > 10000 ? merged.slice(merged.length - 10000) : merged
        })
      }

      if (chunk.error && !errMsg) setErrMsg(chunk.error)

      if (chunk.stopped) {
        clearInterval(pollRef.current)
        pollRef.current = null
        jobRef.current = null
        setRunning(false)
        setDone(true)
      }
    }, 800)
  }

  useEffect(() => {
    if (!logTarget?.autoStart || !connected || !ns || !pod) return
    if (!isPodLogSource(sourceType)) return
    if (logTarget.namespace !== ns || logTarget.pod !== pod) return
    if (logTarget.container && ctr !== logTarget.container) return

    const key = [
      logTarget.namespace,
      logTarget.pod,
      logTarget.container || '',
      logTarget.tail || '',
    ].join('/')
    if (autoStartKeyRef.current === key) return
    autoStartKeyRef.current = key
    void startStream()
    setLogTarget(null)
  }, [logTarget, connected, sourceType, ns, pod, ctr])

  async function copyAll() {
    const text = filtered.join('\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  const filtered = filter
    ? lines.filter(line => line.toLowerCase().includes(filter.toLowerCase()))
    : lines

  const canStart = canStartLogStream({ connected, sourceType, namespace: ns, target: pod })
  const targetLabel = isPodLogSource(sourceType) ? '파드' : '워크로드'
  const activeSource = LOG_SOURCE_OPTIONS.find(opt => opt.id === sourceType)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 14px', borderBottom: '1px solid var(--border)',
        background: 'var(--bg-1)', flexShrink: 0, flexWrap: 'wrap',
      }}>
        <ScrollText size={14} color="var(--nimbus)" />
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-bright)' }}>
          로그 뷰어
        </span>

        <div style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 2px' }} />

        <Sel value={sourceType} onChange={value => {
          setSourceType(value)
          setPod('')
          setCtr('')
          setLines([])
          setErrMsg('')
          setDone(false)
        }} style={{ width: 145 }}>
          {LOG_SOURCE_OPTIONS.map(opt => (
            <option key={opt.id} value={opt.id}>{opt.label}</option>
          ))}
        </Sel>

        {!isIngressLogSource(sourceType) && (
          <Sel value={ns} onChange={value => { setNs(value); setPod(''); setCtr('') }}
            style={{ width: 150 }}>
            <option value="">네임스페이스 선택</option>
            {(namespaces || []).filter(item => item !== 'All Namespaces').map(item =>
              <option key={item}>{item}</option>
            )}
          </Sel>
        )}

        {!isIngressLogSource(sourceType) && (
          <Sel value={pod} onChange={value => { setPod(value); setCtr('') }}
            style={{ width: 210 }}>
            <option value="">{targetLabel} 선택</option>
            {targets.map(item => <option key={item}>{item}</option>)}
          </Sel>
        )}

        {isIngressLogSource(sourceType) && (
          <span className="chip chip-blue" style={{ fontSize: 11 }}>
            controller 자동 탐색
          </span>
        )}

        {isPodLogSource(sourceType) && ctrs.length > 1 && (
          <Sel value={ctr} onChange={setCtr} style={{ width: 140 }}>
            {ctrs.map(c => <option key={c}>{c}</option>)}
          </Sel>
        )}

        <div style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 2px' }} />

        <label style={{ fontSize: 11, color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: 5 }}>
          Tail
          <input
            type="number" min={10} max={5000} value={tail}
            onChange={e => setTail(Number(e.target.value))}
            style={{
              width: 60, background: 'var(--bg-3)', border: '1px solid var(--border)',
              borderRadius: 4, color: 'var(--text)', fontSize: 11, padding: '2px 6px',
              fontFamily: 'var(--font-mono)',
            }}
          />
        </label>

        <Toggle value={follow} onChange={setFollow} label="Follow" />

        <span style={{ flex: 1 }} />

        {!running ? (
          <button className="btn btn-primary btn-sm" onClick={startStream}
            disabled={!canStart} style={{ gap: 5 }}>
            <Play size={11} />
            시작
          </button>
        ) : (
          <button className="btn btn-danger btn-sm" onClick={stopStream} style={{ gap: 5 }}>
            <Square size={11} />
            중단
          </button>
        )}
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 14px', borderBottom: '1px solid var(--border)',
        background: 'var(--bg-0)', flexShrink: 0,
      }}>
        <Search size={12} color="var(--text-dim)" />
        <input
          type="text"
          placeholder="로그 필터"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--text)', fontSize: 12, fontFamily: 'var(--font-mono)',
          }}
        />

        <span style={{ fontSize: 11, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
          {filter ? `${filtered.length} / ${lines.length}줄` : `${lines.length}줄`}
        </span>

        <button className="btn btn-ghost btn-sm" onClick={copyAll}
          disabled={filtered.length === 0} style={{ gap: 4 }}>
          {copied ? <Check size={11} color="var(--green)" /> : <Copy size={11} />}
          {copied ? '복사됨' : '복사'}
        </button>

        <button className="btn btn-ghost btn-sm" onClick={() => setLines([])}
          disabled={lines.length === 0} style={{ gap: 4 }}>
          <Trash2 size={11} />
          지우기
        </button>

        <Toggle value={autoScroll} onChange={setAutoScroll} label="자동스크롤" />

        {!autoScroll && (
          <button className="btn btn-ghost btn-sm" onClick={() => {
            logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
            setAutoScroll(true)
          }}>
            <ArrowDown size={11} />
          </button>
        )}
      </div>

      <div
        ref={logBoxRef}
        onScroll={handleScroll}
        style={{
          flex: 1, overflow: 'auto',
          background: 'var(--bg-0)',
          padding: '10px 16px',
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          lineHeight: 1.65,
        }}
      >
        {lines.length === 0 && !running && !errMsg && (
          <div className="empty-state" style={{ height: '100%', minHeight: 300 }}>
            <ScrollText size={36} opacity={0.2} />
            {canStart
              ? <p style={{ fontWeight: 600, marginTop: 12 }}>{activeSource?.label || '대상'} 로그 준비됨</p>
              : <p style={{ fontWeight: 600, marginTop: 12 }}>클러스터 연결 또는 로그 대상을 확인하세요.</p>
            }
          </div>
        )}

        {errMsg && (
          <div style={{
            color: 'var(--red)', background: 'var(--red-bg)',
            border: '1px solid var(--red)', borderRadius: 6,
            padding: '8px 14px', marginBottom: 10, fontSize: 12,
            whiteSpace: 'pre-wrap',
          }}>
            {errMsg}
          </div>
        )}

        {filtered.map((line, i) => (
          <div key={i} style={{
            color: lineColor(line),
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            padding: '0 2px',
          }}>
            {filter ? highlightFilter(line, filter) : line}
          </div>
        ))}

        {running && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6,
            marginTop: 6, color: 'var(--nimbus)', fontSize: 11 }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: 'var(--nimbus)',
              animation: 'pulse 1.2s ease-in-out infinite',
            }} />
            {follow ? '스트리밍 중...' : '로드 중...'}
          </div>
        )}

        {done && !running && lines.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-dim)',
            borderTop: '1px dashed var(--border)', paddingTop: 6 }}>
            EOF ({lines.length}줄)
          </div>
        )}

        <div ref={logEndRef} />
      </div>

      <div style={{
        padding: '4px 14px', borderTop: '1px solid var(--border)',
        background: 'var(--bg-1)', flexShrink: 0,
        display: 'flex', alignItems: 'center', gap: 10, fontSize: 11,
        color: 'var(--text-dim)',
      }}>
        {isIngressLogSource(sourceType) ? (
          <span style={{ fontFamily: 'var(--font-mono)' }}>Ingress 통합 로그</span>
        ) : pod ? (
          <span style={{ fontFamily: 'var(--font-mono)' }}>
            {ns} / <span style={{ color: 'var(--text)' }}>{pod}</span>
            {isPodLogSource(sourceType) && ctr && ctrs.length > 1
              ? <> / <span style={{ color: 'var(--nimbus)' }}>{ctr}</span></>
              : null}
          </span>
        ) : (
          <span>대상 미선택</span>
        )}
        <span style={{ flex: 1 }} />
        {running && <span style={{ color: 'var(--nimbus)' }}>실행 중</span>}
        {done && !running && <span style={{ color: 'var(--green)' }}>완료</span>}
      </div>
    </div>
  )
}
