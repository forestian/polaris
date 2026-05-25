import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { RefreshCw, Plus, Pencil, Trash2, RefreshCcw, RotateCcw, X, ChevronDown, Search } from 'lucide-react'

const COLUMNS = [
  { key: 'name',      label: '앱 이름',      width: 200 },
  { key: 'namespace', label: '네임스페이스', width: 120 },
  { key: 'project',   label: '프로젝트',     width: 100 },
  { key: 'sync',      label: 'Sync',         width: 100 },
  { key: 'health',    label: 'Health',       width: 100 },
  { key: 'repo',      label: 'Repo',         width: 240 },
  { key: 'revision',  label: 'Revision',     width: 100 },
]

// ── 앱 생성/수정 모달 ─────────────────────────────────────────────────────────
function AppFormModal({ mode, app, onClose, onSave }) {
  const empty = {
    name: '', namespace: 'argocd', project: 'default',
    repo_url: '', target_revision: 'HEAD', path: '',
    dest_server: 'https://kubernetes.default.svc', dest_namespace: 'default',
    sync_policy: 'none', source_mode: 'single', sources: [],
  }
  const [form, setForm] = useState(mode === 'edit' && app ? {
    name:             app.name            || '',
    namespace:        app.namespace       || 'argocd',
    project:          app.project         || 'default',
    repo_url:         app.repo_url        || app.repo || '',
    target_revision:  app.target_revision || app.revision || 'HEAD',
    path:             app.path            || '',
    dest_server:      app.dest_server     || 'https://kubernetes.default.svc',
    dest_namespace:   app.dest_namespace  || 'default',
    sync_policy:      app.sync_policy     || 'none',
    source_mode:      app.source_mode     || 'single',
    sources:          app.sources         || [],
  } : empty)

  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  function set(key, val) { setForm(prev => ({ ...prev, [key]: val })) }

  const isMultiSource = form.source_mode === 'multi' && form.sources?.length > 1

  async function handleSave() {
    if (!form.name.trim())     { setError('앱 이름을 입력하세요.'); return }
    if (!isMultiSource && !form.repo_url.trim()) { setError('Repo URL을 입력하세요.'); return }
    if (!isMultiSource && !form.path.trim())     { setError('경로를 입력하세요.'); return }
    setLoading(true); setError('')
    try {
      let res
      if (mode === 'create') res = await api.createArgoApp(form)
      else res = await api.updateArgoApp({ ...form, name: app.name, namespace: app.namespace })
      if (res?.ok === false) setError(res.error || '저장 실패')
      else { onSave(); onClose() }
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ width: 520 }}>
        <div className="modal-header">
          <h2>{mode === 'create' ? '⎈ 앱 생성' : '✎ 앱 수정'}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={14} /></button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: -4 }}>기본 정보</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-row">
              <label className="form-label">앱 이름 *</label>
              <input className="input" value={form.name} onChange={e => set('name', e.target.value)} placeholder="my-app" disabled={mode === 'edit'} />
            </div>
            <div className="form-row">
              <label className="form-label">네임스페이스</label>
              <input className="input" value={form.namespace} onChange={e => set('namespace', e.target.value)} placeholder="argocd" />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-row">
              <label className="form-label">프로젝트</label>
              <input className="input" value={form.project} onChange={e => set('project', e.target.value)} placeholder="default" />
            </div>
            <div className="form-row">
              <label className="form-label">Sync 정책</label>
              <div style={{ position: 'relative' }}>
                <select className="select" value={form.sync_policy} onChange={e => set('sync_policy', e.target.value)} style={{ paddingRight: 28, width: '100%' }}>
                  <option value="none">Manual</option>
                  <option value="automated">Automated</option>
                </select>
                <ChevronDown size={11} style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-dim)' }} />
              </div>
            </div>
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 4, marginBottom: -4 }}>소스</div>
          <div className="form-row">
            <label className="form-label">Repo URL *</label>
            <input className="input" value={form.repo_url} onChange={e => set('repo_url', e.target.value)} placeholder="https://github.com/org/repo.git" disabled={isMultiSource} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-row">
              <label className="form-label">Revision</label>
              <input className="input" value={form.target_revision} onChange={e => set('target_revision', e.target.value)} placeholder="HEAD" disabled={isMultiSource} />
            </div>
            <div className="form-row">
              <label className="form-label">Path *</label>
              <input className="input" value={form.path} onChange={e => set('path', e.target.value)} placeholder="./manifests" disabled={isMultiSource} />
            </div>
          </div>
          {isMultiSource && (
            <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 10px', fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.6 }}>
              <div style={{ color: 'var(--text-bright)', fontWeight: 700, marginBottom: 4 }}>Multi-source Application: 소스 {form.sources.length}개 보존</div>
              {form.sources.map((src, idx) => (
                <div key={idx} className="mono" style={{ wordBreak: 'break-all' }}>
                  {idx + 1}. {src.repoURL || '-'} / {src.path || src.chart || src.ref || '-'} @ {src.targetRevision || 'HEAD'}
                </div>
              ))}
            </div>
          )}
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 4, marginBottom: -4 }}>대상 클러스터</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-row">
              <label className="form-label">Server</label>
              <input className="input" value={form.dest_server} onChange={e => set('dest_server', e.target.value)} placeholder="https://kubernetes.default.svc" />
            </div>
            <div className="form-row">
              <label className="form-label">Namespace</label>
              <input className="input" value={form.dest_namespace} onChange={e => set('dest_namespace', e.target.value)} placeholder="default" />
            </div>
          </div>
          {error && <div style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid #7f1d1d', borderRadius: 5, padding: '8px 12px', fontSize: 12 }}>{error}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-default" onClick={onClose}>취소</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? <><div className="spinner" style={{ width: 13, height: 13 }} />저장 중...</> : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── 롤백 모달 ─────────────────────────────────────────────────────────────────
function RollbackModal({ app, onClose, onRollback }) {
  const history = app?.history || []
  const [sel, setSel]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')

  async function handleRollback() {
    if (sel == null) return
    setLoading(true); setError('')
    try {
      const res = await api.rollbackArgoApp(app.namespace, app.name, sel)
      if (res?.ok === false) setError(res.error || '롤백 실패')
      else { onRollback(); onClose() }
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ width: 500 }}>
        <div className="modal-header">
          <h2>↩ 롤백 — {app.name}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={14} /></button>
        </div>
        <div className="modal-body">
          {history.length === 0 ? (
            <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>배포 이력이 없습니다.</div>
          ) : (
            <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
              <table className="data-table">
                <thead><tr><th>ID</th><th>Revision</th><th>배포 시각</th><th></th></tr></thead>
                <tbody>
                  {[...history].reverse().map((h, i) => (
                    <tr key={i} className={sel === h.id ? 'selected' : ''} onClick={() => setSel(h.id)} style={{ cursor: 'pointer' }}>
                      <td className="mono" style={{ fontSize: 11 }}>{h.id}</td>
                      <td className="mono" style={{ fontSize: 11 }}>{h.revision?.slice(0, 8) || '—'}</td>
                      <td style={{ fontSize: 11, color: 'var(--text-dim)' }}>{h.deployed_at || '—'}</td>
                      <td>{sel === h.id && <span className="chip chip-green">선택됨</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {error && <div style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid #7f1d1d', borderRadius: 5, padding: '8px 12px', fontSize: 12, marginTop: 8 }}>{error}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-default" onClick={onClose}>취소</button>
          <button className="btn btn-primary" onClick={handleRollback} disabled={sel == null || loading}>
            {loading ? <><div className="spinner" style={{ width: 13, height: 13 }} />롤백 중...</> : '롤백'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── 삭제 확인 모달 ────────────────────────────────────────────────────────────
function DeleteConfirm({ app, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onCancel()}>
      <div className="modal" style={{ width: 400 }}>
        <div className="modal-header">
          <h2 style={{ color: 'var(--red)' }}>🗑 앱 삭제</h2>
          <button className="btn btn-ghost btn-sm" onClick={onCancel}><X size={14} /></button>
        </div>
        <div className="modal-body">
          <p style={{ fontSize: 13, color: 'var(--text)' }}>
            <strong style={{ color: 'var(--text-bright)' }}>{app.name}</strong> 앱을 삭제하시겠습니까?
          </p>
          <p style={{ fontSize: 12, color: 'var(--red)', marginTop: 8 }}>
            ⚠ ArgoCD Application CR이 삭제됩니다. 배포된 리소스는 유지됩니다.
          </p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-default" onClick={onCancel}>취소</button>
          <button className="btn btn-danger" onClick={onConfirm}>삭제</button>
        </div>
      </div>
    </div>
  )
}

// ── Sync 확인 모달 (운영 실수 방지) ──────────────────────────────────────────
function SyncConfirm({ app, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onCancel()}>
      <div className="modal" style={{ width: 420 }}>
        <div className="modal-header">
          <h2 style={{ color: 'var(--nimbus)' }}>↻ Sync 실행</h2>
          <button className="btn btn-ghost btn-sm" onClick={onCancel}><X size={14} /></button>
        </div>
        <div className="modal-body">
          <p style={{ fontSize: 13, color: 'var(--text)' }}>
            <strong style={{ color: 'var(--text-bright)' }}>{app.name}</strong> 앱을 동기화하시겠습니까?
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 8, lineHeight: 1.5 }}>
            현재 Git 상태({app.targetRevision || app.revision || 'HEAD'})를 클러스터에 적용합니다.
            실행 중인 워크로드가 재시작될 수 있습니다.
          </p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-default" onClick={onCancel}>취소</button>
          <button className="btn btn-primary" onClick={onConfirm}>Sync 실행</button>
        </div>
      </div>
    </div>
  )
}

// ── 앱 상세 사이드 패널 ───────────────────────────────────────────────────────
function DetailPanel({ app, onClose }) {
  const history = app?.history || []
  function Row({ label, value }) {
    return (
      <div style={{ display: 'flex', gap: 8, padding: '5px 0', borderBottom: '1px solid var(--border)', fontSize: 12 }}>
        <span style={{ color: 'var(--text-dim)', width: 110, flexShrink: 0 }}>{label}</span>
        <span className="mono truncate" style={{ color: 'var(--text-bright)' }}>{value || '—'}</span>
      </div>
    )
  }
  return (
    <div style={{ width: 300, borderLeft: '1px solid var(--border)', background: 'var(--bg-1)', display: 'flex', flexDirection: 'column', flexShrink: 0, overflowY: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid var(--border)', fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>
        <span className="truncate">{app.name}</span>
        <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={13} /></button>
      </div>
      <div style={{ padding: '12px 14px', flex: 1 }}>
        <Row label="네임스페이스" value={app.namespace} />
        <Row label="프로젝트" value={app.project} />
        <Row label="Sync 상태" value={app.sync} />
        <Row label="Health" value={app.health} />
        <Row label="Repo" value={app.repo} />
        <Row label="Revision" value={app.revision} />
        <Row label="Path" value={app.path} />
        <Row label="소스 수" value={app.source_count > 1 ? `${app.source_count}개` : '1개'} />
        <Row label="대상 Server" value={app.dest_server} />
        <Row label="대상 NS" value={app.dest_namespace} />
        {app.source_count > 1 && (
          <>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 16, marginBottom: 8 }}>Sources</div>
            {(app.sources || []).map((src, i) => (
              <div key={i} style={{ background: 'var(--bg-2)', borderRadius: 5, padding: '6px 10px', marginBottom: 6, fontSize: 11 }}>
                <div className="mono" style={{ color: 'var(--text-bright)', wordBreak: 'break-all' }}>{src.repoURL || '-'}</div>
                <div className="mono" style={{ color: 'var(--text-dim)', marginTop: 2 }}>{src.path || src.chart || src.ref || '-'} @ {src.targetRevision || 'HEAD'}</div>
              </div>
            ))}
          </>
        )}
        {history.length > 0 && (
          <>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 16, marginBottom: 8 }}>배포 이력</div>
            {[...history].reverse().slice(0, 5).map((h, i) => (
              <div key={i} style={{ background: 'var(--bg-2)', borderRadius: 5, padding: '6px 10px', marginBottom: 6, fontSize: 11 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-dim)' }}>#{h.id}</span>
                  <span className="mono" style={{ color: 'var(--text-bright)' }}>{h.revision?.slice(0, 8) || '?'}</span>
                </div>
                {h.deployed_at && <div style={{ color: 'var(--text-dim)', marginTop: 2 }}>{h.deployed_at}</div>}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}

// ── 앱 카드 ──────────────────────────────────────────────────────────────────
function AppCard({ app, selected, onSelect, onSync, onEdit, onRollback, onDelete, syncing }) {
  const isSel    = selected === app
  const syncOk   = app.sync === 'Synced'
  const healthOk = app.health === 'Healthy' || app.health === 'Progressing'
  return (
    <div
      onClick={() => onSelect(app)}
      style={{
        background: isSel ? 'rgba(52,211,153,0.06)' : 'var(--bg-2)',
        border: `1px solid ${isSel ? 'var(--nimbus)' : 'var(--border)'}`,
        borderRadius: 10, padding: '14px 16px', cursor: 'pointer',
        display: 'flex', flexDirection: 'column', gap: 8,
        transition: 'border-color 0.15s, background 0.15s',
      }}
    >
      {/* 이름 + 상태 */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
          {app.name}
        </div>
        <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
          <span className={`chip ${syncOk ? 'chip-green' : 'chip-yellow'}`}>{app.sync || '—'}</span>
          <span className={`chip ${healthOk ? 'chip-green' : app.health ? 'chip-red' : 'chip-dim'}`}>{app.health || '—'}</span>
        </div>
      </div>

      {/* 프로젝트 + 네임스페이스 */}
      <div style={{ fontSize: 11, color: 'var(--text-dim)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <span style={{ color: 'var(--purple)' }}>{app.project || 'default'}</span>
        <span>·</span>
        <span style={{ fontFamily: 'var(--font-mono)' }}>{app.namespace}</span>
      </div>

      {/* Repo */}
      {app.repo && (
        <div style={{ fontSize: 10.5, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {app.repo}
        </div>
      )}

      {/* 액션 버튼 */}
      <div style={{ display: 'flex', gap: 4, marginTop: 2, flexWrap: 'wrap' }}
        onClick={e => e.stopPropagation()}>
        <button className="btn btn-ghost btn-sm" onClick={() => onSync(app)} disabled={syncing && selected === app} style={{ fontSize: 10 }}>
          <RefreshCcw size={10} />Sync
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => onEdit(app)} style={{ fontSize: 10 }}>
          <Pencil size={10} />수정
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => onRollback(app)} style={{ fontSize: 10 }}>
          <RotateCcw size={10} />롤백
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => onDelete(app)} style={{ fontSize: 10, color: 'var(--red)' }}>
          <Trash2 size={10} />삭제
        </button>
      </div>
    </div>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────
export default function ArgoPage() {
  const { connected } = useApp()
  const [rows, setRows]           = useState([])
  const [loading, setLoading]     = useState(false)
  const [selected, setSelected]   = useState(null)
  const [modal, setModal]         = useState(null)
  const [toast, setToast]         = useState(null)
  const [syncing, setSyncing]     = useState(false)
  const [filterStatus, setFilterStatus] = useState('All')
  const [filterProject, setFilterProject] = useState('')
  const [filterSearch, setFilterSearch]   = useState('')

  const load = useCallback(async () => {
    if (!connected) return
    setLoading(true)
    setSelected(null)
    try {
      const data = await api.getArgoApps()
      setRows(Array.isArray(data) ? data : [])
    } catch { setRows([]) }
    setLoading(false)
  }, [connected])

  useEffect(() => { load() }, [load])

  function showToast(msg, type = 'ok') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  // 보안 — Sync 즉시 실행 대신 확인 모달을 거치도록 (운영 실수 방지)
  function requestSync(app) {
    const target = app || selected
    if (!target) return
    setSelected(target)
    setModal('sync')
  }

  async function handleSyncConfirm() {
    const target = selected
    if (!target) return
    setModal(null)
    setSyncing(true)
    try {
      const res = await api.syncArgoApp(target.namespace, target.name)
      if (res?.ok === false) showToast(res.error || 'Sync 실패', 'err')
      else { showToast(`${target.name} Sync 요청 완료`); setTimeout(load, 1500) }
    } catch (e) { showToast(String(e), 'err') }
    setSyncing(false)
  }

  async function handleDeleteConfirm() {
    if (!selected) return
    try {
      const res = await api.deleteArgoApp(selected.namespace, selected.name)
      if (res?.ok === false) showToast(res.error || '삭제 실패', 'err')
      else { showToast(`${selected.name} 삭제 완료`); setModal(null); load() }
    } catch (e) { showToast(String(e), 'err'); setModal(null) }
  }

  // KPI 카운트
  const synced   = rows.filter(r => r.sync === 'Synced').length
  const outSync  = rows.filter(r => r.sync === 'OutOfSync').length
  const healthy  = rows.filter(r => r.health === 'Healthy').length
  const degraded = rows.filter(r => r.health && r.health !== 'Healthy' && r.health !== 'Progressing').length

  // 고유 프로젝트 목록
  const projects = [...new Set(rows.map(r => r.project).filter(Boolean))]

  // 필터 적용
  const filtered = rows.filter(r => {
    if (filterStatus === 'Synced'    && r.sync   !== 'Synced')    return false
    if (filterStatus === 'OutOfSync' && r.sync   !== 'OutOfSync') return false
    if (filterStatus === 'Degraded'  && (r.health === 'Healthy' || r.health === 'Progressing')) return false
    if (filterProject && r.project !== filterProject) return false
    if (filterSearch  && !r.name.toLowerCase().includes(filterSearch.toLowerCase())) return false
    return true
  })

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <span style={{ fontSize: 32, opacity: 0.3 }}>⎈</span>
      <p>클러스터에 연결되지 않았습니다.</p>
    </div>
  )

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── 왼쪽 필터 사이드바 ── */}
      <div style={{
        width: 180, flexShrink: 0,
        borderRight: '1px solid var(--border)',
        background: 'var(--bg-1)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        {/* 타이틀 */}
        <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{ fontSize: 16 }}>⎈</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-bright)' }}>ArgoCD</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
            {rows.length}개 앱
          </div>
        </div>

        {/* 검색 */}
        <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ position: 'relative' }}>
            <Search size={11} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }} />
            <input
              className="input"
              value={filterSearch}
              onChange={e => setFilterSearch(e.target.value)}
              placeholder="앱 검색..."
              style={{ width: '100%', paddingLeft: 26, fontSize: 11 }}
            />
          </div>
        </div>

        {/* Sync 상태 필터 */}
        <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 7 }}>Sync 상태</div>
          {['All', 'Synced', 'OutOfSync', 'Degraded'].map(s => {
            const count = s === 'All' ? rows.length : s === 'Synced' ? synced : s === 'OutOfSync' ? outSync : degraded
            const active = filterStatus === s
            return (
              <button key={s} onClick={() => setFilterStatus(s)} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                width: '100%', padding: '4px 8px', marginBottom: 2,
                background: active ? 'rgba(52,211,153,0.1)' : 'transparent',
                border: `1px solid ${active ? 'rgba(52,211,153,0.25)' : 'transparent'}`,
                borderRadius: 5, cursor: 'pointer',
                fontSize: 11, color: active ? 'var(--nimbus)' : 'var(--text-dim)',
                fontWeight: active ? 600 : 400,
              }}>
                <span>{s === 'All' ? '전체' : s}</span>
                <span style={{ fontSize: 10, opacity: 0.7, fontVariantNumeric: 'tabular-nums' }}>{count}</span>
              </button>
            )
          })}
        </div>

        {/* 프로젝트 필터 */}
        {projects.length > 0 && (
          <div style={{ padding: '10px 12px', flex: 1, overflowY: 'auto' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 7 }}>프로젝트</div>
            <button onClick={() => setFilterProject('')} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              width: '100%', padding: '4px 8px', marginBottom: 2,
              background: !filterProject ? 'rgba(52,211,153,0.1)' : 'transparent',
              border: `1px solid ${!filterProject ? 'rgba(52,211,153,0.25)' : 'transparent'}`,
              borderRadius: 5, cursor: 'pointer',
              fontSize: 11, color: !filterProject ? 'var(--nimbus)' : 'var(--text-dim)',
              fontWeight: !filterProject ? 600 : 400,
            }}>
              <span>전체</span>
              <span style={{ fontSize: 10, opacity: 0.7 }}>{rows.length}</span>
            </button>
            {projects.map(p => {
              const cnt = rows.filter(r => r.project === p).length
              const active = filterProject === p
              return (
                <button key={p} onClick={() => setFilterProject(active ? '' : p)} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  width: '100%', padding: '4px 8px', marginBottom: 2,
                  background: active ? 'rgba(52,211,153,0.1)' : 'transparent',
                  border: `1px solid ${active ? 'rgba(52,211,153,0.25)' : 'transparent'}`,
                  borderRadius: 5, cursor: 'pointer',
                  fontSize: 11, color: active ? 'var(--nimbus)' : 'var(--text-dim)',
                  fontWeight: active ? 600 : 400, textAlign: 'left',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{p}</span>
                  <span style={{ fontSize: 10, opacity: 0.7, flexShrink: 0, marginLeft: 4 }}>{cnt}</span>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* ── 메인 영역 ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* 툴바 */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 16px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-1)', flexShrink: 0,
        }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>
            {filterStatus !== 'All' || filterProject || filterSearch
              ? `${filtered.length}개 / 전체 ${rows.length}개`
              : `${rows.length}개 앱`}
          </span>
          <span style={{ flex: 1 }} />
          <button className="btn btn-primary btn-sm" onClick={() => setModal('create')} style={{ gap: 4 }}>
            <Plus size={12} />생성
          </button>
          <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            새로고침
          </button>
        </div>

        {/* KPI 스트립 */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10,
          padding: '12px 16px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-1)', flexShrink: 0,
        }}>
          {[
            { label: '전체 앱',   value: rows.length,  color: 'var(--text-bright)' },
            { label: 'Synced',    value: synced,        color: 'var(--green)'       },
            { label: 'OutOfSync', value: outSync,       color: 'var(--yellow)'      },
            { label: 'Degraded',  value: degraded,      color: degraded > 0 ? 'var(--red)' : 'var(--text-dim)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px' }}>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color, fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em' }}>{value}</div>
            </div>
          ))}
        </div>

        {/* 앱 카드 그리드 + 상세 패널 */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            {loading ? (
              <div className="empty-state" style={{ height: '100%', minHeight: 200 }}>
                <div className="spinner" /><span>불러오는 중...</span>
              </div>
            ) : filtered.length === 0 ? (
              <div className="empty-state" style={{ minHeight: 200 }}>
                <span style={{ fontSize: 28, opacity: 0.3 }}>⎈</span>
                <p>{rows.length === 0 ? 'ArgoCD Application이 없습니다.' : '필터 조건에 맞는 앱이 없습니다.'}</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                {filtered.map(app => (
                  <AppCard
                    key={app.name + app.namespace}
                    app={app}
                    selected={selected}
                    syncing={syncing}
                    onSelect={a => setSelected(prev => prev === a ? null : a)}
                    onSync={requestSync}
                    onEdit={a => { setSelected(a); setModal('edit') }}
                    onRollback={a => { setSelected(a); setModal('rollback') }}
                    onDelete={a => { setSelected(a); setModal('delete') }}
                  />
                ))}
              </div>
            )}
          </div>

          {/* 상세 패널 */}
          {selected && modal === null && (
            <DetailPanel app={selected} onClose={() => setSelected(null)} />
          )}
        </div>
      </div>

      {/* 모달 */}
      {(modal === 'create' || modal === 'edit') && (
        <AppFormModal mode={modal} app={selected} onClose={() => setModal(null)} onSave={load} />
      )}
      {modal === 'delete' && selected && (
        <DeleteConfirm app={selected} onConfirm={handleDeleteConfirm} onCancel={() => setModal(null)} />
      )}
      {modal === 'sync' && selected && (
        <SyncConfirm app={selected} onConfirm={handleSyncConfirm} onCancel={() => setModal(null)} />
      )}
      {modal === 'rollback' && selected && (
        <RollbackModal app={selected} onClose={() => setModal(null)} onRollback={load} />
      )}

      {/* 토스트 */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 40, left: '50%', transform: 'translateX(-50%)',
          background: toast.type === 'err' ? 'var(--red-bg)' : 'var(--bg-4)',
          color: toast.type === 'err' ? 'var(--red)' : 'var(--green)',
          border: `1px solid ${toast.type === 'err' ? '#7f1d1d' : 'var(--border-bright)'}`,
          borderRadius: 6, padding: '8px 18px', fontSize: 12,
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)', zIndex: 9999,
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
