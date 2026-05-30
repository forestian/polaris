/**
 * EventsPage — 클러스터 이벤트 타임라인 (v3.7.5)
 *
 * 기능:
 *   - SVG 시간축 차트 — 1h / 6h / 24h 윈도우, 분 단위 버킷 + 색상 분리(Warning 빨강, Normal 회색)
 *   - 버킷 클릭 → 해당 시간대 필터링
 *   - 타입(Normal/Warning) · 네임스페이스 · 자유 텍스트 필터
 *   - 이벤트 표: 시각 · 타입 · 이유 · 대상 · 메시지 · 횟수
 *   - 자동 새로고침 (10s 폴링) 토글
 */
import React, { useEffect, useState, useMemo, useRef } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Activity, RefreshCw, AlertCircle, Copy, Check, Download } from 'lucide-react'

const RANGES = [
  { id: '1h',  label: '1시간',  ms:    60 * 60 * 1000, bucketMs:  60 * 1000 },  // 1 min
  { id: '6h',  label: '6시간',  ms:  6 * 60 * 60 * 1000, bucketMs:  5 * 60 * 1000 },  // 5 min
  { id: '24h', label: '24시간', ms: 24 * 60 * 60 * 1000, bucketMs: 15 * 60 * 1000 },  // 15 min
]

// ── 시간 포맷 헬퍼 ──────────────────────────────────────────────────────────
function pad(n) { return String(n).padStart(2, '0') }
function fmtTime(d) {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}
function fmtFull(d) {
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function parseTs(s) {
  if (!s) return null
  const t = new Date(s)
  return isNaN(t.getTime()) ? null : t
}

// ── 메인 페이지 ──────────────────────────────────────────────────────────────
export default function EventsPage() {
  const { connected, namespace, windowVisible } = useApp()
  const [rangeId, setRangeId]   = useState('6h')
  const [typeFilter, setTypeFilter] = useState('all')   // all | Normal | Warning
  const [query, setQuery]       = useState('')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [events, setEvents]     = useState([])
  const [loading, setLoading]   = useState(false)
  const [err, setErr]           = useState(null)
  const [warning, setWarning]   = useState(null)
  const [source, setSource]     = useState(null)    // 어느 방식으로 수집했는지
  const [attempts, setAttempts] = useState([])      // 시도 내역 (디버그용)
  const [bucketSel, setBucketSel] = useState(null)   // 선택된 버킷의 [startMs, endMs]
  const [copied, setCopied]       = useState(false)

  const range = RANGES.find(r => r.id === rangeId) || RANGES[1]

  async function load() {
    if (!connected) return
    setLoading(true)
    setErr(null); setWarning(null)
    try {
      const ns = (namespace && namespace !== 'All Namespaces') ? namespace : ''
      const res = await api.getClusterEvents(ns, 500, null)
      // 신규 응답 형식: {ok, events, source, warning?, error?, attempts}
      if (res && typeof res === 'object' && 'events' in res) {
        setEvents(Array.isArray(res.events) ? res.events : [])
        setSource(res.source || null)
        setAttempts(Array.isArray(res.attempts) ? res.attempts : [])
        if (res.warning) setWarning(String(res.warning))
        if (res.ok === false && res.error) setErr(String(res.error))
      } else if (Array.isArray(res)) {
        // 구버전 백엔드 호환
        setEvents(res); setSource(null); setAttempts([])
      } else {
        setEvents([]); setSource(null); setAttempts([])
        if (res?.error) setErr(String(res.error))
      }
    } catch (e) {
      setErr(String(e))
      setEvents([]); setSource(null); setAttempts([])
    } finally {
      setLoading(false)
    }
  }

  // 초기 + 변경 시 로드
  useEffect(() => { load() }, [connected, namespace])

  // 자동 새로고침 — 트레이로 hide된 동안은 일시정지 (v3.7.11)
  useEffect(() => {
    if (!autoRefresh || !connected || !windowVisible) return
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [autoRefresh, connected, namespace, windowVisible])

  // 범위 변경 시 버킷 선택 초기화
  useEffect(() => { setBucketSel(null) }, [rangeId])

  // 타임라인 윈도우
  const now = Date.now()
  const winStart = now - range.ms

  // 시간 + 타입 + 텍스트 + 버킷 선택 필터링
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return events.filter(e => {
      const t = parseTs(e.last_time)
      if (!t) return false
      const ts = t.getTime()
      if (ts < winStart) return false
      if (bucketSel && (ts < bucketSel[0] || ts >= bucketSel[1])) return false
      if (typeFilter !== 'all' && e.type !== typeFilter) return false
      if (q) {
        const hay = `${e.reason} ${e.obj} ${e.message} ${e.namespace}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [events, query, typeFilter, winStart, range.ms, bucketSel])

  // 버킷 집계
  const buckets = useMemo(() => {
    const bucketCount = Math.ceil(range.ms / range.bucketMs)
    const arr = new Array(bucketCount).fill(0).map(() => ({ normal: 0, warning: 0 }))
    // 타입/텍스트 필터는 적용하지만 bucketSel은 적용하지 않음 (차트 자체이므로)
    const q = query.trim().toLowerCase()
    for (const e of events) {
      const t = parseTs(e.last_time)
      if (!t) continue
      const ts = t.getTime()
      if (ts < winStart || ts > now) continue
      if (typeFilter !== 'all' && e.type !== typeFilter) continue
      if (q) {
        const hay = `${e.reason} ${e.obj} ${e.message} ${e.namespace}`.toLowerCase()
        if (!hay.includes(q)) continue
      }
      const idx = Math.floor((ts - winStart) / range.bucketMs)
      if (idx < 0 || idx >= bucketCount) continue
      if (e.type === 'Warning') arr[idx].warning += (e.count || 1)
      else                       arr[idx].normal  += (e.count || 1)
    }
    return arr
  }, [events, range, winStart, now, typeFilter, query])

  const maxBucket = useMemo(() => Math.max(1, ...buckets.map(b => b.normal + b.warning)), [buckets])
  const warningTotal = useMemo(() => events.reduce((s, e) => {
    const t = parseTs(e.last_time); if (!t || t.getTime() < winStart) return s
    return s + (e.type === 'Warning' ? (e.count || 1) : 0)
  }, 0), [events, winStart])

  const normalTotal = useMemo(() => events.reduce((s, e) => {
    const t = parseTs(e.last_time); if (!t || t.getTime() < winStart) return s
    return s + (e.type === 'Normal' ? (e.count || 1) : 0)
  }, 0), [events, winStart])

  // ── 내보내기 (현재 필터된 이벤트를 TSV 로) ─────────────────────────────────
  function eventsToTSV() {
    const head = ['시각', '타입', '이유', '대상', '네임스페이스', '메시지', '횟수'].join('\t')
    const rows = filtered.map(e => {
      const t = parseTs(e.last_time)
      return [
        t ? fmtFull(t) : '',
        e.type || '',
        e.reason || '',
        e.obj || '',
        e.namespace || '',
        String(e.message || '').replace(/[\t\r\n]+/g, ' '),
        e.count ?? '',
      ].join('\t')
    })
    return [head, ...rows].join('\n')
  }

  async function copyEvents() {
    if (filtered.length === 0) return
    try { await navigator.clipboard.writeText(eventsToTSV()) } catch {}
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  async function downloadEvents() {
    if (filtered.length === 0) return
    const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
    await api.saveTextFile(eventsToTSV(), `events-${stamp}.tsv`)
  }

  if (!connected) {
    return (
      <div className="empty-state" style={{ height: '100%' }}>
        <AlertCircle size={36} opacity={0.3} />
        <p>클러스터에 연결되지 않았습니다.</p>
      </div>
    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* ── 헤더 ── */}
      <div style={{
        padding: '12px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
        background: 'var(--bg-1)',
      }}>
        <Activity size={16} color="var(--nimbus)" />
        <h2 style={{
          fontSize: 14, fontWeight: 700, color: 'var(--text-bright)', margin: 0,
          letterSpacing: '0.02em',
        }}>이벤트 타임라인</h2>

        <span style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 4 }}>
          {namespace && namespace !== 'All Namespaces' ? `네임스페이스: ${namespace}` : '모든 네임스페이스'}
        </span>

        <span style={{ flex: 1 }} />

        {/* 범위 선택 */}
        <div style={{ display: 'flex', gap: 1, background: 'var(--bg-3)', borderRadius: 5, padding: 2 }}>
          {RANGES.map(r => (
            <button key={r.id} onClick={() => setRangeId(r.id)}
              style={{
                padding: '3px 10px', fontSize: 11, border: 'none', cursor: 'pointer',
                background: rangeId === r.id ? 'var(--nimbus)' : 'transparent',
                color: rangeId === r.id ? '#051a0e' : 'var(--text-mid)',
                fontWeight: rangeId === r.id ? 700 : 500,
                borderRadius: 3,
              }}>
              {r.label}
            </button>
          ))}
        </div>

        {/* 타입 필터 */}
        <select className="select" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          style={{ fontSize: 11, padding: '3px 8px' }}>
          <option value="all">전체 타입</option>
          <option value="Warning">Warning</option>
          <option value="Normal">Normal</option>
        </select>

        {/* 검색 */}
        <input
          className="input"
          placeholder="이유·대상·메시지 검색..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{ fontSize: 11, width: 180, padding: '3px 8px' }}
        />

        {/* 자동 새로고침 */}
        <label style={{
          display: 'flex', alignItems: 'center', gap: 4,
          fontSize: 11, color: 'var(--text-mid)', cursor: 'pointer',
        }}>
          <input type="checkbox" checked={autoRefresh}
            onChange={e => setAutoRefresh(e.target.checked)} />
          자동
        </label>

        <button className="btn btn-ghost btn-sm" onClick={copyEvents}
          disabled={filtered.length === 0} style={{ gap: 4 }} title="필터된 이벤트 복사 (TSV)">
          {copied ? <Check size={11} color="var(--green)" /> : <Copy size={11} />}
          {copied ? '복사됨' : '복사'}
        </button>

        <button className="btn btn-ghost btn-sm" onClick={downloadEvents}
          disabled={filtered.length === 0} style={{ gap: 4 }} title="필터된 이벤트를 파일로 저장 (TSV)">
          <Download size={11} />
          다운로드
        </button>

        <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={11} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          새로고침
        </button>
      </div>

      {/* ── 통계 + 차트 ── */}
      <div style={{ flexShrink: 0, padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
        <div style={{
          display: 'flex', gap: 16, marginBottom: 10, fontSize: 12,
          alignItems: 'center',
        }}>
          <div>
            <span style={{ color: 'var(--text-dim)' }}>Warning</span>
            <span style={{ color: 'var(--red)', fontWeight: 700, marginLeft: 6 }}>
              {warningTotal}건
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)' }}>Normal</span>
            <span style={{ color: 'var(--text-mid)', fontWeight: 700, marginLeft: 6 }}>
              {normalTotal}건
            </span>
          </div>
          {bucketSel && (
            <div style={{
              marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8,
              fontSize: 11, color: 'var(--nimbus)',
            }}>
              <span>
                선택: {fmtTime(new Date(bucketSel[0]))} ~ {fmtTime(new Date(bucketSel[1]))}
              </span>
              <button onClick={() => setBucketSel(null)} className="btn btn-ghost btn-sm">
                해제
              </button>
            </div>
          )}
        </div>

        <TimelineChart
          buckets={buckets}
          maxBucket={maxBucket}
          range={range}
          winStart={winStart}
          now={now}
          selected={bucketSel}
          onSelect={(start, end) => {
            if (bucketSel && bucketSel[0] === start && bucketSel[1] === end) {
              setBucketSel(null)
            } else {
              setBucketSel([start, end])
            }
          }}
        />
      </div>

      {/* ── 진단 정보 (warning / source) ── */}
      {(warning || (source && source !== 'all-ns')) && (
        <div style={{
          margin: '8px 16px 0', padding: '8px 12px',
          background: warning ? 'rgba(251,191,36,0.08)' : 'rgba(96,165,250,0.06)',
          border: `1px solid ${warning ? 'rgba(251,191,36,0.25)' : 'rgba(96,165,250,0.18)'}`,
          borderRadius: 6, fontSize: 11, color: 'var(--text-mid)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <AlertCircle size={12} color={warning ? '#fbbf24' : '#60a5fa'} />
          <span style={{ flex: 1, lineHeight: 1.5 }}>
            {warning && <span>{warning} · </span>}
            {source && (
              <span style={{ color: 'var(--text-dim)' }}>
                수집 방식: <code style={{ color: 'var(--nimbus)', fontFamily: 'var(--font-mono)' }}>{source}</code>
                {source === 'per-ns'         && ' (네임스페이스 순회 — 전체 NS 조회 권한 없음)'}
                {source === 'events.k8s.io/v1' && ' (구 API 실패 시 신규 API 사용)'}
              </span>
            )}
          </span>
        </div>
      )}

      {/* ── 이벤트 목록 ── */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {err && (
          <div style={{ padding: '12px 20px', color: 'var(--red)', fontSize: 12 }}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>오류: {err}</div>
            {attempts.length > 0 && (
              <details style={{ marginTop: 4, fontSize: 11, color: 'var(--text-dim)' }}>
                <summary style={{ cursor: 'pointer' }}>시도 내역 ({attempts.length})</summary>
                <ul style={{ marginTop: 6, paddingLeft: 18, lineHeight: 1.6 }}>
                  {attempts.map((a, i) => (
                    <li key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5,
                      wordBreak: 'break-all' }}>{a}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
        {!err && filtered.length === 0 && (
          <div className="empty-state" style={{ height: 200 }}>
            <p style={{ color: 'var(--text-dim)', fontSize: 12 }}>
              {events.length === 0 ? '수집된 이벤트가 없습니다.' : '조건에 맞는 이벤트가 없습니다.'}
            </p>
          </div>
        )}
        {!err && filtered.length > 0 && (
          <EventTable events={filtered} />
        )}
      </div>
    </div>
  )
}

// ── 타임라인 SVG 차트 ────────────────────────────────────────────────────────
function TimelineChart({ buckets, maxBucket, range, winStart, now, selected, onSelect }) {
  const W = 1200
  const H = 100
  const padLeft = 30
  const padBottom = 18
  const chartW = W - padLeft - 4
  const chartH = H - padBottom - 6
  const n = buckets.length
  const barW = chartW / n

  // X축 시간 라벨 — 6개 등분
  const ticks = []
  for (let i = 0; i <= 6; i++) {
    const ts = winStart + (range.ms * i) / 6
    ticks.push({ x: padLeft + (chartW * i) / 6, label: fmtTime(new Date(ts)) })
  }

  return (
    <div style={{ width: '100%', overflow: 'hidden' }}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
        style={{ width: '100%', height: 90, display: 'block' }}>
        {/* 기준선 */}
        <line x1={padLeft} y1={chartH + 6} x2={W - 4} y2={chartH + 6}
          stroke="var(--border)" strokeWidth="0.5" />

        {/* 막대 */}
        {buckets.map((b, i) => {
          const total = b.normal + b.warning
          if (total === 0) return null
          const bx     = padLeft + i * barW
          const totalH = (chartH * total) / maxBucket
          const warnH  = (chartH * b.warning) / maxBucket
          const normH  = (chartH * b.normal)  / maxBucket
          const bucketStart = winStart + i * range.bucketMs
          const bucketEnd   = bucketStart + range.bucketMs
          const isSel = selected && selected[0] === bucketStart && selected[1] === bucketEnd
          return (
            <g key={i} onClick={() => onSelect(bucketStart, bucketEnd)}
              style={{ cursor: 'pointer' }}>
              {/* 호버 영역 */}
              <rect
                x={bx} y={0} width={Math.max(barW, 2)} height={chartH + 6}
                fill={isSel ? 'rgba(52,211,153,0.10)' : 'transparent'}
                stroke={isSel ? 'var(--nimbus)' : 'none'} strokeWidth="0.5"
              />
              <title>
                {fmtTime(new Date(bucketStart))} ~ {fmtTime(new Date(bucketEnd))}
                {'\n'}Warning {b.warning} · Normal {b.normal}
              </title>
              {/* Normal (아래) */}
              {b.normal > 0 && (
                <rect
                  x={bx + 0.5} width={Math.max(barW - 1, 1)}
                  y={chartH - normH + 6}
                  height={normH}
                  fill="var(--text-dim)"
                  opacity="0.55"
                />
              )}
              {/* Warning (위, 빨강) */}
              {b.warning > 0 && (
                <rect
                  x={bx + 0.5} width={Math.max(barW - 1, 1)}
                  y={chartH - totalH + 6}
                  height={warnH}
                  fill="var(--red)"
                />
              )}
            </g>
          )
        })}

        {/* X축 시간 라벨 */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={t.x} y1={chartH + 6} x2={t.x} y2={chartH + 10}
              stroke="var(--border-bright)" strokeWidth="0.5" />
            <text x={t.x} y={H - 4} fontSize="9" fill="var(--text-dim)"
              textAnchor="middle" fontFamily="var(--font-mono)">{t.label}</text>
          </g>
        ))}

        {/* Y 라벨 (최대값) */}
        <text x={padLeft - 4} y={10} fontSize="9" fill="var(--text-dim)"
          textAnchor="end" fontFamily="var(--font-mono)">{maxBucket}</text>
        <text x={padLeft - 4} y={chartH + 6} fontSize="9" fill="var(--text-dim)"
          textAnchor="end" fontFamily="var(--font-mono)">0</text>
      </svg>
    </div>
  )
}

// ── 이벤트 테이블 ────────────────────────────────────────────────────────────
function EventTable({ events }) {
  return (
    <div style={{
      background: 'var(--bg-2)', margin: 0,
    }}>
      {/* 헤더 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '110px 70px 130px 1.4fr 2fr 60px',
        columnGap: 12,
        padding: '8px 20px', fontSize: 10, fontWeight: 700,
        color: 'var(--text-mid)', textTransform: 'uppercase',
        letterSpacing: '0.06em', borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, background: 'var(--bg-2)', zIndex: 1,
      }}>
        <div>시각</div>
        <div>타입</div>
        <div>이유</div>
        <div>대상</div>
        <div>메시지</div>
        <div style={{ textAlign: 'right' }}>횟수</div>
      </div>

      {/* 행 */}
      {events.map((e, i) => {
        const isWarning = e.type === 'Warning'
        const ts = parseTs(e.last_time)
        return (
          <div key={i} style={{
            display: 'grid',
            gridTemplateColumns: '110px 70px 130px 1.4fr 2fr 60px',
            columnGap: 12,
            padding: '7px 20px', fontSize: 11.5,
            borderBottom: i < events.length - 1 ? '1px solid var(--border)' : 'none',
            background: isWarning ? 'rgba(248,113,113,0.03)' : 'transparent',
            fontVariantNumeric: 'tabular-nums',
          }}>
            <div style={{ color: 'var(--text-mid)', fontFamily: 'var(--font-mono)', fontSize: 10.5 }}
              title={ts ? fmtFull(ts) : ''}>
              {ts ? fmtTime(ts) : '-'}
            </div>
            <div>
              <span className={`chip ${isWarning ? 'chip-red' : 'chip-dim'}`}
                style={{ fontSize: 10 }}>{e.type || '?'}</span>
            </div>
            <div style={{ color: 'var(--text-bright)', overflow: 'hidden',
              textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              fontFamily: 'var(--font-mono)', fontSize: 11 }}
              title={e.reason}>{e.reason || '-'}</div>
            <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <span style={{ color: 'var(--text)' }}>{e.obj || '-'}</span>
              {e.namespace && (
                <span style={{ color: 'var(--text-dim)', fontSize: 10, marginLeft: 6 }}>
                  {e.namespace}
                </span>
              )}
            </div>
            <div style={{ color: 'var(--text)', overflow: 'hidden',
              textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={e.message}>
              {e.message || '-'}
            </div>
            <div style={{ textAlign: 'right', color: 'var(--text-mid)' }}>{e.count}</div>
          </div>
        )
      })}
    </div>
  )
}
