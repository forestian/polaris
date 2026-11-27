import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Layers, RefreshCw, Server, Box, AlertTriangle, CheckCircle2,
         Circle, ArrowRightCircle, Loader2 } from 'lucide-react'

// 멀티클러스터 집계 뷰 — 연결된 모든 클러스터의 노드/파드 요약을 한 화면에.
// 백엔드가 클러스터별 카운트를 병렬 수집(get_multicluster_summary)한다.
export default function MultiClusterPage() {
  const { switchCluster } = useApp()
  const [data, setData] = useState(null)     // {clusters, totals}
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [switching, setSwitching] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.getMulticlusterSummary()
      if (r?.ok) { setData(r); setErr('') }
      else { setData(null); setErr(r?.error || '집계를 불러오지 못했습니다.') }
    } catch (e) { setData(null); setErr(String(e)) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  async function onSwitch(id) {
    setSwitching(id)
    try { await switchCluster(id) } catch {}
    setSwitching(null)
    load()
  }

  const totals = data?.totals
  const clusters = data?.clusters || []

  return (
    <div style={{ padding: '18px 22px', height: '100%', overflowY: 'auto' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <Layers size={20} style={{ color: 'var(--nimbus)' }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-bright)' }}>멀티클러스터</div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            연결된 모든 클러스터의 노드·파드 상태를 한눈에
          </div>
        </div>
        <button className="btn btn-default btn-sm" onClick={load} disabled={loading} style={{ gap: 5 }}>
          {loading ? <Loader2 size={13} className="spin" /> : <RefreshCw size={13} />} 새로고침
        </button>
      </div>

      {err && (
        <div style={{ padding: '10px 14px', borderRadius: 8, marginBottom: 14, fontSize: 12,
          background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', color: 'var(--red)' }}>
          {err}
        </div>
      )}

      {/* 전체 합계 카드 */}
      {totals && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: 12, marginBottom: 20 }}>
          <StatCard icon={Layers} label="클러스터" value={`${totals.connected}/${totals.clusters}`} sub="연결됨" />
          <StatCard icon={Server} label="노드" value={`${totals.nodes_ready}/${totals.nodes}`} sub="Ready"
            warn={totals.nodes_ready < totals.nodes} />
          <StatCard icon={Box} label="파드" value={totals.pods} sub="전체" />
          <StatCard icon={AlertTriangle} label="비정상 파드" value={totals.pods_not_ready}
            sub="not Running" warn={totals.pods_not_ready > 0} />
        </div>
      )}

      {/* 클러스터 목록 */}
      {loading && !data ? (
        <div style={{ color: 'var(--text-dim)', fontSize: 13, padding: 20 }}>불러오는 중…</div>
      ) : clusters.length === 0 ? (
        <div style={{ color: 'var(--text-dim)', fontSize: 13, padding: 20 }}>
          연결된 클러스터가 없습니다. 상단에서 kubeconfig 를 추가·연결하세요.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
          {clusters.map(c => (
            <ClusterCard key={c.id} c={c} switching={switching === c.id}
              onSwitch={() => onSwitch(c.id)} />
          ))}
        </div>
      )}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, sub, warn }) {
  return (
    <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 10,
      padding: '12px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <Icon size={13} style={{ color: warn ? 'var(--red, #f87171)' : 'var(--text-dim)' }} />
        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{label}</span>
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, lineHeight: 1,
        color: warn ? 'var(--red, #f87171)' : 'var(--text-bright)' }}>{value}</div>
      <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 3 }}>{sub}</div>
    </div>
  )
}

function ClusterCard({ c, switching, onSwitch }) {
  const nodes = c.nodes || {}
  const pods = c.pods || {}
  const nodeWarn = c.connected && (nodes.ready ?? 0) < (nodes.total ?? 0)
  const podWarn = c.connected && (pods.notReady ?? 0) > 0
  return (
    <div style={{ background: 'var(--bg-2)',
      border: `1px solid ${c.active ? 'var(--nimbus)' : 'var(--border)'}`,
      borderRadius: 10, padding: '13px 15px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
        {c.connected
          ? <CheckCircle2 size={14} style={{ color: 'var(--nimbus)', flexShrink: 0 }} />
          : <Circle size={14} style={{ color: 'var(--text-dim)', flexShrink: 0 }} />}
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-bright)', flex: 1,
          minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          title={c.display_name}>{c.display_name}</span>
        {c.active && <span style={{ fontSize: 9.5, fontWeight: 700, padding: '2px 7px',
          borderRadius: 4, background: 'rgba(52,211,153,0.15)', color: 'var(--nimbus)' }}>활성</span>}
      </div>

      <div style={{ fontSize: 10.5, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {c.context || '—'} · {c.version || '?'}
      </div>

      {c.error ? (
        <div style={{ fontSize: 11, color: 'var(--red)' }}>{c.error}</div>
      ) : (
        <div style={{ display: 'flex', gap: 16 }}>
          <Metric label="노드" value={`${nodes.ready ?? 0}/${nodes.total ?? 0}`} warn={nodeWarn} />
          <Metric label="파드" value={pods.total ?? 0} />
          <Metric label="비정상" value={pods.notReady ?? 0} warn={podWarn} />
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        {c.active ? (
          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>현재 보는 클러스터</span>
        ) : (
          <button className="btn btn-ghost btn-sm" onClick={onSwitch} disabled={switching || !c.connected}
            style={{ gap: 4 }}>
            {switching ? <Loader2 size={12} className="spin" /> : <ArrowRightCircle size={12} />} 이 클러스터로 전환
          </button>
        )}
      </div>
    </div>
  )
}

function Metric({ label, value, warn }) {
  return (
    <div>
      <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1,
        color: warn ? 'var(--red, #f87171)' : 'var(--text-bright)' }}>{value}</div>
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>{label}</div>
    </div>
  )
}
