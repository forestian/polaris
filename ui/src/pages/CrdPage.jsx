/**
 * CrdPage — CRD(CustomResourceDefinition) 자동 발견
 *
 * 좌측: 클러스터의 모든 CRD 목록 (group/kind 그룹화 + 검색)
 * 가운데: 선택한 CRD 의 커스텀 객체 목록 (additionalPrinterColumns 동적 렌더링)
 * 우측: 객체 클릭 시 상세 패널 (YAML 편집/적용 · 삭제 · 이벤트)
 *
 * 고정 15종 리소스 외에, 클러스터에 설치된 모든 CRD 를 탐색하고 다룰 수 있다.
 */
import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Boxes, RefreshCw, AlertCircle, Search } from 'lucide-react'
import ResourcePanel from '../components/ResourcePanel.jsx'

export default function CrdPage() {
  const { connected, namespace } = useApp()

  const [crds, setCrds]       = useState(null)   // null=로딩전, []=없음
  const [err, setErr]         = useState('')
  const [filter, setFilter]   = useState('')
  const [selected, setSelected] = useState(null) // 선택된 CRD 메타
  const [objects, setObjects] = useState(null)   // 선택 CRD 의 객체들
  const [objErr, setObjErr]   = useState('')
  const [busy, setBusy]       = useState(false)
  const [picked, setPicked]   = useState(null)   // 상세 패널 대상 객체

  async function loadCrds() {
    if (!connected) return
    setBusy(true); setErr('')
    try {
      const r = await api.getCrds()
      if (r?.ok) setCrds(r.items || [])
      else { setCrds([]); setErr(r?.error || 'CRD 목록을 가져오지 못했습니다.') }
    } catch (e) { setCrds([]); setErr(String(e)) }
    setBusy(false)
  }

  async function loadObjects(crd) {
    setSelected(crd); setObjects(null); setObjErr(''); setPicked(null)
    setBusy(true)
    try {
      const ns = (namespace && namespace !== 'All Namespaces') ? namespace : ''
      const r = await api.getCrdObjects(
        crd.group, crd.version, crd.plural, crd.namespaced, ns,
        crd.printer_columns || [],
      )
      if (r?.ok) setObjects(r.items || [])
      else { setObjects([]); setObjErr(r?.error || '객체를 가져오지 못했습니다.') }
    } catch (e) { setObjects([]); setObjErr(String(e)) }
    setBusy(false)
  }

  useEffect(() => { loadCrds() }, [connected])
  // 네임스페이스 변경 시 현재 선택된 CRD 객체 다시 로드
  useEffect(() => { if (selected) loadObjects(selected) }, [namespace])

  const filtered = useMemo(() => {
    if (!crds) return []
    const q = filter.trim().toLowerCase()
    if (!q) return crds
    return crds.filter(c =>
      `${c.kind} ${c.group} ${c.name} ${c.short}`.toLowerCase().includes(q))
  }, [crds, filter])

  const grouped = useMemo(() => {
    const m = {}
    for (const c of filtered) (m[c.group || '(core)'] ||= []).push(c)
    return Object.entries(m).sort((a, b) => a[0].localeCompare(b[0]))
  }, [filtered])

  // 선택된 CRD 객체를 ResourcePanel 에 넘길 때 쓸 kind = <plural>.<group>
  const crdKind = selected ? `${selected.plural}.${selected.group}` : ''
  const printerCols = selected?.printer_columns || []

  if (!connected) {
    return <Empty icon={AlertCircle} text="클러스터에 연결되지 않았습니다." />
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── 좌측: CRD 목록 ── */}
      <div style={{
        width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column',
        borderRight: '1px solid var(--border)', background: 'var(--bg-1)',
      }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <Boxes size={16} color="var(--nimbus)" />
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-bright)' }}>
              CRD
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              {crds ? `${crds.length}종` : ''}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={loadCrds} disabled={busy}
              style={{ marginLeft: 'auto' }} title="새로고침">
              <RefreshCw size={12} />
            </button>
          </div>
          <div style={{ position: 'relative' }}>
            <Search size={12} style={{ position: 'absolute', left: 8, top: 8, color: 'var(--text-dim)' }} />
            <input
              value={filter} onChange={e => setFilter(e.target.value)}
              placeholder="kind / group 검색"
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px 5px 26px',
                fontSize: 12, background: 'var(--bg-0)', border: '1px solid var(--border)',
                borderRadius: 4, color: 'var(--text)', outline: 'none',
              }}
            />
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {crds === null ? <Loading /> :
           crds.length === 0 ? <Empty icon={Boxes} text={err || 'CRD 가 없습니다.'} small /> :
           grouped.map(([group, list]) => (
            <div key={group}>
              <div style={{
                padding: '5px 14px', fontSize: 10, fontWeight: 700,
                color: 'var(--text-dim)', background: 'var(--bg-2)',
                textTransform: 'uppercase', letterSpacing: '0.04em',
                position: 'sticky', top: 0, zIndex: 1,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }} title={group}>{group}</div>
              {list.map(c => {
                const active = selected?.name === c.name
                return (
                  <button key={c.name} onClick={() => loadObjects(c)}
                    style={{
                      width: '100%', textAlign: 'left', padding: '7px 14px',
                      border: 'none', cursor: 'pointer', fontSize: 12.5,
                      borderLeft: active ? '2px solid var(--nimbus)' : '2px solid transparent',
                      background: active ? 'rgba(52,211,153,0.1)' : 'transparent',
                      color: active ? 'var(--text-bright)' : 'var(--text)',
                      display: 'flex', alignItems: 'center', gap: 6,
                    }}
                    onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
                    onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
                  >
                    <span style={{ fontWeight: 600, overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.kind}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 5px', borderRadius: 3, flexShrink: 0,
                      background: c.namespaced ? 'rgba(96,165,250,0.15)' : 'rgba(192,132,252,0.15)',
                      color: c.namespaced ? 'var(--blue)' : '#c084fc',
                    }}>{c.namespaced ? 'NS' : 'Cluster'}</span>
                    <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-dim)',
                      fontFamily: 'var(--font-mono)', flexShrink: 0 }}>{c.version}</span>
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* ── 가운데: 객체 목록 ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {!selected ? (
          <Empty icon={Boxes} text="왼쪽에서 CRD 를 선택하세요." />
        ) : (
          <>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)' }}>
                {selected.kind}
                <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-dim)', marginLeft: 8 }}>
                  {objects ? `${objects.length}개` : ''}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2,
                fontFamily: 'var(--font-mono)' }}>
                {selected.group}/{selected.version} · {selected.plural}
                {selected.namespaced
                  ? ` · ${(namespace && namespace !== 'All Namespaces') ? namespace : '전체 네임스페이스'}`
                  : ' · 클러스터 범위'}
              </div>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', overflowX: 'auto', padding: '0 16px' }}>
              {objects === null ? <Loading /> :
               objErr ? <Empty icon={AlertCircle} text={objErr} small /> :
               objects.length === 0 ? <Empty icon={Boxes} text="이 CRD 의 객체가 없습니다." small /> : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5,
                  whiteSpace: 'nowrap' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', color: 'var(--text-dim)',
                      borderBottom: '1px solid var(--border)' }}>
                      <th style={{ padding: '8px 10px 8px 6px', fontWeight: 600 }}>이름</th>
                      {selected.namespaced &&
                        <th style={{ padding: '8px 10px', fontWeight: 600 }}>네임스페이스</th>}
                      {printerCols.map(c => (
                        <th key={c.name} style={{ padding: '8px 10px', fontWeight: 600 }}>{c.name}</th>
                      ))}
                      <th style={{ padding: '8px 10px', fontWeight: 600 }}>나이</th>
                    </tr>
                  </thead>
                  <tbody>
                    {objects.map((o, i) => {
                      const active = picked?.name === o.name && picked?.namespace === o.namespace
                      return (
                        <tr key={i}
                          onClick={() => setPicked(o)}
                          style={{
                            borderBottom: '1px solid var(--border)', cursor: 'pointer',
                            background: active ? 'rgba(52,211,153,0.08)' : 'transparent',
                          }}
                          onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
                          onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
                        >
                          <td style={{ padding: '7px 10px 7px 6px', color: 'var(--text)',
                            fontFamily: 'var(--font-mono)' }}>{o.name}</td>
                          {selected.namespaced &&
                            <td style={{ padding: '7px 10px', color: 'var(--text-mid)' }}>{o.namespace || '-'}</td>}
                          {printerCols.map(c => (
                            <td key={c.name} style={{ padding: '7px 10px', color: 'var(--text-mid)' }}>
                              {o[`col_${c.name}`] || '-'}
                            </td>
                          ))}
                          <td style={{ padding: '7px 10px', color: 'var(--text-dim)' }}>{o.age}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>

      {/* ── 우측: 상세 패널 (객체 선택 시) ── */}
      {picked && (
        <ResourcePanel
          item={picked}
          kind={crdKind}
          onClose={() => setPicked(null)}
          onDelete={async (it) => {
            if (!window.confirm(`${selected.kind} "${it.name}" 을(를) 삭제하시겠습니까?`)) return
            try {
              const r = await api.deleteResource(crdKind, it.namespace || '', it.name)
              if (r?.ok !== false) {
                setPicked(null)
                loadObjects(selected)
              }
            } catch (e) { /* no-op */ }
          }}
        />
      )}
    </div>
  )
}

function Loading() {
  return <div className="empty-state" style={{ height: 120 }}><div className="spinner" /></div>
}

function Empty({ icon: Icon, text, small }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 10, padding: small ? 24 : 60,
      color: 'var(--text-dim)', height: small ? 'auto' : '100%',
    }}>
      <Icon size={small ? 22 : 34} />
      <span style={{ fontSize: 12.5 }}>{text}</span>
    </div>
  )
}
