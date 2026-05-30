/**
 * RbacPage — RBAC 분석 뷰어
 *
 * 탭 1 (ServiceAccount): SA 선택 → 바인딩된 Role/ClusterRole → 실제 권한(verbs×resources)
 * 탭 2 (Roles):          Role/ClusterRole 목록 → 선택 시 규칙 펼침
 * 탭 3 (Bindings):       RoleBinding/ClusterRoleBinding → roleRef + subjects
 *
 * "이 ServiceAccount 가 무엇을 할 수 있나" 를 역추적해 보안 감사에 활용.
 */
import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { KeyRound, RefreshCw, AlertCircle, Search, ChevronRight, ChevronDown } from 'lucide-react'

const TABS = ['ServiceAccount', 'Role / ClusterRole', 'Binding']

export default function RbacPage() {
  const { connected } = useApp()
  const [data, setData]   = useState(null)   // {roles, bindings, service_accounts, summary}
  const [err, setErr]     = useState('')
  const [busy, setBusy]   = useState(false)
  const [tab, setTab]     = useState('ServiceAccount')
  const [filter, setFilter] = useState('')
  const [includeSystem, setIncludeSystem] = useState(false)
  const [selSa, setSelSa] = useState(null)
  const [expanded, setExpanded] = useState({})  // role/binding 펼침

  async function load() {
    if (!connected) return
    setBusy(true); setErr('')
    try {
      const r = await api.getRbac(includeSystem)
      if (r?.ok) setData(r)
      else { setData(null); setErr(r?.error || 'RBAC 정보를 가져오지 못했습니다.') }
    } catch (e) { setData(null); setErr(String(e)) }
    setBusy(false)
  }

  useEffect(() => { load() }, [connected, includeSystem])
  useEffect(() => { setFilter(''); setSelSa(null); setExpanded({}) }, [tab])

  if (!connected) return <Empty icon={AlertCircle} text="클러스터에 연결되지 않았습니다." />

  const q = filter.trim().toLowerCase()
  const sas      = (data?.service_accounts || []).filter(s => !q || `${s.name} ${s.namespace}`.toLowerCase().includes(q))
  const roles    = (data?.roles || []).filter(r => !q || `${r.name} ${r.kind} ${r.namespace}`.toLowerCase().includes(q))
  const bindings = (data?.bindings || []).filter(b => !q || `${b.name} ${b.kind} ${b.role_ref?.name}`.toLowerCase().includes(q))
  const sm = data?.summary || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* 헤더 */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <KeyRound size={16} color="var(--nimbus)" />
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)' }}>RBAC 분석</span>
          {data && (
            <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              ClusterRole {sm.cluster_roles} · Role {sm.roles} · CRB {sm.cluster_role_bindings} ·
              RB {sm.role_bindings} · SA {sm.service_accounts}
            </span>
          )}
          <label style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-dim)',
            display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input type="checkbox" checked={includeSystem}
              onChange={e => setIncludeSystem(e.target.checked)} />
            system: 포함
          </label>
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={busy} title="새로고침">
            <RefreshCw size={12} />
          </button>
        </div>
        {/* 탭 */}
        <div style={{ display: 'flex', gap: 4 }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              style={{
                padding: '5px 12px', fontSize: 12.5, border: 'none', cursor: 'pointer',
                borderRadius: 4, fontWeight: tab === t ? 600 : 400,
                background: tab === t ? 'var(--bg-3)' : 'transparent',
                color: tab === t ? 'var(--text-bright)' : 'var(--text-dim)',
                borderBottom: tab === t ? '2px solid var(--nimbus)' : '2px solid transparent',
              }}>{t}</button>
          ))}
          <div style={{ position: 'relative', marginLeft: 'auto' }}>
            <Search size={12} style={{ position: 'absolute', left: 8, top: 7, color: 'var(--text-dim)' }} />
            <input value={filter} onChange={e => setFilter(e.target.value)} placeholder="검색"
              style={{ padding: '4px 8px 4px 26px', fontSize: 12, width: 180,
                background: 'var(--bg-0)', border: '1px solid var(--border)',
                borderRadius: 4, color: 'var(--text)', outline: 'none' }} />
          </div>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {data === null ? <div style={{ flex: 1 }}><Loading /></div> :
         err ? <div style={{ flex: 1 }}><Empty icon={AlertCircle} text={err} /></div> :
         tab === 'ServiceAccount' ? (
          <SaView sas={sas} selSa={selSa} setSelSa={setSelSa} />
        ) : tab === 'Role / ClusterRole' ? (
          <RoleView roles={roles} expanded={expanded} setExpanded={setExpanded} />
        ) : (
          <BindingView bindings={bindings} expanded={expanded} setExpanded={setExpanded} />
        )}
      </div>
    </div>
  )
}

// ── ServiceAccount 권한 역추적 뷰 ──────────────────────────────────────────
function SaView({ sas, selSa, setSelSa }) {
  return (
    <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
      {/* SA 목록 */}
      <div style={{ width: 320, flexShrink: 0, overflowY: 'auto',
        borderRight: '1px solid var(--border)' }}>
        {sas.length === 0 ? <Empty icon={KeyRound} text="ServiceAccount 가 없습니다." small /> :
         sas.map((s, i) => {
          const active = selSa?.name === s.name && selSa?.namespace === s.namespace
          return (
            <button key={i} onClick={() => setSelSa(s)}
              style={{
                width: '100%', textAlign: 'left', padding: '8px 14px', border: 'none',
                cursor: 'pointer', fontSize: 12.5,
                borderLeft: active ? '2px solid var(--nimbus)' : '2px solid transparent',
                background: active ? 'rgba(52,211,153,0.1)' : 'transparent',
                borderBottom: '1px solid var(--border)',
              }}>
              <div style={{ color: active ? 'var(--text-bright)' : 'var(--text)',
                fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{s.name}</div>
              <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 2,
                display: 'flex', gap: 8 }}>
                <span>{s.namespace}</span>
                <span style={{ color: s.binding_count ? 'var(--nimbus)' : 'var(--text-dim)' }}>
                  바인딩 {s.binding_count || 0}
                </span>
              </div>
            </button>
          )
        })}
      </div>
      {/* 선택 SA 권한 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {!selSa ? <Empty icon={KeyRound} text="ServiceAccount 를 선택하면 권한을 분석합니다." /> :
         (
          <>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)',
              fontFamily: 'var(--font-mono)' }}>{selSa.namespace}/{selSa.name}</div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4, marginBottom: 16 }}>
              {selSa.binding_count
                ? `${selSa.binding_count}개 바인딩을 통해 다음 권한을 가집니다`
                : '이 ServiceAccount 에 연결된 RoleBinding/ClusterRoleBinding 이 없습니다 (권한 없음).'}
            </div>

            {selSa.bindings?.length > 0 && (
              <Section title="바인딩">
                {selSa.bindings.map((b, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--text)', padding: '3px 0',
                    fontFamily: 'var(--font-mono)' }}>
                    <span style={{ color: 'var(--text-dim)' }}>{b.binding_kind}</span> {b.binding}
                    <ChevronRight size={11} style={{ verticalAlign: 'middle', margin: '0 4px',
                      color: 'var(--text-dim)' }} />
                    <span style={{ color: 'var(--blue)' }}>{b.role_kind}/{b.role}</span>
                  </div>
                ))}
              </Section>
            )}

            {selSa.rules?.length > 0 && (
              <Section title={`유효 권한 (규칙 ${selSa.rules.length})`}>
                <RuleTable rules={selSa.rules} />
              </Section>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Role / ClusterRole 뷰 ───────────────────────────────────────────────────
function RoleView({ roles, expanded, setExpanded }) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px' }}>
      {roles.length === 0 ? <Empty icon={KeyRound} text="Role 이 없습니다." small /> :
       roles.map((r, i) => {
        const key = `${r.kind}/${r.namespace}/${r.name}`
        const open = expanded[key]
        return (
          <div key={i} style={{ borderBottom: '1px solid var(--border)' }}>
            <button onClick={() => setExpanded(e => ({ ...e, [key]: !e[key] }))}
              style={{ width: '100%', textAlign: 'left', padding: '9px 6px', border: 'none',
                cursor: 'pointer', background: 'transparent', display: 'flex',
                alignItems: 'center', gap: 8 }}>
              {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              <span style={{
                fontSize: 9.5, padding: '1px 5px', borderRadius: 3,
                background: r.kind === 'ClusterRole' ? 'rgba(192,132,252,0.15)' : 'rgba(96,165,250,0.15)',
                color: r.kind === 'ClusterRole' ? '#c084fc' : 'var(--blue)',
              }}>{r.kind === 'ClusterRole' ? 'Cluster' : 'NS'}</span>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)',
                fontFamily: 'var(--font-mono)' }}>{r.name}</span>
              {r.namespace && <span style={{ fontSize: 10.5, color: 'var(--text-dim)' }}>{r.namespace}</span>}
              <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text-dim)' }}>
                규칙 {r.rule_count}
              </span>
            </button>
            {open && (
              <div style={{ padding: '0 6px 12px 27px' }}>
                {r.rules.length === 0
                  ? <div style={{ fontSize: 11.5, color: 'var(--text-dim)' }}>규칙 없음</div>
                  : <RuleTable rules={r.rules} />}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Binding 뷰 ──────────────────────────────────────────────────────────────
function BindingView({ bindings, expanded, setExpanded }) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px' }}>
      {bindings.length === 0 ? <Empty icon={KeyRound} text="Binding 이 없습니다." small /> :
       bindings.map((b, i) => {
        const key = `${b.kind}/${b.namespace}/${b.name}`
        const open = expanded[key]
        return (
          <div key={i} style={{ borderBottom: '1px solid var(--border)' }}>
            <button onClick={() => setExpanded(e => ({ ...e, [key]: !e[key] }))}
              style={{ width: '100%', textAlign: 'left', padding: '9px 6px', border: 'none',
                cursor: 'pointer', background: 'transparent', display: 'flex',
                alignItems: 'center', gap: 8 }}>
              {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              <span style={{
                fontSize: 9.5, padding: '1px 5px', borderRadius: 3,
                background: b.kind === 'ClusterRoleBinding' ? 'rgba(192,132,252,0.15)' : 'rgba(96,165,250,0.15)',
                color: b.kind === 'ClusterRoleBinding' ? '#c084fc' : 'var(--blue)',
              }}>{b.kind === 'ClusterRoleBinding' ? 'Cluster' : 'NS'}</span>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)',
                fontFamily: 'var(--font-mono)' }}>{b.name}</span>
              <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--blue)' }}>
                → {b.role_ref?.kind}/{b.role_ref?.name}
              </span>
            </button>
            {open && (
              <div style={{ padding: '0 6px 12px 27px' }}>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>
                  Subjects ({b.subjects.length})
                </div>
                {b.subjects.length === 0
                  ? <div style={{ fontSize: 11.5, color: 'var(--text-dim)' }}>subject 없음</div>
                  : b.subjects.map((s, j) => (
                    <div key={j} style={{ fontSize: 12, color: 'var(--text)', padding: '2px 0',
                      fontFamily: 'var(--font-mono)' }}>
                      <span style={{ color: 'var(--text-dim)' }}>{s.kind}</span> {s.name}
                      {s.namespace && <span style={{ color: 'var(--text-dim)' }}> ({s.namespace})</span>}
                    </div>
                  ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── 규칙 테이블 (verbs × resources × apiGroups) ─────────────────────────────
function RuleTable({ rules }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5, marginTop: 4 }}>
      <thead>
        <tr style={{ textAlign: 'left', color: 'var(--text-dim)',
          borderBottom: '1px solid var(--border)' }}>
          <th style={{ padding: '4px 8px', fontWeight: 600 }}>API 그룹</th>
          <th style={{ padding: '4px 8px', fontWeight: 600 }}>리소스</th>
          <th style={{ padding: '4px 8px', fontWeight: 600 }}>동작 (verbs)</th>
        </tr>
      </thead>
      <tbody>
        {rules.map((rule, i) => {
          const allVerbs = rule.verbs?.includes('*')
          return (
            <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '4px 8px', color: 'var(--text-mid)', fontFamily: 'var(--font-mono)' }}>
                {(rule.apiGroups || []).map(g => g === '' ? '(core)' : g).join(', ') || '-'}
              </td>
              <td style={{ padding: '4px 8px', color: 'var(--text)', fontFamily: 'var(--font-mono)' }}>
                {(rule.resources || []).join(', ') || '-'}
              </td>
              <td style={{ padding: '4px 8px', fontFamily: 'var(--font-mono)',
                color: allVerbs ? 'var(--red)' : 'var(--text)' }}>
                {(rule.verbs || []).join(', ') || '-'}
                {allVerbs && <span style={{ fontSize: 9, marginLeft: 6,
                  color: 'var(--red)' }}>⚠ 전체 권한</span>}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-dim)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6,
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
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 10, padding: small ? 24 : 60,
      color: 'var(--text-dim)', height: small ? 'auto' : '100%', width: '100%',
    }}>
      <Icon size={small ? 22 : 34} />
      <span style={{ fontSize: 12.5 }}>{text}</span>
    </div>
  )
}
