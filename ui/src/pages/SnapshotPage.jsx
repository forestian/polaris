/**
 * SnapshotPage — 클러스터 스냅샷 + 시점 비교 (운영 점검 핵심)
 *
 * - 현재 클러스터 상태를 시점별로 저장 (스냅샷 찍기)
 * - 두 스냅샷 선택 → Diff: 추가/삭제/변경된 리소스 + 새로 생긴/해결된 이슈
 *
 * "지난 점검 대비 무엇이 바뀌고 무엇이 위험해졌나" 를 한눈에.
 */
import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Camera, RefreshCw, AlertCircle, Trash2, GitCompare,
         Plus, Minus, Pencil, ArrowRight } from 'lucide-react'

const SEV_COLOR = {
  critical: 'var(--red)', high: 'var(--red)', medium: 'var(--yellow)',
  low: 'var(--text-mid)', info: 'var(--text-dim)',
}

export default function SnapshotPage() {
  const { connected } = useApp()
  const [snaps, setSnaps]   = useState(null)
  const [busy, setBusy]     = useState(false)
  const [msg, setMsg]       = useState(null)        // {ok, text}
  const [selA, setSelA]     = useState(null)        // 기준(이전)
  const [selB, setSelB]     = useState(null)        // 비교(이후)
  const [diff, setDiff]     = useState(null)

  async function loadList() {
    setBusy(true)
    try {
      const r = await api.listSnapshots()
      setSnaps(r?.ok ? (r.items || []) : [])
    } catch { setSnaps([]) }
    setBusy(false)
  }

  useEffect(() => { loadList() }, [])

  async function takeSnap() {
    if (!connected) { setMsg({ ok: false, text: '클러스터에 연결되지 않았습니다.' }); return }
    setBusy(true); setMsg(null)
    try {
      const r = await api.takeSnapshot('')
      if (r?.ok) { setMsg({ ok: true, text: `스냅샷 저장됨: ${r.id}` }); await loadList() }
      else setMsg({ ok: false, text: r?.error || '스냅샷 실패' })
    } catch (e) { setMsg({ ok: false, text: String(e) }) }
    setBusy(false)
  }

  async function removeSnap(sid, e) {
    e.stopPropagation()
    if (!window.confirm(`스냅샷 "${sid}" 을(를) 삭제하시겠습니까?`)) return
    await api.deleteSnapshot(sid)
    if (selA === sid) setSelA(null)
    if (selB === sid) setSelB(null)
    setDiff(null)
    loadList()
  }

  // 행 클릭: 기준(A) 없으면 A, 그다음 B. 같은 거 다시 누르면 해제.
  function pick(sid) {
    if (selA === sid) { setSelA(null); setDiff(null); return }
    if (selB === sid) { setSelB(null); setDiff(null); return }
    if (!selA) setSelA(sid)
    else if (!selB) setSelB(sid)
    else { setSelA(sid); setSelB(null) }   // 둘 다 찼으면 새로 시작
    setDiff(null)
  }

  async function runDiff() {
    if (!selA || !selB) return
    setBusy(true); setMsg(null)
    try {
      // 시간순 자동 정렬 — 오래된 게 기준(a)
      const a = snaps.find(s => s.id === selA)
      const b = snaps.find(s => s.id === selB)
      const [older, newer] = (a?.created_at <= b?.created_at) ? [selA, selB] : [selB, selA]
      const r = await api.diffSnapshots(older, newer)
      if (r?.ok) setDiff(r)
      else setMsg({ ok: false, text: r?.error || 'Diff 실패' })
    } catch (e) { setMsg({ ok: false, text: String(e) }) }
    setBusy(false)
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── 좌: 스냅샷 목록 ── */}
      <div style={{ width: 360, flexShrink: 0, display: 'flex', flexDirection: 'column',
        borderRight: '1px solid var(--border)', background: 'var(--bg-1)' }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <Camera size={16} color="var(--nimbus)" />
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-bright)' }}>스냅샷</span>
            <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              {snaps ? `${snaps.length}개` : ''}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={loadList} disabled={busy}
              style={{ marginLeft: 'auto' }} title="새로고침"><RefreshCw size={12} /></button>
          </div>
          <button className="btn btn-primary btn-sm" onClick={takeSnap} disabled={busy || !connected}
            style={{ width: '100%', gap: 6, justifyContent: 'center' }}>
            <Camera size={13} /> 현재 상태 스냅샷
          </button>
          {msg && (
            <div style={{ marginTop: 8, fontSize: 11, padding: '5px 8px', borderRadius: 4,
              color: msg.ok ? 'var(--nimbus)' : 'var(--red)',
              background: msg.ok ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)' }}>
              {msg.ok ? '✓ ' : '✗ '}{msg.text}
            </div>
          )}
          {(selA || selB) && (
            <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-dim)' }}>
              선택: {selA ? '①' : '○'} 기준 · {selB ? '②' : '○'} 비교
              {selA && selB && (
                <button className="btn btn-primary btn-sm" onClick={runDiff} disabled={busy}
                  style={{ marginLeft: 8, gap: 4 }}>
                  <GitCompare size={12} /> 비교
                </button>
              )}
            </div>
          )}
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {snaps === null ? <Loading /> :
           snaps.length === 0 ? <Empty icon={Camera} text="저장된 스냅샷이 없습니다." small /> :
           snaps.map(s => {
            const tag = selA === s.id ? '①' : selB === s.id ? '②' : ''
            return (
              <div key={s.id} onClick={() => pick(s.id)}
                style={{
                  padding: '9px 14px', borderBottom: '1px solid var(--border)', cursor: 'pointer',
                  borderLeft: tag ? '2px solid var(--nimbus)' : '2px solid transparent',
                  background: tag ? 'rgba(52,211,153,0.08)' : 'transparent',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}>
                <span style={{ width: 16, flexShrink: 0, color: 'var(--nimbus)',
                  fontWeight: 700 }}>{tag}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-bright)',
                    fontFamily: 'var(--font-mono)', overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.created_at}</div>
                  <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 2 }}>
                    {s.cluster} · {s.cluster_version}
                  </div>
                </div>
                <button onClick={e => removeSnap(s.id, e)} title="삭제"
                  style={{ background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-dim)', flexShrink: 0, padding: 4 }}>
                  <Trash2 size={13} />
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── 우: Diff 결과 ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {!diff ? (
          <Empty icon={GitCompare}
            text={snaps && snaps.length < 2
              ? '스냅샷을 2개 이상 만든 뒤 두 개를 선택해 비교하세요.'
              : '스냅샷 2개를 선택하고 "비교" 를 누르세요.'} />
        ) : (
          <DiffResult diff={diff} />
        )}
      </div>
    </div>
  )
}

function DiffResult({ diff }) {
  const t = diff.totals || {}
  const fd = diff.finding_delta || {}
  return (
    <div>
      {/* 비교 대상 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6,
        fontSize: 12.5, color: 'var(--text)' }}>
        <span style={{ fontFamily: 'var(--font-mono)' }}>{diff.meta_a?.created_at}</span>
        <ArrowRight size={14} color="var(--text-dim)" />
        <span style={{ fontFamily: 'var(--font-mono)' }}>{diff.meta_b?.created_at}</span>
      </div>

      {/* 총계 칩 */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <Chip icon={Plus}  color="var(--nimbus)" label="추가" value={t.added} />
        <Chip icon={Minus} color="var(--red)"   label="삭제" value={t.removed} />
        <Chip icon={Pencil} color="var(--yellow)" label="변경" value={t.changed} />
        <Chip icon={AlertCircle} color="var(--red)" label="새 이슈" value={fd.new?.length || 0} />
        <Chip icon={AlertCircle} color="var(--nimbus)" label="해결된 이슈" value={fd.resolved?.length || 0} />
      </div>

      {/* 이슈 변화 */}
      {(fd.new?.length > 0 || fd.resolved?.length > 0) && (
        <Section title="이슈 추이">
          {fd.new?.map((f, i) => (
            <IssueLine key={'n'+i} f={f} kind="new" />
          ))}
          {fd.resolved?.map((f, i) => (
            <IssueLine key={'r'+i} f={f} kind="resolved" />
          ))}
        </Section>
      )}

      {/* 리소스 변화 */}
      {diff.kinds.length === 0 ? (
        <div style={{ fontSize: 13, color: 'var(--text-dim)', padding: 20, textAlign: 'center' }}>
          두 스냅샷 간 리소스 변화가 없습니다.
        </div>
      ) : diff.kinds.map((k, i) => (
        <Section key={i} title={`${k.kind}  (+${k.added.length} / -${k.removed.length} / ~${k.changed.length})`}>
          {k.added.map((name, j) => (
            <div key={'a'+j} style={lineStyle}>
              <Plus size={12} color="var(--nimbus)" /> <span style={{ color: 'var(--nimbus)' }}>{name}</span>
            </div>
          ))}
          {k.removed.map((name, j) => (
            <div key={'r'+j} style={lineStyle}>
              <Minus size={12} color="var(--red)" /> <span style={{ color: 'var(--red)' }}>{name}</span>
            </div>
          ))}
          {k.changed.map((c, j) => (
            <div key={'c'+j} style={{ ...lineStyle, alignItems: 'flex-start', flexDirection: 'column', gap: 2 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Pencil size={12} color="var(--yellow)" />
                <span style={{ color: 'var(--yellow)' }}>{c.key}</span>
              </div>
              {c.fields.map((f, fi) => (
                <div key={fi} style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 18,
                  fontFamily: 'var(--font-mono)' }}>
                  {f.field}: <span style={{ color: 'var(--red)' }}>{f.old}</span>
                  {' → '}<span style={{ color: 'var(--nimbus)' }}>{f.new}</span>
                </div>
              ))}
            </div>
          ))}
        </Section>
      ))}
    </div>
  )
}

const lineStyle = {
  display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0',
  fontSize: 12, fontFamily: 'var(--font-mono)',
}

function IssueLine({ f, kind }) {
  const sev = (f.severity || 'info').toLowerCase()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 12 }}>
      <span style={{ fontSize: 10, fontWeight: 700, flexShrink: 0,
        color: kind === 'new' ? 'var(--red)' : 'var(--nimbus)' }}>
        {kind === 'new' ? '▲ 신규' : '▼ 해결'}
      </span>
      <span style={{ fontSize: 10, padding: '1px 5px', borderRadius: 3, flexShrink: 0,
        color: SEV_COLOR[sev] || 'var(--text-dim)',
        border: `1px solid ${SEV_COLOR[sev] || 'var(--border)'}` }}>{sev}</span>
      <span style={{ color: 'var(--text-dim)' }}>{f.category}</span>
      <span style={{ color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>
        {f.namespace ? `${f.namespace}/` : ''}{f.name}
      </span>
      {f.detail && <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>— {f.detail}</span>}
    </div>
  )
}

function Chip({ icon: Icon, color, label, value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
      background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 6 }}>
      <Icon size={13} color={color} />
      <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{label}</span>
      <span style={{ fontSize: 15, fontWeight: 700, color }}>{value || 0}</span>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-dim)',
        textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8,
        paddingBottom: 4, borderBottom: '1px solid var(--border)' }}>{title}</div>
      {children}
    </div>
  )
}

function Loading() {
  return <div className="empty-state" style={{ height: 120 }}><div className="spinner" /></div>
}

function Empty({ icon: Icon, text, small }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 10, padding: small ? 24 : 60,
      color: 'var(--text-dim)', height: small ? 'auto' : '100%' }}>
      <Icon size={small ? 22 : 34} />
      <span style={{ fontSize: 12.5, textAlign: 'center', maxWidth: 320 }}>{text}</span>
    </div>
  )
}
