import React, { useEffect, useState, useMemo } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { RefreshCw, Globe, ChevronDown, X, Filter } from 'lucide-react'
import {
  buildTopologyGraph,
  TOPOLOGY_COLUMNS,
  TOPOLOGY_LAYOUT,
  TYPE_STYLE,
  styleOf,
  typeKey,
} from '../topologyGraph.js'

// 타입별 카테고리 분류
const TYPE_GROUPS = [
  { key: 'workload', label: '워크로드', types: ['deploy', 'statefulset', 'daemonset', 'job', 'cronjob'] },
  { key: 'service',  label: '서비스',   types: ['service', 'ingress'] },
  { key: 'config',   label: '설정',     types: ['configmap', 'secret'] },
  { key: 'storage',  label: '스토리지', types: ['pvc'] },
]

function toGroupKey(node) {
  const tk = typeKey(node)
  for (const g of TYPE_GROUPS) {
    if (g.types.includes(tk)) return g.key
  }
  return 'other'
}

const NODE_W = TOPOLOGY_LAYOUT.nodeWidth
const NODE_H = TOPOLOGY_LAYOUT.nodeHeight

// ── SVG Node ──────────────────────────────────────────────────────────────────
function SvgNode({ node, selectedId, highlighted, onSelect }) {
  const s          = styleOf(node)
  const isSel      = selectedId === node.id
  const isHi       = highlighted.has(node.id)
  const isDim      = selectedId && !isSel && !isHi
  const strokeClr  = isSel ? s.color : isHi ? `${s.color}99` : 'rgba(255,255,255,0.1)'
  const strokeW    = isSel ? 2 : isHi ? 1.5 : 1

  const displayName = node.name.length > 21
    ? node.name.slice(0, 19) + '…'
    : node.name

  const podText = (node.total !== undefined)
    ? `${node.running}/${node.total}`
    : null
  const podColor = podText
    ? (node.running === node.total ? '#34d399' : '#f87171')
    : null

  return (
    <g onClick={() => onSelect(node)} style={{ cursor: 'pointer', opacity: isDim ? 0.25 : 1 }}>
      {/* 배경 */}
      <rect x={node.x} y={node.y} width={NODE_W} height={NODE_H}
        rx={7} fill={s.bg} stroke={strokeClr} strokeWidth={strokeW} />

      {/* 왼쪽 액센트 바 */}
      <rect x={node.x} y={node.y} width={4} height={NODE_H} rx={3} fill={s.color} />

      {/* 타입 뱃지 */}
      <text x={node.x + 12} y={node.y + 19}
        fill={s.color} fontSize={9} fontWeight={700}
        fontFamily="'Consolas','Menlo',monospace" textAnchor="start">
        {s.badge}
      </text>

      {/* 이름 */}
      <text x={node.x + 12} y={node.y + 36}
        fill="rgba(255,255,255,0.88)" fontSize={11.5}
        fontFamily="'Consolas','Menlo',monospace" textAnchor="start">
        {displayName}
      </text>

      {/* 파드 카운트 (워크로드) */}
      {podText && (
        <text x={node.x + NODE_W - 9} y={node.y + 19}
          fill={podColor} fontSize={9} fontFamily="'Consolas','Menlo',monospace"
          textAnchor="end" fontWeight={600}>
          {podText} ▶
        </text>
      )}
    </g>
  )
}

// ── SVG Edge ──────────────────────────────────────────────────────────────────
function SvgEdge({ edge, selectedId, highlighted }) {
  const isHi  = highlighted.has(edge.from) || highlighted.has(edge.to)
  const isDim = selectedId && !isHi
  return (
    <path d={edge.d} fill="none"
      stroke={isHi ? edge.srcColor : 'rgba(255,255,255,0.11)'}
      strokeWidth={isHi ? 2 : 1}
      opacity={isDim ? 0.12 : 1}
      markerEnd={isHi ? 'url(#arr)' : undefined}
    />
  )
}

// ── 오른쪽 상세 패널 ──────────────────────────────────────────────────────────
function InfoPanel({ node, onClose, onNavigate }) {
  if (!node) return null
  const s = styleOf(node)
  const tk = typeKey(node)

  function kv(label, value) {
    if (value == null || value === '') return null
    return (
      <div style={{ display: 'flex', gap: 8, marginBottom: 5, fontSize: 12 }}>
        <span style={{ color: 'var(--text-dim)', minWidth: 86, flexShrink: 0 }}>{label}</span>
        <span style={{ color: 'var(--text)', fontFamily: 'var(--font-mono)',
          wordBreak: 'break-all', lineHeight: 1.5 }}>
          {value}
        </span>
      </div>
    )
  }

  const NAV_TYPES = {
    deployment: 'deployments', statefulset: 'statefulsets', daemonset: 'daemonsets',
    job: 'jobs', cronjob: 'cronjobs',
    service: 'services', ingress: 'ingresses',
    configmap: 'configmaps', secret: 'secrets', pvc: 'pvcs',
  }

  return (
    <div style={{
      width: 270, flexShrink: 0,
      borderLeft: '1px solid var(--border)',
      background: 'var(--bg-1)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* 헤더 */}
      <div style={{
        padding: '10px 13px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{ width: 10, height: 10, borderRadius: 2, background: s.color, flexShrink: 0 }} />
        <span style={{
          fontWeight: 700, fontSize: 12, color: 'var(--text-bright)',
          flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {node.name}
        </span>
        <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={12} /></button>
      </div>

      {/* 내용 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 13px' }}>
        {kv('타입',   s.badge)}
        {kv('이름',   node.name)}
        {node.ns && kv('네임스페이스', node.ns)}
        {node.kind && kv('Kind', node.kind)}
        {node.type && kv('Type', node.type)}
        {node.svc_type && kv('Service', node.svc_type)}
        {node.status && kv('상태', node.status)}
        {node.schedule && kv('스케줄', node.schedule)}
        {node.completions !== undefined && kv('완료 목표', node.completions)}
        {node.succeeded !== undefined && kv('성공', node.succeeded)}
        {node.failed !== undefined && kv('실패', node.failed)}
        {node.active !== undefined && kv('실행 중', node.active)}
        {node.bound_pv && kv('Bound PV', node.bound_pv)}

        {/* 파드 상태 (워크로드) */}
        {node.total !== undefined && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase',
              letterSpacing: '0.07em', marginBottom: 6 }}>파드</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{
                background: 'var(--bg-3)', borderRadius: 6, padding: '6px 12px',
                textAlign: 'center', flex: 1,
              }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#34d399' }}>
                  {node.running}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>실행 중</div>
              </div>
              <div style={{
                background: 'var(--bg-3)', borderRadius: 6, padding: '6px 12px',
                textAlign: 'center', flex: 1,
              }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>
                  {node.total}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>전체</div>
              </div>
            </div>
          </div>
        )}

        {/* Selector */}
        {node.sel && Object.keys(node.sel).length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase',
              letterSpacing: '0.07em', marginBottom: 5 }}>Selector</div>
            {Object.entries(node.sel).map(([k, v]) => (
              <div key={k} style={{ fontSize: 11, fontFamily: 'var(--font-mono)',
                color: 'var(--text-dim)', marginBottom: 2 }}>
                <span style={{ color: '#c084fc' }}>{k}</span>: {v}
              </div>
            ))}
          </div>
        )}

        {/* Ingress backend services */}
        {node.svc_refs?.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase',
              letterSpacing: '0.07em', marginBottom: 5 }}>Backend Services</div>
            {node.svc_refs.map(sr => (
              <div key={sr} style={{ fontSize: 11, fontFamily: 'var(--font-mono)',
                color: '#34d399', marginBottom: 2 }}>
                {sr}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 리소스 브라우저 이동 */}
      {NAV_TYPES[tk] && node.ns && (
        <div style={{ padding: '10px 13px', borderTop: '1px solid var(--border)' }}>
          <button className="btn btn-default" style={{ width: '100%' }}
            onClick={() => onNavigate(node)}>
            리소스 브라우저에서 열기
          </button>
        </div>
      )}
    </div>
  )
}

// ── 메인 페이지 ──────────────────────────────────────────────────────────────
export default function TopologyPage() {
  const { connected, namespaces, namespace: globalNs, navigate } = useApp()

  const [ns,           setNs]           = useState(() => globalNs === 'All Namespaces' ? '' : globalNs)
  const [raw,          setRaw]          = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [errMsg,       setErrMsg]       = useState('')
  const [selected,     setSelected]     = useState(null)
  const [hiddenGroups, setHiddenGroups] = useState(new Set())

  const graph = useMemo(() => raw ? buildTopologyGraph(raw) : null, [raw])

  function toggleGroup(key) {
    setHiddenGroups(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  async function load() {
    if (!connected) return
    setLoading(true)
    setErrMsg('')
    setSelected(null)
    try {
      const d = await api.getTopologyData(ns)
      if (d?.ok === false) { setErrMsg(d.error || '데이터 수집 실패'); setRaw(null) }
      else setRaw(d)
    } catch (e) { setErrMsg(String(e)); setRaw(null) }
    setLoading(false)
  }

  useEffect(() => { load() }, [connected, ns])

  // 선택 시 연결된 노드/엣지 하이라이트
  const highlighted = useMemo(() => {
    if (!selected || !graph) return new Set()
    const set = new Set([selected.id])
    for (const e of graph.edges) {
      if (e.from === selected.id) set.add(e.to)
      if (e.to   === selected.id) set.add(e.from)
    }
    return set
  }, [selected, graph])

  function handleNavigate(node) {
    const MAP = {
      deployment: 'deployments', statefulset: 'statefulsets', daemonset: 'daemonsets',
      job: 'jobs', cronjob: 'cronjobs',
      service: 'services', ingress: 'ingresses',
      configmap: 'configmaps', secret: 'secrets', pvc: 'pvcs',
    }
    const res = MAP[typeKey(node)]
    if (res) navigate('resources', res)
  }

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Globe size={40} opacity={0.25} />
      <p style={{ fontWeight: 600, marginTop: 10 }}>클러스터에 연결되지 않았습니다.</p>
    </div>
  )

  // 가시 노드 목록 (hiddenGroups 기반 필터)
  const visibleNodeIds = useMemo(() => {
    if (!graph) return new Set()
    return new Set(graph.nodes.filter(n => !hiddenGroups.has(toGroupKey(n))).map(n => n.id))
  }, [graph, hiddenGroups])

  // KPI 카운트
  const kpiCounts = useMemo(() => {
    if (!graph) return null
    const nodes = graph.nodes
    return TYPE_GROUPS.map(g => ({
      ...g,
      count: nodes.filter(n => g.types.includes(typeKey(n))).length,
    }))
  }, [graph])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* ── 툴바 ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 14px', borderBottom: '1px solid var(--border)',
        background: 'var(--bg-1)', flexShrink: 0,
      }}>
        <Globe size={14} color="var(--nimbus)" />
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-bright)' }}>토폴로지</span>
        <div style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 2px' }} />
        {graph && !loading && (
          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            노드 {graph.nodes.length} · 엣지 {graph.edges.length}
          </span>
        )}
        <span style={{ flex: 1 }} />
        {selected && (
          <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>선택 해제</button>
        )}
        <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          새로고침
        </button>
      </div>

      {/* ── 본문 ── */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>

        {/* ── 왼쪽 필터 패널 ── */}
        <div style={{
          width: 170, flexShrink: 0,
          borderRight: '1px solid var(--border)',
          background: 'var(--bg-1)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          {/* 네임스페이스 */}
          <div style={{ padding: '12px 12px 10px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 7 }}>
              네임스페이스
            </div>
            <div style={{ position: 'relative' }}>
              <select className="select" value={ns}
                onChange={e => { setNs(e.target.value); setSelected(null) }}
                style={{ width: '100%', paddingRight: 24, fontSize: 11 }}>
                <option value="">전체</option>
                {(namespaces ?? []).filter(n => n !== 'All Namespaces').map(n =>
                  <option key={n}>{n}</option>
                )}
              </select>
              <ChevronDown size={10} style={{
                position: 'absolute', right: 7, top: '50%',
                transform: 'translateY(-50%)', pointerEvents: 'none',
                color: 'var(--text-dim)',
              }} />
            </div>
          </div>

          {/* 리소스 타입 필터 */}
          <div style={{ padding: '12px 12px', flex: 1, overflowY: 'auto' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>
              타입 표시
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {TYPE_GROUPS.map(g => {
                const isHidden = hiddenGroups.has(g.key)
                const count = kpiCounts?.find(k => k.key === g.key)?.count ?? 0
                return (
                  <label key={g.key} style={{
                    display: 'flex', alignItems: 'center', gap: 7,
                    cursor: 'pointer', padding: '4px 6px', borderRadius: 5,
                    background: isHidden ? 'transparent' : 'rgba(52,211,153,0.06)',
                    border: `1px solid ${isHidden ? 'var(--border)' : 'rgba(52,211,153,0.2)'}`,
                  }}>
                    <input
                      type="checkbox"
                      checked={!isHidden}
                      onChange={() => toggleGroup(g.key)}
                      style={{ accentColor: 'var(--nimbus)', width: 12, height: 12, flexShrink: 0 }}
                    />
                    <span style={{ fontSize: 11, color: isHidden ? 'var(--text-dim)' : 'var(--text)', flex: 1 }}>{g.label}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>{count}</span>
                  </label>
                )
              })}
            </div>
          </div>

          {/* 범례 */}
          {graph && graph.nodes.length > 0 && !loading && (
            <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 7 }}>
                범례
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {Object.entries(TYPE_STYLE).map(([k, s]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div style={{ width: 7, height: 7, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{s.badge}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── 그래프 + 상세 패널 ── */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>

          {/* KPI 스트립 */}
          {kpiCounts && !loading && graph?.nodes.length > 0 && (
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8,
              padding: '10px 12px', borderBottom: '1px solid var(--border)',
              background: 'var(--bg-1)', flexShrink: 0,
            }}>
              {kpiCounts.map(({ key, label, count }) => (
                <div key={key} style={{
                  background: hiddenGroups.has(key) ? 'transparent' : 'var(--bg-2)',
                  border: `1px solid ${hiddenGroups.has(key) ? 'var(--border)' : 'var(--border)'}`,
                  borderRadius: 7, padding: '8px 10px', cursor: 'pointer',
                  opacity: hiddenGroups.has(key) ? 0.4 : 1,
                }}
                  onClick={() => toggleGroup(key)}
                >
                  <div style={{ fontSize: 9.5, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: 3 }}>{label}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-bright)', fontVariantNumeric: 'tabular-nums' }}>{count}</div>
                </div>
              ))}
            </div>
          )}

          {/* 그래프 + 상세 패널 나란히 */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>

            {/* 그래프 영역 */}
            <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-0)' }}
              onClick={e => { if (e.target.tagName === 'svg' || e.target.tagName === 'SVG') setSelected(null) }}>

              {loading ? (
                <div className="empty-state" style={{ height: '100%', minHeight: 300 }}>
                  <div className="spinner" /><span>데이터 수집 중...</span>
                </div>
              ) : errMsg ? (
                <div className="empty-state" style={{ height: '100%', minHeight: 300 }}>
                  <Globe size={36} opacity={0.2} />
                  <p style={{ color: 'var(--red)', marginTop: 10 }}>{errMsg}</p>
                </div>
              ) : !graph || graph.nodes.length === 0 ? (
                <div className="empty-state" style={{ height: '100%', minHeight: 300 }}>
                  <Globe size={36} opacity={0.2} />
                  <p style={{ fontWeight: 600, marginTop: 10 }}>시각화할 리소스가 없습니다.</p>
                  <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
                    다른 네임스페이스를 선택하거나 클러스터에 워크로드를 배포하세요.
                  </p>
                </div>
              ) : (
                <svg
                  width={TOPOLOGY_LAYOUT.svgWidth}
                  height={graph.svgH}
                  style={{ display: 'block', minWidth: '100%' }}
                >
                  <defs>
                    <marker id="arr" markerWidth={8} markerHeight={8} refX={6} refY={3} orient="auto">
                      <path d="M 0 0 L 6 3 L 0 6 Z" fill="rgba(255,255,255,0.5)" />
                    </marker>
                  </defs>

                  {TOPOLOGY_COLUMNS.map(col => (
                    <text key={col.id} x={col.x + NODE_W / 2} y={22}
                      textAnchor="middle" fill="rgba(255,255,255,0.2)"
                      fontSize={9} fontWeight={700} fontFamily="system-ui,sans-serif">
                      {col.label.toUpperCase()}
                    </text>
                  ))}
                  {TOPOLOGY_COLUMNS.slice(1).map(col => (
                    <line key={col.id}
                      x1={col.x - 36} y1={32} x2={col.x - 36} y2={graph.svgH - 10}
                      stroke="rgba(255,255,255,0.04)" strokeDasharray="4 4" />
                  ))}
                  {graph.edges.map(e => (
                    <SvgEdge key={e.id} edge={e}
                      selectedId={selected?.id} highlighted={highlighted} />
                  ))}
                  {graph.nodes.map(n => (
                    <g key={n.id} style={{ opacity: visibleNodeIds.has(n.id) ? 1 : 0.12, transition: 'opacity 0.2s' }}>
                      <SvgNode node={n}
                        selectedId={selected?.id} highlighted={highlighted}
                        onSelect={visibleNodeIds.has(n.id) ? setSelected : () => {}} />
                    </g>
                  ))}
                </svg>
              )}
            </div>

            {/* 상세 패널 */}
            {selected && (
              <InfoPanel node={selected} onClose={() => setSelected(null)} onNavigate={handleNavigate} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
