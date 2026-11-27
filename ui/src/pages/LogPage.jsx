import React, { useState, useEffect, useRef, useCallback, useMemo, useDeferredValue, memo } from 'react'
import { api } from '../api.js'
import { startPoll } from '../poll.js'
import { useApp } from '../store.jsx'
import AiDiagnoseButton from '../components/AiDiagnose.jsx'
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
  ArrowDown, Copy, Check, Download,
} from 'lucide-react'

function lineColor(line) {
  const lo = line.toLowerCase()
  if (/\b(error|exception|fatal|critical|panic)\b/.test(lo)) return 'var(--red)'
  if (/\b(warn(ing)?)\b/.test(lo)) return 'var(--yellow)'
  if (/\b(debug|trace)\b/.test(lo)) return 'var(--text-dim)'
  return 'var(--text)'
}

// AI 진단으로 보낼 로그 텍스트 정리. 인그레스 access log 등에는 공격 탐침의 바이너리/제어문자가
// 섞여(예: \x00) JS→Python 브리지 직렬화를 깨 text 가 비어 전달되곤 했다.
// 제어문자(탭·개행 제외) 제거 + 크기 캡(백엔드가 어차피 추가 트림). 빈 줄 배열도 안전 처리.
function logTextForAi(lines) {
  const recent = (Array.isArray(lines) ? lines : []).slice(-1200)
  return recent.join('\n')
    .replace(/[\u0000-\u001F]/g, c => (c === '\t' || c === '\n' || c === '\r') ? c : '')
    .slice(-80000)
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

// 로그 한 줄 (v1.3.42, 성능 P9) — 같은 글·같은 필터면 다시 그리지 않는다.
// `content-visibility: auto` 로 화면 밖 줄은 브라우저가 배치·그리기를 건너뛴다
// (줄마다 높이가 달라 고정 높이 창 방식은 맞지 않는다). 예전엔 800ms 마다 1만 줄을
// 전부 다시 배치했다.
const LOG_LINE_STYLE_BASE = {
  whiteSpace: 'pre-wrap', wordBreak: 'break-all', padding: '0 2px',
  contentVisibility: 'auto', containIntrinsicSize: 'auto 20px',
}
const LogLine = memo(function LogLine({ text, color, filter }) {
  return (
    <div style={{ ...LOG_LINE_STYLE_BASE, color }}>
      {filter ? highlightFilter(text, filter) : text}
    </div>
  )
})

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

  // lines: [{id, text, color}] — id 는 단조증가 카운터(react key 로 사용). 버퍼 상한 초과 시
  // 앞쪽을 잘라내는데, 예전엔 배열 인덱스를 key 로 써서 잘릴 때마다 남은 줄 전부의 key 가
  // 밀려 React 가 "전부 새 노드"로 보고 1만 줄을 통째로 재마운트했다(스트리밍 중 0.8초마다).
  // 안정적 id 를 쓰면 유지되는 줄은 React 가 기존 DOM 을 그대로 재사용한다. color 도 수신
  // 시점에 1회만 계산해 렌더마다(줄당 정규식 3회) 반복 안 하도록 저장.
  const [lines, setLines] = useState([])
  const lineIdRef = useRef(0)
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
    setLines([]); lineIdRef.current = 0
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
    // scrollIntoView 는 조상 스크롤까지 계산한다 — 상자 하나만 내리면 된다 (v1.3.42)
    const box = logBoxRef.current
    if (autoScroll && box) box.scrollTop = box.scrollHeight
  }, [lines, autoScroll])

  function handleScroll() {
    const box = logBoxRef.current
    if (!box) return
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40
    setAutoScroll(atBottom)
  }

  const stopStream = useCallback(async () => {
    if (pollRef.current) {
      pollRef.current()          // startPoll 의 stop (v1.3.41)
      pollRef.current = null
    }
    if (jobRef.current) {
      await api.stopLogStream(jobRef.current)
      jobRef.current = null
    }
    setRunning(false)
  }, [])

  // 시작 요청이 돌아오기 전에 화면을 떠나거나 다시 시작하면, 늦게 온 작업을 닫는다 (v1.3.73).
  // 예전엔 그 job 이 백엔드에 남고, 떠난 화면이 0.8초 폴링까지 시작했다.
  const startGenRef = useRef(0)
  useEffect(() => () => { startGenRef.current += 1; stopStream() }, [stopStream])

  async function startStream() {
    if (!canStartLogStream({ connected, sourceType, namespace: ns, target: pod })) return
    const gen = ++startGenRef.current
    await stopStream()
    setLines([]); lineIdRef.current = 0
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
    if (gen !== startGenRef.current) {            // 그 사이 떠났거나 다시 시작했다
      if (res?.ok && res.job_id) { try { await api.stopLogStream(res.job_id) } catch { /* 이미 끝남 */ } }
      return
    }
    if (!res?.ok) {
      setErrMsg(res?.error || '시작 실패')
      setRunning(false)
      return
    }
    jobRef.current = res.job_id
    const jid = res.job_id

    // 겹치지 않는 폴러(v1.3.41) — setInterval 이면 느린 응답 뒤에 다음 호출이 겹쳐,
    // 읽으면 비워지는 로그가 **순서가 뒤바뀐 채** 붙을 수 있었다.
    pollRef.current = startPoll(async () => {
      // 트레이로 hide된 상태면 폴링 스킵 (백엔드 job은 살림)
      if (!visibleRef.current) return
      if (jobRef.current !== jid) return false
      const chunk = await api.getLogChunk(jid)
      // 기다리는 사이 [중지] · 다시 시작했다 — 지난 작업의 줄을 새 화면에 붙이거나 새 작업을 끝난 것으로
      // 표시하지 않는다(v1.5.28 검토)
      if (jobRef.current !== jid) return false
      if (!chunk?.ok) {
        await stopStream()
        return
      }

      if (chunk.lines?.length > 0) {
        setLines(prev => {
          const appended = chunk.lines.map(text => ({
            id: lineIdRef.current++, text, color: lineColor(text),
          }))
          const merged = [...prev, ...appended]
          return merged.length > 10000 ? merged.slice(merged.length - 10000) : merged
        })
      }

      if (chunk.error && !errMsg) setErrMsg(chunk.error)

      if (chunk.stopped) {
        pollRef.current = null
        jobRef.current = null
        setRunning(false)
        setDone(true)
        return false
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
    const text = filtered.map(l => l.text).join('\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  async function downloadAll() {
    const text = filtered.map(l => l.text).join('\n')
    if (!text) return
    const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
    const base = String(pod || sourceType || 'logs').replace(/[^\w.-]/g, '_')
    await api.saveTextFile(text, `${base}-${stamp}.log`)
  }

  // 입력은 바로, 1만 줄 거르기는 한 박자 뒤에 — 타이핑이 밀리지 않게 (v1.3.42)
  const deferredFilter = useDeferredValue(filter)
  const filtered = useMemo(() => {
    if (!deferredFilter) return lines
    const needle = deferredFilter.toLowerCase()
    return lines.filter(l => l.text.toLowerCase().includes(needle))
  }, [lines, deferredFilter])

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
          setLines([]); lineIdRef.current = 0
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

        <button className="btn btn-ghost btn-sm" onClick={downloadAll}
          disabled={filtered.length === 0} style={{ gap: 4 }} title="로그를 파일로 저장">
          <Download size={11} />
          다운로드
        </button>

        <AiDiagnoseButton source="logs" disabled={filtered.length === 0}
          title="현재 로그를 LLM 으로 진단/질의"
          getPayload={() => ({
            namespace: ns, pod, container: ctr,
            text: logTextForAi(filtered.map(l => l.text)),
          })} />

        <button className="btn btn-ghost btn-sm" onClick={() => { setLines([]); lineIdRef.current = 0 }}
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

        {filtered.map(l => (
          <LogLine key={l.id} text={l.text} color={l.color} filter={deferredFilter} />
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
