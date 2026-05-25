/**
 * MetricsTab — 파드 메트릭 실시간 그래프 (v3.7.8)
 *
 * metrics.k8s.io API를 5초마다 폴링하여 시계열 데이터로 축적.
 * 컨테이너별 CPU(mCore) / Memory(MiB) 라인 차트 + 통계.
 *
 * 데이터:
 *   points[] = [{t, cpu_m, mem_mi, containers: [{name, cpu_m, mem_mi}]}, ...]
 *   윈도우: 5분 (60p) / 15분 (180p) / 1시간 (720p)
 */
import React, { useState, useEffect, useRef, useMemo } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Cpu, MemoryStick, AlertCircle, Activity } from 'lucide-react'

// ── 윈도우 설정 ────────────────────────────────────────────────────────────
const WINDOWS = [
  { key: '5m',  label: '5분',  points: 60  },
  { key: '15m', label: '15분', points: 180 },
  { key: '1h',  label: '1시간', points: 720 },
]
const POLL_MS    = 5000
const MAX_BUFFER = 720

// ── 컨테이너 색상 팔레트 ───────────────────────────────────────────────────
const COLORS = [
  '#34d399', // 녹색 (nimbus)
  '#60a5fa', // 파랑
  '#fbbf24', // 노랑
  '#f87171', // 빨강
  '#a78bfa', // 보라
  '#fb923c', // 주황
  '#22d3ee', // 청록
  '#f472b6', // 분홍
]

// ── 포맷터 ─────────────────────────────────────────────────────────────────
function fmtCpu(m) {
  if (m == null) return '—'
  if (m >= 1000) return (m / 1000).toFixed(2) + ' Core'
  return Math.round(m) + ' mCore'
}
function fmtMem(mi) {
  if (mi == null) return '—'
  if (mi >= 1024) return (mi / 1024).toFixed(2) + ' GiB'
  return Math.round(mi) + ' MiB'
}
function fmtTime(ts) {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

// ── 통계 계산 ──────────────────────────────────────────────────────────────
function stats(values) {
  if (!values || values.length === 0) return { cur: 0, avg: 0, max: 0 }
  const cur = values[values.length - 1] ?? 0
  const max = Math.max(...values)
  const avg = values.reduce((a, b) => a + b, 0) / values.length
  return { cur, avg, max }
}

// ── 평활화된 path 빌더 (catmull-rom → cubic bezier) ───────────────────────
function smoothPath(pts) {
  if (pts.length === 0) return ''
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`
  let d = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[i + 2] || p2
    // catmull-rom → bezier 변환 (텐션 0.5)
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`
  }
  return d
}

// ── 라인 차트 ──────────────────────────────────────────────────────────────
function LineChart({
  series,       // [{name, values: [{t, v}], color}]
  unit,         // 'm' | 'Mi'
  fmt,          // (v) => string
  request,      // request 임계선 값 (또는 null)
  limit,        // limit 임계선 값
  height = 140,
  hovered,      // {idx, x, y} | null
  onHover,
}) {
  const PAD_L = 48, PAD_R = 14, PAD_T = 10, PAD_B = 22
  const wrapRef = useRef(null)
  const [width, setWidth] = useState(600)

  useEffect(() => {
    if (!wrapRef.current) return
    const ro = new ResizeObserver(entries => {
      for (const e of entries) setWidth(e.contentRect.width)
    })
    ro.observe(wrapRef.current)
    return () => ro.disconnect()
  }, [])

  const innerW = Math.max(width - PAD_L - PAD_R, 50)
  const innerH = height - PAD_T - PAD_B

  // 데이터 없을 때
  const allVals = series.flatMap(s => s.values.map(p => p.v))
  const hasData = allVals.length > 0
  const maxV = hasData ? Math.max(...allVals, request || 0, limit || 0, 1) : 1
  const niceMax = niceUpperBound(maxV)
  const tCount = series[0]?.values?.length || 0
  const xStep = tCount > 1 ? innerW / (tCount - 1) : innerW

  function xOf(i) { return PAD_L + i * xStep }
  function yOf(v) { return PAD_T + innerH - (v / niceMax) * innerH }

  // y축 눈금 (4개)
  const yTicks = Array.from({ length: 5 }, (_, i) => (niceMax / 4) * i)

  return (
    <div ref={wrapRef} style={{ position: 'relative' }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        style={{ display: 'block', overflow: 'visible' }}
        onMouseMove={e => {
          if (!hasData) return
          const rect = e.currentTarget.getBoundingClientRect()
          const px = (e.clientX - rect.left) * (width / rect.width)
          if (px < PAD_L) { onHover?.(null); return }
          const idx = Math.max(0, Math.min(tCount - 1, Math.round((px - PAD_L) / xStep)))
          onHover?.({ idx, x: xOf(idx) })
        }}
        onMouseLeave={() => onHover?.(null)}
      >
        {/* 배경 격자 */}
        {yTicks.map((v, i) => (
          <g key={i}>
            <line
              x1={PAD_L} y1={yOf(v)} x2={width - PAD_R} y2={yOf(v)}
              stroke="rgba(255,255,255,0.04)" strokeWidth="1"
            />
            <text
              x={PAD_L - 6} y={yOf(v) + 3}
              fontSize="9" fill="var(--text-dim)" textAnchor="end"
              fontFamily="var(--font-mono)"
            >
              {fmt(v)}
            </text>
          </g>
        ))}

        {/* request / limit 임계선 */}
        {request > 0 && request < niceMax && (
          <>
            <line
              x1={PAD_L} y1={yOf(request)} x2={width - PAD_R} y2={yOf(request)}
              stroke="#fbbf24" strokeWidth="1" strokeDasharray="3 4" opacity="0.55"
            />
            <text x={width - PAD_R + 2} y={yOf(request) + 3}
              fontSize="9" fill="#fbbf24" opacity="0.8">req</text>
          </>
        )}
        {limit > 0 && limit < niceMax && (
          <>
            <line
              x1={PAD_L} y1={yOf(limit)} x2={width - PAD_R} y2={yOf(limit)}
              stroke="#f87171" strokeWidth="1" strokeDasharray="3 4" opacity="0.55"
            />
            <text x={width - PAD_R + 2} y={yOf(limit) + 3}
              fontSize="9" fill="#f87171" opacity="0.8">lim</text>
          </>
        )}

        {/* 각 컨테이너 라인 + 그라데이션 fill */}
        {series.map((s, si) => {
          const pts = s.values.map((p, i) => ({ x: xOf(i), y: yOf(p.v) }))
          if (pts.length === 0) return null
          const d = smoothPath(pts)
          const fillD = d + ` L ${pts[pts.length - 1].x} ${PAD_T + innerH} L ${pts[0].x} ${PAD_T + innerH} Z`
          const gradId = `mt-grad-${unit}-${si}`
          return (
            <g key={s.name}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor={s.color} stopOpacity="0.22" />
                  <stop offset="100%" stopColor={s.color} stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d={fillD} fill={`url(#${gradId})`} />
              <path d={d} fill="none" stroke={s.color}
                    strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </g>
          )
        })}

        {/* hover 인디케이터 */}
        {hovered && hasData && (
          <g pointerEvents="none">
            <line
              x1={hovered.x} y1={PAD_T} x2={hovered.x} y2={PAD_T + innerH}
              stroke="rgba(255,255,255,0.18)" strokeWidth="1" strokeDasharray="2 3"
            />
            {series.map((s, si) => {
              const p = s.values[hovered.idx]
              if (!p) return null
              return (
                <circle key={si} cx={hovered.x} cy={yOf(p.v)} r="3"
                        fill={s.color} stroke="var(--bg-2)" strokeWidth="1.5" />
              )
            })}
          </g>
        )}

        {/* x축 시간 라벨 (양 끝만) */}
        {hasData && tCount > 0 && (
          <>
            <text x={PAD_L} y={height - 6}
              fontSize="9" fill="var(--text-dim)" textAnchor="start"
              fontFamily="var(--font-mono)">
              {fmtTime(series[0].values[0].t)}
            </text>
            <text x={width - PAD_R} y={height - 6}
              fontSize="9" fill="var(--text-dim)" textAnchor="end"
              fontFamily="var(--font-mono)">
              {fmtTime(series[0].values[tCount - 1].t)}
            </text>
          </>
        )}

        {/* 빈 데이터 안내 */}
        {!hasData && (
          <text x={width / 2} y={height / 2}
            fontSize="11" fill="var(--text-dim)" textAnchor="middle">
            데이터 수집 중...
          </text>
        )}
      </svg>
    </div>
  )
}

// y축 최댓값을 깔끔한 숫자로
function niceUpperBound(v) {
  if (v <= 0) return 1
  const pow = Math.pow(10, Math.floor(Math.log10(v)))
  const norm = v / pow
  let nice
  if      (norm <= 1)   nice = 1
  else if (norm <= 2)   nice = 2
  else if (norm <= 2.5) nice = 2.5
  else if (norm <= 5)   nice = 5
  else                  nice = 10
  return nice * pow
}

// ── 메인 ───────────────────────────────────────────────────────────────────
export default function MetricsTab({ ns, name }) {
  const [windowKey, setWindowKey]   = useState('5m')
  const [points, setPoints]         = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [noServer, setNoServer]     = useState(false)
  const [reqs, setReqs]             = useState({ cpu_m: 0, mem_mi: 0 })
  const [lims, setLims]             = useState({ cpu_m: 0, mem_mi: 0 })
  const [hoveredCpu, setHoveredCpu] = useState(null)
  const [hoveredMem, setHoveredMem] = useState(null)
  const [paused, setPaused]         = useState(false)
  const { windowVisible }           = useApp()

  const cancelRef = useRef(false)

  // 폴링 — 일시정지 또는 트레이로 hide된 동안 중단 (v3.7.11)
  useEffect(() => {
    if (paused || !windowVisible) return
    cancelRef.current = false
    let timer = null

    async function tick() {
      const res = await api.getPodMetrics(ns, name)
      if (cancelRef.current) return
      if (!res?.ok) {
        if (res?.no_metrics_server) {
          setNoServer(true); setError(null)
        } else {
          setError(res?.error || '메트릭 로드 실패')
        }
        setLoading(false)
        return
      }
      setError(null); setNoServer(false); setLoading(false)
      setReqs(res.requests || { cpu_m: 0, mem_mi: 0 })
      setLims(res.limits   || { cpu_m: 0, mem_mi: 0 })
      setPoints(prev => {
        const t = Date.now()
        const next = [...prev, {
          t,
          cpu_m:      res.total?.cpu_m  ?? 0,
          mem_mi:     res.total?.mem_mi ?? 0,
          containers: res.containers || [],
        }]
        return next.length > MAX_BUFFER ? next.slice(-MAX_BUFFER) : next
      })
    }

    tick()
    timer = setInterval(tick, POLL_MS)
    return () => {
      cancelRef.current = true
      if (timer) clearInterval(timer)
    }
  }, [ns, name, paused, windowVisible])

  // 파드 변경 시 데이터 초기화
  useEffect(() => {
    setPoints([]); setLoading(true); setError(null); setNoServer(false)
  }, [ns, name])

  // 윈도우 적용
  const winPoints = WINDOWS.find(w => w.key === windowKey)?.points ?? 60
  const sliced = useMemo(() => points.slice(-winPoints), [points, winPoints])

  // 컨테이너 목록 (현재 시점 기준)
  const containerNames = useMemo(() => {
    const set = new Set()
    for (const p of sliced) {
      for (const c of (p.containers || [])) set.add(c.name)
    }
    return Array.from(set)
  }, [sliced])

  // 시리즈 빌드
  const cpuSeries = useMemo(() => containerNames.map((cn, i) => ({
    name:   cn,
    color:  COLORS[i % COLORS.length],
    values: sliced.map(p => {
      const c = (p.containers || []).find(x => x.name === cn)
      return { t: p.t, v: c?.cpu_m ?? 0 }
    }),
  })), [sliced, containerNames])

  const memSeries = useMemo(() => containerNames.map((cn, i) => ({
    name:   cn,
    color:  COLORS[i % COLORS.length],
    values: sliced.map(p => {
      const c = (p.containers || []).find(x => x.name === cn)
      return { t: p.t, v: c?.mem_mi ?? 0 }
    }),
  })), [sliced, containerNames])

  // 합산 통계
  const cpuTotals = sliced.map(p => p.cpu_m ?? 0)
  const memTotals = sliced.map(p => p.mem_mi ?? 0)
  const cpuStats  = stats(cpuTotals)
  const memStats  = stats(memTotals)

  // ── 렌더 ────────────────────────────────────────────────────────────────
  if (noServer) {
    return (
      <div style={{ padding: '24px 12px' }}>
        <div style={{
          background: 'var(--bg-3)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '18px 20px',
          display: 'flex', gap: 12, alignItems: 'flex-start',
        }}>
          <AlertCircle size={20} color="var(--yellow)" style={{ flexShrink: 0, marginTop: 2 }} />
          <div style={{ fontSize: 12, lineHeight: 1.7 }}>
            <div style={{ fontWeight: 700, color: 'var(--text-bright)', marginBottom: 4 }}>
              metrics-server를 찾을 수 없습니다
            </div>
            <div style={{ color: 'var(--text-mid)' }}>
              파드 메트릭을 표시하려면 클러스터에 metrics-server가 설치되어야 합니다.
            </div>
            <pre style={{
              marginTop: 10, padding: '8px 10px',
              background: 'var(--bg-0)', border: '1px solid var(--border)',
              borderRadius: 5, fontSize: 11, color: 'var(--nimbus)',
              fontFamily: 'var(--font-mono)',
            }}>
{`kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`}
            </pre>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div style={{ padding: 30, textAlign: 'center' }}>
        <div className="spinner" />
        <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-dim)' }}>
          메트릭 수집 중...
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '4px 0 14px' }}>
      {/* ── 상단 컨트롤 바 ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        marginBottom: 14, padding: '6px 10px',
        background: 'var(--bg-3)', border: '1px solid var(--border)',
        borderRadius: 6,
      }}>
        <Activity size={12} color="var(--nimbus)" />
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-bright)' }}>
          실시간 메트릭
        </span>
        <span style={{
          fontSize: 9, padding: '1px 6px', borderRadius: 3,
          background: paused ? 'rgba(248,113,113,0.15)' : 'rgba(52,211,153,0.15)',
          color: paused ? '#f87171' : 'var(--nimbus)',
          border: `1px solid ${paused ? 'rgba(248,113,113,0.3)' : 'rgba(52,211,153,0.3)'}`,
          fontWeight: 700,
        }}>
          {paused ? '일시정지' : `5s · ${sliced.length}p`}
        </span>
        <span style={{ flex: 1 }} />

        {/* 윈도우 토글 */}
        <div style={{ display: 'flex', gap: 2 }}>
          {WINDOWS.map(w => (
            <button
              key={w.key}
              onClick={() => setWindowKey(w.key)}
              style={{
                fontSize: 10, padding: '3px 9px',
                background: windowKey === w.key ? 'var(--nimbus)' : 'transparent',
                color:      windowKey === w.key ? '#000' : 'var(--text-dim)',
                border:    `1px solid ${windowKey === w.key ? 'var(--nimbus)' : 'var(--border)'}`,
                borderRadius: 4, cursor: 'pointer', fontWeight: 600,
                transition: 'all 0.1s',
              }}
            >
              {w.label}
            </button>
          ))}
        </div>

        <button
          onClick={() => setPaused(p => !p)}
          style={{
            fontSize: 10, padding: '3px 9px',
            background: 'transparent', color: 'var(--text-dim)',
            border: '1px solid var(--border)', borderRadius: 4,
            cursor: 'pointer', fontWeight: 600,
          }}
        >
          {paused ? '재개' : '일시정지'}
        </button>
      </div>

      {/* ── 에러 표시 ── */}
      {error && (
        <div style={{
          background: 'var(--red-bg)', color: 'var(--red)',
          border: '1px solid #7f1d1d', borderRadius: 5,
          padding: '8px 12px', fontSize: 11, marginBottom: 12,
        }}>
          {error}
        </div>
      )}

      {/* ── CPU 차트 ── */}
      <div style={{
        background: 'var(--bg-2)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '10px 12px', marginBottom: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Cpu size={12} color="var(--nimbus)" />
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-bright)' }}>
            CPU
          </span>
          <span style={{ flex: 1 }} />
          <StatChip label="현재" value={fmtCpu(
            hoveredCpu ? (sliced[hoveredCpu.idx]?.cpu_m ?? cpuStats.cur) : cpuStats.cur
          )} />
          <StatChip label="평균" value={fmtCpu(cpuStats.avg)} />
          <StatChip label="최대" value={fmtCpu(cpuStats.max)} />
        </div>
        <LineChart
          series={cpuSeries}
          unit="m"
          fmt={fmtCpu}
          request={reqs.cpu_m}
          limit={lims.cpu_m}
          hovered={hoveredCpu}
          onHover={setHoveredCpu}
        />
      </div>

      {/* ── Memory 차트 ── */}
      <div style={{
        background: 'var(--bg-2)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '10px 12px', marginBottom: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <MemoryStick size={12} color="#60a5fa" />
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-bright)' }}>
            Memory
          </span>
          <span style={{ flex: 1 }} />
          <StatChip label="현재" value={fmtMem(
            hoveredMem ? (sliced[hoveredMem.idx]?.mem_mi ?? memStats.cur) : memStats.cur
          )} />
          <StatChip label="평균" value={fmtMem(memStats.avg)} />
          <StatChip label="최대" value={fmtMem(memStats.max)} />
        </div>
        <LineChart
          series={memSeries}
          unit="Mi"
          fmt={fmtMem}
          request={reqs.mem_mi}
          limit={lims.mem_mi}
          hovered={hoveredMem}
          onHover={setHoveredMem}
        />
      </div>

      {/* ── 컨테이너 범례 ── */}
      {containerNames.length > 0 && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10,
          padding: '8px 10px',
          background: 'var(--bg-2)', border: '1px solid var(--border)',
          borderRadius: 6,
        }}>
          <span style={{
            fontSize: 9, fontWeight: 700, color: 'var(--text-dim)',
            textTransform: 'uppercase', letterSpacing: '0.06em',
            alignSelf: 'center', marginRight: 4,
          }}>
            컨테이너
          </span>
          {containerNames.map((cn, i) => {
            const lastPoint = sliced[sliced.length - 1]
            const c = lastPoint?.containers?.find(x => x.name === cn)
            return (
              <div key={cn} style={{
                display: 'flex', alignItems: 'center', gap: 5,
                fontSize: 10.5, padding: '3px 8px',
                background: 'var(--bg-3)', borderRadius: 12,
                border: '1px solid var(--border)',
              }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: COLORS[i % COLORS.length], flexShrink: 0,
                }} />
                <span style={{ color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>
                  {cn}
                </span>
                {c && (
                  <span style={{ color: 'var(--text-dim)', fontSize: 9.5 }}>
                    {fmtCpu(c.cpu_m)} · {fmtMem(c.mem_mi)}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── 리소스 컨텍스트 (request/limit) ── */}
      {(reqs.cpu_m > 0 || lims.cpu_m > 0 || reqs.mem_mi > 0 || lims.mem_mi > 0) && (
        <div style={{
          marginTop: 10, padding: '8px 10px',
          background: 'var(--bg-2)', border: '1px solid var(--border)',
          borderRadius: 6,
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px',
          fontSize: 10.5, color: 'var(--text-mid)',
        }}>
          <div>
            <span style={{ color: '#fbbf24' }}>req</span> CPU {fmtCpu(reqs.cpu_m)} · MEM {fmtMem(reqs.mem_mi)}
          </div>
          <div>
            <span style={{ color: '#f87171' }}>lim</span> CPU {fmtCpu(lims.cpu_m)} · MEM {fmtMem(lims.mem_mi)}
          </div>
        </div>
      )}
    </div>
  )
}

// ── 통계 칩 ────────────────────────────────────────────────────────────────
function StatChip({ label, value }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', gap: 4,
      fontSize: 10, color: 'var(--text-dim)',
    }}>
      <span>{label}</span>
      <span style={{
        color: 'var(--text-bright)', fontWeight: 700,
        fontFamily: 'var(--font-mono)', fontSize: 11,
      }}>
        {value}
      </span>
    </div>
  )
}
