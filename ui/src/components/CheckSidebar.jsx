import React from 'react'
import { useApp } from '../store.jsx'
import { visibleCheckGroups } from '../checkPages.js'
import { HeartPulse, FileText, KeyRound, Lock, Unlock, ChevronUp, ArrowUpCircle } from 'lucide-react'

const ICONS = { health: HeartPulse, upgrade: ArrowUpCircle, report: FileText }

export default function CheckSidebar() {
  const { checkActivePage, setCheckActivePage } = useApp()
  const groups = visibleCheckGroups()

  return (
    <aside style={{
      width: 'var(--sidebar-w)', background: 'var(--bg-2)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0,
    }}>
      <div style={{ padding: '10px 14px 2px', fontSize: 10, fontWeight: 700, color: 'var(--text-dim)',
                    letterSpacing: '0.08em' }}>CHECK</div>
      <div style={{ padding: '2px 0', overflowY: 'auto' }}>
        {groups.map(g => (
          <div key={g.id} style={{ marginTop: 6 }}>
            <div style={{ padding: '6px 14px 3px', fontSize: 10.5, fontWeight: 600, color: 'var(--text-dim)' }}>{g.label}</div>
            {g.items.map(p => {
              const Icon = ICONS[p.id] || FileText
              const active = checkActivePage === p.id
              return (
                <button key={p.id} onClick={() => setCheckActivePage(p.id)}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px', margin: '1px 0',
                    border: 'none', cursor: 'pointer', fontSize: 12.5, fontFamily: 'var(--font)', textAlign: 'left',
                    transition: 'all 0.12s',
                    ...(active
                      ? { color: 'var(--text-bright)', background: 'linear-gradient(90deg, rgba(52,211,153,0.15), rgba(96,165,250,0.04))',
                          borderLeft: '2px solid var(--nimbus)', fontWeight: 600 }
                      : { color: 'var(--text)', background: 'transparent', borderLeft: '2px solid transparent', fontWeight: 400 }),
                  }}>
                  <Icon size={14} color={active ? 'var(--nimbus)' : 'var(--text-dim)'} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.label}</div>
                    <div style={{ fontSize: 9.5, color: 'var(--text-dim)', fontWeight: 400, marginTop: 1,
                                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.sub}</div>
                  </div>
                </button>
              )
            })}
          </div>
        ))}
      </div>

      <div style={{ flex: 1 }} />

      {/* 보안 보관함 */}
      <VaultBox />
    </aside>
  )
}

/** 사이드바 아래 보안 보관함 칸 */
export function VaultBox() {
  const { vaultStatus, setShowVaultPanel } = useApp()
  return (
    <button onClick={() => setShowVaultPanel(true)} title="보안 보관함 열기"
      style={{ margin: '10px 10px 12px', padding: '10px 12px', borderRadius: 8, background: 'var(--bg-3)',
               border: '1px solid var(--border)', cursor: 'pointer', textAlign: 'left', width: 'calc(100% - 20px)' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--nimbus)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
        <div style={{ width: 30, height: 30, borderRadius: 7, flexShrink: 0, background: 'var(--bg-2)',
                      display: 'grid', placeItems: 'center' }}>
          <KeyRound size={15} color="var(--nimbus)" />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-bright)' }}>보안 보관함</div>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 1, display: 'flex', alignItems: 'center', gap: 4 }}>
            {vaultStatus?.unlocked ? <Unlock size={9} color="var(--nimbus)" /> : <Lock size={9} />}
            <span>패스워드 / 키</span>
          </div>
        </div>
        <ChevronUp size={12} color="var(--text-dim)" />
      </div>
    </button>
  )
}
