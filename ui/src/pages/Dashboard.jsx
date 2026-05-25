import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Server, RefreshCw } from 'lucide-react'

// ── KPI 카드 (시안 B 스타일) ───────────────────────────────────────────────────
function KpiCard({ label, value, suffix, sub, color = 'var(--nimbus)' }) {
  return (
    <div style={{
      background: 'var(--bg-2)', border: '1px solid var(--border)',
      borderRadius: 10, padding: 14, position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        fontSize: 10.5, color: 'var(--text-dim)', letterSpacing: '0.06em',
        textTransform: 'uppercase', fontWeight: 600,
      }}>{label}</div>
      <div style={{ marginTop: 6, display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{
          fontSize: 30, fontWeight: 700, color, letterSpacing: '-0.02em',
          fontVariantNumeric: 'tabular-nums', lineHeight: 1,
        }}>{value ?? '—'}</span>
        {suffix && <span style={{ fontSize: 14, color: 'var(--text-dim)' }}>{suffix}</span>}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

// ── 섹션 제목 ─────────────────────────────────────────────────────────────────
function SectionTitle({ children, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: 'var(--text-mid)',
        letterSpacing: '0.07em', textTransform: 'uppercase',
      }}>{children}</div>
      {right}
    </div>
  )
}

// ── 사용률 바 ─────────────────────────────────────────────────────────────────
function UsageBar({ label, pct, used, total, color }) {
  const width = Math.max(0, Math.min(Number(pct) || 0, 100))
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{label}</span>
        <span style={{ fontSize: 10, color: 'var(--text-mid)', whiteSpace: 'nowrap' }}>
          {used} / {total} ({width}%)
        </span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: 'var(--bg-4)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 2, width: `${width}%`,
          background: width > 85 ? 'var(--red)' : width > 70 ? 'var(--yellow)' : color,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  )
}

// ── 노드 카드 ────────────────────────────────────────────────────────────────
function formatCpu(m = 0) {
  const v = Number(m) || 0
  return v >= 1000 ? `${(v / 1000).toFixed(1)}Core` : `${v}m`
}
function formatMem(mi = 0) {
  const v = Number(mi) || 0
  return v >= 1024 ? `${(v / 1024).toFixed(1)}GiB` : `${v}MiB`
}

function NodeCard({ node }) {
  const ok = node.status === 'Ready'
  const podPct = node.max_pods > 0 ? Math.round(node.pod_count / node.max_pods * 100) : 0
  const cpuStr = formatCpu(node.cpu_alloc_m)
  const memStr = formatMem(node.mem_alloc_mi)
  const hasMetrics = Boolean(node.metrics_available)

  return (
    <div style={{
      background: 'var(--bg-2)',
      border: `1px solid ${ok ? 'var(--border)' : '#7f1d1d'}`,
      borderRadius: 10, padding: '14px 16px', minWidth: 0,
    }}>
      {/* 이름 + 상태 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: ok ? 'var(--nimbus)' : 'var(--red)',
            boxShadow: ok ? '0 0 6px var(--nimbus)' : 'none',
          }} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {node.name}
            </div>
            <div style={{ fontSize: 9.5, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              {node.role}
            </div>
          </div>
        </div>
        <span className={`chip ${ok ? 'chip-green' : 'chip-red'}`} style={{ fontSize: 10 }}>
          {node.status}
        </span>
      </div>

      {/* 파드 */}
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
          <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>파드</span>
          <span style={{ fontSize: 10, color: 'var(--text-mid)' }}>{node.pod_count} / {node.max_pods}</span>
        </div>
        <div style={{ height: 4, borderRadius: 2, background: 'var(--bg-4)', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 2,
            width: `${podPct}%`,
            background: podPct > 80 ? 'var(--yellow)' : 'var(--nimbus)',
            transition: 'width 0.5s ease',
          }} />
        </div>
      </div>

      {hasMetrics ? (
        <>
          <UsageBar label="CPU" pct={node.cpu_pct} used={formatCpu(node.cpu_used_m)} total={cpuStr} color="var(--nimbus)" />
          <UsageBar label="MEM" pct={node.mem_pct} used={formatMem(node.mem_used_mi)} total={memStr} color="var(--blue)" />
        </>
      ) : node.cpu_alloc_m > 0 && (
        <div style={{ fontSize: 10, color: 'var(--text-dim)', lineHeight: 1.6 }}>
          <div>CPU {cpuStr} · MEM {memStr}</div>
          <div style={{ color: 'var(--text-dim)', opacity: 0.7 }}>metrics-server 없음</div>
        </div>
      )}
    </div>
  )
}

// ── 상태 칩 ──────────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const s = String(status || '').toLowerCase()
  const isOk   = s === 'running' || s === 'succeeded' || s === 'completed'
  const isWarn = s === 'pending' || s.startsWith('containercreating') || s.startsWith('init')
  return (
    <span className={`chip ${isOk ? 'chip-green' : isWarn ? 'chip-yellow' : 'chip-red'}`}>
      {status}
    </span>
  )
}

// ── 메인 페이지 ──────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { connected, clusterName, setShowConnect } = useApp()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    if (!connected) return
    setLoading(true)
    try { setData(await api.getDashboard()) } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [connected])

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Server size={40} opacity={0.3} />
      <p>클러스터에 연결되지 않았습니다.</p>
      <button className="btn btn-primary" onClick={() => setShowConnect(true)}>
        kubeconfig 연결
      </button>
    </div>
  )

  const pods    = data?.pods  || []
  const nodes   = data?.nodes || []
  const running  = pods.filter(p => p.status === 'Running').length
  const abnormal = pods.filter(p => !['Running', 'Succeeded', 'Completed'].includes(p.status))
  const notReady = nodes.filter(n => n.status !== 'Ready').length
  const restarts = data?.total_restarts || 0
  const nsCnt    = data?.namespace_count || 0

  const recentPods = [...pods].sort((a, b) => {
    const aOk = ['Running', 'Succeeded', 'Completed'].includes(a.status)
    const bOk = ['Running', 'Succeeded', 'Completed'].includes(b.status)
    if (!aOk && bOk) return -1
    if (aOk && !bOk) return 1
    return parseInt(b.restarts || 0) - parseInt(a.restarts || 0)
  }).slice(0, 30)

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '20px 22px' }}>

      {/* ── 헤더 ── */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 10.5, color: 'var(--text-dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          DASHBOARD{clusterName ? ` · ${clusterName}` : ''}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em', margin: 0 }}>
            {notReady === 0 && abnormal.length === 0
              ? '클러스터 상태가 양호합니다'
              : '클러스터 점검이 필요합니다'}
          </h1>
          <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            새로고침
          </button>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
          {nodes.length}개 노드 · {pods.length}개 파드 · {nsCnt}개 네임스페이스
        </div>
      </div>

      {/* ── KPI 카드 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
        <KpiCard
          label="노드"
          value={nodes.length}
          sub={notReady > 0 ? `NotReady ${notReady}개` : '모두 Ready'}
          color={notReady > 0 ? 'var(--red)' : 'var(--nimbus)'}
        />
        <KpiCard
          label="파드"
          value={pods.length}
          sub={`Running ${running}개`}
          color="var(--blue)"
        />
        <KpiCard
          label="네임스페이스"
          value={nsCnt || '—'}
          sub="활성 워크로드"
          color="var(--purple)"
        />
        <KpiCard
          label="총 재시작"
          value={restarts}
          sub={restarts > 50 ? '점검 권장' : '정상 범위'}
          color={restarts > 100 ? 'var(--red)' : restarts > 30 ? 'var(--yellow)' : 'var(--text-bright)'}
        />
      </div>

      {/* ── 노드 상태 ── */}
      {nodes.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <SectionTitle>NODES</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
            {nodes.map(n => <NodeCard key={n.name} node={n} />)}
          </div>
        </section>
      )}

      {/* ── 파드 현황 ── */}
      {pods.length > 0 && (
        <section>
          <SectionTitle
            right={
              <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                {abnormal.length > 0 && (
                  <span style={{ color: 'var(--red)', fontWeight: 600, marginRight: 10 }}>
                    ⚠ 비정상 {abnormal.length}개
                  </span>
                )}
                상위 {recentPods.length}개
              </span>
            }
          >
            RECENT PODS
          </SectionTitle>

          <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            {/* 헤더 */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '2.5fr 1.3fr 110px 72px 68px 110px',
              columnGap: 8,
              padding: '10px 14px', fontSize: 10, fontWeight: 600,
              color: 'var(--text-mid)', textTransform: 'uppercase',
              letterSpacing: '0.05em', borderBottom: '1px solid var(--border)',
              position: 'sticky', top: 0, background: 'var(--bg-2)',
            }}>
              <div>이름</div>
              <div>네임스페이스</div>
              <div>상태</div>
              <div style={{ textAlign: 'right' }}>재시작</div>
              <div>AGE</div>
              <div>노드</div>
            </div>

            {/* 행 */}
            {recentPods.map((p, i) => {
              const isAbnormal = !['Running', 'Succeeded', 'Completed'].includes(p.status)
              return (
                <div key={i} style={{
                  display: 'grid',
                  gridTemplateColumns: '2.5fr 1.3fr 110px 72px 68px 110px',
                  columnGap: 8,
                  padding: '8px 14px', fontSize: 12,
                  borderBottom: i < recentPods.length - 1 ? '1px solid var(--border)' : 'none',
                  fontVariantNumeric: 'tabular-nums',
                  background: isAbnormal ? 'rgba(248,113,113,0.04)' : 'transparent',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                      background: p.status === 'Running' ? 'var(--green)'
                        : p.status === 'Pending' ? 'var(--yellow)' : 'var(--red)',
                      boxShadow: p.status === 'Running' ? '0 0 5px var(--green)' : 'none',
                    }} />
                    <span style={{ color: 'var(--text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                      {p.name}
                    </span>
                  </div>
                  <div style={{ color: 'var(--blue)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.namespace}</div>
                  <div><StatusBadge status={p.status} /></div>
                  <div style={{ textAlign: 'right', color: parseInt(p.restarts || 0) > 30 ? 'var(--yellow)' : 'var(--text)' }}>
                    {p.restarts}
                  </div>
                  <div style={{ color: 'var(--text-mid)' }}>{p.age}</div>
                  <div style={{ color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.node}</div>
                </div>
              )
            })}
          </div>
        </section>
      )}

    </div>
  )
}
