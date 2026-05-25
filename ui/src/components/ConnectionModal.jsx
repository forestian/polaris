import React, { useState, useCallback } from 'react'
import { useApp } from '../store.jsx'
import { api } from '../api.js'
import { FolderOpen, X, Loader, Check } from 'lucide-react'

export default function ConnectionModal() {
  const { setShowConnect, addCluster } = useApp()

  const [path, setPath]           = useState('')
  const [ctxList, setCtxList]     = useState(null)   // null=미조회 | string[]
  const [currentCtx, setCurrentCtx] = useState('')
  const [selected, setSelected]   = useState(new Set())
  const [ctxLoading, setCtxLoading] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError]         = useState('')

  // ── 컨텍스트 목록 조회 — 성공 시 {contexts, current, initialSelected} 반환, 실패 시 null ──
  const loadContexts = useCallback(async (p) => {
    const target = (typeof p === 'string' ? p : path).trim()
    if (!target) { setError('kubeconfig 경로를 선택하세요.'); return null }
    setCtxLoading(true); setError(''); setCtxList(null); setSelected(new Set())
    const res = await api.listKubeconfigContexts(target)
    setCtxLoading(false)
    if (!res?.ok) { setError(res?.error || '컨텍스트 불러오기 실패'); return null }
    if (!res.contexts?.length) { setError('kubeconfig에 컨텍스트가 없습니다.'); return null }
    const initialSelected = new Set(res.current ? [res.current] : [res.contexts[0]])
    setCtxList(res.contexts)
    setCurrentCtx(res.current || '')
    setSelected(initialSelected)
    return { contexts: res.contexts, current: res.current || '', initialSelected }
  }, [path])

  // ── 파일 탐색 ─────────────────────────────────────────────────────────────
  async function browse() {
    try {
      const p = await api.browseKubeconfig()
      if (!p) return
      setPath(p)
      setCtxList(null); setSelected(new Set()); setError('')
      await loadContexts(p)
    } catch (e) {
      setError(String(e))
    }
  }

  // ── path 직접 수정 시 컨텍스트 초기화 ────────────────────────────────────
  function handlePathChange(e) {
    setPath(e.target.value)
    setCtxList(null); setSelected(new Set()); setError('')
  }

  // ── 체크박스 토글 ─────────────────────────────────────────────────────────
  function toggleCtx(ctx) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(ctx)) next.delete(ctx)
      else next.add(ctx)
      return next
    })
  }

  // ── 연결 실행 ─────────────────────────────────────────────────────────────
  async function connect() {
    // 컨텍스트 미조회 상태: 먼저 조회
    if (!ctxList) {
      const data = await loadContexts()
      if (!data) return
      // 단일 컨텍스트: 바로 연결 (목록 없이 기존처럼 동작)
      if (data.contexts.length === 1) {
        await doConnect(data.initialSelected)
      }
      // 복수 컨텍스트: 목록 표시 후 사용자가 다시 연결 버튼 클릭
      return
    }
    await doConnect(selected)
  }

  async function doConnect(ctxSet) {
    if (ctxSet.size === 0) { setError('연결할 컨텍스트를 선택하세요.'); return }
    setConnecting(true); setError('')
    let successCount = 0
    let lastError = ''
    for (const ctx of ctxSet) {
      const result = await addCluster(path.trim(), ctx)
      if (result?.ok) successCount++
      else lastError = result?.error || '연결 실패'
    }
    setConnecting(false)
    if (successCount > 0) {
      setShowConnect(false)
    } else {
      setError(lastError)
    }
  }

  const canConnect = !ctxLoading && !connecting
  const btnLabel = connecting
    ? '연결 중...'
    : ctxList && selected.size > 1
      ? `${selected.size}개 연결`
      : '연결'

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowConnect(false)}>
      <div className="modal">
        <div className="modal-header">
          <h2>⎈ 클러스터 연결</h2>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowConnect(false)}>
            <X size={14} />
          </button>
        </div>

        <div className="modal-body">
          {/* ── 경로 입력 ── */}
          <div className="form-row">
            <label className="form-label">kubeconfig 경로</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                className="input"
                value={path}
                onChange={handlePathChange}
                placeholder="경로를 입력하거나 탐색..."
                onKeyDown={e => e.key === 'Enter' && !ctxList && loadContexts()}
                style={{ flex: 1 }}
              />
              <button className="btn btn-default" onClick={browse}>
                <FolderOpen size={13} />
              </button>
            </div>
            {/* 직접 입력 시 수동 조회 버튼 */}
            {path && !ctxList && !ctxLoading && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => loadContexts()}
                style={{ marginTop: 6, alignSelf: 'flex-start', fontSize: 11 }}
              >
                컨텍스트 불러오기
              </button>
            )}
          </div>

          {/* ── 로딩 표시 ── */}
          {ctxLoading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8,
              marginTop: 10, color: 'var(--text-dim)', fontSize: 12 }}>
              <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} />
              컨텍스트 목록 조회 중...
            </div>
          )}

          {/* ── 컨텍스트 선택 ── */}
          {ctxList && ctxList.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <div style={{
                fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '0.06em', color: 'var(--text-dim)', marginBottom: 6,
              }}>
                연결할 컨텍스트 선택 {ctxList.length > 1 && (
                  <span style={{ fontWeight: 400, textTransform: 'none',
                    letterSpacing: 0, color: 'var(--text-mid)' }}>
                    — {ctxList.length}개 감지됨
                  </span>
                )}
              </div>
              <div style={{
                border: '1px solid var(--border)',
                borderRadius: 6,
                overflow: 'hidden',
                maxHeight: 200,
                overflowY: 'auto',
              }}>
                {ctxList.map((ctx, i) => {
                  const isCurrent = ctx === currentCtx
                  const isChecked = selected.has(ctx)
                  return (
                    <label
                      key={ctx}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '8px 12px',
                        cursor: 'pointer',
                        background: isChecked ? 'rgba(52,211,153,0.06)' : 'transparent',
                        borderTop: i > 0 ? '1px solid var(--border)' : 'none',
                        transition: 'background 0.1s',
                      }}
                    >
                      {/* 커스텀 체크박스 */}
                      <div style={{
                        width: 16, height: 16, borderRadius: 3, flexShrink: 0,
                        border: `2px solid ${isChecked ? 'var(--nimbus)' : 'var(--border-bright)'}`,
                        background: isChecked ? 'var(--nimbus)' : 'transparent',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'all 0.1s',
                      }}>
                        {isChecked && <Check size={10} color="#000" strokeWidth={3} />}
                      </div>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleCtx(ctx)}
                        style={{ display: 'none' }}
                      />
                      <span style={{
                        fontSize: 12.5, flex: 1,
                        color: isChecked ? 'var(--text-bright)' : 'var(--text)',
                        fontFamily: 'var(--font-mono)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {ctx}
                      </span>
                      {isCurrent && (
                        <span style={{
                          fontSize: 10, color: 'var(--nimbus)',
                          background: 'rgba(52,211,153,0.12)',
                          padding: '1px 6px', borderRadius: 3,
                          border: '1px solid rgba(52,211,153,0.25)',
                          flexShrink: 0,
                        }}>
                          current
                        </span>
                      )}
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {/* ── 에러 ── */}
          {error && (
            <div style={{
              background: 'var(--red-bg)', color: 'var(--red)',
              border: '1px solid #7f1d1d', borderRadius: 5,
              padding: '8px 12px', fontSize: 12, marginTop: 10,
              whiteSpace: 'pre-wrap', lineHeight: 1.7,
            }}>
              {error}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-default" onClick={() => setShowConnect(false)}>
            취소
          </button>
          <button
            className="btn btn-primary"
            onClick={connect}
            disabled={!canConnect || (ctxList !== null && selected.size === 0)}
          >
            {(connecting || ctxLoading) && (
              <div className="spinner" style={{ width: 13, height: 13 }} />
            )}
            {btnLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
