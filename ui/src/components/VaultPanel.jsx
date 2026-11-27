import React, { useState, useEffect, useCallback } from 'react'
import { useApp } from '../store.jsx'
import { api } from '../api.js'
import {
  Lock, Unlock, KeyRound, FileKey, Server, Camera, X,
  Plug, Trash2, RefreshCw, AlertCircle, CheckCircle2, ShieldCheck,
  Pencil, Check,
} from 'lucide-react'

/**
 * VaultPanel — 보안 보관함 패널 (v1.2.1).
 *
 * 좌하단 클러스터/Vault 박스를 클릭하면 오른쪽에서 슬라이드로 열린다.
 * vault 에 보관된 항목을 분류해 보여주고(값은 절대 노출 X),
 * kubeconfig 연결/삭제, 잠그기, 마스터 비밀번호 변경을 제공.
 */
export default function VaultPanel() {
  const {
    showVaultPanel, setShowVaultPanel,
    vaultStatus, vaultLock, vaultChangePassword,
    connectFromVault, refreshClusters,
    clusters, renameCluster,
  } = useApp()

  const [entries, setEntries] = useState({ kubeconfig: [], snapshot: [], other: [] })
  const [snapCount, setSnapCount] = useState(0)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)        // {kind, text}
  const [showChange, setShowChange] = useState(false)
  const [editing, setEditing] = useState(null)   // 이름 변경 중인 kubeconfig 이름 (null = 없음)
  const [editValue, setEditValue] = useState('')

  const refresh = useCallback(async () => {
    const r = await api.vaultEntries()
    if (r?.ok) setEntries(r.groups || {})
    const s = await api.listSnapshots()
    if (s?.ok) setSnapCount((s.items || []).length)
  }, [])

  useEffect(() => {
    if (showVaultPanel) { setMsg(null); setShowChange(false); setEditing(null); refresh() }
  }, [showVaultPanel, refresh])

  if (!showVaultPanel) return null

  const close = () => setShowVaultPanel(false)

  async function handleConnect(name) {
    setBusy(true); setMsg(null)
    const r = await connectFromVault(name)
    setBusy(false)
    if (r?.ok) {
      setMsg({ kind: 'ok', text: `${name} 연결됨` })
      close()
    } else {
      setMsg({ kind: 'error', text: r?.error || '연결 실패' })
    }
  }

  async function handleDelete(name) {
    setBusy(true); setMsg(null)
    const r = await api.deleteKubeconfig(name)
    setBusy(false)
    if (r?.ok) { setMsg({ kind: 'ok', text: `${name} 삭제됨` }); refresh() }
    else setMsg({ kind: 'error', text: r?.error || '삭제 실패' })
  }

  function startEdit(name) {
    setMsg(null); setEditValue(name); setEditing(name)
  }

  // 이름 변경 — 이 kubeconfig 가 현재 연결된 클러스터면 rename_cluster 로 라우팅해
  // 상위 탭(display_name)과 vault 키를 함께 바꾼다. 미연결 보관본이면 rename_kubeconfig.
  async function handleRename(oldName) {
    const newName = (editValue || '').trim()
    if (!newName || newName === oldName) { setEditing(null); return }
    setBusy(true); setMsg(null)
    const connected = (clusters || []).find(c => c.kc_name === oldName)
    const r = connected
      ? await renameCluster(connected.id, newName)   // 탭 + vault 동기화
      : await api.renameKubeconfig(oldName, newName)  // 보관본만
    setBusy(false)
    if (r?.ok) {
      setEditing(null)
      setMsg({ kind: 'ok', text: `이름 변경됨: ${oldName} → ${newName}` })
      refresh()
    } else {
      setMsg({ kind: 'error', text: r?.error || '이름 변경 실패' })
    }
  }

  async function handleLock() {
    close()              // 패널 먼저 닫기 (이후 잠금 → 게이트가 전체 화면 덮음)
    await vaultLock()    // → vaultUnlocked=false → VaultGate 가 다시 로그인 표시
  }

  return (
    <>
      {/* 백드롭 */}
      <div onClick={close} style={{
        position: 'fixed', inset: 0, zIndex: 1400,
        background: 'rgba(0,0,0,0.4)',
      }} />

      {/* 드로어 */}
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 1401,
        width: 420, maxWidth: '92vw',
        background: 'var(--bg-1)', borderLeft: '1px solid var(--border-bright)',
        boxShadow: '-16px 0 50px rgba(0,0,0,0.5)',
        display: 'flex', flexDirection: 'column',
        animation: 'vaultDrawerIn 0.18s ease-out',
      }}>
        {/* 헤더 */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '14px 16px', borderBottom: '1px solid var(--border)',
        }}>
          <KeyRound size={17} color="var(--nimbus)" />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)' }}>
              보안 보관함
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 1 }}>
              AES-256-GCM 암호화 · 값은 표시되지 않습니다
            </div>
          </div>
          <button onClick={refresh} title="새로고침" style={iconBtn}>
            <RefreshCw size={13} />
          </button>
          <button onClick={close} title="닫기" style={iconBtn}>
            <X size={15} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {/* 상태 */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '11px 13px', borderRadius: 9, marginBottom: 14,
            background: 'var(--bg-2)', border: '1px solid var(--border)',
          }}>
            {vaultStatus.unlocked
              ? <Unlock size={18} color="var(--nimbus)" />
              : <Lock size={18} color="var(--text-mid)" />}
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12.5, fontWeight: 700 }}>
                {vaultStatus.unlocked ? '잠금 해제됨' : '잠겨 있음'}
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 1 }}>
                {vaultStatus.unlocked ? '앱 실행 중 보관 항목 사용 가능' : '비밀번호 입력 필요'}
              </div>
            </div>
            <button onClick={handleLock} disabled={busy} style={lockBtn} title="화면 잠금 (자리비움 보호) — 자물쇠 화면으로 전환">
              <Lock size={12} /> 화면 잠금
            </button>
          </div>

          {/* 메시지 */}
          {msg && (
            <div style={{
              padding: '8px 11px', borderRadius: 6, marginBottom: 12,
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5,
              background: msg.kind === 'ok' ? 'rgba(52,211,153,0.1)' : 'rgba(239,68,68,0.1)',
              border: `1px solid ${msg.kind === 'ok' ? 'rgba(52,211,153,0.4)' : 'rgba(239,68,68,0.4)'}`,
            }}>
              {msg.kind === 'ok'
                ? <CheckCircle2 size={13} color="var(--nimbus)" />
                : <AlertCircle size={13} color="var(--red)" />}
              {msg.text}
            </div>
          )}

          {/* kubeconfig 그룹 */}
          <GroupHeader icon={FileKey} title="Kubeconfig" count={entries.kubeconfig?.length || 0} />
          {(entries.kubeconfig || []).length === 0 ? (
            <EmptyHint text="보관된 kubeconfig 가 없습니다. 클러스터를 연결하면 자동 저장됩니다." />
          ) : (
            <div style={{ marginBottom: 16 }}>
              {entries.kubeconfig.map(name => (
                <div key={name} style={rowStyle}>
                  <FileKey size={13} color="var(--blue)" style={{ flexShrink: 0 }} />
                  {editing === name ? (
                    <>
                      <input autoFocus value={editValue} disabled={busy}
                        onChange={e => setEditValue(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleRename(name)
                          else if (e.key === 'Escape') setEditing(null)
                        }}
                        style={editInput} />
                      <button onClick={() => handleRename(name)} disabled={busy}
                        style={{ ...miniBtn, color: 'var(--nimbus)' }} title="이름 저장">
                        <Check size={11} />
                      </button>
                      <button onClick={() => setEditing(null)} disabled={busy}
                        style={miniBtn} title="취소">
                        <X size={11} />
                      </button>
                    </>
                  ) : (
                    <>
                      <span style={rowName} title={name}>{name}</span>
                      <button onClick={() => startEdit(name)} disabled={busy}
                        style={miniBtn} title="이름 변경 (연결 중이면 상위 탭도 함께 변경)">
                        <Pencil size={11} /> 변경
                      </button>
                      <button onClick={() => handleConnect(name)} disabled={busy}
                        style={miniBtn} title="이 kubeconfig 로 연결">
                        <Plug size={11} /> 연결
                      </button>
                      <button onClick={() => handleDelete(name)} disabled={busy}
                        style={{ ...miniBtn, color: 'var(--red)' }} title="vault 에서 삭제">
                        <Trash2 size={11} />
                      </button>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 클러스터 스냅샷 (암호화) */}
          <GroupHeader icon={Camera} title="클러스터 스냅샷 (암호화)" count={snapCount} />
          <EmptyHint text={snapCount > 0
            ? `${snapCount}개의 클러스터 스냅샷이 암호화되어 저장됨 (스냅샷 화면에서 열람)`
            : '저장된 스냅샷이 없습니다.'} />

          {/* 마스터 비밀번호 변경 */}
          <div style={{ marginTop: 18, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
            {!showChange ? (
              <button onClick={() => { setShowChange(true); setMsg(null) }} style={ghostWide}>
                <ShieldCheck size={13} /> 마스터 비밀번호 변경
              </button>
            ) : (
              <ChangePasswordForm
                busy={busy} setBusy={setBusy}
                onDone={(m) => { setMsg(m); if (m?.kind === 'ok') setShowChange(false) }}
                onCancel={() => setShowChange(false)}
                vaultChangePassword={vaultChangePassword}
              />
            )}
          </div>
        </div>
      </aside>
    </>
  )
}

function ChangePasswordForm({ busy, setBusy, onDone, onCancel, vaultChangePassword }) {
  const [oldPw, setOld] = useState('')
  const [newPw, setNew] = useState('')
  const [new2, setNew2] = useState('')

  async function submit() {
    if (newPw.length < 4) { onDone({ kind: 'error', text: '새 비밀번호는 4자 이상' }); return }
    if (newPw !== new2)   { onDone({ kind: 'error', text: '새 비밀번호가 일치하지 않습니다' }); return }
    setBusy(true)
    const r = await vaultChangePassword(oldPw, newPw)
    setBusy(false)
    onDone(r?.ok
      ? { kind: 'ok', text: '비밀번호 변경 완료' }
      : { kind: 'error', text: r?.error || '변경 실패' })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <input type="password" placeholder="현재 비밀번호" value={oldPw}
        onChange={e => setOld(e.target.value)} disabled={busy} style={pwInput} />
      <input type="password" placeholder="새 비밀번호 (4자 이상)" value={newPw}
        onChange={e => setNew(e.target.value)} disabled={busy} style={pwInput} />
      <input type="password" placeholder="새 비밀번호 확인" value={new2}
        onChange={e => setNew2(e.target.value)} disabled={busy} style={pwInput} />
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={submit} disabled={busy} style={{ ...miniBtn, flex: 1, justifyContent: 'center', padding: '7px 0', background: 'var(--nimbus)', color: 'var(--accent-ink)', border: 'none' }}>
          변경
        </button>
        <button onClick={onCancel} disabled={busy} style={{ ...ghostWide, flex: 1, marginTop: 0 }}>
          취소
        </button>
      </div>
    </div>
  )
}

function GroupHeader({ icon: Icon, title, count }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
      <Icon size={13} color="var(--text-dim)" />
      <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-mid)' }}>
        {title}
      </span>
      <span style={{
        fontSize: 10, fontWeight: 700, color: 'var(--text-dim)',
        background: 'var(--bg-3)', borderRadius: 9, padding: '1px 7px',
      }}>{count}</span>
    </div>
  )
}

function EmptyHint({ text }) {
  return (
    <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 16, paddingLeft: 2 }}>
      {text}
    </div>
  )
}


const iconBtn = {
  width: 28, height: 28, display: 'grid', placeItems: 'center',
  background: 'var(--bg-3)', border: '1px solid var(--border)',
  borderRadius: 6, color: 'var(--text-mid)', cursor: 'pointer', flexShrink: 0,
}
const lockBtn = {
  display: 'inline-flex', alignItems: 'center', gap: 5,
  padding: '5px 10px', fontSize: 11, fontWeight: 600,
  background: 'transparent', color: 'var(--text)',
  border: '1px solid var(--border-bright)', borderRadius: 6, cursor: 'pointer',
}
const rowStyle = {
  display: 'flex', alignItems: 'center', gap: 8,
  padding: '7px 9px', marginBottom: 4, borderRadius: 6,
  background: 'var(--bg-2)', border: '1px solid var(--border)',
}
const rowName = {
  flex: 1, minWidth: 0, fontSize: 12, color: 'var(--text-bright)',
  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
}
const editInput = {
  flex: 1, minWidth: 0, padding: '4px 8px', fontSize: 12,
  background: 'var(--bg-3)', border: '1px solid var(--nimbus)',
  borderRadius: 5, color: 'var(--text-bright)', outline: 'none',
}
const miniBtn = {
  display: 'inline-flex', alignItems: 'center', gap: 4,
  padding: '4px 8px', fontSize: 10.5, fontWeight: 600,
  background: 'var(--bg-3)', color: 'var(--text)',
  border: '1px solid var(--border-bright)', borderRadius: 5, cursor: 'pointer', flexShrink: 0,
}
const ghostWide = {
  width: '100%', marginTop: 0, padding: '8px 0',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
  fontSize: 12, fontWeight: 600,
  background: 'transparent', color: 'var(--text)',
  border: '1px solid var(--border-bright)', borderRadius: 6, cursor: 'pointer',
}
const pwInput = {
  width: '100%', padding: '8px 11px', boxSizing: 'border-box',
  background: 'var(--bg-2)', border: '1px solid var(--border-bright)',
  borderRadius: 6, color: 'var(--text-bright)', fontSize: 12, outline: 'none',
}
